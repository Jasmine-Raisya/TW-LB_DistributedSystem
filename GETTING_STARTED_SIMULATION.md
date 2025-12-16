# Getting Started with Realistic Node Simulation

This guide will help you test and understand the realistic node simulation features.

## Quick Start

### 1. Rebuild and Start the System

Since we've updated the node code, rebuild the containers:

```bash
# Stop current system
docker-compose down

# Rebuild with new node code
docker-compose build

# Start the system
docker-compose up -d

# Check logs to see node initialization with their characteristics
docker-compose logs -f node-1 node-2 node-3
```

You should see output like:
```
node-1  | --- Node node-1 initialized ---
node-1  |   FAULT_TYPE: benign
node-1  |   Base Latency: 32.45ms
node-1  |   Base CPU Load: 35.2%
node-1  |   Network Jitter: ±8.12ms
node-1  |   Stability Factor: 0.87
```

### 2. Quick Interactive Test

Run the interactive test script to verify nodes are working:

```bash
python test_simulation.py
```

Choose option **1** to test a single node and observe:
- Variable latencies (network jitter)
- Changing load factors
- Request counts

Example output:
```
Testing node-1 (http://localhost:8001/process)...
------------------------------------------------------------
  Request 1: 45.32ms - {'node': 'node-1', 'status': 'ok', 'processed_in': '0.045s', 'load_factor': '0.73', 'request_num': 1}
  Request 2: 52.18ms - {'node': 'node-1', 'status': 'ok', 'processed_in': '0.052s', 'load_factor': '0.68', 'request_num': 2}
  Request 3: 38.91ms - {'node': 'node-1', 'status': 'ok', 'processed_in': '0.039s', 'load_factor': '0.81', 'request_num': 3}

Summary:
  Successful: 20/20
  Errors: 0
  Timeouts: 0
  Avg Latency: 45.67 ± 8.23ms
  Range: 32.15 - 68.42ms
  Avg Load Factor: 0.74 ± 0.12
```

### 3. Compare Node Characteristics

Test multiple nodes to see their different baseline characteristics:

```bash
python test_simulation.py
# Choose option 2
# Enter: node-1,node-5,node-10
```

This will show how different nodes have different latencies, error rates, and behavior patterns.

### 4. Observe Load Variation Over Time

Watch how load changes dynamically:

```bash
python test_simulation.py
# Choose option 3
# Enter node: node-1
# Duration: 60 seconds
```

You'll see the load factor oscillating (sinusoidal pattern) with occasional spikes.

## Comprehensive Analysis

After the system has been running for **at least 5 minutes**, run the analysis script:

```bash
python analyze_simulation.py
```

This will:
1. ✓ Connect to Prometheus
2. Analyze node baseline characteristics
3. Analyze network noise patterns
4. Analyze Byzantine fault behavior (probabilistic)
5. Generate latency distribution plots
6. Generate load pattern plots

**Generated files:**
- `latency_distribution.png` - Shows latency variation across all nodes
- `load_patterns.png` - Shows CPU load over time (sinusoidal + spikes)
- `byzantine_analysis.png` - Shows which nodes are exhibiting Byzantine behavior

## Understanding the Simulation

### What Makes It Realistic?

1. **Each Node is Different**
   - Different base latencies (10-50ms)
   - Different CPU baselines (20-50%)
   - Different network characteristics
   - Consistent across restarts (seeded with node number)

2. **Dynamic Workload**
   - Load varies over time (sinusoidal pattern)
   - Random traffic spikes (5% chance)
   - Computational work scales with load
   - Realistic I/O patterns

3. **Network Realism**
   - Gaussian jitter distribution
   - Packet loss simulation (0.1-2%)
   - Retransmission delays
   - Per-node variance

4. **Probabilistic Faults**
   - Byzantine nodes don't ALWAYS fail
   - Fault rates increase over time
   - More realistic for ML detection
   
   | Fault Type | Probability | Behavior |
   |------------|-------------|----------|
   | 500-error  | 40% | Intermittent errors |
   | delay      | 50% | Sometimes slow |
   | crash      | 0.1% | Rare crashes |
   | lie-latency| 70% | Often lies about latency |

