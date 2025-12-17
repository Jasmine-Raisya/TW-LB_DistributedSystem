import pandas as pd
import numpy as np

DATA_FILE = 'final_research_dataset.csv'
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])

def calculate_window_metrics(window):
    # Mean Confidence of all predictions in this window
    mean_confidence = window['svm_confidence_score'].mean()
    
    # Error Intensity
    total_errors = window['error_500_count'].sum()
    error_intensity = total_errors / len(window)
    
    return pd.Series({
        'mean_confidence': mean_confidence, 
        'error_intensity': error_intensity
    })

windowed_df = df.groupby('timestamp').apply(calculate_window_metrics).dropna()

print("\n=== DATA VARIANCE CHECK ===")
conf_std = windowed_df['mean_confidence'].std()
print(f"Confidence Std Dev: {conf_std:.5f}")
print(f"Confidence Range: {windowed_df['mean_confidence'].min():.4f} - {windowed_df['mean_confidence'].max():.4f}")

print("\n=== CORRELATION CHECK (Confidence) ===")
corr = windowed_df['mean_confidence'].corr(windowed_df['error_intensity'])
print(f"Pearson r: {corr:.4f}")

if corr < -0.4:
    print("✅ FOUND IT! Confidence correlates with Errors.")
else:
    print("❌ No valid correlation found.")
