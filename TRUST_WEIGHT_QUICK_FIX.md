# Trust Weight Calculation - Quick Summary

## ❌ Why It's Currently Failing

Your load balancer **cannot calculate trust weights** because:

### 1. No Model Artifacts Exist
```
❌ Missing: ./artifacts/tw_lb_svm_model.joblib
❌ Missing: ./artifacts/feature_scaler.joblib
❌ Missing: ./artifacts/label_encoder.joblib
```

**Current behavior**: Load balancer falls back to **Round Robin** mode (no ML).

### 2. Prometheus Query Mismatch (FIXED)
**Was querying**: `process_cpu_seconds_total`, `process_resident_memory_bytes`  
**Should query**: `node_cpu_usage_percent`, `node_memory_mb` (from realistic simulation)

**Status**: ✅ **FIXED** in the recent code update.

## ✅ How to Fix It (3 Steps)

### Step 1: Collect Training Data
```bash
# Start system
docker-compose up -d

# Wait 2-3 minutes for metrics
sleep 180

# Export training data
python data_exporter.py
```

**Output**: `training_data_YYYY-MM-DD_HH-MM-SS.csv`

### Step 2: Train Model
```bash
python train_improved.py
```

**Output**: Creates `./artifacts/` directory with 3 files:
- `tw_lb_svm_model.joblib`
- `feature_scaler.joblib`
- `label_encoder.joblib`

### Step 3: Rebuild Load Balancer
```bash
# Rebuild to include artifacts
docker-compose build tw-lb

# Restart load balancer
docker-compose up -d tw-lb

# Watch it work!
docker-compose logs -f tw-lb
```

## 📊 Expected Logs After Fix

### Before (Round Robin Mode)
```
tw-lb | ⚠ WARNING: Model artifacts not found
tw-lb | ⚠ Falling back to Round Robin routing
tw-lb | [14:55:23] node-1 (RR) | Status: 200
tw-lb | [14:55:24] node-2 (RR) | Status: 200
tw-lb | [14:55:25] node-5 (RR) | Status: 500  ← No penalty!
```

### After (TWLB Mode with Realistic Simulation)
```
tw-lb | ✓ TWLB initialized successfully
tw-lb | ✓ Connected to Prometheus at http://prometheus:9090
tw-lb | 
tw-lb | [14:56:01] Updating trust weights...
tw-lb | DEBUG METRICS (node-1): {'avg_latency_seconds': 0.0423, 'error_count': 0.0, 'cpu_usage_rate': 0.352, 'resident_mem_mb': 45.23}
tw-lb | DEBUG PREDICT (node-1): Features=0.00 (Error), P_Faulty(500-error)=0.023, Classes=['benign' '500-error' 'delay']
tw-lb | DEBUG METRICS (node-5): {'avg_latency_seconds': 0.0512, 'error_count': 12.3, 'cpu_usage_rate': 0.423, 'resident_mem_mb': 48.92}
tw-lb | DEBUG PREDICT (node-5): Features=12.30 (Error), P_Faulty(500-error)=0.876, Classes=['benign' '500-error' 'delay']
tw-lb | 
tw-lb | [14:56:01] --- WEIGHTS UPDATED (TWLB) ---
tw-lb | Active Weights: {'node-5': 0.1}  ← Byzantine node penalized!
tw-lb | ------------------------------------------------------------
tw-lb | 
tw-lb | [14:56:02] node-3 (TWLB) | Status: 200
tw-lb | [14:56:02] node-1 (TWLB) | Status: 200
tw-lb | [14:56:03] node-7 (TWLB) | Status: 200
tw-lb | [14:56:05] node-5 (TWLB) | Status: 500  ← Rarely selected!
```

## 🎯 Key Differences

| Aspect | WITHOUT Artifacts | WITH Artifacts |
|--------|------------------|----------------|
| **Mode** | Round Robin | Trust-Weighted |
| **Routing** | Sequential | Probability-based |
| **Byzantine Detection** | None | Automatic |
| **Logs** | Simple | Detailed metrics + predictions |
| **node-5 selection** | Equal (6.67%) | Rare (~1%) |

## 🔍 Node Logs (Realistic Simulation)

### Benign Node
```
node-1 | --- Node node-1 initialized ---
node-1 |   FAULT_TYPE: benign
node-1 |   Base Latency: 32.45ms
node-1 |   Base CPU Load: 35.20%
node-1 |   Network Jitter: ±8.12ms
node-1 |   Stability Factor: 0.87
```

### Byzantine Node (500-error)
```
node-5 | --- Node node-5 initialized ---
node-5 |   FAULT_TYPE: 500-error
node-5 |   Base Latency: 28.91ms
node-5 |   Base CPU Load: 42.30%
node-5 |   Network Jitter: ±12.34ms
node-5 |   Stability Factor: 0.73
node-5 | [node-5] 500-ERROR fault triggered (probabilistic)
node-5 | INFO: 172.18.0.5:48234 - "GET /process HTTP/1.1" 500
node-5 | INFO: 172.18.0.5:48235 - "GET /process HTTP/1.1" 200  ← Sometimes succeeds!
node-5 | [node-5] 500-ERROR fault triggered (probabilistic)
node-5 | INFO: 172.18.0.5:48236 - "GET /process HTTP/1.1" 500
```

## 🚨 Common Issues

### Issue: "All weights are 1.0"
**Cause**: No Byzantine nodes configured or not enough error data
**Fix**: 
```yaml
# In docker-compose.yml, add:
environment:
  - NODE_5_FAULT=500-error
  - NODE_10_FAULT=delay
```

### Issue: "DEBUG METRICS shows all zeros"
**Cause**: Prometheus not scraping or nodes not running
**Fix**: 
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check node directly
curl http://localhost:8001/metrics
```

### Issue: "P_Faulty is always ~0.5"
**Cause**: Model not trained properly or features don't match
**Fix**: Retrain with more diverse data (wait longer before collecting)

## 📁 File Checklist

Before rebuilding load balancer:
- ✅ `./artifacts/tw_lb_svm_model.joblib` exists
- ✅ `./artifacts/feature_scaler.joblib` exists
- ✅ `./artifacts/label_encoder.joblib` exists
- ✅ Training data CSV exists
- ✅ `docker-compose.yml` has byzantine nodes configured

## 🎓 Understanding Trust Weights

```python
# From the code:
if p_faulty < 0.20:
    trust_weight = 1.0    # Fully trusted (benign)
elif p_faulty < 0.60:
    trust_weight = 0.5    # Partially trusted (suspicious)
else:
    trust_weight = 0.1    # Low trust (Byzantine)
```

**Example**:
- node-1: 0 errors → P(Faulty) = 0.02 → Weight = 1.0 ✓
- node-5: 12 errors → P(Faulty) = 0.88 → Weight = 0.1 ✓
- node-10: 2 errors → P(Faulty) = 0.45 → Weight = 0.5 ⚠️

## 🎯 Next Steps

1. Follow the 3 steps above to create artifacts
2. Check `TRUST_WEIGHT_TROUBLESHOOTING.md` for detailed examples
3. Check `REALISTIC_SIMULATION.md` for simulation details
4. Use `test_simulation.py` to verify node behavior
5. Use `analyze_simulation.py` to visualize metrics

**Full documentation**: `TRUST_WEIGHT_TROUBLESHOOTING.md`
