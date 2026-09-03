"""
Step 2: run traceroute against a single target and parse its output into
per-hop RTT data (assignment 1, part 2a).

See DECISIONS.md for why: WSL-wrapped traceroute on Windows vs native
traceroute elsewhere, -n/-q/-w flags, min-of-probes aggregation, and how
non-responsive destinations are detected.
"""

import platform
import re
import socket
import subprocess
from dataclasses import dataclass, field

PROBES_PER_HOP = 3
PROBE_TIMEOUT_SEC = 2
MAX_HOPS = 30
WSL_DISTRO = "Ubuntu-22.04"

# Matches one traceroute output line, e.g.:
#   " 3  10.0.0.3  12.345 ms  11.876 ms  13.001 ms"
#   " 5  * * *"
#   " 7  8.8.8.8  31.084 ms  *  31.063 ms"
HOP_LINE_RE = re.compile(r"^\s*(\d+)\s+(.*)$")
# Matches an individual probe result within a hop line: either a number
# (RTT in ms) or a bare "*" (no reply).
PROBE_RE = re.compile(r"(\*|[\d.]+)\s*(?:ms)?")


@dataclass
class Hop:
    number: int
    address: str | None          # None if all probes timed out
    probe_rtts_ms: list[float]   # only the responsive probes


@dataclass
class TracerouteResult:
    target: str
    resolved_ip: str | None
    reached: bool                # did the destination itself respond?
    hops: list[Hop] = field(default_factory=list)
    raw_output: str = ""


def _build_command(target: str) -> list[str]:
    base = [
        "traceroute",
        "-I",                        # ICMP echo probes, not default UDP --
                                      # see DECISIONS.md: many hosts/firewalls
                                      # silently drop UDP traceroute's expected
                                      # "port unreachable" reply while still
                                      # answering ICMP fine.
        "-n",                       # numeric output, skip reverse DNS
        "-q", str(PROBES_PER_HOP),
        "-w", str(PROBE_TIMEOUT_SEC),
        "-m", str(MAX_HOPS),
        target,
    ]
    if platform.system() == "Windows":
        return ["wsl", "-d", WSL_DISTRO, "--"] + base
    return base


def _resolve(target: str) -> str | None:
    try:
        return socket.gethostbyname(target)
    except socket.gaierror:
        return None


def _parse_hop_line(line: str) -> Hop | None:
    m = HOP_LINE_RE.match(line)
    if not m:
        return None
    hop_num = int(m.group(1))
    rest = m.group(2).strip()

    if rest.startswith("*"):
        # fully non-responsive hop, e.g. "* * *"
        return Hop(number=hop_num, address=None, probe_rtts_ms=[])

    # First token is the hop's address (numeric, since we pass -n).
    tokens = rest.split()
    address = tokens[0]
    rtts = []
    for tok in tokens[1:]:
        if tok == "*":
            continue
        if tok == "ms":
            continue
        try:
            rtts.append(float(tok))
        except ValueError:
            continue
    return Hop(number=hop_num, address=address, probe_rtts_ms=rtts)


def run_traceroute(target: str) -> TracerouteResult:
    """Run traceroute against `target` and parse the result. Never raises
    on a non-responsive target -- that's reflected in `.reached`."""
    resolved_ip = _resolve(target)
    cmd = _build_command(target)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SEC * PROBES_PER_HOP * MAX_HOPS + 10,
        )
        output = proc.stdout
    except subprocess.TimeoutExpired as e:
        output = (e.stdout or "")

    hops = []
    for line in output.splitlines():
        hop = _parse_hop_line(line)
        if hop is not None:
            hops.append(hop)

    # We reached the destination if the last hop's address matches the
    # resolved target IP (traceroute stops as soon as the destination
    # itself replies; hitting MAX_HOPS without that means it didn't).
    reached = bool(
        hops
        and resolved_ip is not None
        and hops[-1].address == resolved_ip
    )

    return TracerouteResult(
        target=target,
        resolved_ip=resolved_ip,
        reached=reached,
        hops=hops,
        raw_output=output,
    )


def hop_min_rtt(hop: Hop) -> float | None:
    """Min of the responsive probes at this hop, or None if all timed out."""
    return min(hop.probe_rtts_ms) if hop.probe_rtts_ms else None


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "8.8.8.8"
    result = run_traceroute(target)
    print(f"target={result.target} resolved_ip={result.resolved_ip} reached={result.reached}")
    for hop in result.hops:
        print(f"  hop {hop.number}: address={hop.address} min_rtt={hop_min_rtt(hop)} probes={hop.probe_rtts_ms}")