5. **Resource Metrics**
   - CPU usage with realistic noise
   - Memory growth (simulating leaks)
   - Periodic GC drops

## Testing Byzantine Behavior

### Configure Byzantine Nodes

Edit `docker-compose.yml` to set node faults:

```yaml
environment:
  - NODE_ID=node-10
  - NODE_10_FAULT=500-error  # This node will have 40% error rate
```

Restart that specific node:
```bash
docker-compose up -d node-10
```

### Verify Byzantine Detection

Watch the load balancer logs to see trust weight changes:

```bash
docker-compose logs -f lb
```

You should see:
```
Trust Weights Update:
  node-1: 1.00 (benign, low fault probability)
  node-10: 0.10 (Byzantine detected, high fault probability)
```

## Collecting Training Data

To collect realistic training data for your SVM:

```bash
# Make sure system is running
docker-compose up -d

# Let it run for at least 30 minutes for diverse data
# Then collect metrics
python data_exporter.py

# This will generate training data with realistic noise
```

## Monitoring Prometheus Metrics

Access Prometheus at: http://localhost:9090

**Useful queries:**

1. **Node CPU usage (with noise):**
   ```
   node_cpu_usage_percent{node_id="node-1"}
   ```

2. **Memory usage (with growth pattern):**
   ```
   node_memory_mb{node_id="node-1"}
   ```

3. **Latency distribution:**
   ```
   histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))
   ```

4. **Error rate (Byzantine nodes):**
   ```
   rate(http_requests_total{status="500"}[5m]) / rate(http_requests_total[5m])
   ```

## Troubleshooting

### Nodes not responding
```bash
# Check container status
docker-compose ps

# Check logs for specific node
docker-compose logs node-1

# Restart if needed
docker-compose restart node-1
```

### Cannot connect to Prometheus
```bash
# Verify Prometheus is running
docker-compose ps prometheus

# Check Prometheus logs
docker-compose logs prometheus

# Access Prometheus UI
# http://localhost:9090
```

### Analysis script fails
```bash
# Install dependencies
pip install -r requirements.txt

# Make sure system has been running for at least 5 minutes
# Verify Prometheus connection:
curl http://localhost:9090/api/v1/status/config
```

## Next Steps

1. **Collect Training Data**
   ```bash
   python data_exporter.py
   ```

2. **Retrain SVM Model**
   ```bash
   python train_improved.py
   ```

3. **Test Load Balancer**
   - Watch trust weights adapt to node behavior
   - Monitor request distribution
   - Verify Byzantine nodes are avoided

4. **Analyze Performance**
   - Compare with/without realistic noise
   - Measure SVM detection accuracy
   - Evaluate load balancing effectiveness

## Configuration Tuning

### Increase/Decrease Noise

Edit `node/main.py` and modify these constants:

```python
# More aggressive variation
WORKLOAD_VARIATION = random.uniform(0.5, 0.9)  # More chaos

# Less network noise
NETWORK_JITTER_MS = random.uniform(1, 5)  # Less jitter
PACKET_LOSS_PROBABILITY = random.uniform(0.0001, 0.005)  # Less loss

# More Byzantine faults
base_probability = {
    "500-error": 0.6,  # 60% error rate instead of 40%
    ...
}
```

After changes:
```bash
docker-compose build node
docker-compose up -d
```

## Key Benefits

✅ **More realistic training data** - Better SVM generalization  
✅ **Harder Byzantine detection** - Tests robustness  
✅ **Dynamic behavior** - Simulates real production systems  
✅ **Better evaluation** - More confidence in deployment  
✅ **Insightful analysis** - Understand system behavior patterns  

## Questions?

- Check `REALISTIC_SIMULATION.md` for technical details
- Review `analyze_simulation.py` for metric collection
- Examine `test_simulation.py` for testing patterns
