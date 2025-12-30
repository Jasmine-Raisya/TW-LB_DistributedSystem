from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import random
import os
import asyncio
import sys
import math
import psutil
import psutil
from datetime import datetime
from byzantine_faults import AdvancedByzantine

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
process = psutil.Process()
advanced_faults = AdvancedByzantine(NODE_ID)


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
    Update CPU and memory metrics with REAL resource measurements.
    """
    try:
        # Get real CPU usage for this process
        # interval=None makes it non-blocking
        cpu_usage = process.cpu_percent()
        
        # Get real Memory usage (RSS) in MB
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        CPU_USAGE.labels(node_id=NODE_ID).set(cpu_usage)
        MEMORY_USAGE.labels(node_id=NODE_ID).set(memory_mb)
        
        if random.random() < 0.05: # Occasional internal debug log
             print(f"[{NODE_ID}] REAL METRICS: CPU={cpu_usage:.1f}%, MEM={memory_mb:.1f}MB")
             
    except Exception as e:
        print(f"[{NODE_ID}] Error updating metrics: {e}")


def get_fault_probability():
    """
    For Byzantine nodes, faults might not happen 100% of the time.
    This makes detection more realistic and challenging.
    """
    if FAULT_TYPE == "benign":
        return 0.0
    
    # Byzantine nodes exhibit faults with probability, not always
    base_probability = {
        "500-error": 0.4,           # 40% of requests fail
        "delay": 0.5,               # 50% of requests are delayed
        "crash": 0.001,             # Very rare, but can crash
        "lie-latency": 0.7,         # 70% of requests have fake latency
        # NEW SOPHISTICATED FAULTS
        "selective_failure": 0.3,   # 30% base, but context-dependent
        "incorrect_response": 0.25, # 25% return subtly wrong data
        "timing_attack": 0.2,       # 20% strategic delays
        "mixed_faults": 0.35,       # 35% unpredictable mix
        
        # --- ADVANCED FAULTS ---
        "subtle_data_corruption": 0.3, # 30% of requests have corruption
        "strategic_timing": 0.3,       # 30% of critical requests delayed
        "advanced_mixed": 0.4,         # 40% combined advanced behaviors
    }.get(FAULT_TYPE, 0.0)
    
    # Add time-based variation (faults might get worse over time)
    time_factor = min(1.5, 1.0 + (time.time() - start_timestamp) / 300)
    
    return min(1.0, base_probability * time_factor)


# --- NEW SOPHISTICATED FAULT HANDLERS ---

async def handle_selective_failure(request_num: int) -> Response:
    """
    Selective Failure: Only fail for specific patterns.
    More sophisticated than random - targets high-value or critical requests.
    """
    # Fail on requests that are multiples of 7 (simulating pattern-based attack)
    # Or requests in the "critical" range (every 50th request)
    is_critical = request_num % 50 == 0
    is_targeted = request_num % 7 == 0
    
    if is_critical or is_targeted:
        print(f"[{NODE_ID}] SELECTIVE_FAILURE triggered (request #{request_num})")
        return Response(
            content="500 Selective Failure (Byzantine Fault)",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return None  # Continue normally


def generate_incorrect_response(request_num: int) -> dict:
    """
    Incorrect Response: Return subtly corrupted but valid-looking JSON.
    This is harder to detect than outright errors.
    """
    corruptions = [
        # Slightly wrong numeric values
        {"node": NODE_ID, "status": "ok", "result": 42.001, "request_num": request_num},
        # Missing expected fields
        {"node": NODE_ID, "status": "ok", "request_num": request_num},
        # Wrong status but still 200 OK
        {"node": NODE_ID, "status": "partial", "result": None, "request_num": request_num},
        # Stale data (old timestamp)
        {"node": NODE_ID, "status": "ok", "timestamp": "2020-01-01T00:00:00", "request_num": request_num},
        # Conflicting information
        {"node": NODE_ID, "status": "ok", "healthy": False, "request_num": request_num},
    ]
    return random.choice(corruptions)


async def handle_timing_attack() -> None:
    """
    Timing Attack: Strategic delays that are hard to distinguish from network issues.
    Shorter than full "delay" fault, but still disruptive.
    Shallow delay (0.5-2.0s) to frustrate clients without triggering timeouts.
    """
    # Reduced to 0.5-2.0s to ensure we never hit the 5s LB timeout
    delay = random.uniform(0.5, 2.0)
    print(f"[{NODE_ID}] TIMING_ATTACK triggered (delay: {delay:.2f}s)")
    await asyncio.sleep(delay)


async def handle_mixed_faults(request_num: int) -> tuple:
    """
    Mixed Faults: Unpredictable combination of behaviors.
    Most difficult to detect due to randomness.
    Returns (response, should_continue) tuple.
    """
    fault_choice = random.choice(["selective", "incorrect", "timing", "normal"])
    
    if fault_choice == "selective":
        result = await handle_selective_failure(request_num)
        if result:
            return (result, False)
    elif fault_choice == "incorrect":
        return (generate_incorrect_response(request_num), False)
    elif fault_choice == "timing":
        await handle_timing_attack()
        # Continue with normal response after timing attack
    
    return (None, True)  # Continue normally


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
        # REDUCED from 6-7s to 2.0-3.0s to avoid massive timeouts
        # but still high enough to be distinct from benign lag
        delay_time = random.uniform(2.0, 3.0) 
        print(f"[{NODE_ID}] DELAY fault triggered. Sleeping {delay_time:.2f}s")
        await asyncio.sleep(delay_time)
    
    elif fault_occurs and FAULT_TYPE == "lie-latency":
        # Actual slow processing
        await asyncio.sleep(random.uniform(3, 4.5))
        # But will report success quickly
    
    # --- NEW SOPHISTICATED FAULTS ---
    elif fault_occurs and FAULT_TYPE == "selective_failure":
        result = await handle_selective_failure(request_count)
        if result:
            REQUEST_COUNT.labels(node_id=NODE_ID, status="500").inc()
            processing_time = time.time() - start_time
            LATENCY.labels(node_id=NODE_ID).observe(processing_time)
            return result
    
    elif fault_occurs and FAULT_TYPE == "incorrect_response":
        print(f"[{NODE_ID}] INCORRECT_RESPONSE fault triggered")
        REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()  # Looks successful!
        processing_time = time.time() - start_time
        LATENCY.labels(node_id=NODE_ID).observe(processing_time)
        return generate_incorrect_response(request_count)
    
    elif fault_occurs and FAULT_TYPE == "timing_attack":
        await handle_timing_attack()
        # Continue with normal response after timing attack
    
    elif fault_occurs and FAULT_TYPE == "mixed_faults":
        result, should_continue = await handle_mixed_faults(request_count)
        if not should_continue:
            REQUEST_COUNT.labels(node_id=NODE_ID, status="500" if isinstance(result, Response) else "success").inc()
            processing_time = time.time() - start_time
            LATENCY.labels(node_id=NODE_ID).observe(processing_time)
            return result

    # --- ADVANCED FAULT HANDLING ---
    elif fault_occurs and FAULT_TYPE == "subtle_data_corruption":
        # Generate valid response but corrupt numbers
        base_response = {
            "node": NODE_ID,
            "status": "ok",
            "processed_in": f"{time.time() - start_time:.3f}s",
            "load_factor": "0.50",
            "request_num": request_count,
            "healthy": True
        }
        # Log generic success, but content is corrupted
        REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
        processing_time = time.time() - start_time
        LATENCY.labels(node_id=NODE_ID).observe(processing_time)
        return advanced_faults.subtle_data_corruption(base_response)

    elif fault_occurs and FAULT_TYPE == "strategic_timing":
        await advanced_faults.strategic_timing_attack()
        # Continue to process normally after delay
        
    elif fault_occurs and FAULT_TYPE == "advanced_mixed":
        # Randomly choose an advanced behavior
        behavior = random.choice(["subtle", "timing", "lying", "consistency"])
        
        if behavior == "subtle":
             base_response = {
                "node": NODE_ID, "status": "ok", "processed_in": "0.1s", 
                "request_num": request_count, "healthy": True
             }
             REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
             return advanced_faults.subtle_data_corruption(base_response)
        elif behavior == "timing":
             await advanced_faults.strategic_timing_attack()
        elif behavior == "lying":
             # Create a dummy response to pass to selective_lying
             dummy = {"node": NODE_ID, "status": "ok", "result": 100, "request_num": request_count}
             REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
             return advanced_faults.selective_lying(request_count, dummy)
        elif behavior == "consistency":
             dummy = {
                 "node": NODE_ID, "status": "ok", "timestamp": str(datetime.now()),
                 "version": 2, "request_num": request_count
             }
             REQUEST_COUNT.labels(node_id=NODE_ID, status="success").inc()
             return advanced_faults.consistency_attack(dummy)

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
