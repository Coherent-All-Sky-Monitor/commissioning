#!/usr/bin/env bash
# Measure LNA S-parameters (LNA#####P1/P2) with the LibreVNA.
# Results are saved to LNA/s_params/. See tools/vna/README.md for setup.
#
# Usage: ./lna_sparams.sh [--headless]
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install it with:" >&2
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec uv run python tools/vna/sparams.py --device lna "$@"
