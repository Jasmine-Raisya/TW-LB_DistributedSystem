# Trust Weight Calculation Issues & Solutions

## 🔍 Root Cause Analysis

### Issue #1: Missing Artifacts Directory
**Problem**: The load balancer fails to calculate trust weights because the ML model artifacts don't exist.

**Evidence**:
```
c:\Users\Ivy\...\TW-LB_DistributedSystem_SVM\lb\
├── Dockerfile
├── load_balancer.py
├── requirements.txt
└── ❌ NO artifacts/ directory!
```

**What the load balancer expects**:
```python
# From load_balancer.py lines 19-22
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), 'artifacts')
SCALER_FILE = os.path.join(ARTIFACTS_DIR, 'feature_scaler.joblib')
MODEL_FILE = os.path.join(ARTIFACTS_DIR, 'tw_lb_svm_model.joblib')
ENCODER_FILE = os.path.join(ARTIFACTS_DIR, 'label_encoder.joblib')
```

**What actually happens**: Load balancer starts but falls back to Round Robin mode.

### Issue #2: No Training Data Collected Yet
**Problem**: You haven't collected training data with the realistic simulation yet.

**Current state**:
- ❌ No `training_data_*.csv` file
- ❌ No trained model artifacts
- ❌ Load balancer can't use ML-based trust weights

## ✅ Solution Steps

### Step 1: Collect Realistic Training Data

First, start the system to collect data:

```bash
# Start all services
docker-compose up -d

# Wait 2-3 minutes for metrics to accumulate
# Watch the nodes to see realistic simulation in action
docker-compose logs -f node-1 node-2 node-5
```

**Expected node logs**:
```
node-1  | --- Node node-1 initialized ---
node-1  |   FAULT_TYPE: benign
node-1  |   Base Latency: 32.45ms
node-1  |   Base CPU Load: 35.2%
node-1  |   Network Jitter: ±8.12ms
node-1  |   Stability Factor: 0.87
node-1  | INFO:     Started server process [1]
node-1  | INFO:     Uvicorn running on http://0.0.0.0:8000

node-5  | --- Node node-5 initialized ---
node-5  |   FAULT_TYPE: 500-error  ← Byzantine node!
node-5  |   Base Latency: 28.91ms
node-5  |   Base CPU Load: 42.3%
node-5  |   Network Jitter: ±12.34ms
node-5  |   Stability Factor: 0.73
node-5  | [node-5] 500-ERROR fault triggered (probabilistic)
```

### Step 2: Export Training Data

After 2-3 minutes, collect the data:

```bash
python data_exporter.py
```

**Expected output**:
```
Loading data from: byzantine_training_data_20241216_145500.csv
Data preparation complete. Saved artifacts to ./artifacts/
Features used: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
✓ Training data exported: training_data_20241216_145500.csv
```

### Step 3: Train the SVM Model

```bash
python train_improved.py
```

**Expected output**:
```
Loading data from: byzantine_training_data_20241216_145500.csv
Class Distribution: {'benign': 8500, '500-error': 450, 'delay': 320}

Searching for best hyperparameters on 6489 samples...
Fitting 5 folds for each of 40 candidates, totalling 200 fits

Best Parameters: {'estimator__C': 10, 'estimator__gamma': 'scale', 'estimator__class_weight': 'balanced'}
Best CV F1 Score: 0.9234

--- Optimized SVM Model Performance ---
Accuracy: 0.9456
F1 Score (Weighted): 0.9421
ROC-AUC (Weighted, One-vs-Rest): 0.9678

============================================================
SUCCESS: Model artifacts saved to ./artifacts/
  - Model: tw_lb_svm_model.joblib
  - Scaler: feature_scaler.joblib
  - Encoder: label_encoder.joblib
  - Features: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
============================================================
```

### Step 4: Verify Artifacts Were Created

```bash
# Check artifacts directory
ls -la artifacts/
```

**Expected**:
```
artifacts/
├── feature_scaler.joblib       (scaler for features)
├── label_encoder.joblib        (encodes fault types)
└── tw_lb_svm_model.joblib      (trained SVM model)
```

### Step 5: Rebuild Load Balancer with Artifacts

The Docker build context is set to root (`.`), so it will copy the artifacts:

```bash
# Rebuild load balancer with new artifacts
docker-compose build tw-lb

# Restart the load balancer
docker-compose up -d tw-lb
```

### Step 6: Verify Trust Weight Calculation

Watch the load balancer logs:

```bash
docker-compose logs -f tw-lb
```

## 📊 Expected Docker Logs (Complete Example)

### 1. Node Startup Logs (With Realistic Simulation)

