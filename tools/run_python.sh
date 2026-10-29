#!/usr/bin/env bash
# Run one of the repo's Python scripts in the project environment.
# Used by the root scripts (lna_sparams.sh, bac_nf.sh, ...).
#
# Usage: tools/run_python.sh <script relative to repo root> [args...]
#
# Picks the Python to use, in order:
#   1. an activated virtual environment (including one started by `uv run`)
#   2. uv, if installed (creates/updates .venv from uv.lock as needed)
#   3. the repo's .venv, if it already exists
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
script="$REPO/$1"
shift

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    exec "$VIRTUAL_ENV/bin/python" "$script" "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run --project "$REPO" python "$script" "$@"
elif [[ -x "$REPO/.venv/bin/python" ]]; then
    exec "$REPO/.venv/bin/python" "$script" "$@"
else
    echo "No Python environment found. Either:" >&2
    echo "  - install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    echo "  - or create the environment once with uv (uv sync) and activate it:" >&2
    echo "      source .venv/bin/activate" >&2
    exit 1
fi
