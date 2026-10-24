#!/usr/bin/env bash
# DrainFast development runner: local API (port 8000) + Vite frontend (port 5173).
# Usage: ./scripts/dev.sh   (Ctrl+C stops everything)
# Compatible with macOS /bin/bash 3.2 (no `wait -n`).

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

cd "$REPO_ROOT"

# --- Venv (Req 6.1, 6.2) ----------------------------------------------------
require_venv
# Activate scripts may reference unset variables; relax nounset around it.
set +u
# shellcheck disable=SC1091
source .venv/bin/activate
set -u

if [ "${DRAINFAST_FALLBACK:-}" = "1" ]; then
  note "DRAINFAST_FALLBACK=1: API and pipeline steps run in fallback mode"
fi

# --- Port checks (Req 6.3) ---------------------------------------------------
busy=0
for port in 8000 5173; do
  if port_owner "$port" >&2; then
    busy=1
  fi
done
[ "$busy" -eq 0 ] || die "free the port(s) above and rerun ./scripts/dev.sh"

# --- Pipeline (Req 6.4–6.7) --------------------------------------------------
need_pipeline=0
for f in cells.parquet reports.parquet flood_area.geojson; do
  [ -f "data/demo/$f" ] || need_pipeline=1
done

if [ "$need_pipeline" -eq 1 ]; then
  for entry in data:data_pipeline/run.py cells:data_pipeline/cells.py model:model/run.py; do
    step="${entry%%:*}"
    module="${entry#*:}"
    if [ ! -f "$module" ]; then
      note "skipping make $step ($module not found)"
      continue
    fi
    note "running make $step"
    rc=0
    make "$step" || rc=$?
    if [ "$rc" -ne 0 ]; then
      printf 'make %s failed (exit %s)\n' "$step" "$rc" >&2
      exit "$rc"
    fi
  done
else
  note "using existing demo data in data/demo"
fi

# --- Frontend checks (Req 6.11, before any server starts) --------------------
[ -f frontend/package.json ] || die "frontend not set up — run ./scripts/setup.sh"
[ -d frontend/node_modules ] ||
  die "frontend dependencies missing (frontend/node_modules) — run ./scripts/setup.sh"

# --- Process supervision -----------------------------------------------------
API_PID=""
WEB_PID=""
CLEANED=0

# stop_group <pid>: TERM the process group led by <pid> (fallback: the pid).
stop_group() {
  kill -TERM -- "-$1" 2>/dev/null || kill -TERM "$1" 2>/dev/null || true
}

# group_alive <pid>: true while any process in the group (or the pid) lives.
group_alive() {
  kill -0 -- "-$1" 2>/dev/null || kill -0 "$1" 2>/dev/null
}

cleanup() {
  [ "$CLEANED" -eq 0 ] || return 0
  CLEANED=1
  local pid i alive
  for pid in $API_PID $WEB_PID; do
    stop_group "$pid"
  done
  # Poll up to 4 s (40 x 0.1 s) for graceful shutdown.
  i=0
  while [ "$i" -lt 40 ]; do
    alive=0
    for pid in $API_PID $WEB_PID; do
      if group_alive "$pid"; then alive=1; fi
    done
    [ "$alive" -eq 1 ] || break
    sleep 0.1
    i=$((i + 1))
  done
  # KILL anything still running.
  for pid in $API_PID $WEB_PID; do
    if group_alive "$pid"; then
      kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  done
}

on_interrupt() {
  trap - INT TERM
  note ""
  note "stopping DrainFast dev..."
  cleanup
  note "stopped."
  exit 0
}

trap on_interrupt INT TERM
trap cleanup EXIT

# Job control gives each background job its own process group, so the whole
# tree (uvicorn reloader + worker, npm + vite) can be signalled at once.
# stdin is /dev/null so background jobs never stop on terminal reads (SIGTTIN).
set -m
if [ -f backend/app.py ]; then
  make api </dev/null &
  API_PID=$!
else
  note "backend/app.py not found — frontend will use demo fixtures (demo data badge)"
fi
npm --prefix frontend run dev </dev/null &
WEB_PID=$!
# Back to no job control so Ctrl+C reaches this script (the foreground group).
set +m

note ""
note "DrainFast dev: open http://localhost:5173"
if [ -n "$API_PID" ]; then
  note "API at http://localhost:8000"
fi
note "Press Ctrl+C to stop."

# Supervise (Req 6.12): bash 3.2 has no `wait -n`, so poll once a second.
while :; do
  if [ -n "$API_PID" ] && ! kill -0 "$API_PID" 2>/dev/null; then
    printf 'API (make api) exited; stopping frontend\n' >&2
    cleanup
    exit 1
  fi
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    printf 'frontend (npm run dev) exited; stopping API\n' >&2
    cleanup
    exit 1
  fi
  sleep 1
done
