import pandas as pd
import joblib
import numpy as np

# 1. Configuration
INPUT_FILE = 'byzantine_training_data_20251217_105438.csv' # The High-Accuracy Run
OUTPUT_FILE = 'final_research_dataset.csv'

print(f"📦 Loading dataset: {INPUT_FILE}...")
df = pd.read_csv(INPUT_FILE)

# 2. Load Model Artifacts
print("🧠 Loading SVM Model...")
model = joblib.load('artifacts/tw_lb_svm_model.joblib')
scaler = joblib.load('artifacts/feature_scaler.joblib')
encoder = joblib.load('artifacts/label_encoder.joblib')

# 3. Feature Engineering (Must match training pipeline)
# The model expects: [latency_ms, error_500_count, cpu_usage_rate, resident_mem_mb]
df['latency_ms'] = df['avg_latency_seconds'] * 1000
features = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']

X = df[features]
X_scaled = scaler.transform(X)

# 4. Generate Predictions
print("⚡ Re-running Model Inference on all rows...")
valid_encodings = encoder.transform(encoder.classes_) # [0, 1] usually

# Get raw labels
predictions_encoded = model.predict(X_scaled)
df['svm_predicted_label'] = encoder.inverse_transform(predictions_encoded)

# Get confidence score (distance to hyperplane)
# For binary classification, result is shape (N,). Positive=Class1, Negative=Class0
confidence = model.decision_function(X_scaled)
df['svm_confidence_score'] = np.abs(confidence) # Magnitude = Confidence

# 5. Calculate Correctness (Ground Truth Check)
def check_correctness(row):
    true_lbl = row['fault_type']
    pred_lbl = row['svm_predicted_label']
    
    if true_lbl == 'benign':
        # Must predict benign
        return True if pred_lbl == 'benign' else False
    else:
        # Must predict ANY fault (not benign)
        return True if pred_lbl != 'benign' else False

df['svm_is_correct'] = df.apply(check_correctness, axis=1)

# 6. Save Validated Dataset
print(f"💾 Saving augmented dataset to: {OUTPUT_FILE}")
df.to_csv(OUTPUT_FILE, index=False)

print("\n=== SUMMARY ===")
print(df[['timestamp', 'node_id', 'fault_type', 'svm_predicted_label', 'svm_is_correct']].head())
print(f"\nOverall Reconstruction Accuracy: {df['svm_is_correct'].mean()*100:.2f}%")
