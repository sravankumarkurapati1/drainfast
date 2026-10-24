#!/usr/bin/env bash
# Production-like local run: build frontend/dist, then serve it plus the API
# from `make api` on http://localhost:8000. macOS /bin/bash 3.2 compatible.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

cd "$REPO_ROOT"

# Preconditions, all checked before any build step (Req 7.1, 7.4, 7.6, 7.7).
require_venv
[ -d frontend ] || die "frontend/ directory not found at $REPO_ROOT/frontend"
command -v npm >/dev/null 2>&1 || die "npm not found on PATH — install Node.js (e.g. brew install node)"

if busy="$(port_owner 8000)"; then
  printf '%s\n' "$busy" >&2
  die "Port 8000 is in use; stop that process and re-run ./scripts/prod_local.sh"
fi

# Checked before the build so a missing backend doesn't waste a build.
[ -f backend/app.py ] ||
  die "Production-like mode needs the backend (backend/app.py), which serves frontend/dist and the API. It does not exist yet; use ./scripts/dev.sh meanwhile."

# Empty (not unset) so it overrides any VITE_API_URL in frontend/.env.local (Req 7.1).
VITE_API_URL= npm --prefix frontend run build || die "frontend build failed"

# activate references unset variables, so relax -u around it.
set +u
# shellcheck disable=SC1091
source .venv/bin/activate
set -u

# Only pass fallback through when explicitly 1 (Req 7.5).
if [ "${DRAINFAST_FALLBACK:-}" = "1" ]; then
  export DRAINFAST_FALLBACK=1
  note "Fallback mode on (DRAINFAST_FALLBACK=1)"
else
  unset DRAINFAST_FALLBACK
fi

note "DrainFast (production-like): open http://localhost:8000"
# exec hands Ctrl+C straight to make/uvicorn (Req 7.8).
exec make api
