# TW-LB_DistributedSystem
Enhance Byzantine Resillience in Small, Resource-Constraint Environments

## Setup and Installation Guide

### Prerequisites

You must have the following software installed on your machine:

1.  **Git:** For cloning the repository.
2.  **Docker & Docker Compose:** For running the containerized load balancer, nodes, and monitoring stack (Prometheus, Grafana).
3.  **Python 3.x:** With the `python3-venv` package installed.

### Step 1: Clone the Repository

Clone the project to your local machine and navigate into the directory:

### Set Up Python Virtual Environment

python3 -m venv venv

source venv/bin/activate

### Install Python Dependencies
pip install -r requirements.txt

./start_random.sh
echo "Waiting 60 seconds for metrics to accumulate..."
sleep 60
python data_exporter.py
docker-compose down
deactivate
