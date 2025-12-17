#!/bin/bash
set -e

echo "Copying data_exporter to load balancer container..."
LB_CONTAINER=$(docker ps --filter "name=tw-lb" --format "{{.Names}}" | head -1)

if [ -z "$LB_CONTAINER" ]; then
    echo "❌ Error: Load balancer container not found. Is the system running?"
    exit 1
fi

echo "Using container: $LB_CONTAINER"

docker cp data_exporter.py $LB_CONTAINER:/tmp/
docker cp .env $LB_CONTAINER:/tmp/

echo "Collecting data from Prometheus..."
docker exec -e PROMETHEUS_URL=http://prometheus:9090 \
  $LB_CONTAINER \
  python /tmp/data_exporter.py

echo "Copying results back..."
docker cp $LB_CONTAINER:/tmp/byzantine_training_data_*.csv . 2>/dev/null || \
  docker cp $LB_CONTAINER:/app/byzantine_training_data_*.csv . || \
  echo "Warning: Could not find CSV file in /tmp or /app, checking container"

# List what's in the container to debug
docker exec $LB_CONTAINER sh -c "ls -lh /tmp/byzantine*.csv 2>/dev/null || ls -lh /app/byzantine*.csv 2>/dev/null || echo 'No CSV files found'"

echo "Done! Data collected."
