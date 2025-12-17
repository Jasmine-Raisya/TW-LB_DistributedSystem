import pandas as pd
import numpy as np

DATA_FILE = 'final_research_dataset.csv'
df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])

def calculate_window_metrics(window):
    # Mean Accuracy for this moment in time
    svm_accuracy = window['svm_is_correct'].mean()
    
    # Error Intensity
    # Normalize error count by number of nodes to get intensity
    total_errors = window['error_500_count'].sum()
    error_intensity = total_errors / len(window)
    
    return pd.Series({
        'svm_accuracy': svm_accuracy, 
        'error_intensity': error_intensity
    })

windowed_df = df.groupby('timestamp').apply(calculate_window_metrics).dropna()

print("\n=== DATA VARIANCE CHECK ===")
acc_std = windowed_df['svm_accuracy'].std()
print(f"SVM Accuracy Std Dev: {acc_std:.5f}")
print(f"SVM Accuracy Range: {windowed_df['svm_accuracy'].min():.4f} - {windowed_df['svm_accuracy'].max():.4f}")

print("\n=== CORRELATION CHECK (Granular Accuracy) ===")
corr = windowed_df['svm_accuracy'].corr(windowed_df['error_intensity'])
print(f"Pearson r: {corr:.4f}")

print("\n=== SAMPLE DATA ===")
print(windowed_df.head(10))
