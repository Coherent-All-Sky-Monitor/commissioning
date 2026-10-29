#!/usr/bin/env bash
# Measure LNA S-parameters (LNA#####P1/P2) with the LibreVNA.
# Results are saved to LNA/s_params/. See tools/vna/README.md for setup.
#
# Usage: ./lna_sparams.sh [--headless]
#
# Runs with uv, or with an activated virtual environment (see README "Setup").
exec "$(dirname "$0")/tools/run_python.sh" tools/vna/sparams.py --device lna "$@"
