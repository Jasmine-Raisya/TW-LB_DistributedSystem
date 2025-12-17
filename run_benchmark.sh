#!/bin/bash

echo "======================================================="
echo "   🚀 SYSTEM PERFORMANCE BENCHMARK SUITE"
echo "======================================================="

# 1. Start the System (Clean Slate)
echo ""
echo "[1/3] Starting Distributed System (Randomized Faults)..."
./start_random.sh

# 2. Wait for Steady State
DURATION=600 # 10 minutes for statistical significance
echo ""
echo "[2/3] Waiting for System Stabilization ($DURATION seconds)..."
echo "      Generating high-load traffic (20 TPS)..."

# Countdown
for (( i=$DURATION; i>0; i-- )); do
    printf "\rTime remaining: %-10s" "$i sec"
    sleep 1
done
echo ""

# 3. Run Exporters
echo ""
echo "[3/3] Exporting Data..."

echo "   A. Generating Time-Series CSV (for Statistical Analysis)..."
export PROMETHEUS_URL="http://localhost:9094"
./venv/bin/python data_exporter.py

echo ""
echo "   B. Calculating Summary Metrics..."
./venv/bin/python benchmark_exporter.py

echo ""
echo "======================================================="
echo "   ✅ BENCHMARK COMPLETE"
echo "======================================================="
echo "Results saved to system_metrics.json"
