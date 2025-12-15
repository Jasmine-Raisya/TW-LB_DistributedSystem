import time
import requests
import os
import pandas as pd
import numpy as np
import joblib
import random
from typing import Dict, List
from prometheus_api_client import PrometheusConnect
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv(dotenv_path='../.env', override=True)
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")

# Artifact paths
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), 'artifacts')
SCALER_FILE = os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib')
MODEL_FILE = os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib')
ENCODER_FILE = os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib')

# Node configuration
NODES = [f"node-{i}" for i in range(1, 16)]

# CRITICAL: These MUST match the training script exactly
REQUIRED_FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']

# --- PROMETHEUS QUERY HELPERS ---

def get_instant_pql_query(node: str, metric_type: str) -> str:
    """Generates instant PQL queries for the latest metric values."""
    target_instance = f'{node}:8000'
    
    queries = {
        'latency': f'''
            avg_over_time(request_latency_seconds_sum{{instance="{target_instance}", status="200"}}[5s]) / 
            avg_over_time(request_latency_seconds_count{{instance="{target_instance}", status="200"}}[5s])
        ''',
        'error_count': f'''
            sum(increase(http_requests_total{{instance="{target_instance}", status="500"}}[10s]))
        ''',
        'cpu': f'''
            rate(process_cpu_seconds_total{{instance="{target_instance}"}}[5s])
        ''',
        'memory': f'''
            process_resident_memory_bytes{{instance="{target_instance}"}}
        '''
    }
    
    return queries.get(metric_type, '')

# --- TRUST WEIGHT LOAD BALANCER ---

class TrustWeightLoadBalancer:
    """
    Implements Byzantine-robust Trust-Weighted Load Balancing using SVM fault detection.
    Falls back to Round Robin if model fails to load or Prometheus is unavailable.
    """
    
    def __init__(self, node_ids: List[str]):
        """Initialize the TWLB with model artifacts and Prometheus connection."""
        self.node_ids = node_ids
        self.node_weights: Dict[str, float] = {node_id: 1.0 for node_id in node_ids}
        self.rr_index = 0
        self.model_loaded = False
        
        # Load ML artifacts
        try:
            self.scaler = joblib.load(SCALER_FILE)
            self.model = joblib.load(MODEL_FILE)
            self.label_encoder = joblib.load(ENCODER_FILE)
            self.model_loaded = True
            print(f"✓ TWLB initialized successfully")
            print(f"  - Model: {os.path.basename(MODEL_FILE)}")
            print(f"  - Features: {REQUIRED_FEATURES}")
            print(f"  - Classes: {list(self.label_encoder.classes_)}")
        except FileNotFoundError as e:
            print(f"⚠ WARNING: Model artifacts not found: {e}")
            print(f"⚠ Falling back to Round Robin routing")
            self.model = None
            self.scaler = None
            
        # Initialize Prometheus connection
        try:
            self.prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
            print(f"✓ Connected to Prometheus at {PROMETHEUS_URL}")
        except Exception as e:
            print(f"⚠ WARNING: Failed to connect to Prometheus: {e}")
            print(f"⚠ Weight updates will not function")
            self.prom = None

    def _fetch_node_metrics(self, node: str) -> Dict[str, float]:
        """Fetch latest metrics for a single node from Prometheus."""
        if not self.prom:
            return None
            
        try:
            metrics = {}
            
            # Fetch latency
            latency_result = self.prom.custom_query(get_instant_pql_query(node, 'latency'))
            metrics['avg_latency_seconds'] = float(latency_result[0]['value'][1]) if latency_result else 0.0
            
            # Fetch error count
            error_result = self.prom.custom_query(get_instant_pql_query(node, 'error_count'))
            metrics['error_count'] = float(error_result[0]['value'][1]) if error_result else 0.0
            
            # Fetch CPU
            cpu_result = self.prom.custom_query(get_instant_pql_query(node, 'cpu'))
            metrics['cpu_usage_rate'] = float(cpu_result[0]['value'][1]) if cpu_result else 0.0
            
            # Fetch memory (convert bytes to MB)
            memory_result = self.prom.custom_query(get_instant_pql_query(node, 'memory'))
            memory_bytes = float(memory_result[0]['value'][1]) if memory_result else 0.0
            metrics['resident_mem_mb'] = memory_bytes / (1024 * 1024)
            
            return metrics
            
        except Exception as e:
            print(f"⚠ Warning: Failed to fetch metrics for {node}: {e}")
            return None

    def _engineer_features(self, raw_metrics: Dict[str, float]) -> pd.DataFrame:
        """
        Transform raw Prometheus metrics into the feature vector expected by the model.
        Must match training script feature engineering exactly.
        """
        features = {
            'latency_ms': raw_metrics['avg_latency_seconds'] * 1000,
            'error_500_count': raw_metrics['error_count'],
            'cpu_usage_rate': raw_metrics['cpu_usage_rate'],
            'resident_mem_mb': raw_metrics['resident_mem_mb']
        }
        
        # Return as DataFrame with exact column order
        return pd.DataFrame([features])[REQUIRED_FEATURES]

    def _calculate_trust_weight(self, node_id: str, raw_metrics: Dict[str, float]) -> float:
        """
        Calculate trust weight based on SVM fault probability prediction.
        
        Formula:
        - P(Faulty) < 0.20  → TW = 1.0  (High trust)
        - 0.20 ≤ P < 0.60   → TW = 0.5  (Medium trust)
        - P ≥ 0.60          → TW = 0.1  (Low trust, avoid but don't eliminate)
        """
        if not self.model_loaded or raw_metrics is None:
            return 1.0
            
        try:
            # Engineer features
            feature_df = self._engineer_features(raw_metrics)
            
            # Scale features (CRITICAL: must use same scaler as training)
            X_scaled = self.scaler.transform(feature_df)
            
            # Predict fault probability
            # predict_proba returns [[P(benign), P(faulty)]]
            probabilities = self.model.predict_proba(X_scaled)[0]
            
            # Get index of 'faulty' class (could be 0 or 1 depending on label encoding)
            try:
                fault_idx = list(self.label_encoder.classes_).index('delay')  # or 'faulty'
            except ValueError:
                # If 'delay' not found, try other common fault names
                fault_class_candidates = ['delay', 'faulty', 'crash', '500-error']
                fault_idx = None
                for candidate in fault_class_candidates:
                    if candidate in self.label_encoder.classes_:
                        fault_idx = list(self.label_encoder.classes_).index(candidate)
                        break
                if fault_idx is None:
                    fault_idx = 1  # Default to second class
            
            p_faulty = probabilities[fault_idx]
            
            # Apply trust weighting formula
            if p_faulty < 0.20:
                tw = 1.0
            elif p_faulty < 0.60:
                tw = 0.5
            else:
                tw = 0.1
                
            return tw
            
        except Exception as e:
            print(f"⚠ Error calculating trust weight for {node_id}: {e}")
            return 1.0  # Safe default

    def update_trust_weights(self):
        """Fetch metrics from Prometheus and update trust weights for all nodes."""
        if not self.model_loaded or not self.prom:
            return
            
        print(f"\n[{time.strftime('%H:%M:%S')}] Updating trust weights...")
        
        for node_id in self.node_ids:
            raw_metrics = self._fetch_node_metrics(node_id)
            
            if raw_metrics is not None:
                new_weight = self._calculate_trust_weight(node_id, raw_metrics)
                self.node_weights[node_id] = new_weight

    def select_next_node(self) -> str:
        """
        Select the next node using weighted random selection based on trust weights.
        Falls back to Round Robin if model is not loaded or all weights are zero.
        """
        # Fallback to Round Robin if model not loaded
        if not self.model_loaded:
            selected = self.node_ids[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.node_ids)
            return selected
        
        # Weighted random selection
        node_list = list(self.node_weights.keys())
        weight_list = list(self.node_weights.values())
        
        # If all weights are zero (rare edge case), fall back to RR
        if sum(weight_list) <= 0.01:
            selected = self.node_ids[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.node_ids)
            return selected
        
        # Weighted random choice
        return random.choices(node_list, weights=weight_list, k=1)[0]

    def get_distribution_weights(self) -> Dict[str, float]:
        """Get current trust weight distribution (for logging)."""
        return {k: round(v, 2) for k, v in self.node_weights.items()}


