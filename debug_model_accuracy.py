import pandas as pd
import joblib
import os

# Define the two datasets
DATASETS = [
    'byzantine_training_data_20251217_105438.csv', # Phase 6 (High Accuracy expected)
    'byzantine_training_data_20251217_113847.csv'  # Phase 8 (Latest, Crash faults?)
]

# Load Artifacts
try:
    model = joblib.load('artifacts/tw_lb_svm_model.joblib')
    scaler = joblib.load('artifacts/feature_scaler.joblib')
    encoder = joblib.load('artifacts/label_encoder.joblib')
    print("✅ Artifacts loaded.")
except Exception as e:
    print(f"❌ Failed to load artifacts: {e}")
    exit(1)

def evaluate_dataset(filename):
    print(f"\n🔎 Analyzing {filename}...")
    if not os.path.exists(filename):
        print("   ❌ File not found.")
        return

    df = pd.read_csv(filename)
    
    # Check for prediction column
    if 'prediction' in df.columns or 'predicted_label' in df.columns:
        print("   ℹ️  Dataset HAS existing prediction column.")
    else:
        print("   ⚠️  Dataset MISSING prediction column (User suspicion confirmed).")

    # Reconstruct Predictions
    # Feature Engineering must match train_validated.py
    # Features: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
    if 'avg_latency_seconds' in df.columns:
        df['latency_ms'] = df['avg_latency_seconds'] * 1000
    
    # Select features
    feature_cols = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
    try:
        X = df[feature_cols]
        X_scaled = scaler.transform(X)
        preds = model.predict(X_scaled)
        pred_labels = encoder.inverse_transform(preds)
        
        # Calculate Accuracy
        correct = 0
        total = 0
        for i, row in df.iterrows():
            total += 1
            true_lbl = row['fault_type']
            pred_lbl = pred_labels[i]
            
            # Logic: 
            # If Benign -> Pred must be Benign
            # If Faulty -> Pred can be ANY fault class (not benign)
            is_correct = False
            if true_lbl == 'benign':
                if pred_lbl == 'benign': is_correct = True
            else:
                if pred_lbl != 'benign': is_correct = True # Detection
                
            if is_correct: correct += 1
            
        acc = (correct / total) * 100
        print(f"   🎯 Reconstructed Model Accuracy: {acc:.1f}%")
        
        # Fault Distribution
        print(f"   📊 Fault Types: {df['fault_type'].unique()}")
        
    except Exception as e:
        print(f"   ❌ Prediction failed: {e}")

for ds in DATASETS:
    evaluate_dataset(ds)
