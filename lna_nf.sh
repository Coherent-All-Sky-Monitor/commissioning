#!/usr/bin/env bash
# Analyze LNA noise-figure measurements (Y-factor, hot/cold loads).
# Reads LNA/noise_figure/data/, writes plots to LNA/noise_figure/plots/
# and results to LNA/noise_figure/nf_log.csv. See tools/noise_figure/README.md.
#
# Usage: ./lna_nf.sh -b lna173 --save-plot   # one measurement
#        ./lna_nf.sh --all                   # every measurement
#
# Runs with uv, or with an activated virtual environment (see README "Setup").
exec "$(dirname "$0")/tools/run_python.sh" tools/noise_figure/nf.py --device lna "$@"
