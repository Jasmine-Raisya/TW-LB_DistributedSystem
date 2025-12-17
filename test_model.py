#!/usr/bin/env python3
"""
Quick diagnostic to test if the SVM model is working correctly
"""
import joblib
import pandas as pd
import numpy as np

# Load artifacts
scaler = joblib.load('artifacts/feature_scaler.joblib')
model = joblib.load('artifacts/tw_lb_svm_model.joblib')
encoder = joblib.load('artifacts/label_encoder.joblib')

print("=" * 60)
print("SVM Model Diagnostic")
print("=" * 60)

print(f"\nClasses: {list(encoder.classes_)}")
print(f"\nFeature names expected: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']")

# Test case 1: Benign node (low latency, no errors)
test_benign = pd.DataFrame([{
    'latency_ms': 30,
    'error_500_count': 0,
    'cpu_usage_rate': 0.3,
    'resident_mem_mb': 250
}])

# Test case 2: Delay fault (high latency)
test_delay = pd.DataFrame([{
    'latency_ms': 3500,  # 3.5 seconds
    'error_500_count': 0,
    'cpu_usage_rate': 0.3,
    'resident_mem_mb': 300
}])

# Test case 3: 500-error fault
test_500 = pd.DataFrame([{
    'latency_ms': 30,
    'error_500_count': 5,
    'cpu_usage_rate': 0.3,
    'resident_mem_mb': 250
}])

for name, test_data in [("Benign", test_benign), ("Delay", test_delay), ("500-Error", test_500)]:
    print(f"\n{name} Test:")
    print(f"  Input: {test_data.iloc[0].to_dict()}")
    
    # Scale
    X_scaled = scaler.transform(test_data)
    print(f"  Scaled: {X_scaled[0]}")
    
    # Predict
    pred_class = model.predict(X_scaled)[0]
    pred_proba = model.predict_proba(X_scaled)[0]
    
    print(f"  Predicted class: {pred_class}")
    print(f"  Probabilities: {dict(zip(encoder.classes_, pred_proba))}")