**Benign Node (node-1)**:
```
node-1  | INFO:     Started server process [1]
node-1  | INFO:     Waiting for application startup.
node-1  | --- Node node-1 initialized ---
node-1  |   FAULT_TYPE: benign
node-1  |   Base Latency: 32.45ms
node-1  |   Base CPU Load: 35.20%
node-1  |   Network Jitter: ±8.12ms
node-1  |   Stability Factor: 0.87
node-1  | INFO:     Application startup complete.
node-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Byzantine Node (node-5 with 500-error)**:
```
node-5  | INFO:     Started server process [1]
node-5  | INFO:     Waiting for application startup.
node-5  | --- Node node-5 initialized ---
node-5  |   FAULT_TYPE: 500-error
node-5  |   Base Latency: 28.91ms
node-5  |   Base CPU Load: 42.30%
node-5  |   Network Jitter: ±12.34ms
node-5  |   Stability Factor: 0.73
node-5  | INFO:     Application startup complete.
node-5  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
node-5  | [node-5] 500-ERROR fault triggered (probabilistic)
node-5  | [node-5] 500-ERROR fault triggered (probabilistic)
```

### 2. Load Balancer Startup (WITHOUT Artifacts)

```
tw-lb   | ============================================================
tw-lb   | Trust-Weighted Load Balancer Starting
tw-lb   | ============================================================
tw-lb   | ⚠ WARNING: Model artifacts not found: [Errno 2] No such file or directory: '/app/artifacts/tw_lb_svm_model.joblib'
tw-lb   | ⚠ Falling back to Round Robin routing
tw-lb   | ✓ Connected to Prometheus at http://prometheus:9090
tw-lb   | 
tw-lb   | ⚠ Running in Round Robin mode (model not loaded)
tw-lb   | 
tw-lb   | Starting request routing (interval: 0.5s)
tw-lb   | ============================================================
tw-lb   | 
tw-lb   | [14:55:23] node-1 (RR) | Status: 200
tw-lb   | [14:55:24] node-2 (RR) | Status: 200
tw-lb   | [14:55:24] node-3 (RR) | Status: 200
tw-lb   | [14:55:25] node-4 (RR) | Status: 200
tw-lb   | [14:55:25] node-5 (RR) | Status: 500  ← Byzantine, but no weight adjustment
tw-lb   | [14:55:26] node-6 (RR) | Status: 200
```

### 3. Load Balancer Startup (WITH Artifacts, DEBUG=True)

```
tw-lb   | ============================================================
tw-lb   | Trust-Weighted Load Balancer Starting
tw-lb   | ============================================================
tw-lb   | ✓ TWLB initialized successfully
tw-lb   |   - Model: tw_lb_svm_model.joblib
tw-lb   |   - Features: ['latency_ms', 'error_500_count', 'cpu_usage_rate', 'resident_mem_mb']
tw-lb   |   - Classes: ['benign' '500-error' 'delay']
tw-lb   | ✓ Connected to Prometheus at http://prometheus:9090
tw-lb   | 
tw-lb   | [14:56:01] Updating trust weights...
tw-lb   | DEBUG METRICS (node-1): {'avg_latency_seconds': 0.0423, 'error_count': 0.0, 'cpu_usage_rate': 0.352, 'resident_mem_mb': 45.23}
tw-lb   | DEBUG PREDICT (node-1): Features=0.00 (Error), P_Faulty(500-error)=0.023, Classes=['benign' '500-error' 'delay']
tw-lb   | DEBUG METRICS (node-2): {'avg_latency_seconds': 0.0389, 'error_count': 0.0, 'cpu_usage_rate': 0.287, 'resident_mem_mb': 43.81}
tw-lb   | DEBUG PREDICT (node-2): Features=0.00 (Error), P_Faulty(500-error)=0.018, Classes=['benign' '500-error' 'delay']
tw-lb   | ...
tw-lb   | DEBUG METRICS (node-5): {'avg_latency_seconds': 0.0512, 'error_count': 12.3, 'cpu_usage_rate': 0.423, 'resident_mem_mb': 48.92}
tw-lb   | DEBUG PREDICT (node-5): Features=12.30 (Error), P_Faulty(500-error)=0.876, Classes=['benign' '500-error' 'delay']
tw-lb   | 
tw-lb   | [14:56:01] --- WEIGHTS UPDATED (TWLB) ---
tw-lb   | Active Weights: {'node-5': 0.1}  ← Byzantine node penalized!
tw-lb   | ------------------------------------------------------------
tw-lb   | 
tw-lb   | Initial Trust Weights: {'node-1': 1.0, 'node-2': 1.0, 'node-3': 1.0, 'node-4': 1.0, 'node-5': 0.1, ..., 'node-15': 1.0}
tw-lb   | 
tw-lb   | Starting request routing (interval: 0.5s)
tw-lb   | ============================================================
tw-lb   | 
tw-lb   | [14:56:02] node-3 (TWLB) | Status: 200
tw-lb   | [14:56:02] node-1 (TWLB) | Status: 200
tw-lb   | [14:56:03] node-7 (TWLB) | Status: 200
tw-lb   | [14:56:03] node-2 (TWLB) | Status: 200
tw-lb   | [14:56:04] node-5 (TWLB) | Status: 500  ← Rarely selected (weight 0.1)
tw-lb   | [14:56:04] node-4 (TWLB) | Status: 200
```

### 4. Node Request Logs (With Realistic Simulation)

**Benign Node**:
```
node-1  | INFO:     172.18.0.5:45678 - "GET /process HTTP/1.1" 200 OK
node-1  | INFO:     172.18.0.5:45679 - "GET /process HTTP/1.1" 200 OK
node-1  | INFO:     172.18.0.5:45680 - "GET /process HTTP/1.1" 200 OK
```

**Byzantine Node (Probabilistic Faults)**:
```
node-5  | [node-5] 500-ERROR fault triggered (probabilistic)
node-5  | INFO:     172.18.0.5:48234 - "GET /process HTTP/1.1" 500 Internal Server Error
node-5  | INFO:     172.18.0.5:48235 - "GET /process HTTP/1.1" 200 OK  ← Sometimes succeeds!
node-5  | [node-5] 500-ERROR fault triggered (probabilistic)
node-5  | INFO:     172.18.0.5:48236 - "GET /process HTTP/1.1" 500 Internal Server Error
node-5  | INFO:     172.18.0.5:48237 - "GET /process HTTP/1.1" 200 OK
```

### 5. Weight Updates Over Time

Every 5 seconds, you'll see:
```
tw-lb   | [14:56:06] Updating trust weights...
tw-lb   | DEBUG METRICS (node-1): {'avg_latency_seconds': 0.0445, 'error_count': 0.0, 'cpu_usage_rate': 0.389, 'resident_mem_mb': 46.12}
tw-lb   | DEBUG PREDICT (node-1): Features=0.00 (Error), P_Faulty(500-error)=0.019, Classes=['benign' '500-error' 'delay']
tw-lb   | ...
tw-lb   | DEBUG METRICS (node-5): {'avg_latency_seconds': 0.0523, 'error_count': 15.8, 'cpu_usage_rate': 0.441, 'resident_mem_mb': 49.23}
tw-lb   | DEBUG PREDICT (node-5): Features=15.80 (Error), P_Faulty(500-error)=0.891, Classes=['benign' '500-error' 'delay']
tw-lb   | 
tw-lb   | [14:56:06] --- WEIGHTS UPDATED (TWLB) ---
tw-lb   | Active Weights: {'node-5': 0.1}
tw-lb   | ------------------------------------------------------------
```

## 🎯 Key Observations

### Trust Weight Thresholds

From the code (lines 207-212):
```python
if p_faulty < 0.20:
    tw = 1.0   # High trust
