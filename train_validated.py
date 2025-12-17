#!/usr/bin/env python3
"""
Train SVM Model on Real Byzantine Fault Data with Validation
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import joblib
import glob
import os

print("="*60)
print("Training SVM Model with Validation")
print("="*60)

# 1. Load most recent data
files = glob.glob('byzantine_training_data_*.csv')
if not files:
    print("❌ No data files found!")
    print("Run './run_quick_collection.sh' first to collect data")
    exit(1)

latest_file = max(files, key=os.path.getctime)
print(f"\n📊 Loading data from: {latest_file}")
df = pd.read_csv(latest_file)

print(f"Total samples: {len(df)}")
print(f"\nFault type distribution:")
fault_counts = df['fault_type'].value_counts()
for fault, count in fault_counts.items():
    print(f"  {fault}: {count}")

# 2. Check minimum samples
if len(df) < 100:
    print("\n⚠️  Warning: Less than 100 samples. Results may be poor.")
    print("Consider running data collection longer.")

# 3. Feature engineering  
df['latency_ms'] = df['avg_latency_seconds'] * 1000
FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
X = df[FEATURES]
y = df['fault_type']

# 4. Train/test split (80/20)
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
except ValueError as e:
    print(f"\n❌ Error: {e}")
    print("Not enough samples per fault type for stratified split.")
    print("Using non-stratified split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

print(f"\nTrain samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")

# 5. Encode and scale
label_encoder = LabelEncoder()
y_train_enc = label_encoder.fit_transform(y_train)
y_test_enc = label_encoder.transform(y_test)

print(f"\nClasses found: {list(label_encoder.classes_)}")

scaler = RobustScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 6. Train SVM
print("\n🔧 Training SVM...")
model = SVC(kernel='rbf', C=10.0, gamma='scale', probability=True, random_state=42)
model.fit(X_train_scaled, y_train_enc)

# 7. Validation
print("\n📊 Evaluating on test set...")
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test_enc, y_pred)
f1 = f1_score(y_test_enc, y_pred, average='weighted')

print("\n" + "="*60)
print("📈 VALIDATION RESULTS")
print("="*60)
print(f"Accuracy: {accuracy:.3f}")
print(f"F1 Score: {f1:.3f}")

print("\n" + "-"*60)
print("Classification Report:")
print("-"*60)
print(classification_report(y_test_enc, y_pred, target_names=label_encoder.classes_))

print("\n" + "-"*60)
print("Confusion Matrix:")
print("-"*60)
cm = confusion_matrix(y_test_enc, y_pred)
print(cm)
print(f"\nRows = True labels: {list(label_encoder.classes_)}")
print(f"Cols = Predictions: {list(label_encoder.classes_)}")

# 8. Test with sample cases
print("\n" + "="*60)
print("🧪 Testing Model on Sample Cases")  
print("="*60)

test_cases = [
    ("Benign node", [30, 0, 0.3, 250]),
    ("Delay fault (3.5s)", [3500, 0, 0.3, 300]),
    ("500-Error fault", [30, 5, 0.3, 250]),
]

for name, features in test_cases:
    X_sample = scaler.transform([features])
    pred_class = model.predict(X_sample)[0]
    pred_proba = model.predict_proba(X_sample)[0]
    
    print(f"\n{name}:")
    print(f"  Predicted: {label_encoder.classes_[pred_class]}")
    max_prob = pred_proba[pred_class]
    print(f"  Confidence: {max_prob:.1%}")

# 9. Save artifacts
print("\n" + "="*60)
print("💾 Saving Model Artifacts")
print("="*60)

os.makedirs('artifacts', exist_ok=True)
joblib.dump(scaler, 'artifacts/feature_scaler.joblib')
joblib.dump(model, 'artifacts/tw_lb_svm_model.joblib')
joblib.dump(label_encoder, 'artifacts/label_encoder.joblib')

print("✅ Saved:")
print("  - artifacts/feature_scaler.joblib")
print("  - artifacts/tw_lb_svm_model.joblib")
print("  - artifacts/label_encoder.joblib")

print("\n" + "="*60)
print("✅ Training Complete!")
print("="*60)
print("\nNext step: Deploy new model")
print("  docker compose up -d --build tw-lb")
print("\nThen monitor detection:")
print("  docker logs -f $(docker ps --filter 'name=tw-lb' --format '{{.Names}}')")
