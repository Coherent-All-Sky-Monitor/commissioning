#!/usr/bin/env bash
# Acquire LNA noise-figure hot/cold traces from the Siglent spectrum analyzer.
# Traces are saved to LNA/noise_figure/data/<subfolder>/. See tools/noise_figure/README.md.
#
# Usage: ./lna_nf_measure.sh
#
# Runs with uv, or with an activated virtual environment (see README "Setup").
exec "$(dirname "$0")/tools/run_python.sh" tools/noise_figure/spectrum_analyzer.py --device lna "$@"
