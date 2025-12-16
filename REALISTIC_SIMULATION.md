# Realistic Node Simulation - Configuration and Documentation

## Overview
This enhanced node implementation simulates realistic distributed system behavior with various noise sources and dynamic patterns to better test the Byzantine fault detection system.

## Key Features Implemented

### 1. **Node-Specific Characteristics**
Each node has unique baseline properties (simulating different hardware):
- **BASE_LATENCY_MS**: 10-50ms (varies per node)
- **BASE_CPU_LOAD**: 20-50% (varies per node)
- **WORKLOAD_VARIATION**: 30-70% variation range
- **NETWORK_JITTER_MS**: 2-15ms jitter
- **PACKET_LOSS_PROBABILITY**: 0.1-2% packet loss
- **STABILITY_FACTOR**: 0.7-1.0 (higher = more stable)

These parameters are seeded with the node number, so each node consistently exhibits different baseline behavior across restarts.

### 2. **Realistic Workload Patterns**

#### Time-Based Load Variation
The `get_time_based_load_factor()` function simulates:
- **Sinusoidal patterns**: Mimicking daily traffic cycles (peak hours vs. off-hours)
- **Traffic spikes**: 5% chance of 1.5-3x load bursts
- **Continuous variation**: Load changes smoothly over time

#### Variable Computational Work
The `simulate_realistic_workload()` function:
- Scales work based on current load factor
- Adds ±20% random variation per request
- Sometimes performs extra I/O-like operations (30% of requests)
- Simulates realistic CPU-bound and memory-bound operations

### 3. **Network Noise Simulation**

#### Network Jitter
- Uses Gaussian distribution for realistic jitter patterns
- Per-node baseline jitter (2-15ms)
- Simulates normal network variance

#### Packet Loss & Retransmission
- Random packet loss (0.1-2% probability)
- Adds 50-150ms delay when packets are "lost" (simulating TCP retransmission)

### 4. **Resource Usage Metrics**

#### CPU Usage
- Correlates with current workload
- Includes Gaussian noise (σ=10%)
- Responds to load factor and time-based patterns
- Realistic range: 0-100%

#### Memory Usage
- Gradual memory growth (simulating minor memory leaks)
- Periodic drops (simulating garbage collection)
- Random noise around baseline
- Realistic range: 128MB+ with gradual increase

### 5. **Probabilistic Byzantine Faults**

Instead of deterministic faults, Byzantine nodes now exhibit **probabilistic** faulty behavior that evolves over time:

| Fault Type   | Base Probability | Behavior                                    |
|--------------|------------------|---------------------------------------------|
| 500-error    | 40%              | Returns HTTP 500 errors intermittently      |
| delay        | 50%              | Timeout delays (6-7s + noise)               |
| crash        | 0.1%             | Rare catastrophic crashes                   |
| lie-latency  | 70%              | Reports success but processes slowly        |

**Time Evolution**: Fault probability increases over time (up to 1.5x after 5 minutes), simulating degrading nodes.

### 6. **Enhanced Metrics**

New Prometheus metrics added:
- `node_cpu_usage_percent`: Real-time simulated CPU usage
- `node_memory_mb`: Real-time simulated memory usage
- Both metrics include realistic noise and patterns

### 7. **Response Enrichment**

The `/process` endpoint now returns:
```json
{
    "node": "node-1",
    "status": "ok",
    "processed_in": "0.123s",
    "load_factor": "0.85",
    "request_num": 42
}
```

Additional `/health` endpoint:
```json
{
    "node": "node-1",
    "status": "healthy",
    "uptime_seconds": "123.4",
    "fault_type": "benign",
    "total_requests": 42
}
```

## Why These Improvements Matter

### For SVM Training
1. **More diverse training data**: Nodes exhibit natural variation beyond just fault/no-fault
2. **Realistic noise**: The SVM learns to distinguish signal from noise
3. **Temporal patterns**: The model can learn time-dependent behavior
4. **Feature richness**: CPU and memory metrics add valuable dimensions

### For Byzantine Detection
1. **Harder to detect**: Probabilistic faults are more realistic and challenging
2. **Gradual degradation**: Models degrading nodes, not just sudden failures
3. **Less perfect separation**: More realistic class boundaries
4. **Better generalization**: Trained on noisy data generalizes better to production

### For Load Balancing
1. **Dynamic trust weights**: Weights update based on current load and performance
2. **Realistic routing**: Selection reflects actual distributed system patterns
3. **Stress testing**: Traffic spikes test the robustness of the algorithm
4. **Performance validation**: Realistic metrics validate actual performance gains

## Implementation Details

### Random Seeding
Each node uses its node number as a random seed for baseline characteristics:
```python
random.seed(node_number)
BASE_LATENCY_MS = random.uniform(10, 50)
# ... other node-specific parameters
```

This ensures:
- Consistent behavior across container restarts
- Different behavior per node
- Reproducible experiments

### Request Flow
1. **Network delay** (jitter + possible packet loss)
2. **Fault check** (probabilistic Byzantine behavior)
3. **Workload simulation** (time-based + random variation)
4. **Micro-delays** (context switching simulation)
5. **Metrics update** (latency, counters, resources)
6. **Response** (with enriched data)

## Testing the Implementation

### Observe Different Node Behaviors
```bash
# Watch node logs to see different baseline parameters
docker-compose logs -f node-1 node-2 node-3
```

### Monitor Metrics
Access Prometheus at `http://localhost:9090` and query:
- `node_cpu_usage_percent` - See varying CPU loads
- `node_memory_mb` - Observe memory patterns
- `request_latency_seconds` - Network jitter and workload variation
- `http_requests_total` - Request counts by status

### Test Byzantine Patterns
Byzantine nodes will now show **intermittent** faults rather than constant failures, making detection more realistic.

## Configuration Options

### Adjust Noise Levels
Modify these constants in `node/main.py` to tune simulation realism:

```python
# For more/less network noise
NETWORK_JITTER_MS = random.uniform(2, 15)  # Increase range for more jitter

# For more/less packet loss
PACKET_LOSS_PROBABILITY = random.uniform(0.001, 0.02)  # Adjust range

# For more/less workload variation
WORKLOAD_VARIATION = random.uniform(0.3, 0.7)  # Increase for more chaos
```

### Adjust Fault Probabilities
Modify fault probabilities in `get_fault_probability()`:

```python
base_probability = {
    "500-error": 0.4,      # Increase for more frequent errors
    "delay": 0.5,          # Increase for more timeouts
    "crash": 0.001,        # Keep low to avoid too many crashes
    "lie-latency": 0.7,    # Increase for more lying behavior
}
```

## Expected Impact on SVM Model

### Benefits
1. **Reduced overfitting**: More realistic noise prevents memorization
2. **Better precision/recall tradeoff**: Model learns softer decision boundaries
3. **Improved real-world performance**: Training data closer to production patterns
4. **More robust features**: Features must be discriminative despite noise

### Challenges
1. **May need more data**: Noise requires larger training sets
2. **Longer training time**: More complex patterns take longer to learn
3. **Careful hyperparameter tuning**: Regularization becomes more critical
4. **Feature engineering**: May need to engineer features to handle noise

## Next Steps

1. **Collect new training data** with these realistic simulations
2. **Retrain SVM model** on the enhanced dataset
3. **Compare performance** metrics (precision, recall, F1) before/after
4. **Monitor trust weights** in the load balancer to see dynamic adaptation
5. **Tune simulation parameters** based on observed model performance
