# TW-LB_DistributedSystem  
**Enhancing Byzantine Resilience in Small, Resource-Constrained Environments**

## Overview

This project simulates a small, load-balanced distributed system where Byzantine faults—such as delays, crashes, and HTTP 500 errors—can be randomly injected into backend nodes.

The primary objective is to collect labeled training data (system metrics plus ground-truth fault types) to train isolated Machine Learning model (e.g., a Support Vector Machine or SVM) for fault detection weights (Trust Weights), embedded in the Trust Weighted Load Balancer ("TW-LB")

### 🆕 Realistic Simulation Features

The system now includes **realistic node simulation** with:
- ✅ **Node-specific characteristics** - Each node has unique baseline performance (latency, CPU, network)
- ✅ **Dynamic workload patterns** - Sinusoidal load variation with traffic spikes
- ✅ **Network noise** - Gaussian jitter and packet loss simulation
- ✅ **Resource usage metrics** - CPU and memory patterns with realistic noise
- ✅ **Probabilistic Byzantine faults** - Faults occur with probability, not deterministically
- ✅ **Time-based evolution** - Node behavior changes over time

**📖 See [GETTING_STARTED_SIMULATION.md](GETTING_STARTED_SIMULATION.md) for detailed usage guide**

---

## Setup and Installation Guide

### Prerequisites

Ensure the following software is installed on your machine:

- **Git** – for cloning the repository  
- **Docker & Docker Compose** – for running the containerized load balancer, backend nodes, and monitoring stack (Prometheus and Grafana)  
- **Python 3.x** – with `python3-venv` installed  

---

## Step 1: Clone the Repository
Clone the project and navigate into the directory:


`git clone https://github.com/Jasmine-Raisya/TW-LB_DistributedSystem.git
cd TW-LB_DistributedSystem'\`

## Step 2: Set Up Python Virtual Environment
Create the virtual environment
`python3 -m venv venv`
`source venv/bin/activate`

## Step 3: Install Python Dependencies
`pip install -r requirements.txt`
the actual dependencies are: ..... just making sure yall r okay, i havent rechecked the requirements.txt
`pip install prometheus-api_client pandas python-dotenv tabulate scikit-learn`

- Activate the virtual environment (must be done before running scripts)
`source venv/bin/activate`

## Step 4: : Inject Random Faults and Start Containers
The start_random.sh script performs the following actions:
- Stops any existing Docker containers
- Randomly selects a fault type (delay, crash, 500-error, or benign) for each backend node
- Saves ground-truth fault labels (e.g., NODE_2_FAULT=delay) into the .env file
- Starts all services using docker-compose up

`./start_random.sh`

## Step 5: Collect Labeled Training Data
- Wait at least 60 seconds after the containers start to allow Prometheus to scrape sufficient metrics. Then run the data exporter.

The data_exporter.py script uses the python-dotenv library to read ground-truth labels from the .env file and automatically attach them as the fault_type column to the collected metrics.
`echo "Waiting 60 seconds for metrics to accumulate..."
sleep 60
python data_exporter.py
`

## CLEANUP
`docker-compose down`
`deactivate`



