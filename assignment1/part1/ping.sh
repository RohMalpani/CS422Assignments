#!/bin/bash

# Run relative to this script's own directory (part1/), regardless of where
# it's invoked from -- matters now that this got moved out of the repo root.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"

input_csv="$SCRIPT_DIR/../ips.csv"
results_out="$SCRIPT_DIR/results.csv"
plots_out="$SCRIPT_DIR/../figures"
limit=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      input_csv="$2"
      shift 2
      ;;
    --results-out)
      results_out="$2"
      shift 2
      ;;
    --plots-out)
      plots_out="$2"
      shift 2
      ;;
    --limit)
      limit="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -n "$limit" ]] && { ! [[ "$limit" =~ ^[0-9]+$ ]] || (( limit < 2 )); }; then
  echo "--limit must be an integer of at least 2 (including the local IP)." >&2
  exit 2
fi

mkdir -p "$(dirname "$results_out")" "$plots_out"
printf 'ip,continent,country,site,min_rtt_ms,avg_rtt_ms,max_rtt_ms,latitude,longitude\n' > "$results_out"

add_row () {
  ip="$1"
  continent="$2"
  country="$3"
  site="$4"

  echo "Testing $ip ($site, $country)..."

  ping_output=$(mktemp)
  ping -c 10 -W 1000 "$ip" > "$ping_output" 2>&1

  rtts=$(sed -n 's/.*= \([^/]*\)\/\([^/]*\)\/\([^/]*\)\/.*/\1\/\2\/\3/p' "$ping_output")

  if [ -n "$rtts" ]; then
    IFS=/ read -r min_rtt avg_rtt max_rtt <<< "$rtts"
  else
    min_rtt="NA"
    avg_rtt="NA"
    max_rtt="NA"
  fi

  coords=$(curl -s --max-time 10 \
    "http://ip-api.com/json/$ip?fields=status,lat,lon" |
    "$PYTHON_BIN" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("lat","NA"))+","+str(d.get("lon","NA")))' \
    2>/dev/null)

  [ -z "$coords" ] && coords="NA,NA"
  IFS=, read -r latitude longitude <<< "$coords"

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$ip" "$continent" "$country" "$site" \
    "$min_rtt" "$avg_rtt" "$max_rtt" \
    "$latitude" "$longitude" >> "$results_out"

  rm "$ping_output"
}

#our ip
my_ip=$(curl -s --max-time 10 https://api.ipify.org)
add_row "$my_ip" "North America" "USA" "West Lafayette"

# Other IPs. A limit includes our public IP, so process at most limit - 1
# rows from the supplied server list.
remote_count=0
while IFS=, read -r ip port speed continent country site provider; do
  if [[ -n "$limit" ]] && (( remote_count >= limit - 1 )); then
    break
  fi
  add_row "$ip" "$continent" "$country" "$site"
  ((remote_count += 1))
done < <(tail -n +2 "$input_csv")

"$PYTHON_BIN" scatter.py --input "$results_out" --output "$plots_out/distance_vs_rtt.pdf"
