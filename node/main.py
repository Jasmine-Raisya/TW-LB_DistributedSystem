from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import random
import os
import asyncio
import sys
import math
from datetime import datetime

app = FastAPI()

# --- Configuration & Environment Variables ---
NODE_ID = os.getenv("NODE_ID", "node-X")

# Extract node number
try:
    node_number = int(NODE_ID.split('-')[1])
except (IndexError, ValueError):
    node_number = 0

# Construct fault environment variable name
FAULT_ENV_VAR_NAME = f"NODE_{node_number}_FAULT"
FAULT_TYPE = os.getenv(FAULT_ENV_VAR_NAME, "benign")

# --- REALISTIC SIMULATION PARAMETERS ---
# Each node has slightly different baseline characteristics
random.seed(node_number)  # Consistent but varied per node

# Baseline performance varies by node (simulating different hardware)
BASE_LATENCY_MS = random.uniform(10, 50)  # Base processing time
BASE_CPU_LOAD = random.uniform(0.2, 0.5)  # Base CPU percentage
WORKLOAD_VARIATION = random.uniform(0.3, 0.7)  # How much workload varies

# Network characteristics (simulating real network conditions)
NETWORK_JITTER_MS = random.uniform(2, 15)  # Network jitter range
PACKET_LOSS_PROBABILITY = random.uniform(0.001, 0.02)  # 0.1% - 2% packet loss

# Node behavior patterns (some nodes are naturally more stable)
STABILITY_FACTOR = random.uniform(0.7, 1.0)  # Higher = more stable

print(f"--- Node {NODE_ID} initialized ---")
print(f"  FAULT_TYPE: {FAULT_TYPE}")
print(f"  Base Latency: {BASE_LATENCY_MS:.2f}ms")
print(f"  Base CPU Load: {BASE_CPU_LOAD:.2%}")
print(f"  Network Jitter: ±{NETWORK_JITTER_MS:.2f}ms")
print(f"  Stability Factor: {STABILITY_FACTOR:.2f}")

# --- Prometheus Metrics ---
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
# Additional metrics for realism
CPU_USAGE = Gauge(
    'node_cpu_usage_percent',
    'Simulated CPU usage percentage',
    ['node_id']
)
MEMORY_USAGE = Gauge(
    'node_memory_mb',
    'Simulated memory usage in MB',
    ['node_id']
)

# --- Global State for Dynamic Behavior ---
request_count = 0
start_timestamp = time.time()


# --- REALISTIC WORKLOAD SIMULATION FUNCTIONS ---

def get_time_based_load_factor():
    """
    Simulate realistic load patterns that change over time.
    Creates daily and hourly cycles similar to real systems.
    """
    current_time = time.time() - start_timestamp
    
    # Sinusoidal load pattern (simulating daily traffic patterns)
    # Peak during certain hours, lower at others
    hourly_cycle = 0.5 + 0.5 * math.sin(current_time / 10)  # Fast cycle for demo
    
    # Add some random spikes (simulating burst traffic)
    spike = 1.0
    if random.random() < 0.05:  # 5% chance of traffic spike
        spike = random.uniform(1.5, 3.0)
    
    return hourly_cycle * spike


def simulate_realistic_workload(intensity: float):
    """
    Simulate CPU-bound work with realistic variation.
    Intensity: 0.0 to 1.0+ (can exceed 1.0 during spikes)
    """
    # Base work amount
    base_work = 500_000
    
    # Add intensity factor and random noise
    work_amount = int(base_work * intensity * random.uniform(0.8, 1.2))
    
    # Perform the work
    _ = sum(i * i for i in range(work_amount))
    
    # Simulate some I/O or memory access patterns
    if random.random() < 0.3:  # 30% of requests do extra work
        _ = [random.random() for _ in range(random.randint(100, 1000))]


def add_network_noise():
    """
    Simulate realistic network jitter and delays.
    Returns the delay in seconds.
    """
    # Normal network jitter (Gaussian distribution)
    jitter = random.gauss(0, NETWORK_JITTER_MS / 3) / 1000
    
    # Occasional packet retransmission delay
    if random.random() < PACKET_LOSS_PROBABILITY:
        jitter += random.uniform(0.05, 0.15)  # Retransmission delay
    
    return abs(jitter)


