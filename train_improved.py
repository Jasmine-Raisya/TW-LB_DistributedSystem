import os
import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
from sklearn.multiclass import OneVsRestClassifier

# --- Configuration ---
FILE_NAME = "byzantine_training_data_20251215_203025.csv"
# Output paths - save to artifacts directory for Docker integration
ARTIFACTS_DIR = './artifacts'
MODEL_FILENAME = os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib')
SCALER_FILENAME = os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib')
ENCODER_FILENAME = os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib')

# --- Core Training Functions ---

def load_and_prepare_data(file_name):
    """Loads, cleans, and preprocesses the dataset."""
    print(f"Loading data from: {file_name}")
    try:
        df = pd.read_csv(file_name)
    except FileNotFoundError:
        print(f"ERROR: The file '{file_name}' was not found.")
        return None, None, None, None

    # 1. Feature Engineering
    # Ensure latency is numeric and handle missing values if any
    df['latency_ms'] = df['avg_latency_seconds'] * 1000
    
    # 2. Feature Selection
    # Included CPU and Memory as they are potent indicators of faults (e.g., resource exhaustion)
    features = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
    target = 'fault_type'

    # Drop rows with missing values in critical columns
    df = df.dropna(subset=features + [target])

    X = df[features]
    y = df[target]

    # 3. Encode the Target Variable
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Print class distribution helps understand imbalance
    unique, counts = np.unique(y_encoded, return_counts=True)
    class_dist = dict(zip(le.inverse_transform(unique), counts))
    print(f"Class Distribution: {class_dist}")

    # 4. Scale Features
    # Changed from StandardScaler to RobustScaler. 
    # Network data deals with latency spikes (outliers). RobustScaler scales data using 
    # statistics that are robust to outliers (IQR), providing better inputs for the SVM.
    from sklearn.preprocessing import RobustScaler
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # Save artifacts to dedicated directory
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(le, ENCODER_FILENAME)
    joblib.dump(scaler, SCALER_FILENAME)

    print(f"Data preparation complete. Saved artifacts to {ARTIFACTS_DIR}/")
    print(f"Features used: {features}")
    return X_scaled, y_encoded, le, features

def train_and_evaluate_svm(X, y, label_encoder):
    """Trains the SVM using GridSearchCV for hyperparameter tuning."""

    # Split data (70% Train, 30% Test)
    # Using stratify is excellent for maintaining class ratios
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    print(f"\nSearching for best hyperparameters on {len(X_train)} samples...")

    # UPDATE 1: Class Weights
    # Handling imbalanced data (e.g., fewer faults than benign requests)
    # We add 'class_weight': 'balanced' to the parameter search.

    # UPDATE 2: GridSearchCV
    # Instead of hardcoding C=10, we search for the best C and Gamma.
    # Note: Since we are using OneVsRestClassifier, parameters are prefixed with 'estimator__'
    
    param_grid = {
        'estimator__C': [0.1, 1, 10, 100, 1000],
        'estimator__gamma': ['scale', 'auto', 0.1, 1],
        'estimator__class_weight': ['balanced', None] 
    }

    # Base estimator with probability=True (needed for ROC-AUC)
    svc = SVC(kernel='rbf', probability=True, random_state=42)
    ovr = OneVsRestClassifier(svc)

    # StratifiedKFold ensures each fold represents all classes
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Optimize for F1 Weighted as it balances precision/recall better than accuracy for imbalance
    grid_search = GridSearchCV(
        ovr, 
        param_grid, 
        cv=cv, 
        scoring='f1_weighted', 
        n_jobs=-1, 
        verbose=1
    )

    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    print(f"\nBest Parameters: {grid_search.best_params_}")
    print(f"Best CV F1 Score: {grid_search.best_score_:.4f}")

    # Predict and Evaluate with the best model
    y_pred = best_model.predict(X_test)
    y_proba = best_model.predict_proba(X_test)

    # Calculate Metrics
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_test, y_proba, multi_class='ovr', average='weighted')
    except ValueError:
        roc_auc = 0.0
        print("Warning: ROC-AUC could not be calculated (possibly only one class in test set).")

    print("\n--- Optimized SVM Model Performance ---")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 Score (Weighted): {f1:.4f}")
    print(f"ROC-AUC (Weighted, One-vs-Rest): {roc_auc:.4f}")
    
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    # Save the best model
    joblib.dump(best_model, MODEL_FILENAME)
    print(f"\n{'='*60}")
    print(f"SUCCESS: Model artifacts saved to {ARTIFACTS_DIR}/")
    print(f"  - Model: {os.path.basename(MODEL_FILENAME)}")
    print(f"  - Scaler: {os.path.basename(SCALER_FILENAME)}")
    print(f"  - Encoder: {os.path.basename(ENCODER_FILENAME)}")
    print(f"  - Features: {features}")
    print(f"{'='*60}")

    return best_model

# --- Main Execution ---
if __name__ == "__main__":
    # Ensure dependencies are installed (for Colab)
    # !pip install scikit-learn joblib pandas -qq
    
    try:
        if os.path.exists(FILE_NAME):
            X, y, le, features = load_and_prepare_data(FILE_NAME)
            if X is not None:
                train_and_evaluate_svm(X, y, le)
        else:
            print(f"File {FILE_NAME} not found. Please upload the dataset.")
            
    except Exception as e:
        print(f"\nAn unexpected error occurred during execution: {e}")
