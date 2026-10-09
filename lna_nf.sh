#!/usr/bin/env bash
# Analyze LNA noise-figure measurements (Y-factor, hot/cold loads).
# Reads LNA/noise_figure/data/, writes plots to LNA/noise_figure/plots/
# and results to LNA/noise_figure/nf_log.csv. See tools/noise_figure/README.md.
#
# Usage: ./lna_nf.sh -b lna173 --save-plot   # one measurement
#        ./lna_nf.sh --all                   # every measurement
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install it with:" >&2
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec uv run python tools/noise_figure/nf.py --device lna "$@"
