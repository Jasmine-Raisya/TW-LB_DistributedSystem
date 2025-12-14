'''from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, generate_latest
import time
import random
import os
import asyncio
import sys # <-- Added sys import for sys.exit(1)

app = FastAPI()

# --- Configuration & Environment Variables (CORRECTED) ---
NODE_ID = os.getenv("NODE_ID", "node-X") # e.g., 'node-1'

# 1. Extract the number from the ID (e.g., '1' from 'node-1')
try:
    node_number = NODE_ID.split('-')[1]
except IndexError:
    node_number = 'X' # Fallback for safety

# 2. Construct the correct environment variable name (e.g., 'NODE_1_FAULT')
FAULT_ENV_VAR_NAME = f"NODE_{node_number}_FAULT"

# 3. Fetch the value using the correctly constructed name
FAULT_TYPE = os.getenv(FAULT_ENV_VAR_NAME, "benign") 

print(f"--- Node {NODE_ID} initialized. FAULT_TYPE: {FAULT_TYPE} ---")


# --- Prometheus Metrics Initialization ---
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP Requests', 
    ['node_id', 'status']
)
LATENCY = Histogram(
    'request_latency_seconds', 
    'Request latency distribution', 
    ['node_id']
)

# NOTE: The incorrect if __name__ == '__main__': app.run(...) block has been removed, 
# as 'uvicorn main:app' handles server startup correctly.

# --- Endpoint 1: Health Check and Workload Simulation ---
@app.get("/process")
async def process_request():
    start_time = time.time()
    
    # --- Byzantine Fault Injection ---
    if FAULT_TYPE == "crash":
        # Simulate a hard crash. This will result in a FAILURE: ConnectionError on the Load Balancer.
        REQUEST_COUNT.labels(node_id=NODE_ID, status="error").inc()
        print(f"[{NODE_ID}] CRASH fault triggered. Exiting container...")
        sys.exit(1) # <--- GUARANTEES A CONNECTION ERROR

    elif FAULT_TYPE == "delay":
        # Ensure delay exceeds the 5.0s Load Balancer timeout.
        print(f"[{NODE_ID}] DELAY fault triggered. Sleeping for 6.0-7.0 seconds...")
        await asyncio.sleep(random.uniform(6, 7)) # <--- GUARANTEES A TIMEOUT    

    elif FAULT_TYPE == "lie-latency":
        # Simulate a lie: the node is slow, but returns a fake low latency time
        await asyncio.sleep(random.uniform(3, 4))
        # We report success and then the true latency is measured by Prometheus (external)

    # --- Benign Workload Simulation ---
    # Simulate a moderate amount of work (MIPS/processing cycles)
    _ = sum(i * i for i in range(1_000_000))
    
    processing_time = time.time() - start_time
    
    # --- Metrics Reporting ---
    LATENCY.labels(node_id=NODE_ID).observe(processing_time)
    REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
    
    return {
        "node": NODE_ID, 
        "status": "ok", 
        "processed_in": f"{processing_time:.3f}s"
    }

# --- Endpoint 2: Prometheus Scrape Target ---
@app.get("/metrics")
def metrics():
    """
    Prometheus hits this endpoint to scrape the metrics data.
    """
    return Response(generate_latest(), media_type="text/plain")
'''

from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, generate_latest
import time
import random
import os
import asyncio
import sys

app = FastAPI()

# --- Configuration & Environment Variables ---
NODE_ID = os.getenv("NODE_ID", "node-X") # e.g., 'node-1'

# 1. Extract the number from the ID
try:
    node_number = NODE_ID.split('-')[1]
except IndexError:
    node_number = 'X' # Fallback for safety

# 2. Construct the correct environment variable name
FAULT_ENV_VAR_NAME = f"NODE_{node_number}_FAULT"

# 3. Fetch the value using the correctly constructed name
FAULT_TYPE = os.getenv(FAULT_ENV_VAR_NAME, "benign") 

print(f"--- Node {NODE_ID} initialized. FAULT_TYPE: {FAULT_TYPE} ---")


# --- Prometheus Metrics Initialization ---
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP Requests', 
    ['node_id', 'status']
)
LATENCY = Histogram(
    'request_latency_seconds', 
    'Request latency distribution', 
    ['node_id']
)


# --- Endpoint 1: Health Check and Workload Simulation ---
@app.get("/process")
async def process_request():
    start_time = time.time()
    
    # --- Byzantine Fault Injection ---
    
    # CRITICAL FIX: ADDING THE 500-ERROR FAULT INSTRUMENTATION
    if FAULT_TYPE == "500-error":
        print(f"[{NODE_ID}] 500-ERROR fault triggered. Reporting 500 status.")
        
        # 1. Increment the counter with status="500"
        REQUEST_COUNT.labels(node_id=NODE_ID, status="500").inc()
        
        # 2. Return the HTTP 500 response immediately.
        # This bypasses the benign workload simulation below.
        return Response(
            content="500 Internal Server Error (Byzantine Fault)",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    elif FAULT_TYPE == "crash":
        # Simulate a hard crash. This will result in a FAILURE: ConnectionError on the Load Balancer.
        # This metric is captured right before the exit.
        REQUEST_COUNT.labels(node_id=NODE_ID, status="error").inc()
        print(f"[{NODE_ID}] CRASH fault triggered. Exiting container...")
        sys.exit(1) # <--- GUARANTEES A CONNECTION ERROR

    elif FAULT_TYPE == "delay":
        # Ensure delay exceeds the 5.0s Load Balancer timeout.
        print(f"[{NODE_ID}] DELAY fault triggered. Sleeping for 6.0-7.0 seconds...")
        await asyncio.sleep(random.uniform(6, 7)) # <--- GUARANTEES A TIMEOUT 

    elif FAULT_TYPE == "lie-latency":
        # Simulate a lie: the node is slow, but returns a fake low latency time
        await asyncio.sleep(random.uniform(3, 4))
        # Metrics reporting for this case is still handled as 'success' below

    # --- Benign Workload Simulation ---
    # Simulate a moderate amount of work (MIPS/processing cycles)
    _ = sum(i * i for i in range(1_000_000))
    
    processing_time = time.time() - start_time
    
    # --- Metrics Reporting for Successful (Benign/Delay/Lie) Requests ---
    LATENCY.labels(node_id=NODE_ID).observe(processing_time)
    REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
    
    return {
        "node": NODE_ID, 
        "status": "ok", 
        "processed_in": f"{processing_time:.3f}s"
    }

# --- Endpoint 2: Prometheus Scrape Target ---
@app.get("/metrics")
def metrics():
    """
    Prometheus hits this endpoint to scrape the metrics data.
    """
    return Response(generate_latest(), media_type="text/plain")
