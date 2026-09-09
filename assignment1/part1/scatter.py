"""Create the Part 1 geographic-distance-versus-RTT plot as a PDF."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def calculate_distances(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c


def main():
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "results.csv"
    default_output = script_dir.parent / "figures" / "distance_vs_rtt.pdf"

    parser = argparse.ArgumentParser(description="Plot geographic distance versus ping RTT.")
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()

    df = pd.read_csv(args.input, na_values=["NA"])
    numeric_columns = ["latitude", "longitude", "min_rtt_ms", "avg_rtt_ms", "max_rtt_ms"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Row 0 is the local public IP. Drop unavailable pings/geolocations so
    # every plotted point has a valid distance and RTT.
    baseline = df.iloc[0]
    targets = df.iloc[1:].dropna(subset=numeric_columns).copy()
    if pd.isna(baseline["latitude"]) or pd.isna(baseline["longitude"]):
        raise ValueError("The local public IP has no usable geolocation.")
    if targets.empty:
        raise ValueError("No responsive destinations with usable geolocation were collected.")

    distances_km = calculate_distances(
        baseline["latitude"], baseline["longitude"],
        targets["latitude"].to_numpy(), targets["longitude"].to_numpy(),
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(distances_km, targets["min_rtt_ms"], color="tab:green", label="Minimum RTT", alpha=0.8)
    ax.scatter(distances_km, targets["avg_rtt_ms"], color="tab:blue", label="Average RTT", alpha=0.8)
    ax.scatter(distances_km, targets["max_rtt_ms"], color="tab:red", label="Maximum RTT", alpha=0.8)
    ax.set_title("RTT versus Geographic Distance")
    ax.set_xlabel("Geographic distance from West Lafayette (km)")
    ax.set_ylabel("Round-trip time (ms)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="pdf")
    print(f"Wrote {args.output} using {len(targets)} responsive destinations.")


if __name__ == "__main__":
    main()
