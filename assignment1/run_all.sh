#!/usr/bin/env bash
# Reproduce the Assignment 1 measurements and plot PDFs from this folder.
set -euo pipefail

cd "$(dirname "$0")"
assignment_dir="$(pwd)"
output_root="$assignment_dir"
limit=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      limit="$2"
      shift 2
      ;;
    --output-root)
      output_root="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--limit N] [--output-root DIRECTORY]" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$output_root"
output_root="$(cd "$output_root" && pwd)"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet -r requirements.txt

part1_args=(
  --input "$assignment_dir/ips.csv"
  --results-out "$output_root/part1/results.csv"
  --plots-out "$output_root/figures"
)
if [[ -n "$limit" ]]; then
  part1_args+=(--limit "$limit")
fi

PYTHON_BIN="$assignment_dir/.venv/bin/python" ./part1/ping.sh "${part1_args[@]}"
"$assignment_dir/.venv/bin/python" part2/run.py \
  --input "$assignment_dir/ips.csv" \
  --data-out "$output_root/part2/data/traceroute_results.json" \
  --plots-out "$output_root/figures"
