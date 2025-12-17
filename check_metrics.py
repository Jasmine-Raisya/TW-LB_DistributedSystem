import pandas as pd
import joblib
import os
import glob
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize

# Paths
ARTIFACTS_DIR = 'artifacts'
MODEL_FILE = os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib')
SCALER_FILE = os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib')
ENCODER_FILE = os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib')

# Find latest data file
list_of_files = glob.glob('byzantine_training_data_*.csv') 
LATEST_DATA_FILE = max(list_of_files, key=os.path.getctime)

print(f"📊 Loading data from: {LATEST_DATA_FILE}")
df = pd.read_csv(LATEST_DATA_FILE)

# Features expected by model
REQUIRED_FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']

# Load Artifacts
print("🔧 Loading model artifacts (Model, Scaler, Encoder)...")
model = joblib.load(MODEL_FILE)
scaler = joblib.load(SCALER_FILE)
encoder = joblib.load(ENCODER_FILE)

# Feature Engineering (Must match training)
df['latency_ms'] = df['avg_latency_seconds'] * 1000

# Prepare Data
X = df[REQUIRED_FEATURES]
y_true = df['fault_type']

# Scale features
X_scaled = scaler.transform(X)

# Predict
y_pred = model.predict(X_scaled)
y_prob = model.predict_proba(X_scaled)

# Encode y_true to match model output integers
y_true_encoded = encoder.transform(y_true)

# --- METRICS ---
accuracy = accuracy_score(y_true_encoded, y_pred)
f1 = f1_score(y_true_encoded, y_pred, average='weighted')

# ROC-AUC (Multi-class handling)
# Binarize labels for One-vs-Rest ROC-AUC
classes = encoder.classes_
# Use y_true_encoded for binarize? No, label_binarize handles classes arg.
# But cleaner to use y_true_encoded if we use integer classes. 
# Let's stick to using the strings if we pass classes argument, OR use integers.
# Simplest: use integers for everything.
y_true_bin = label_binarize(y_true_encoded, classes=range(len(classes)))
n_classes = len(classes)

# Handle case where only 2 classes exist in test set but model trained on 3
if y_true_bin.shape[1] != n_classes:
    # This might happen if 'crash' is missing from this specific dataset but model knows it
    # For simplicity in this check, we might skip or adjust. 
    # But usually, predict_proba returns columns for all trained classes.
    pass

try:
    if n_classes == 2:
        # Binary case
        roc_auc = roc_auc_score(y_true, y_prob[:, 1])
    else:
        # Multi-class case (weighted to account for class imbalance)
        roc_auc = roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted')
except ValueError as e:
    print(f"⚠️ Could not calculate ROC-AUC: {e}")
    roc_auc = 0.0

print("\n" + "="*40)
print("🎯 SVM Model Accuracy Metrics")
print("="*40)
print(f"✅ Accuracy:  {accuracy:.4f}  ({accuracy*100:.1f}%)")
print(f"✅ F1 Score:  {f1:.4f}")
print(f"✅ ROC-AUC:   {roc_auc:.4f}")
print("="*40)
print("\n(Note: Calculated on the 80-sample dataset used for training/validation)")
