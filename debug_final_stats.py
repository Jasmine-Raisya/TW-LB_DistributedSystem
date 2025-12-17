import pandas as pd
import numpy as np

DATA_FILE = 'final_research_dataset.csv'
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Loaded {len(df)} rows.")

def calculate_window_metrics(window):
    # Active nodes: Latency > 0
    active_nodes = window[window['avg_latency_seconds'] > 0]
    
    if len(active_nodes) == 0:
        return None
    
    # Traffic Purity: (Active Benign) / (Total Active)
    active_benign = active_nodes[active_nodes['fault_type'] == 'benign']
    traffic_purity = len(active_benign) / len(active_nodes)

    # Error Intensity: Total Errors / Total Active Nodes
    total_errors = window['error_500_count'].sum()
    error_intensity = total_errors / len(active_nodes)
    
    return pd.Series({
        'traffic_purity': traffic_purity, 
        'error_intensity': error_intensity,
        'active_count': len(active_nodes),
        'error_sum': total_errors
    })

# Sample every 15s
windowed_df = df.groupby('timestamp').apply(calculate_window_metrics).dropna()

print("\n=== RAW DATA INSPECTION (First 20 Windows) ===")
print(windowed_df.head(20))

print("\n=== CORRELATION DEBUG ===")
# Check correlation manually
corr = windowed_df['traffic_purity'].corr(windowed_df['error_intensity'])
print(f"Calculated Pearson r: {corr:.4f}")

print("\n=== EXTREME CASES ===")
print("High Purity (1.0) but High Errors (>0):")
print(windowed_df[(windowed_df['traffic_purity'] == 1.0) & (windowed_df['error_intensity'] > 0)])

print("\nLow Purity (<1.0) but Low Errors (0):")
print(windowed_df[(windowed_df['traffic_purity'] < 1.0) & (windowed_df['error_intensity'] == 0)])
