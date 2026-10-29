#!/usr/bin/env bash
# Acquire backboard noise-figure traces (noise source on/off) from the Siglent
# spectrum analyzer. Traces are saved to BB/noise_figure/data/<subfolder>/.
# See BB/noise_figure/README.md for the procedure.
#
# Usage: ./bac_nf_measure.sh
#
# Runs with uv, or with an activated virtual environment (see README "Setup").
exec "$(dirname "$0")/tools/run_python.sh" tools/noise_figure/spectrum_analyzer.py --device bac "$@"
