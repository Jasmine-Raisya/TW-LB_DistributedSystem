#!/bin/bash

echo "======================================================="
echo "   🎯 ZERO-ERROR VERIFICATION RUN"
echo "======================================================="

# Note: We assume the system is ALREADY running (we just deployed it)
# We just need to wait for traffic to generate and then measure.

DURATION=180 # 3 minutes
echo ""
echo "[1/2] Waiting for Traffic Generation ($DURATION seconds)..."
echo "      Generating high-load traffic (20 TPS) on optimized model..."

# Countdown
for (( i=$DURATION; i>0; i-- )); do
    printf "\rTime remaining: %-10s" "$i sec"
    sleep 1
done
echo ""

# 2. Run Exporter
echo ""
echo "[2/2] Calculating Final Metrics..."
echo "      Executing benchmark_exporter.py..."

# Ensure we use the correct port
export PROMETHEUS_URL="http://localhost:9094" 
./venv/bin/python benchmark_exporter.py

echo ""
echo "======================================================="
echo "   ✅ VERIFICATION COMPLETE"
echo "======================================================="
