#!/bin/bash

# --- Configuration ---
TOTAL_NODES=15
FAULTY_COUNT=3 # 20% of 15 nodes
# We use only 'crash' and 'delay' for faults, 'benign' is the default for others.
FAULT_TYPES=("crash" "delay" "500-error")

# --- Cleanup previous environment and logs ---
echo "1. Shutting down existing containers and cleaning up..."
# Use 'down -v' to clean up all volumes/networks and ensure a fresh start
docker compose down #EDITED HERE RAISYA

# --- Select Random Faulty Nodes ---
# 1. Create an array of node IDs (1 to 15)
NODE_IDS=($(seq 1 $TOTAL_NODES))

# 2. Shuffle the array and pick the first $FAULTY_COUNT (3) nodes
# This selects 3 random indices without replacement
RANDOM_FAULTY_NODES=($(shuf -e "${NODE_IDS[@]}" -n $FAULTY_COUNT))

# --- Prepare Environment Variables ---
# Remove any old .env file
rm -f ./.env

echo "2. Randomly selected Byzantine nodes for this run (3/15): ${RANDOM_FAULTY_NODES[@]}"
echo "3. Generating .env file with FAULT_TYPE assignments..."

# Initialize all nodes as benign
declare -A FAULT_ASSIGNMENTS
for i in "${NODE_IDS[@]}"; do
    FAULT_ASSIGNMENTS[$i]="benign"
done

# Assign a random fault type to the selected faulty nodes
for i in "${RANDOM_FAULTY_NODES[@]}"; do
    # Pick a random fault type (crash or delay)
    # The 'random' variable is an internal Bash variable
    RANDOM_FAULT_TYPE=${FAULT_TYPES[$RANDOM % ${#FAULT_TYPES[@]}]}
    FAULT_ASSIGNMENTS[$i]=$RANDOM_FAULT_TYPE
done

# Write assignments to a temporary .env file
for i in "${NODE_IDS[@]}"; do
    echo "NODE_${i}_FAULT=${FAULT_ASSIGNMENTS[$i]}" >> ./.env
done

# --- Start Docker Compose ---
echo "4. Building and starting Docker Compose with new, randomized fault assignments..."
# Build all images again to ensure the Round Robin load balancer and node logic are up-to-date
docker compose up -d --build

echo "====================================================================="
echo "Setup complete. The 3 Byzantine nodes are randomly set."
echo "Wait 10-15 minutes, then run 'python3 data_exporter.py' to collect the dataset."
echo "====================================================================="
