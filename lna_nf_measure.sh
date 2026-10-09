#!/usr/bin/env bash
# Acquire LNA noise-figure hot/cold traces from the Siglent spectrum analyzer.
# Traces are saved to LNA/noise_figure/data/<subfolder>/. See tools/noise_figure/README.md.
#
# Usage: ./lna_nf_measure.sh
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install it with:" >&2
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec uv run python tools/noise_figure/spectrum_analyzer.py --device lna "$@"
