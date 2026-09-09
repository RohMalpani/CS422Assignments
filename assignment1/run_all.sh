#!/usr/bin/env bash
# Reproduce the Assignment 1 measurements, plots, and report from this folder.
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet -r requirements.txt

PYTHON_BIN="$(pwd)/.venv/bin/python" ./part1/ping.sh
.venv/bin/python part2/run.py --input ips.csv
