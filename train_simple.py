#!/usr/bin/env python3
"""
Simple training script that creates a basic SVM model with correct feature scaling
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
import joblib

print("Creating synthetic training data for SVM model...")

# Create synthetic training data based on expected patterns
np.random.seed(42)

data = []

# Benign nodes: low latency, no errors
for _ in range(100):
    data.append({
        'latency_ms': np.random.uniform(20, 50),
        'error_500_count': 0,
        'cpu_usage_rate': np.random.uniform(0.1, 0.5),
        'resident_mem_mb': np.random.uniform(200, 350),
        'fault_type': 'benign'
    })

# Delay fault: HIGH latency, no errors
for _ in range(100):
    data.append({
        'latency_ms': np.random.uniform(3000, 7000),  # 3-7 seconds
        'error_500_count': 0,
        'cpu_usage_rate': np.random.uniform(0.1, 0.5),
        'resident_mem_mb': np.random.uniform(200, 350),
        'fault_type': 'delay'
    })

# 500-error fault: normal latency, HIGH error count
for _ in range(100):
    data.append({
        'latency_ms': np.random.uniform(20, 50),
        'error_500_count': np.random.uniform(1, 10),
        'cpu_usage_rate': np.random.uniform(0.1, 0.5),
        'resident_mem_mb': np.random.uniform(200, 350),
        'fault_type': '500-error'
    })

# Crash fault: similar to benign but slightly different (hard to detect)
for _ in range(100):
    data.append({
        'latency_ms': np.random.uniform(20, 50),
        'error_500_count': 0,
        'cpu_usage_rate': np.random.uniform(0.05, 0.3),  # Lower CPU
        'resident_mem_mb': np.random.uniform(200, 350),
        'fault_type': 'crash'
    })

df = pd.DataFrame(data)

print(f"\nCreated {len(df)} training samples")
print(f"Class distribution:\n{df['fault_type'].value_counts()}")

# Prepare features and labels
FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
X = df[FEATURES]
y = df['fault_type']

# Encode labels
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

print(f"\nLabel encoding: {dict(zip(label_encoder.classes_, range(len(label_encoder.classes_))))}")

# Scale features using RobustScaler (handles outliers better)
scaler = RobustScaler()
X_scaled = scaler.fit_transform(X)

print(f"\nFeature scaling statistics:")
print(f"Original latency range: {X['latency_ms'].min():.1f} - {X['latency_ms'].max():.1f}")
print(f"Scaled latency range: {X_scaled[:, 0].min():.3f} - {X_scaled[:, 0].max():.3f}")

# Train SVM model
print("\nTraining SVM model...")
model = SVC(kernel='rbf', C=10.0, gamma='scale', probability=True, random_state=42)
model.fit(X_scaled, y_encoded)

# Test the model
print("\nTesting model predictions:")

test_cases = [
    ("Benign", [30, 0, 0.3, 250]),
    ("Delay (3.5s)", [3500, 0, 0.3, 300]),
    ("500-Error (5 errors)", [30, 5, 0.3, 250]),
    ("Crash", [30, 0, 0.15, 250])
]

for name, features in test_cases:
    X_test = scaler.transform([features])
    pred_class = model.predict(X_test)[0]
    pred_proba = model.predict_proba(X_test)[0]
    
    print(f"\n{name}:")
    print(f"  Features: {features}")
    print(f"  Predicted: {label_encoder.classes_[pred_class]}")
    print(f"  Probabilities: {dict(zip(label_encoder.classes_, pred_proba))}")

# Save artifacts
print("\nSaving model artifacts...")
joblib.dump(scaler, 'artifacts/feature_scaler.joblib')
joblib.dump(model, 'artifacts/tw_lb_svm_model.joblib')
joblib.dump(label_encoder, 'artifacts/label_encoder.joblib')

print("\n✅ Model training complete!")
print("Artifacts saved to artifacts/ directory")
print("\nNow restart the load balancer to use the new model:")
print("  docker compose up -d --build tw-lb")
