import time
import requests
import os

# --- Configuration ---
NODES = [f"node-{i}" for i in range(1, 16)]
NODE_INDEX = 0 

def route_request():
    """
    Selects a worker node using a simple Round Robin strategy 
    and sends a request, ensuring all nodes are hit equally for data generation.
    """
    global NODE_INDEX
    
    # 1. Select node using Round Robin index
    selected_node = NODES[NODE_INDEX]
    
    # 2. Advance the index for the next request
    NODE_INDEX = (NODE_INDEX + 1) % len(NODES)
    
    # 3. Send request to the selected node
    try:
        # Use the internal Docker service name and port 8000
        # Increased timeout to 5.0 seconds to handle the deliberate delay faults
        response = requests.get(f"http://{selected_node}:8000/process", timeout=5.0) 
        
        # Log outcome
        print(f"[{time.strftime('%H:%M:%S')}] ROUTE -> {selected_node} (Strategy: RR) | Status: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        # This handles crashes (ConnectionError) and timeouts (Timeout)
        print(f"[{time.strftime('%H:%M:%S')}] ROUTE -> {selected_node} | FAILURE: {type(e).__name__}")


if __name__ == "__main__":
    print("--- Starting Round Robin Central Operator for Data Collection ---")
    
    while True:
        route_request()
        time.sleep(0.5) # Simulated request interval
