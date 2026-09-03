#!/bin/bash

printf 'ip,continent,country,site,min_rtt_ms,avg_rtt_ms,max_rtt_ms,latitude,longitude\n' > results.csv

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
    python3 -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("lat","NA"))+","+str(d.get("lon","NA")))' \
    2>/dev/null)

  [ -z "$coords" ] && coords="NA,NA"
  IFS=, read -r latitude longitude <<< "$coords"

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$ip" "$continent" "$country" "$site" \
    "$min_rtt" "$avg_rtt" "$max_rtt" \
    "$latitude" "$longitude" >> results.csv

  rm "$ping_output"
}

#our ip
my_ip=$(curl -s --max-time 10 https://api.ipify.org)
add_row "$my_ip" "North America" "USA" "West Lafayette"

#other ips
tail -n +2 ips.csv | while IFS=, read -r ip port speed continent country site provider
do
  add_row "$ip" "$continent" "$country" "$site"
done