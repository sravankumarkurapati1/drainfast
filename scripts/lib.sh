#!/usr/bin/env bash
# Shared helpers for scripts/setup.sh, scripts/dev.sh and scripts/prod_local.sh.
# Sourced, not executed. Must stay compatible with macOS /bin/bash 3.2:
# no `wait -n`, `mapfile`, associative arrays or `${var,,}`; safe under `set -u`.

set -Eeuo pipefail

# Repository root: parent of the directory holding this file, independent of cwd.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# die <message...>: print to stderr and exit 1.
die() {
  printf '%s\n' "$*" >&2
  exit 1
}

# note <message...>: informational message on stdout.
note() {
  printf '%s\n' "$*"
}

# port_owner <port>: print "port <port> busy: <command> (PID <pid>)" for each
# process listening on TCP <port>. Returns 0 if busy, 1 if free.
port_owner() {
  local port="${1:?port_owner: port required}"
  local out line pid="" busy=1
  out="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -Fpc 2>/dev/null || true)"
  # lsof -F output: "p<pid>" starts a process record, "c<command>" follows it.
  while IFS= read -r line; do
    case "$line" in
      p*) pid="${line#p}" ;;
      c*)
        if [ -n "$pid" ]; then
          printf 'port %s busy: %s (PID %s)\n' "$port" "${line#c}" "$pid"
          busy=0
          pid=""
        fi
        ;;
    esac
  done <<EOF
$out
EOF
  return "$busy"
}

# require_venv: die unless the project venv exists at $REPO_ROOT/.venv.
require_venv() {
  [ -f "$REPO_ROOT/.venv/bin/activate" ] ||
    die "Python venv not found at .venv — run ./scripts/setup.sh first"
}
