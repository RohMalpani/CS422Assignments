# Randomly select iperf3 destinations and ports, with bounded replacements for failed servers.
import argparse
import csv
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Server:
    host: str
    port: int
    country: str = ""
    site: str = ""
    provider: str = ""

    def __str__(self):
        return f"{self.host}:{self.port} ({self.site}, {self.country}, {self.provider})"


def parse_ports(field):
    """'5201' -> [5201]; '5201-5210' -> [5201..5210]."""
    field = field.strip()
    if "-" in field:
        lo, hi = field.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(field)]


def load_servers(path):
    """Read the iperf3serverlist.net CSV. Returns [(host, [ports], row), ...]; skips malformed rows."""
    entries = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                host = row["IP/HOST"].strip()
                ports = parse_ports(row["PORT"])
            except (KeyError, ValueError, AttributeError):
                continue
            if host and ports:
                entries.append((host, ports, row))
    return entries


class ServerPool:
    """Hands out random servers one at a time; never returns the same host twice.

    Use next_server() for the initial n, then again for each replacement after a failure.
    """

    def __init__(self, path, seed=None):
        self._rng = random.Random(seed)
        self._entries = load_servers(path)
        self._rng.shuffle(self._entries)  # one shuffle = uniform sample without replacement

    def __len__(self):
        return len(self._entries)

    def next_server(self):
        """Return a Server on a random port from its range, or None if the list is exhausted."""
        if not self._entries:
            return None
        host, ports, row = self._entries.pop()
        return Server(
            host=host,
            port=self._rng.choice(ports),
            country=row.get("COUNTRY", ""),
            site=row.get("SITE", ""),
            provider=row.get("PROVIDER", ""),
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pick n random iperf3 servers (standalone test).")
    ap.add_argument("--servers", default="servers.csv")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    pool = ServerPool(args.servers, args.seed)
    print(f"{len(pool)} servers in list")
    for _ in range(args.n):
        s = pool.next_server()
        if s is None:
            break
        print(s)
