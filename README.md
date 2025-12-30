# TW-LB: Trust-Weighted Load Balancer Implementation

## Research Overview
This repository contains the core implementation of the **Trust-Weighted Load Balancer (TW-LB)**, a machine learning-driven solution for Byzantine fault mitigation in distributed edge systems. The system employs **Support Vector Machine (SVM)** classification to compute real-time trust scores for worker nodes, enabling adaptive traffic routing that isolates potentially malicious components while maintaining system availability.

## Architecture Components

### Core Modules
- **`lb/load_balancer.py`** - Main load balancing service with integrated SVM inference and dynamic weight adjustment.
- **`svm_evaluator.py`** - Machine learning pipeline for fault detection and trust score calculation.
- **`node/byzantine_faults.py`** - Comprehensive Byzantine behavior implementations for experimental validation.
- **`scenario_runner.py`** - Automated experimentation framework for systematic evaluation.
- **`advanced_ratio_tester.py`** - Statistical evaluation suite for multi-iteration ratio testing.
- **`data_exporter.py`** - Metrics collection and real-time monitoring interface for Prometheus.

### Infrastructure Configuration
- **`docker-compose.yml`** - Complete container orchestration for the 15-node test environment.
- **`requirements.txt`** - Python dependencies and version specifications.
- **`monitoring/prometheus.yml`** - Metrics collection and time-series data configuration.

## System Requirements
- **Python**: 3.9+
- **Docker & Docker Compose**: Latest stable release
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB available disk space

## Quick Deployment
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch complete test environment
docker-compose up -d

# 3. Execute baseline validation
python scenario_runner.py --scenario baseline

# 4. Monitor system metrics (optional)
# Access Prometheus: http://localhost:9094
# Access Load Balancer: http://localhost:8080/health
```

## Experimental Validation
The implementation includes configurable Byzantine fault injection with three sophistication levels:
- **Subtle Data Corruption**: Numeric value manipulation (±10%).
- **Strategic Timing Attacks**: Selective response delays on critical operations.
- **Advanced Mixed Behaviors**: Comprehensive attack combinations for robustness testing.

## Key Features
- **Real-time Trust Scoring**: SVM-based probability estimates updated every 10 seconds.
- **Weighted Traffic Distribution**: Probabilistic routing based on computed trust weights (Tiered: Trusted/Suspicious/Quarantine).
- **External Observation**: Metrics collected from the load balancer perspective to prevent node deception.
- **Statistical Rigor**: Support for multi-iteration experimental protocols with Mean, SD, and CI95 calculation.

## Research Context
This implementation corresponds to the research paper *"Trust-Weighted Load Balancing: ML-Driven Byzantine Mitigation for Edge Systems"* submitted for peer review. The system demonstrates:
- Byzantine fault detection with **ROC-AUC > 0.98**
- **Zero false positive** operation (Precision = 1.0)
- Error containment **below 3%** even with 20% adversarial nodes
- Computational overhead **under 3.2% CPU utilization**

## Citation
If using this implementation in academic work, please reference the associated research publication *(citation to be added upon acceptance)*.

## License
**Research Implementation** - For academic and evaluation use only.

---
*Note: Complete experimental datasets, detailed results analysis, and the full research paper are available per request. This repository contains the reference implementation necessary for technical validation and reproducibility assessment.*
