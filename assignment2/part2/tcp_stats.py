"""Prepare Part 1's live data-socket TCP_INFO samples for Part 2 plots.

Part 1 already samples the data socket, so Part 2 does not repeat a transfer or
decode TCP_INFO again. Units in the source CSV are retained; plotting adds
milliseconds and Mbps columns. `retrans_interval` is the loss proxy: the
increase in cumulative TCP retransmissions during each sampling interval.
"""

from pathlib import Path

import pandas as pd

REQUIRED_SAMPLES = (
    "run_id", "rep", "host", "port", "algorithm", "timestamp", "elapsed_s",
    "interval_s", "goodput_bps", "snd_cwnd", "rtt_us", "retrans_interval",
)
PLOT_VALUES = ("elapsed_s", "goodput_bps", "snd_cwnd", "rtt_us", "retrans_interval")


def load_tcp_stats(results_dir, algorithm=None):
    """Load successful Part 1 traces and verify their recorded socket algorithm."""
    results_dir = Path(results_dir)
    runs = pd.read_csv(results_dir / "part1_runs.csv", dtype={"host": str})
    samples = pd.read_csv(results_dir / "part1_samples.csv", dtype={"host": str})
    missing = set(REQUIRED_SAMPLES) - set(samples.columns)
    if missing:
        raise ValueError(f"Part 1 samples are missing columns: {sorted(missing)}")
    if not {"status", "run_id", "rep", "host", "port", "algorithm"}.issubset(runs.columns):
        raise ValueError("Part 1 runs CSV lacks status or run identity columns")

    # Part 1's run_id identifies a batch, so rep + destination complete the key.
    keys = ["run_id", "rep", "host", "port"]
    completed = runs.loc[runs["status"] == "ok", keys + ["algorithm", "site", "country"]]
    completed = completed.drop_duplicates(keys)
    data = samples.merge(completed, on=keys, how="inner", suffixes=("", "_run"),
                         validate="many_to_one")
    if data.empty:
        raise ValueError("No successful Part 1 TCP samples to plot")
    if not data["algorithm"].eq(data["algorithm_run"]).all():
        raise ValueError("A sample's algorithm differs from its successful run record")

    actual = sorted(data["algorithm_run"].dropna().unique())
    if algorithm is None:
        if len(actual) != 1:
            raise ValueError(f"Part 2 requires one algorithm; found {actual}. "
                             "Pass --algorithm to choose one.")
        algorithm = actual[0]
    data = data[data["algorithm_run"] == algorithm].copy()
    if data.empty:
        raise ValueError(f"No successful Part 1 samples used {algorithm!r}; found {actual}")

    for column in PLOT_VALUES:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].notna().sum() == 0:
            raise ValueError(f"Required TCP metric {column!r} has no values")
    data["rtt_ms"] = data["rtt_us"] / 1000.0
    data["goodput_mbps"] = data["goodput_bps"] / 1_000_000.0
    return data


def parse_destination(value):
    """Convert HOST:PORT or [IPv6]:PORT into the saved host/port pair."""
    host, separator, port = (value[1:].partition("]:") if value.startswith("[")
                             else value.rpartition(":"))
    if not separator or not host or not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError("destination must be HOST:PORT or [IPv6]:PORT")
    return host, int(port)


def select_representative(samples, destination=None):
    """Choose a saved destination with median mean goodput, or use an explicit one."""
    if destination:
        host, port = parse_destination(destination)
    else:
        means = samples.groupby(["host", "port"])["goodput_mbps"].mean()
        middle = means.median()
        host, port = min(means.index, key=lambda item: (abs(means[item] - middle), item))
    chosen = samples[(samples["host"] == host) & (samples["port"] == port)].copy()
    if chosen.empty:
        raise ValueError(f"No successful Part 1 samples for {host}:{port}")
    return chosen, (host, port)
