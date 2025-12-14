TW-LB_DistributedSystem
Enhance Byzantine Resilience in Small, Resource-Constraint Environments

This project simulates a small, load-balanced, distributed system environment where Byzantine faults (delays, crashes, 500 errors) can be randomly injected into backend nodes. The primary goal is to collect labeled training data (metrics + ground truth fault type) to train a Machine Learning model (e.g., Support Vector Machine or SVM) for real-time fault detection.
🚀 Setup and Installation Guide
Prerequisites

You must have the following software installed on your machine:

    Git: For cloning the repository.

    Docker & Docker Compose: For running the containerized load balancer, nodes, and monitoring stack (Prometheus, Grafana).

    Python 3.x: With the python3-venv package installed.

Step 1: Clone the Repository

Clone the project to your local machine and navigate into the directory:
Bash

git clone https://github.com/Jasmine-Raisya/TW-LB_DistributedSystem.git
cd TW-LB_DistributedSystem

Step 2: Set Up Python Virtual Environment

It is critical to install project dependencies in an isolated environment to avoid system conflicts.
Bash

# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment (Must be done before running the script!)
source venv/bin/activate

Step 3: Install Python Dependencies

The requirements.txt file contains all necessary Python libraries for data collection and labeling.
Bash

pip install -r requirements.txt

💻 Running the System and Collecting Data
Step 4: Inject a Random Fault and Start Containers

The ./start_random.sh script handles the fault injection and container orchestration:

    It stops any existing containers.

    It randomly selects a fault type (delay, crash, 500-error, or benign) for each of the three backend nodes.

    It saves the ground truth labels (e.g., NODE_2_FAULT=delay) into the crucial .env file.

    It starts the Docker containers (docker-compose up).

Run this script to begin the simulation:
Bash

./start_random.sh

Step 5: Collect Labeled Training Data

Wait for at least 60 seconds after the containers are up for Prometheus to scrape enough metrics. Then, run the data exporter.

Key Fix: The data_exporter.py script uses the python-dotenv library to read the ground truth labels from the .env file and automatically attach them as the fault_type column to the metrics collected from Prometheus.
Bash

echo "Waiting 60 seconds for metrics to accumulate..."
sleep 60
python data_exporter.py

Expected Output

The script will output a success message, confirming the correct labeling based on the .env file:

--- Ground Truth Fault Map: {'node-1': 'benign', 'node-2': 'delay', 'node-3': 'benign'} ---

--- DATA COLLECTION SUCCESSFUL & AUTOMATICALLY LABELED ---
...
Ground Truth Labels Found in Data:
| fault_type   | count |
| :----------- | :---- |
| benign       | 150   |
| delay        | 75    |

SUCCESS: Multiple fault types detected! Your SVM training is now possible.

The resulting CSV file (byzantine_training_data_...csv) is your clean, labeled dataset for machine learning.
🛑 Cleanup (When Finished)

To stop and remove the running Docker containers, use:
Bash

docker-compose down

To exit the Python environment:
Bash

deactivate
