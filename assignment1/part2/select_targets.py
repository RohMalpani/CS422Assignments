"""
Step 1: load the iperf3 server list and randomly pick N destination targets
for the traceroute latency-breakdown experiment (assignment 1, part 2a).

The "IP/HOST" column in ips.csv is a mix of raw IPs and hostnames
(e.g. "speedtest.hkg12.hk.leaseweb.net") -- traceroute handles both fine
via DNS resolution, so we don't need to distinguish or pre-resolve them
here.
"""

import argparse
import csv
import random
from dataclasses import dataclass

DEFAULT_SEED = 42  # arbitrary, fixed only for reproducibility -- see DECISIONS.md
DEFAULT_N = 5


@dataclass
class Server:
    host: str          # IP or hostname, whatever traceroute should target
    continent: str
    country: str
    site: str
    provider: str


def load_servers(csv_path: str) -> list[Server]:
    """Read the server list CSV into a list of Server records, skipping rows with
    no usable host entry."""
    servers = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            host = row.get("IP/HOST", "").strip()
            if not host:
                continue
            servers.append(
                Server(
                    host=host,
                    continent=row.get("CONTINENT", "").strip(),
                    country=row.get("COUNTRY", "").strip(),
                    site=row.get("SITE", "").strip(),
                    provider=row.get("PROVIDER", "").strip(),
                )
            )
    return servers


def pick_targets(servers: list[Server], n: int = DEFAULT_N, seed: int = DEFAULT_SEED) -> list[Server]:
    """Randomly select n servers using a fixed seed, so the choice is
    reproducible across runs (same 5 every time, but genuinely produced
    by random selection rather than hardcoded)."""
    rng = random.Random(seed)
    return rng.sample(servers, k=min(n, len(servers)))


def main():
    parser = argparse.ArgumentParser(description="Pick random traceroute targets from the server list.")
    parser.add_argument("--input", default="../ips.csv", help="Path to the server list CSV")
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="Number of targets to pick")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducibility")
    args = parser.parse_args()

    servers = load_servers(args.input)
    print(f"Loaded {len(servers)} servers from {args.input}")

    targets = pick_targets(servers, n=args.n, seed=args.seed)
    print(f"Selected {len(targets)} targets (seed={args.seed}):")
    for t in targets:
        print(f"  {t.host}  ({t.site}, {t.country}, {t.provider})")


if __name__ == "__main__":
    main()
