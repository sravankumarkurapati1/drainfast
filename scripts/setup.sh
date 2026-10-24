#!/usr/bin/env bash
# One-shot local setup for macOS: checks tools, creates/reuses .venv,
# installs Python and frontend dependencies. Safe to rerun (idempotent).
# Compatible with macOS /bin/bash 3.2.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"

# step <name> <command...>: run the command; on failure name the step and
# exit with the command's status, skipping all later steps.
step() {
  local name="$1"
  shift
  local rc=0
  note "==> $name"
  "$@" || rc=$?
  if [ "$rc" -ne 0 ]; then
    printf 'setup failed at: %s\n' "$name" >&2
    exit "$rc"
  fi
}

# 1. Tool checks: collect every missing tool before touching anything.
missing=""
if ! command -v python3.11 >/dev/null 2>&1; then
  missing="${missing}brew install python@3.11
"
fi
if ! command -v node >/dev/null 2>&1; then
  missing="${missing}brew install node
"
fi
if [ -n "$missing" ]; then
  printf 'Missing required tools. Install them with:\n%s' "$missing" >&2
  exit 1
fi

# 2. Venv: create if absent, otherwise validate it is Python 3.11 (never modify it).
if [ ! -e .venv ]; then
  step "create venv" python3.11 -m venv .venv
else
  venv_version=""
  if [ -x .venv/bin/python ]; then
    venv_version="$(.venv/bin/python -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || true)"
  fi
  if [ "$venv_version" != "3.11" ]; then
    die "Existing .venv is invalid (expected Python 3.11, found: ${venv_version:-no working .venv/bin/python}). Remove .venv and rerun ./scripts/setup.sh"
  fi
  note "Reusing existing .venv (Python 3.11)"
fi

# 3. Required manifests.
[ -f requirements.txt ] || { printf 'setup failed at: pip install (requirements.txt not found)\n' >&2; exit 1; }
[ -f frontend/package.json ] || { printf 'setup failed at: npm install (frontend/package.json not found)\n' >&2; exit 1; }

# 4. Dependencies.
step "pip install" .venv/bin/python -m pip install -r requirements.txt
step "npm install" npm --prefix frontend install

# 5. Done.
note "Setup complete."
note "Next: ./scripts/dev.sh"
