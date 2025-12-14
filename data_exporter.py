import pandas as pd
from prometheus_api_client import PrometheusConnect
from datetime import datetime, timedelta
import time
import os
import re

# --- Configuration ---
PROMETHEUS_URL = "http://localhost:9090"
NODES = [f"node-{i}" for i in range(1, 16)]

# Time range to query (query the last 30 minutes)
START_TIME = datetime.now() - timedelta(minutes=30) 
END_TIME = datetime.now()
STEP_SIZE = '1m' # Get a data point every 1 minute

# --- New Function: Get Fault Map from Host Environment ---
def get_fault_map():
    """
    Reads the host's environment variables (where NODE_X_FAULT is set) 
    to create a map of {node_id: fault_type}.
    """
    fault_map = {}
    
    # Iterate through all environment variables set on the host running the script
    for key, value in os.environ.items():
        # Check if the variable matches the pattern NODE_X_FAULT
        match = re.match(r"NODE_(\d+)_FAULT", key)
        if match:
            node_number = match.group(1)
            node_id = f"node-{node_number}"
            fault_map[node_id] = value.lower()
    
    # Default all nodes not found in environment to benign
    for node in NODES:
        if node not in fault_map:
            fault_map[node] = 'benign'
            
    return fault_map

# --- Prometheus Query Language (PQL) ---
def get_pql_queries(node):
    """
    Returns the PQL queries for latency (200 OK only), 500-error count, CPU, and Memory.
    """
    target_instance = f'{node}:8000' 
    
    # Query 1: Average Latency (Now filtering for only Status 200 responses)
    # This ensures we get a cleaner latency reading by excluding failed requests.
    latency_query = f"""
    avg_over_time(request_latency_seconds_sum{{instance="{target_instance}", status="200"}}[{STEP_SIZE}]) 
    / 
    avg_over_time(request_latency_seconds_count{{instance="{target_instance}", status="200"}}[{STEP_SIZE}])
    """
    
    # Query 2: 500 Error Count (RAW COUNT FOR VERIFICATION)
    # This counts the total number of 500 errors in the time range.
    error_count_query = f"""
    sum(increase(http_requests_total{{instance="{target_instance}", status="500"}}[{STEP_SIZE}]))
    """

    # Query 3: CPU Usage (Percentage)
    cpu_query = f"""
    rate(process_cpu_seconds_total{{instance="{target_instance}"}}[{STEP_SIZE}])
    """
    
    # Query 4: Memory Usage (Bytes - focusing on Resident Set Size, RSS)
    memory_query = f"""
    process_resident_memory_bytes{{instance="{target_instance}"}}
    """
    
    return latency_query, error_count_query, cpu_query, memory_query # RETURN ALL FOUR QUERIES

from dotenv import load_dotenv

def fetch_metrics():
    """Fetches all metrics (latency, 500 count, CPU, and Memory) from Prometheus for all nodes."""
    load_dotenv(dotenv_path='./.env', override=True)    
    # 1. CRITICAL: Get the ground truth fault map first
    fault_map = get_fault_map()
    if not any(v != 'benign' for v in fault_map.values()):
        print("\nWARNING: No non-benign faults found in host environment variables. Check your start script (.env)!")
    print(f"\n--- Ground Truth Fault Map: {fault_map} ---")


    try:
        print(f"Connecting to Prometheus at {PROMETHEUS_URL}...")
        prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    except Exception as e:
        print(f"Failed to connect to Prometheus: {e}")
        return None

    all_data = []

    for node in NODES:
        print(f"Fetching data for {node}...")
        # UNPACK ALL FOUR QUERIES
        latency_query, error_count_query, cpu_query, memory_query = get_pql_queries(node)

        try:
            # Fetch Latency Data
            latency_data = prom.custom_query_range(query=latency_query, start_time=START_TIME, end_time=END_TIME, step=STEP_SIZE)
            # Fetch 500 Error Count Data
            error_count_data = prom.custom_query_range(query=error_count_query, start_time=START_TIME, end_time=END_TIME, step=STEP_SIZE)
            # Fetch CPU Data
            cpu_data = prom.custom_query_range(query=cpu_query, start_time=START_TIME, end_time=END_TIME, step=STEP_SIZE)
            # Fetch Memory Data
            memory_data = prom.custom_query_range(query=memory_query, start_time=START_TIME, end_time=END_TIME, step=STEP_SIZE)
            
            # --- Data Processing ---
            
            def extract_values(data):
                values = {}
                if data and data[0].get('values'):
                    for timestamp, value in data[0]['values']:
                        values[timestamp] = float(value) if value not in ('NaN', 'inf', '-inf') else 0.0
                return values

            latency_values = extract_values(latency_data)
            error_count_values = extract_values(error_count_data)
            cpu_values = extract_values(cpu_data)
            memory_values = extract_values(memory_data) # In bytes
            
            # Combine into records
            all_timestamps = set(latency_values.keys()) | set(error_count_values.keys()) | set(cpu_values.keys()) | set(memory_values.keys())

            # 2. Get the correct fault type for this node
            node_fault_type = fault_map.get(node, 'benign')
            
            for timestamp in all_timestamps:
                # Convert memory from bytes to Megabytes (for easier reading)
                mem_mb = memory_values.get(timestamp, 0.0) / (1024 * 1024)
                
                # Use the presence of 500 errors to inform the status code column
                status_code = 500 if error_count_values.get(timestamp, 0) > 0 else 200

                all_data.append({
                    'timestamp': datetime.fromtimestamp(timestamp),
                    'node_id': node,
                    'avg_latency_seconds': latency_values.get(timestamp, 0.0), 
                    'error_500_count': error_count_values.get(timestamp, 0.0), # RAW COUNT
                    'status_code_for_verification': status_code,              # NEW COLUMN (200 or 500)
                    'cpu_usage_rate': cpu_values.get(timestamp, 0.0), 
                    'resident_mem_mb': mem_mb,                
                    'fault_type': node_fault_type # *** FIXED: AUTOMATICALLY LABELED ***
                })

        except Exception as e:
            print(f"Warning: Could not fetch all data for {node}. Error: {e}")
            continue

    if not all_data:
        return None
        
    df = pd.DataFrame(all_data)
    df = df.sort_values(by=['node_id', 'timestamp'])
    
    return df

if __name__ == "__main__":
    
    df = fetch_metrics()
    
    if df is not None and not df.empty:
        filename = f"byzantine_training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print("\n--- DATA COLLECTION SUCCESSFUL & AUTOMATICALLY LABELED ---")
        print(f"Collected {len(df)} data points across {len(NODES)} nodes.")
        print(f"Data saved to: {filename}")
        
        # --- Final Verification ---
        fault_counts = df['fault_type'].value_counts()
        print("\nGround Truth Labels Found in Data:")
        print(fault_counts.to_markdown(numalign="left", stralign="left"))
        
        if len(fault_counts) > 1:
            print("\nSUCCESS: Multiple fault types detected! Your SVM training is now possible.")
        else:
            print("\nWARNING: Only one fault type detected. Ensure you ran `./start_random.sh` in this same terminal session.")
            
    else:
        print("ERROR: Failed to collect data or DataFrame is empty. Ensure Prometheus has collected enough data.")
