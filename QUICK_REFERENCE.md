# Quick Reference Card - Realistic Node Simulation

## Quick Commands

### Start System
```bash
docker-compose build
docker-compose up -d
```

### Watch Node Initialization
```bash
docker-compose logs -f node-1 node-2 node-3
```

### Quick Test
```bash
python test_simulation.py
```

### Comprehensive Analysis (after 5+ min)
```bash
python analyze_simulation.py
```

### Collect Training Data
```bash
python data_exporter.py
```

### Stop System
```bash
docker-compose down
```

## Node Characteristics (Auto-Generated Per Node)

| Parameter | Range | Description |
|-----------|-------|-------------|
| Base Latency | 10-50ms | Processing time baseline |
| Base CPU | 20-50% | CPU usage baseline |
| Network Jitter | ±2-15ms | Network delay variance |
| Packet Loss | 0.1-2% | Simulated packet loss rate |
| Stability | 0.7-1.0 | Node stability factor |

## Byzantine Fault Probabilities

| Fault Type | Probability | Behavior |
|------------|-------------|----------|
| 500-error | 40% | Returns HTTP 500 |
| delay | 50% | Timeout delays (6-7s) |
| crash | 0.1% | Container crashes |
| lie-latency | 70% | Slow but reports success |

*Note: Probabilities increase over time (up to 1.5x)*

## Useful Prometheus Queries

Access: http://localhost:9090

### CPU Usage
```
node_cpu_usage_percent{node_id="node-1"}
```

### Memory Pattern
```
node_memory_mb{node_id="node-1"}
```

### Error Rate
```
rate(http_requests_total{status="500"}[5m]) / rate(http_requests_total[5m])
```

### 95th Percentile Latency
```
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))
```

## Test Endpoints

### Process Request (with simulation)
```bash
curl http://localhost:8001/process
```
Response:
```json
{
  "node": "node-1",
  "status": "ok",
  "processed_in": "0.045s",
  "load_factor": "0.73",
  "request_num": 42
}
```

### Health Check
```bash
curl http://localhost:8001/health
```
Response:
```json
{
  "node": "node-1",
  "status": "healthy",
  "uptime_seconds": "123.4",
  "fault_type": "benign",
  "total_requests": 42
}
```

### Metrics (Prometheus)
```bash
curl http://localhost:8001/metrics
```

## Configuration Files

| File | Purpose |
|------|---------|
| `node/main.py` | Node simulation code |
| `docker-compose.yml` | Container configuration |
| `.env` | Fault type configuration |
| `REALISTIC_SIMULATION.md` | Technical docs |
| `GETTING_STARTED_SIMULATION.md` | Usage guide |

## Tuning Parameters

Edit `node/main.py` constants:

```python
# More noise
NETWORK_JITTER_MS = random.uniform(5, 25)  # Increase jitter

# Less packet loss
PACKET_LOSS_PROBABILITY = random.uniform(0.0001, 0.005)

# More workload chaos
WORKLOAD_VARIATION = random.uniform(0.5, 0.9)

# Higher fault rates
base_probability = {
    "500-error": 0.6,  # 60% instead of 40%
}
```

Rebuild after changes:
```bash
docker-compose build node
docker-compose up -d
```

## Expected Metrics (Typical Values)

### Benign Node
- Latency: 20-80ms (variable)
- Error rate: 0%
- CPU: 20-60% (oscillating)
- Memory: 256-400MB (growing)

### Byzantine Node (500-error)
- Latency: Variable
- Error rate: 40-60%
- CPU: Erratic
- Memory: Similar to benign

## Troubleshooting

### Nodes not responding
```bash
docker-compose ps
docker-compose logs node-1
docker-compose restart node-1
```

### Can't connect to Prometheus
```bash
curl http://localhost:9090/api/v1/status/config
docker-compose logs prometheus
```

### Analysis script fails
```bash
pip install -r requirements.txt
# Wait 5+ minutes after starting system
```

## File Outputs

### From `analyze_simulation.py`
- `latency_distribution.png` - Latency across nodes
- `load_patterns.png` - CPU over time
- `byzantine_analysis.png` - Fault detection

### From `data_exporter.py`
- `training_data_YYYY-MM-DD_HH-MM-SS.csv` - ML training data

## Key Features at a Glance

✅ **Unique per node** - Different baselines  
✅ **Dynamic over time** - Load varies  
✅ **Network realistic** - Jitter + loss  
✅ **Probabilistic faults** - Not 100% deterministic  
✅ **Resource patterns** - CPU/Memory noise  
✅ **Easy analysis** - Built-in tools  

## Next Steps Workflow

1. **Start system** → `docker-compose up -d`
2. **Quick test** → `python test_simulation.py`
3. **Wait 5+ min** → Let metrics accumulate
4. **Analyze** → `python analyze_simulation.py`
5. **Collect data** → `python data_exporter.py`
6. **Retrain SVM** → `python train_improved.py`
7. **Test LB** → Monitor trust weights

## Documentation Index

- **Quick Start**: `GETTING_STARTED_SIMULATION.md`
- **Technical Details**: `REALISTIC_SIMULATION.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY.md`
- **Analysis Tool**: `analyze_simulation.py`
- **Test Tool**: `test_simulation.py`
- **Main README**: `README.md`

## Support

For issues or questions:
1. Check documentation files
2. Review logs: `docker-compose logs [service]`
3. Verify Prometheus: http://localhost:9090
4. Test individual nodes: `python test_simulation.py`
