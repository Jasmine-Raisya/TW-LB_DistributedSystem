#!/bin/bash
# Run data_exporter.py inside Docker network to access Prometheus

echo "Running data exporter inside Docker network..."

# Create a temporary Dockerfile for data collection
cat > /tmp/Dockerfile.datacollector << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY data_exporter.py .
COPY .env .
CMD ["python", "data_exporter.py"]
EOF

# Build the data collector image
docker build -f /tmp/Dockerfile.datacollector -t data-collector .

# Run it with access to Prometheus
docker run --rm \
  --network tw-lb_distributedsystem_tw_network \
  -v $(pwd):/output \
  -e PROMETHEUS_URL=http://prometheus:9090 \
  data-collector

echo "Data collection complete!"
