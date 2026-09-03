import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_distances(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c


df = pd.read_csv('results.csv')

baseline_lat = df['latitude'].iloc[0]
baseline_long = df['longitude'].iloc[0]

target_lats = df['latitude'].iloc[1:].to_numpy()
target_longs = df['longitude'].iloc[1:].to_numpy()

average_rtt_array = df['avg_rtt_ms'].iloc[1:].to_numpy()
min_rtt_array = df['min_rtt_ms'].iloc[1:].to_numpy()
max_rtt_array = df['max_rtt_ms'].iloc[1:].to_numpy()

distance_array = calculate_distances(baseline_lat, baseline_long, target_lats, target_longs)

plt.figure(figsize=(10, 6))
plt.scatter(distance_array, average_rtt_array, c='blue', label='Average RTT')
plt.scatter(distance_array, min_rtt_array, c='green', label='Min RTT')
plt.scatter(distance_array, max_rtt_array, c='red', label='Max RTT')

# Formatting the plot
plt.title('min/avg/max RTT vs. Geographic Distance')
plt.xlabel('Distance (Kilometers)')
plt.ylabel('RTT (ms)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

plt.savefig('NetworksAssignment1/figures/scatter_plot.png', bbox_inches='tight')
