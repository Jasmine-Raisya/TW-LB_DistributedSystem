"""
SVM Evaluator with Proper Train/Test Split
===========================================
Evaluates the SVM model with:
- Time-based train/test split (avoids data leakage)
- Proper metrics: F1, ROC-AUC, Matthews Correlation Coefficient
- Confusion matrix analysis
- Hypothesis II validation

Usage:
    python svm_evaluator.py [--data-file FILE] [--output-dir DIR]
"""

import os
import json
import argparse
import glob
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder, RobustScaler
from sklearn.svm import SVC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import (
    f1_score,
    roc_auc_score,
    matthews_corrcoef,
    confusion_matrix,
    classification_report,
    accuracy_score,
    precision_score,
    recall_score
)


# --- Configuration ---
ARTIFACTS_DIR = './artifacts'
REQUIRED_FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']

# Hypothesis II thresholds
F1_THRESHOLD = 0.80
ROC_AUC_THRESHOLD = 0.90
MCC_THRESHOLD = 0.50


def find_latest_data_file() -> Optional[str]:
    """Find the most recent training data CSV file."""
    pattern = "byzantine_training_data_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        pattern = "training_data_*.csv"
        files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Sort by modification time, return newest
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def time_based_split(
    df: pd.DataFrame, 
    test_ratio: float = 0.3
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data chronologically to avoid train/test leakage.
    This is CRITICAL for time-series data like system metrics.
    """
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Calculate split point
    split_idx = int(len(df) * (1 - test_ratio))
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    print(f"  Time-based split:")
    print(f"    Train: {len(train_df)} samples ({train_df['timestamp'].min()} to {train_df['timestamp'].max()})")
    print(f"    Test:  {len(test_df)} samples ({test_df['timestamp'].min()} to {test_df['timestamp'].max()})")
    
    return train_df, test_df


def load_and_prepare_data(file_path: str) -> Tuple[pd.DataFrame, Optional[LabelEncoder]]:
    """Load and preprocess the training data."""
    print(f"Loading data from: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        return None, None
    
    print(f"  Loaded {len(df)} rows")
    
    # Feature engineering
    if 'latency_ms' not in df.columns and 'avg_latency_seconds' in df.columns:
        df['latency_ms'] = df['avg_latency_seconds'] * 1000
    
    # Handle missing values
    for feature in REQUIRED_FEATURES:
        if feature in df.columns:
            df[feature] = df[feature].fillna(0)
    
    # Ensure timestamp is datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Print class distribution
    if 'fault_type' in df.columns:
        print(f"  Class distribution:")
        for fault_type, count in df['fault_type'].value_counts().items():
            print(f"    {fault_type}: {count} ({count/len(df)*100:.1f}%)")
    
    return df, None


def train_and_evaluate_svm(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    output_dir: str
) -> Dict[str, Any]:
    """
    Train SVM model and evaluate with proper metrics.
    """
    print("\n--- SVM Training and Evaluation ---")
    
    # Prepare features
    X_train = train_df[REQUIRED_FEATURES].copy()
    X_test = test_df[REQUIRED_FEATURES].copy()
    
    # Encode labels
    le = LabelEncoder()
    y_train = le.fit_transform(train_df['fault_type'])
    y_test = le.transform(test_df['fault_type'])
    
    print(f"  Classes: {list(le.classes_)}")
    
    # Scale features using RobustScaler (better for outliers)
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train SVM with OneVsRest for multi-class
    print("  Training SVM...")
    svm = SVC(
        kernel='rbf',
        C=10,
        gamma='scale',
        probability=True,
        class_weight='balanced',
        random_state=42
    )
    ovr = OneVsRestClassifier(svm)
    ovr.fit(X_train_scaled, y_train)
    
    # Predictions
    y_pred = ovr.predict(X_test_scaled)
    y_proba = ovr.predict_proba(X_test_scaled)
    
    # Calculate metrics
    results = calculate_metrics(y_test, y_pred, y_proba, le)
    
    # Save predictions for analysis
    predictions_df = test_df.copy()
    predictions_df['predicted_fault'] = le.inverse_transform(y_pred)
    predictions_df['correct'] = predictions_df['fault_type'] == predictions_df['predicted_fault']
    
    pred_file = os.path.join(output_dir, 'predictions.csv')
    predictions_df.to_csv(pred_file, index=False)
    print(f"  Predictions saved to: {pred_file}")
    
    # Save model artifacts (updated)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(ovr, os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib'))
    joblib.dump(scaler, os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib'))
    joblib.dump(le, os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib'))
    print(f"  Model artifacts saved to: {ARTIFACTS_DIR}/")
    
    return results


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    label_encoder: LabelEncoder
) -> Dict[str, Any]:
    """Calculate all evaluation metrics."""
    
    results = {}
    
    # Basic metrics
    results['accuracy'] = accuracy_score(y_true, y_pred)
    results['precision_weighted'] = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    results['recall_weighted'] = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    
    # F1 Score (Weighted)
    results['f1_weighted'] = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    results['f1_macro'] = f1_score(y_true, y_pred, average='macro', zero_division=0)
    
    # ROC-AUC (One-vs-Rest)
    try:
        n_classes = len(np.unique(y_true))
        if n_classes > 1:
            # Fix: Ensure y_proba is handled correctly for binary case (2 columns) or multi-class
            if n_classes == 2:
                # For binary, use only the probability of the positive class
                results['roc_auc_weighted'] = roc_auc_score(y_true, y_proba[:, 1], average='weighted')
                results['roc_auc_macro'] = roc_auc_score(y_true, y_proba[:, 1], average='macro')
            else:
                results['roc_auc_weighted'] = roc_auc_score(
                    y_true, y_proba, 
                    multi_class='ovr', 
                    average='weighted'
                )
                results['roc_auc_macro'] = roc_auc_score(
                    y_true, y_proba,
                    multi_class='ovr',
                    average='macro'
                )
        else:
            results['roc_auc_weighted'] = 0.0
            results['roc_auc_macro'] = 0.0
    except Exception as e:
        print(f"  WARNING: Could not calculate ROC-AUC: {e}")
        results['roc_auc_weighted'] = 0.0
        results['roc_auc_macro'] = 0.0
    
    # Matthews Correlation Coefficient
    results['mcc'] = matthews_corrcoef(y_true, y_pred)
    
    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    results['confusion_matrix'] = cm.tolist()
    results['confusion_matrix_labels'] = list(label_encoder.classes_)
    
    # Per-class metrics
    report = classification_report(
        y_true, y_pred,
        target_names=label_encoder.classes_,
        output_dict=True,
        zero_division=0
    )
    results['per_class_report'] = report
    
    # Calculate detection metrics for Byzantine faults
    # Consider all non-benign classes as "faulty"
    benign_idx = list(label_encoder.classes_).index('benign') if 'benign' in label_encoder.classes_ else 0
    
    y_true_binary = (y_true != benign_idx).astype(int)
    y_pred_binary = (y_pred != benign_idx).astype(int)
    
    results['byzantine_detection'] = {
        'true_positives': int(np.sum((y_true_binary == 1) & (y_pred_binary == 1))),
        'true_negatives': int(np.sum((y_true_binary == 0) & (y_pred_binary == 0))),
        'false_positives': int(np.sum((y_true_binary == 0) & (y_pred_binary == 1))),
        'false_negatives': int(np.sum((y_true_binary == 1) & (y_pred_binary == 0))),
        'detection_rate': recall_score(y_true_binary, y_pred_binary, zero_division=0),
        'false_positive_rate': np.sum((y_true_binary == 0) & (y_pred_binary == 1)) / max(1, np.sum(y_true_binary == 0))
    }
    
    return results


def validate_hypothesis_ii(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Hypothesis II:
    - F1 Score > 0.80
    - ROC-AUC > 0.90
    - MCC > 0.50
    """
    validation = {
        'f1_score': {
            'value': results['f1_weighted'],
            'threshold': F1_THRESHOLD,
            'passed': results['f1_weighted'] > F1_THRESHOLD
        },
        'roc_auc': {
            'value': results['roc_auc_weighted'],
            'threshold': ROC_AUC_THRESHOLD,
            'passed': results['roc_auc_weighted'] > ROC_AUC_THRESHOLD
        },
        'mcc': {
            'value': results['mcc'],
            'threshold': MCC_THRESHOLD,
            'passed': results['mcc'] > MCC_THRESHOLD
        }
    }
    
    validation['all_passed'] = all(v['passed'] for v in validation.values())
    
    return validation


def print_results(results: Dict[str, Any], validation: Dict[str, Any]):
    """Print formatted results."""
    
    print("\n" + "="*60)
    print("SVM EVALUATION RESULTS")
    print("="*60)
    
    print(f"\n--- Core Metrics ---")
    print(f"  Accuracy:          {results['accuracy']:.4f}")
    print(f"  Precision:         {results['precision_weighted']:.4f}")
    print(f"  Recall:            {results['recall_weighted']:.4f}")
    print(f"  F1 Score:          {results['f1_weighted']:.4f}")
    print(f"  ROC-AUC:           {results['roc_auc_weighted']:.4f}")
    print(f"  MCC:               {results['mcc']:.4f}")
    
    print(f"\n--- Byzantine Detection ---")
    bd = results['byzantine_detection']
    print(f"  True Positives:    {bd['true_positives']}")
    print(f"  True Negatives:    {bd['true_negatives']}")
    print(f"  False Positives:   {bd['false_positives']}")
    print(f"  False Negatives:   {bd['false_negatives']}")
    print(f"  Detection Rate:    {bd['detection_rate']:.4f}")
    print(f"  FP Rate:           {bd['false_positive_rate']:.4f}")
    
    # Categorize Difficulty
    rate = bd['detection_rate']
    difficulty = "HIGH" if rate < 0.7 else "MEDIUM" if rate < 0.9 else "LOW"
    print(f"  Detection Difficulty: {difficulty} (based on rate)")
    
    print(f"\n--- Confusion Matrix ---")
    labels = results['confusion_matrix_labels']
    cm = results['confusion_matrix']
    print(f"  {' ':15} " + " ".join(f"{l:>10}" for l in labels))
    for i, row in enumerate(cm):
        print(f"  {labels[i]:15} " + " ".join(f"{v:>10}" for v in row))
    
    print(f"\n--- Hypothesis II Validation ---")
    for metric, data in validation.items():
        if metric == 'all_passed':
            continue
        status = "✓ PASSED" if data['passed'] else "✗ FAILED"
        print(f"  {metric.upper():10} {data['value']:.4f} > {data['threshold']} : {status}")
    
    overall = "✓ HYPOTHESIS II VALIDATED" if validation['all_passed'] else "✗ HYPOTHESIS II NOT VALIDATED"
    print(f"\n  {overall}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Evaluate SVM model with proper metrics")
    parser.add_argument(
        "--data-file",
        type=str,
        default=None,
        help="Path to training data CSV (auto-detects if not specified)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./evaluation_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.3,
        help="Ratio of data to use for testing (default: 0.3)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find data file
    data_file = args.data_file or find_latest_data_file()
    if not data_file:
        print("ERROR: No training data file found. Run data_exporter.py first.")
        return 1
    
    # Load data
    df, _ = load_and_prepare_data(data_file)
    if df is None:
        return 1
    
    # Time-based split
    train_df, test_df = time_based_split(df, args.test_ratio)
    
    # Train and evaluate
    results = train_and_evaluate_svm(train_df, test_df, args.output_dir)
    
    # Validate Hypothesis II
    validation = validate_hypothesis_ii(results)
    results['hypothesis_ii_validation'] = validation
    
    # Print results
    print_results(results, validation)
    
    # Save results
    results_file = os.path.join(args.output_dir, 'svm_evaluation_results.json')
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_file}")
    
    return 0 if validation['all_passed'] else 1


if __name__ == "__main__":
    exit(main())
