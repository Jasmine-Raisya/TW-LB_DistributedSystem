# TW-LB: Trust-Weighted Load Balancing for Byzantine Resilience

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker: Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

**TW-LB** is a research-focused distributed system simulator designed to enhance Byzantine fault tolerance in resource-constrained edge/IoT environments. It leverages Machine Learning (SVM) to detect sophisticated adversarial behaviors—including timing attacks and subtle data corruption—and dynamically adjusts traffic routing to preserve system integrity.

## 🌟 Key Research Objectives

1.  **Byzantine Detection via External Observation**: Proving that Load Balancer-observed metrics are superior to node self-reporting for identifying malicious actors.
2.  **Probabilistic Trust Weighting**: Implementing a "Graceful Degradation" strategy that quarantines high-probability attackers while buffering suspicious nodes.
3.  **Low-Overhead Resilience**: Maintaining high availability (< 3% node error rate) with minimal CPU (< 4%) and memory footprint.

## 🏗️ System Architecture

The project utilizes a containerized microservices stack:
- **Load Balancer**: Python-based gateway with an embedded SVM inference engine.
- **Worker Nodes (x15)**: Backend services with randomized Byzantine fault injectors.
- **Monitoring**: Prometheus-driven metrics collection pipeline.

## 📊 Performance at a Glance

| Metric | Target | **Result (TW-LB)** |
|:-------|:-------|:-------------------|
| **ROC-AUC** | > 0.90 | **0.9856** |
| **F1-Score** | > 0.80 | **0.9135** |
| **Precision** | > 0.90 | **1.0000** (Zero False Positives) |

## 🚀 Getting Started

To replicate our research findings or test your own Byzantine mitigation strategies, please see our dedicated execution guide:

👉 **[CLONE_AND_RUN.md](CLONE_AND_RUN.md)**

## 📖 Documentation

- **[methodology_and_results.md](methodology_and_results.md)**: Comprehensive deep dive into the research methodology, SVM feature engineering, and detailed statistical analysis of experiment outcomes.

---
*Created as part of Advanced Agentic Coding Research for Distributed Systems.*
