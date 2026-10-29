#!/usr/bin/env bash
# Analyze backboard noise-figure measurements (Y-factor, ENR noise source).
# Reads BB/noise_figure/data/, writes plots to BB/noise_figure/plots/
# and results to BB/noise_figure/nf_log.csv. See tools/noise_figure/README.md.
#
# Usage: ./bac_nf.sh -b BAC00018P1 --save-plot   # one measurement
#        ./bac_nf.sh --all                       # every measurement
#
# Runs with uv, or with an activated virtual environment (see README "Setup").
exec "$(dirname "$0")/tools/run_python.sh" tools/noise_figure/nf.py --device bac "$@"