# --- MAIN ROUTING LOGIC ---

REQUEST_INTERVAL_SECONDS = 0.5
WEIGHT_UPDATE_INTERVAL_SECONDS = 5.0

# Initialize load balancer
twlb = TrustWeightLoadBalancer(NODES)
last_weight_update_time = 0


def route_request():
    """
    Route a single request to a selected node using trust-weighted selection.
    Periodically updates trust weights based on Prometheus metrics.
    """
    global last_weight_update_time
    
    # Periodic trust weight update
    current_time = time.time()
    if current_time - last_weight_update_time >= WEIGHT_UPDATE_INTERVAL_SECONDS:
        twlb.update_trust_weights()
        last_weight_update_time = current_time
        
        strategy = "TWLB" if twlb.model_loaded else "RR"
        print(f"\n[{time.strftime('%H:%M:%S')}] --- WEIGHTS UPDATED ({strategy}) ---")
        weights_display = twlb.get_distribution_weights()
        # Only show non-zero weights for cleaner output
        active_weights = {k: v for k, v in weights_display.items() if v > 0.0}
        print(f"Active Weights: {active_weights}")
        print("-" * 60)
    
    # Select node
    selected_node = twlb.select_next_node()
    strategy = "TWLB" if twlb.model_loaded else "RR"
    
    # Send request
    try:
        response = requests.get(f"http://{selected_node}:8000/process", timeout=5.0)
        print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | Status: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | TIMEOUT")
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | ERROR: {type(e).__name__}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Trust-Weighted Load Balancer Starting")
    print("="*60)
    
    # Initial weight update
    if twlb.model_loaded:
        twlb.update_trust_weights()
        last_weight_update_time = time.time()
        print(f"\nInitial Trust Weights: {twlb.get_distribution_weights()}")
    else:
        print("\n⚠ Running in Round Robin mode (model not loaded)")
    
    print(f"\nStarting request routing (interval: {REQUEST_INTERVAL_SECONDS}s)")
    print("="*60 + "\n")
    
    # Main routing loop
    while True:
        route_request()
        time.sleep(REQUEST_INTERVAL_SECONDS)
