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
import psutil
from prometheus_client import start_http_server, Gauge, Counter

# --- CONFIGURATION ---
load_dotenv(dotenv_path='../.env', override=True)
# Ensure the hostname here matches the Prometheus SERVICE name in docker-compose.yml
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")

# Artifact paths
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), 'artifacts')
SCALER_FILE = os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib')
MODEL_FILE = os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib')
ENCODER_FILE = os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib')

# Node configuration
NODES = [f"node-{i}" for i in range(1, 16)]

# Debug configuration
DEBUG = True  # Set to False to disable debug logging

# CRITICAL: These MUST match the training script exactly
REQUIRED_FEATURES = ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']

# --- PROMETHEUS QUERY HELPERS ---

def get_instant_pql_query(node: str, metric_type: str) -> str:
    """
    Generates instant PQL queries for the latest metric values.
    Uses REAL metrics collected via psutil inside the nodes.
    This replaces cAdvisor queries which are unreliable on some Docker/Windows environments.
    """
    label_selector = f'node_id="{node}"'
    
    queries = {
        'latency': f'''
            avg_over_time(request_latency_seconds_sum{{{label_selector}}}[5s]) / 
            avg_over_time(request_latency_seconds_count{{{label_selector}}}[5s])
        ''',
        'error_count': f'''
            sum(increase(lb_routed_requests_total{{selected_node="{node}", status!="200"}}[10s]))
        ''',
        # REAL CPU usage (measured via psutil in the node)
        'cpu': f'''
            node_cpu_usage_percent{{{label_selector}}} / 100
        ''',
        # REAL memory usage (measured via psutil in the node)
        'memory': f'''
            node_memory_mb{{{label_selector}}} * 1024 * 1024
        '''
    }
    
    return queries.get(metric_type, '')



# --- HELPER FUNCTION FOR SAFE METRIC EXTRACTION ---

def safe_extract_metric(result: List) -> float:
    """
    Safely extracts the metric value (float) from the Prometheus API result format,
    returning 0.0 if the result list is empty or the value is missing.
    """
    # Result format: [{'metric': {...}, 'value': [timestamp, 'value']}]
    if result and result[0].get('value') and len(result[0]['value']) > 1:
        try:
            return float(result[0]['value'][1])
        except (ValueError, TypeError):
            # Should not happen if data is numeric, but good for safety
            return 0.0
    return 0.0


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
        """Fetch latest metrics for a single node from Prometheus using safe extraction."""
        if not self.prom:
            return None
            
        try:
            metrics = {}
            
            # Fetch latency (Made resilient in PQL)
            latency_result = self.prom.custom_query(get_instant_pql_query(node, 'latency'))
            metrics['avg_latency_seconds'] = safe_extract_metric(latency_result)
            
            # Fetch error count (Made resilient in PQL)
            error_result = self.prom.custom_query(get_instant_pql_query(node, 'error_count'))
            metrics['error_count'] = safe_extract_metric(error_result)
            
            # Fetch CPU (Made resilient in PQL)
            cpu_result = self.prom.custom_query(get_instant_pql_query(node, 'cpu'))
            metrics['cpu_usage_rate'] = safe_extract_metric(cpu_result)
            
            # Fetch memory (Made resilient in PQL)
            memory_result = self.prom.custom_query(get_instant_pql_query(node, 'memory'))
            memory_bytes = safe_extract_metric(memory_result)
            metrics['resident_mem_mb'] = memory_bytes / (1024 * 1024)
            
            if DEBUG:
                print(f"DEBUG METRICS ({node}): {metrics}")
            
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
            
            # --- UNIVERSAL TRUST DETECTION ---
            # Instead of looking for specific faults, we measure "HEALTHINESS"
            try:
                # Get P(Faulty) = 1 - P(Benign)
                benign_idx = list(self.label_encoder.classes_).index('benign')
                p_benign = probabilities[benign_idx]
                p_faulty = 1.0 - p_benign
                
                # Graceful Degradation Logic
                # Avoid harsh penalties for low-confidence detections
                if p_faulty < 0.20:
                    return 1.0  # High trust
                elif p_faulty >= 0.20 and p_faulty < 0.70:
                    return 0.5  # Suspicious: reduced weight but not quarantined
                else:
                    return 0.01 # High confidence fault: Quarantine
                    
            except ValueError:
                # Fallback if 'benign' class not found (should not happen)
                print("⚠ Error: 'benign' class not found in model")
                return 0.5
            except ValueError:
                # Fallback: if 'benign' label is missing, assume the highest prob class is NOT benign
                p_benign = probabilities[0] 

            # Trust Weight logic based on P(Benign)
            # This allows for REHABILITATION: if a node stops failing, its P(Benign) will 
            # increase, and it will eventually gain back its 1.0 weight.
            if p_benign > 0.80:
                tw = 1.0    # High trust (Benign)
            elif p_benign > 0.40:
                tw = 0.4    # Suspicious (Throttle)
            else:
                tw = 0.01   # Probable Byzantine or Unresponsive (Quarantine)

            # --- DYNAMIC RECOVERY LOGGING ---
            if DEBUG:
                best_class_idx = probabilities.argmax()
                best_class = self.label_encoder.classes_[best_class_idx]
                print(f"DEBUG PREDICT ({node_id}): P(Benign)={p_benign:.3f}, Top Prediction={best_class} ({probabilities[best_class_idx]:.2f})")
                
                # Check for rehabilitation (if weight was low and is now high)
                if tw > 0.5 and self.weights.get(node_id, 1.0) < 0.2:
                    print(f"✅ REHABILITATION: {node_id} has recovered and is restored to full trust!")

            return tw

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

