import pandas as pd
import numpy as np
import joblib

DATA_FILE = 'byzantine_training_data_20251217_105438.csv'
df = pd.read_csv(DATA_FILE)

# basic stats
print(f"Total rows: {len(df)}")
print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Error Counts (Raw): \n{df['error_500_count'].value_counts()}")

# Reconstruct predictions to check variance of 'svm_correct'
model = joblib.load('artifacts/tw_lb_svm_model.joblib')
scaler = joblib.load('artifacts/feature_scaler.joblib')
encoder = joblib.load('artifacts/label_encoder.joblib')

features = ['avg_latency_seconds', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
df['latency_ms'] = df['avg_latency_seconds'] * 1000
X = df[features].copy()
# Map to correct feature names expected by random forest/svm if needed, 
# but here we just need to match shape. 
# Wait, the scaler expects specific columns. 
# The script research_analysis.ipynb used: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
X['latency_ms'] = X['avg_latency_seconds'] * 1000
X_for_scale = X[['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']]

X_scaled = scaler.transform(X_for_scale)
predictions = model.predict(X_scaled)
df['predicted_label'] = encoder.inverse_transform(predictions)

def check_correctness(row):
    true_lbl = row['fault_type']
    pred_lbl = row['predicted_label']
    if true_lbl == 'benign':
        return 1 if pred_lbl == 'benign' else 0
    else:
        return 1 if pred_lbl != 'benign' else 0

df['svm_correct'] = df.apply(check_correctness, axis=1)

print("\n--- Variance Analysis ---")
print(f"SVM Accuracy Mean: {df['svm_correct'].mean():.4f}")
print(f"SVM Accuracy Std:  {df['svm_correct'].std():.4f}")
print(f"Predictions Breakdown:\n{df['predicted_label'].value_counts()}")

expected_bad = len(df[df['fault_type'] != 'benign'])
print(f"Ground Truth Faulty Samples: {expected_bad}")
