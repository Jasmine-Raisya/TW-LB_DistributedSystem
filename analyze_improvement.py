import pandas as pd
import glob
import os

# Find latest data file
list_of_files = glob.glob('byzantine_training_data_*.csv') 
LATEST_DATA_FILE = max(list_of_files, key=os.path.getctime)

print(f"📊 Analyzing: {LATEST_DATA_FILE}")
df = pd.read_csv(LATEST_DATA_FILE)

# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])
start_time = df['timestamp'].min()
end_time = df['timestamp'].max()
total_duration = (end_time - start_time).total_seconds()

print(f"⏱️ Total Duration: {total_duration:.1f} seconds")

# Define Phases
# Phase 1: Learning (First 2 minutes)
learning_end = start_time + pd.Timedelta(minutes=2)
# Phase 2: Exploitation (Last 2 minutes)
stable_start = end_time - pd.Timedelta(minutes=2)

df_learning = df[df['timestamp'] < learning_end]
df_stable = df[df['timestamp'] > stable_start]

def calculate_stats(data, phase_name):
    if len(data) == 0:
        return
    
    total_reqs = len(data) # This is data points, not requests, but roughly correlates
    # We need to look at 'error_500_count' sum vs implied total?
    # Actually, we have 'error_500_count' as a raw count in the 15s window.
    # But we don't have total request count in the CSV rows directly (we have latency).
    # However, we can use the 'status_code_for_verification' column.
    # If status_code == 500, that 15s window had errors.
    
    # Better metric: 'error_500_count' column is the sum of increase.
    total_errors = data['error_500_count'].sum()
    
    # To estimate rate, we need total requests. We don't have that column in the CSV clearly.
    # But wait, looking at `data_exporter.py`... 
    # query 2 is `sum(increase(http_requests_total{... status="500"}))`
    # We didn't export TOTAL requests per node in the CSV.
    # We only exported Latency, 500 Count, CPU, Mem.
    
    # Proxy: Timestamps where status_code_for_verification == 500
    # The 'status_code_for_verification' is 500 if error_count > 0.
    # Let's count "Faulty Intervals" vs "Clean Intervals".
    
    bad_intervals = len(data[data['error_500_count'] > 0])
    total_intervals = len(data)
    
    pct_bad = (bad_intervals / total_intervals) * 100 if total_intervals > 0 else 0
    avg_latency = data['avg_latency_seconds'].mean() * 1000
    
    print(f"\n--- {phase_name} ---")
    print(f"  Sample Points:   {total_intervals}")
    print(f"  Windows w/ Errors: {bad_intervals} ({pct_bad:.1f}%)")
    print(f"  Avg Latency:     {avg_latency:.2f} ms")
    
    return pct_bad

print("\n🔎 IMPACT ASSESSMENT")
err_start = calculate_stats(df_learning, "Phase 1: Learning (First 2 mins)")
err_end = calculate_stats(df_stable, "Phase 2: Stabilized (Last 2 mins)")

if err_start and err_end:
    improvement = err_start - err_end
    print(f"\n✅ Improvement: Error frequency dropped by {improvement:.1f}% percentage points")
    if err_end < err_start:
        print("🚀 CONCLUSION: The TW-LB successfully learned to avoid faulty nodes.")
    else:
        print("⚠️ CONCLUSION: No significant improvement detected.")