def update_resource_metrics():
    """
    Update CPU and memory metrics with realistic noise.
    """
    global request_count
    
    # CPU usage varies with load and has random noise
    load_factor = get_time_based_load_factor()
    cpu_noise = random.gauss(0, 10)  # Gaussian noise
    cpu_usage = min(100, max(0, BASE_CPU_LOAD * 100 * load_factor + cpu_noise))
    
    # Memory usage slowly grows (memory leaks?) then occasionally drops (GC)
    base_memory = 256 + (request_count % 100) * 2  # Gradual increase
    memory_noise = random.gauss(0, 20)
    memory_usage = max(128, base_memory + memory_noise)
    
    CPU_USAGE.labels(node_id=NODE_ID).set(cpu_usage)
    MEMORY_USAGE.labels(node_id=NODE_ID).set(memory_usage)


def get_fault_probability():
    """
    For Byzantine nodes, faults might not happen 100% of the time.
    This makes detection more realistic and challenging.
    """
    if FAULT_TYPE == "benign":
        return 0.0
    
    # Byzantine nodes exhibit faults with probability, not always
    base_probability = {
        "500-error": 0.4,      # 40% of requests fail
        "delay": 0.5,          # 50% of requests are delayed
        "crash": 0.001,        # Very rare, but can crash
        "lie-latency": 0.7,    # 70% of requests have fake latency
    }.get(FAULT_TYPE, 0.0)
    
    # Add time-based variation (faults might get worse over time)
    time_factor = min(1.5, 1.0 + (time.time() - start_timestamp) / 300)
    
    return min(1.0, base_probability * time_factor)


# --- MAIN REQUEST PROCESSING ENDPOINT ---

@app.get("/process")
async def process_request():
    global request_count
    request_count += 1
    
    start_time = time.time()
    
    # --- REALISTIC NOISE: Network Jitter ---
    network_delay = add_network_noise()
    await asyncio.sleep(network_delay)
    
    # --- BYZANTINE FAULT INJECTION (Probabilistic) ---
    fault_occurs = random.random() < get_fault_probability()
    
    if fault_occurs and FAULT_TYPE == "500-error":
        print(f"[{NODE_ID}] 500-ERROR fault triggered (probabilistic)")
        REQUEST_COUNT.labels(node_id=NODE_ID, status="500").inc()
        processing_time = time.time() - start_time
        LATENCY.labels(node_id=NODE_ID).observe(processing_time)
        update_resource_metrics()
        
        return Response(
            content="500 Internal Server Error (Byzantine Fault)",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    elif fault_occurs and FAULT_TYPE == "crash":
        print(f"[{NODE_ID}] CRASH fault triggered. Exiting...")
        REQUEST_COUNT.labels(node_id=NODE_ID, status="error").inc()
        sys.exit(1)
    
    elif fault_occurs and FAULT_TYPE == "delay":
        # Variable delay with noise
        delay_time = random.uniform(6, 7) + random.gauss(0, 0.3)
        print(f"[{NODE_ID}] DELAY fault triggered. Sleeping {delay_time:.2f}s")
        await asyncio.sleep(delay_time)
    
    elif fault_occurs and FAULT_TYPE == "lie-latency":
        # Actual slow processing
        await asyncio.sleep(random.uniform(3, 4.5))
        # But will report success quickly
    
    # --- REALISTIC WORKLOAD SIMULATION ---
    load_factor = get_time_based_load_factor()
    workload_intensity = BASE_CPU_LOAD + WORKLOAD_VARIATION * (load_factor - 0.5)
    
    # Add random micro-variations
    workload_intensity *= random.uniform(0.9, 1.1)
    
    # Simulate the actual computational work
    simulate_realistic_workload(workload_intensity)
    
    # Add small random processing delay (context switching, I/O, etc.)
    await asyncio.sleep(random.uniform(0.001, 0.01))
    
    # --- METRICS REPORTING ---
    processing_time = time.time() - start_time
    LATENCY.labels(node_id=NODE_ID).observe(processing_time)
    REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
    
    # Update resource usage metrics
    update_resource_metrics()
    
    return {
        "node": NODE_ID,
        "status": "ok",
        "processed_in": f"{processing_time:.3f}s",
        "load_factor": f"{load_factor:.2f}",
        "request_num": request_count
    }


@app.get("/metrics")
def metrics():
    """
    Prometheus scrapes this endpoint for metrics.
    """
    return Response(generate_latest(), media_type="text/plain")


@app.get("/health")
def health():
    """
    Basic health check endpoint.
    """
    uptime = time.time() - start_timestamp
    return {
        "node": NODE_ID,
        "status": "healthy",
        "uptime_seconds": f"{uptime:.1f}",
        "fault_type": FAULT_TYPE,
        "total_requests": request_count
    }
