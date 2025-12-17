import time
import os
import re
import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any
from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime
from dotenv import dotenv_values

# --- Configuration ---
PROMETHEUS_URL = "http://localhost:9094" 

def get_ground_truth() -> Dict[str, str]:
    """Read .env file to get actual fault status of nodes."""
    config = dotenv_values(".env")
    ground_truth = {}
    for key, value in config.items():
        if key.startswith("NODE_") and key.endswith("_FAULT"):
            match = re.search(r'NODE_(\d+)_FAULT', key)
            if match:
                node_id = f"node-{match.group(1)}"
                ground_truth[node_id] = value
    return ground_truth

def get_svm_predictions() -> Dict[str, str]:
    """Parse docker logs to get the latest prediction for each node."""
    try:
        # Get logs from the last 2 minutes
        cmd = ["docker", "logs", "--since", "2m", "ds_project_tw-lb_1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logs = result.stdout
        
        predictions = {}
        for line in logs.split('\n'):
            if "DEBUG PREDICT" in line:
                node_match = re.search(r'\(node-(\d+)\)', line)
                p_match = re.search(r'P_Faulty\((.*?)\)=([\d\.]+)', line)
                
                if node_match and p_match:
                    node_id = f"node-{node_match.group(1)}"
                    prob = float(p_match.group(2))
                    
                    if prob < 0.20:
                        pred = "benign"
                    elif prob < 0.60:
                        pred = "suspicious"
                    else:
                        pred = "faulty"
                        
                    predictions[node_id] = pred
        return predictions
    except Exception as e:
        print(f"Error parsing logs: {e}")
        return {}

def calculate_accuracy(ground_truth, predictions):
    correct = 0
    total = 0
    details = []
    
    for node, true_label in ground_truth.items():
        if node in predictions:
            pred = predictions[node]
            total += 1
            
            is_correct = False
            if true_label == 'benign':
                if pred == 'benign': is_correct = True
            else:
                # True label is faulty. 'suspicious' or 'faulty' counts as detection.
                if pred != 'benign': is_correct = True
            
            if is_correct:
                correct += 1
            
            details.append({
                "node": node,
                "true": true_label,
                "pred": pred,
                "correct": is_correct
            })
            
    return (correct / total if total > 0 else 0), details

def get_prometheus_metrics(prom, duration_minutes=5):
    """Fetch aggregated system metrics over the last N minutes."""
    metrics = {}
    try:
        # TPS
        tps_query = f'sum(rate(http_requests_total[{duration_minutes}m]))'
        tps_res = prom.custom_query(tps_query)
        metrics['tps'] = float(tps_res[0]['value'][1]) if tps_res else 0.0
        
        # Latency (Avg)
        lat_query = f'sum(rate(request_latency_seconds_sum[{duration_minutes}m])) / sum(rate(request_latency_seconds_count[{duration_minutes}m]))'
        lat_res = prom.custom_query(lat_query)
        metrics['avg_latency_s'] = float(lat_res[0]['value'][1]) if lat_res else 0.0
        
        # Error Rate
        err_query = f'sum(rate(http_requests_total{{status="500"}}[{duration_minutes}m])) / sum(rate(http_requests_total[{duration_minutes}m]))'
        err_res = prom.custom_query(err_query)
        metrics['error_rate'] = float(err_res[0]['value'][1]) if err_res else 0.0
        
        # Resource Utilization
        cpu_query = f'avg(node_cpu_usage_percent)'
        cpu_res = prom.custom_query(cpu_query)
        metrics['avg_cpu_percent'] = float(cpu_res[0]['value'][1]) if cpu_res else 0.0
        
        mem_query = f'avg(node_memory_mb)'
        mem_res = prom.custom_query(mem_query)
        metrics['avg_mem_mb'] = float(mem_res[0]['value'][1]) if mem_res else 0.0
        
    except Exception as e:
        print(f"Prometheus Query Error: {e}")
        
    return metrics

def main():
    print("\n=======================================================")
    print("📊 DISTRIBUTED SYSTEM PERFORMANCE REPORT")
    print("=======================================================")
    
    # 1. Prometheus Metrics
    try:
        prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
        metrics = get_prometheus_metrics(prom)
        
        print(f"\n1. SYSTEM METRICS (Last 5 mins)")
        print(f"   - Throughput (TPS):    {metrics.get('tps', 0):.2f} req/s")
        print(f"   - Avg Latency:         {metrics.get('avg_latency_s', 0)*1000:.2f} ms")
        print(f"   - Error Rate:          {metrics.get('error_rate', 0)*100:.2f}%")
        print(f"   - Avg CPU Usage:       {metrics.get('avg_cpu_percent', 0):.1f}%")
        print(f"   - Avg Memory:          {metrics.get('avg_mem_mb', 0):.1f} MB")
        
    except Exception as e:
        print(f"❌ Failed to connect to Prometheus at {PROMETHEUS_URL}: {e}")

    # 2. Trust Weight Accuracy
    truth = get_ground_truth()
    preds = get_svm_predictions()
    acc, details = calculate_accuracy(truth, preds)
    
    print(f"\n2. FAULT DETECTION ACCURACY")
    print(f"   - Trust Accuracy:      {acc*100:.1f}%")
    print("\n   Detailed Calibration Check:")
    print("   {:<10} {:<15} {:<15} {:<10}".format("Node", "Ground Truth", "Prediction", "Result"))
    print("   " + "-"*55)
    
    for d in details:
        status_icon = "✅" if d['correct'] else "❌"
        print("   {:<10} {:<15} {:<15} {}".format(d['node'], d['true'], d['pred'], status_icon))
        
    print("\n=======================================================")
    
    # Save to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "accuracy": acc,
        "details": details
    }
    with open("system_metrics.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Report saved to system_metrics.json")

if __name__ == "__main__":
    main()
