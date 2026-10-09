#!/usr/bin/env bash
# Analyze backboard noise-figure measurements (Y-factor, ENR noise source).
# Reads BB/noise_figure/data/, writes plots to BB/noise_figure/plots/
# and results to BB/noise_figure/nf_log.csv. See tools/noise_figure/README.md.
#
# Usage: ./bac_nf.sh -b BAC00018P1 --save-plot   # one measurement
#        ./bac_nf.sh --all                       # every measurement
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install it with:" >&2
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec uv run python tools/noise_figure/nf.py --device bac "$@"