elif p_faulty < 0.60:
    tw = 0.5   # Medium trust
else:
    tw = 0.1   # Low trust
```

**Example predictions**:
- **node-1** (benign): P(Faulty) = 0.023 → TW = 1.0 ✓
- **node-5** (500-error): P(Faulty) = 0.876 → TW = 0.1 ✓
- **node-10** (degrading): P(Faulty) = 0.45 → TW = 0.5 ⚠️

### Realistic Simulation Features You'll See

1. **Variable latencies**: 20-80ms with jitter
2. **Load factor changes**: Oscillates over time (0.3-1.2)
3. **Probabilistic faults**: Byzantine nodes don't always fail
4. **Request counters**: Incrementing request numbers
5. **CPU/Memory metrics**: Dynamic resource usage

## 🚀 Quick Fix Commands

If you need to start fresh:

```bash
# 1. Stop everything
docker-compose down

# 2. Start system
docker-compose up -d

# 3. Wait 2-3 minutes, then collect data
sleep 180
python data_exporter.py

# 4. Train model
python train_improved.py

# 5. Rebuild LB with artifacts
docker-compose build tw-lb
docker-compose up -d tw-lb

# 6. Watch it work!
docker-compose logs -f tw-lb
```

## 🔍 Troubleshooting

### Load balancer still in RR mode?
```bash
# Check if artifacts exist in container
docker exec -it ds_project_tw-lb_1 ls -la /app/artifacts/

# Should see:
# feature_scaler.joblib
# label_encoder.joblib
# tw_lb_svm_model.joblib
```

### Metrics showing all zeros?
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check node metrics directly
curl http://localhost:8001/metrics | grep http_requests_total
```

### No predictions/weights changing?
- Make sure byzantine node is configured (node-5 has `NODE_5_FAULT=500-error`)
- Wait at least 30 seconds for metrics to accumulate
- Check DEBUG output for actual P(Faulty) values
