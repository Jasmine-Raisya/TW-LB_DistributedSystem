import pandas as pd
import numpy as np

# Switch to the "Optimization Run" (Where errors dropped to 2%)
DATA_FILE = 'byzantine_training_data_20251217_113847.csv'
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Loaded {len(df)} rows from {DATA_FILE}")

def calculate_window_metrics(window):
    active_nodes = window[window['avg_latency_seconds'] > 0]
    if len(active_nodes) == 0: return None
    
    # Traffic Purity
    # Check what 'fault_type' values exist
    # In this dataset, faults might be 'crash'
    active_benign = active_nodes[active_nodes['fault_type'] == 'benign']
    traffic_purity = len(active_benign) / len(active_nodes)

    total_errors = window['error_500_count'].sum()
    error_intensity = total_errors / len(active_nodes)
    
    return pd.Series({
        'traffic_purity': traffic_purity, 
        'error_intensity': error_intensity
    })

windowed_df = df.groupby('timestamp').apply(calculate_window_metrics).dropna()

print("\n=== RAW DATA SAMPLES (Optimization Run) ===")
print(windowed_df.head(10))
print(windowed_df.tail(10))

print("\n=== CORRELATION CHECK ===")
corr = windowed_df['traffic_purity'].corr(windowed_df['error_intensity'])
print(f"Calculated Pearson r: {corr:.4f}")

if corr < -0.5:
    print("✅ FOUND IT! This dataset has the variance we need.")
else:
    print("❌ Still weak/positive. We need to rethink.")