REQUEST_INTERVAL_SECONDS = 0.05
WEIGHT_UPDATE_INTERVAL_SECONDS = 5.0

# --- SELF-MONITORING METRICS ---
LB_CPU_USAGE = Gauge('lb_cpu_usage_percent', 'CPU usage of the load balancer itself')
LB_MEMORY_USAGE = Gauge('lb_memory_mb', 'Memory usage of the load balancer itself in MB')
LB_REQUESTS_TOTAL = Counter('lb_routed_requests_total', 'Total requests routed by the load balancer', ['selected_node', 'status'])

def update_lb_self_metrics():
    """Update CPU and Memory metrics for the load balancer itself."""
    try:
        cpu = psutil.cpu_percent()
        memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        LB_CPU_USAGE.set(cpu)
        LB_MEMORY_USAGE.set(memory_mb)
    except Exception as e:
        if DEBUG:
            print(f"DEBUG: Failed to update self-metrics: {e}")

# Initialize load balancer
twlb = TrustWeightLoadBalancer(NODES)
last_weight_update_time = 0

# Start metrics server on port 8080
try:
    start_http_server(8080)
    print("✓ Prometheus metrics server started on port 8080")
except Exception as e:
    print(f"⚠ WARNING: Could not start metrics server: {e}")


def route_request():
    """
    Route a single request to a selected node using trust-weighted selection.
    Periodically updates trust weights based on Prometheus metrics.
    """
    global last_weight_update_time
    
    def validate_response(response) -> bool:
        """Check if response contains valid, non-corrupted data."""
        try:
            data = response.json()
            # 1. Check logical status
            if data.get("status") != "ok": 
                return False
            # 2. Check for required keys (incorrect_response faults often miss these)
            if "request_num" not in data:
                return False
            # 3. Check for conflicting info
            if data.get("healthy") is False:
                return False
            return True
        except ValueError:
            return False  # Not valid JSON
    
    # Periodic trust weight update
    current_time = time.time()
    if current_time - last_weight_update_time >= WEIGHT_UPDATE_INTERVAL_SECONDS:
        twlb.update_trust_weights()
        last_weight_update_time = current_time
        
        strategy = "TWLB" if twlb.model_loaded else "RR"
        print(f"\n[{time.strftime('%H:%M:%S')}] --- WEIGHTS UPDATED ({strategy}) ---")
        weights_display = twlb.get_distribution_weights()
        # Only show non-default weights for cleaner output
        active_weights = {k: v for k, v in weights_display.items() if v < 1.0}
        
        # If no weights have dropped, show all weights
        if not active_weights:
             active_weights = weights_display 

        print(f"Active Weights: {active_weights}")
        print("-" * 60)
    
    # Select node
    selected_node = twlb.select_next_node()
    strategy = "TWLB" if twlb.model_loaded else "RR"
    
    # Send request
    try:
        response = requests.get(f"http://{selected_node}:8000/process", timeout=5.0)
        status_code = str(response.status_code)
        
        # --- ACTIVE BYZANTINE VALIDATION ---
        # Don't just trust the status code. Check the content.
        is_valid = True
        if status_code == "200":
             is_valid = validate_response(response)
        
        final_status = status_code
        if not is_valid:
             final_status = "validation_error"  # Treated as non-200 by SVM
             print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | ⚠ VALIDATION FAILED (Lying Node Detected)")
        else:
             print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | Status: {status_code}")

        LB_REQUESTS_TOTAL.labels(selected_node=selected_node, status=final_status).inc()
    except requests.exceptions.Timeout:
        print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | TIMEOUT")
        LB_REQUESTS_TOTAL.labels(selected_node=selected_node, status="timeout").inc()
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] {selected_node} ({strategy}) | ERROR: {type(e).__name__}")
        LB_REQUESTS_TOTAL.labels(selected_node=selected_node, status="error").inc()
    
    # Update self-metrics periodically
    update_lb_self_metrics()


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