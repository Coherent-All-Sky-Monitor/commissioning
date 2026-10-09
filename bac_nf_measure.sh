#!/usr/bin/env bash
# Acquire backboard noise-figure traces (noise source on/off) from the Siglent
# spectrum analyzer. Traces are saved to BB/noise_figure/data/<subfolder>/.
# See BB/noise_figure/README.md for the procedure.
#
# Usage: ./bac_nf_measure.sh
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install it with:" >&2
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec uv run python tools/noise_figure/spectrum_analyzer.py --device bac "$@"
