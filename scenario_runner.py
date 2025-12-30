"""
Scenario Runner for TW-LB Experiments
=====================================
Runs automated experiments with 0%, 10%, 20% Byzantine node scenarios.
Collects metrics and saves results for analysis.

Usage:
    python scenario_runner.py [--duration SECONDS] [--output-dir DIR]
"""

import subprocess
import time
import json
import os
import sys
import random
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any

import requests
import pandas as pd
from prometheus_api_client import PrometheusConnect
from data_exporter import fetch_metrics


# --- Configuration ---
TOTAL_NODES = 15
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9094")
LB_URL = "http://localhost:8080"

# Scenario definitions
SCENARIOS = {
    "0%_byzantine": {
        "byzantine_count": 0,
        "fault_types": [],
        "description": "Baseline: All nodes benign"
    },
    "10%_byzantine": {
        "byzantine_count": 2,  # ~13% of 15 nodes
        "fault_types": ["500-error", "timing_attack"],
        "description": "Low Byzantine: 2 faulty nodes"
    },
    "20%_byzantine": {
        "byzantine_count": 3,  # 20% of 15 nodes
        "fault_types": ["500-error", "selective_failure", "mixed_faults"],
        "description": "Medium Byzantine: 3 faulty nodes"
    },
    # --- ADVANCED SCENARIOS ---
    "subtle_byzantine": {
        "byzantine_count": 3,
        "fault_types": ["subtle_data_corruption"],
        "description": "Testing data corruption detection"
    },
    "strategic_byzantine": {
        "byzantine_count": 3,
        "fault_types": ["strategic_timing", "selective_failure"],
        "description": "Testing timing and targeted attacks"
    },
    "advanced_byzantine": {
        "byzantine_count": 3,
        "fault_types": ["advanced_mixed"],
        "description": "Full Advanced Byzantine Suite"
    },
}

# Available sophisticated fault types
ALL_FAULT_TYPES = [
    "500-error",
    "delay", 
    "selective_failure",
    "incorrect_response",
    "timing_attack",
    "mixed_faults",
    # Advanced
    "subtle_data_corruption",
    "strategic_timing",
    "advanced_mixed"
]


def generate_env_file(byzantine_count: int, fault_types: List[str]) -> Dict[str, str]:
    """
    Generate .env file with Byzantine node configuration.
    Returns a dict mapping node_id -> fault_type for ground truth.
    """
    fault_assignments = {}
    
    # Randomly select which nodes will be Byzantine
    node_ids = list(range(1, TOTAL_NODES + 1))
    random.shuffle(node_ids)
    byzantine_nodes = node_ids[:byzantine_count]
    
    env_lines = []
    for i in range(1, TOTAL_NODES + 1):
        if i in byzantine_nodes:
            # Assign a random fault type from the allowed list
            fault_type = random.choice(fault_types) if fault_types else "500-error"
            env_lines.append(f"NODE_{i}_FAULT={fault_type}")
            fault_assignments[f"node-{i}"] = fault_type
        else:
            env_lines.append(f"NODE_{i}_FAULT=benign")
            fault_assignments[f"node-{i}"] = "benign"
    
    # Write .env file
    with open(".env", "w", encoding='utf-8') as f:
        f.write("\n".join(env_lines) + "\n")
    
    print(f"  Generated .env with {byzantine_count} Byzantine nodes:")
    for node_id, fault in fault_assignments.items():
        if fault != "benign":
            print(f"    - {node_id}: {fault}")
    
    return fault_assignments


def start_docker_stack() -> bool:
    """Start Docker Compose stack and wait for it to be ready."""
    print("  Starting Docker Compose stack...")
    
    try:
        # Build and start
        result = subprocess.run(
            ["docker-compose", "up", "-d", "--build"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            # Try docker compose (v2)
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "--build"],
                capture_output=True,
                text=True,
                timeout=300
            )
        
        if result.returncode != 0:
            print(f"  ERROR: Failed to start stack: {result.stderr}")
            return False
        
        # Wait for services to be healthy
        print("  Waiting for services to initialize (60s)...")
        time.sleep(60)
        
        return True
        
    except subprocess.TimeoutExpired:
        print("  ERROR: Docker compose timed out")
        return False
    except FileNotFoundError:
        print("  ERROR: Docker compose not found")
        return False


def stop_docker_stack():
    """Stop Docker Compose stack."""
    print("  Stopping Docker Compose stack...")
    try:
        subprocess.run(["docker-compose", "down"], capture_output=True, timeout=60)
    except:
        subprocess.run(["docker", "compose", "down"], capture_output=True, timeout=60)


def collect_prometheus_metrics(prom: PrometheusConnect, duration_seconds: int, fault_assignments: Dict[str, str]) -> Dict[str, Any]:
    """
    Query Prometheus for key metrics.
    Includes Throughput, Latency, Error Rate, and Selection Analysis.
    """
    metrics = {}
    duration_str = f"{duration_seconds}s"
    
    try:
        # 1. THROUGHPUT & ERRORS
        total_success = prom.custom_query(f'sum(increase(lb_routed_requests_total{{status="200"}}[{duration_str}]))')
        total_others = prom.custom_query(f'sum(increase(lb_routed_requests_total{{status!="200"}}[{duration_str}]))')
        
        success_val = float(total_success[0]["value"][1]) if total_success else 0
        error_val = float(total_others[0]["value"][1]) if total_others else 0
        total_val = success_val + error_val
        
        metrics["total_requests"] = int(total_val)
        metrics["success_count"] = int(success_val)
        metrics["error_count"] = int(error_val)
        metrics["tps"] = total_val / duration_seconds if duration_seconds > 0 else 0
        
        # 2. AVAILABILITY (%) - Critical for DS paper
        metrics["availability"] = (success_val / total_val * 100) if total_val > 0 else 0
        metrics["error_rate"] = (error_val / total_val * 100) if total_val > 0 else 0
        
        # 3. LATENCY (ms)
        # Use increase() for total sum and count over the duration to get the true average
        lat_sum_q = prom.custom_query(f'sum(increase(request_latency_seconds_sum[{duration_str}]))')
        lat_count_q = prom.custom_query(f'sum(increase(request_latency_seconds_count[{duration_str}]))')
        
        lat_sum = float(lat_sum_q[0]["value"][1]) if lat_sum_q else 0
        lat_count = float(lat_count_q[0]["value"][1]) if lat_count_q else 0
        
        if lat_count > 0:
            metrics["avg_latency_ms"] = (lat_sum / lat_count) * 1000
        else:
            metrics["avg_latency_ms"] = 0
        
        # 4. LOAD BALANCER OVERHEAD
        lb_cpu = prom.custom_query('lb_cpu_usage_percent')
        lb_memory = prom.custom_query('lb_memory_mb')
        metrics["lb_cpu_percent"] = float(lb_cpu[0]["value"][1]) if lb_cpu else 0
        metrics["lb_memory_mb"] = float(lb_memory[0]["value"][1]) if lb_memory else 0
        
        # 5. NODE SELECTION ANALYSIS (Proven mitigation)
        # We compare how many requests were sent to nodes THAT WE KNOW are bad vs good.
        byzantine_reqs = 0
        benign_reqs = 0
        
        for node_id, fault_type in fault_assignments.items():
            query = f'sum(increase(lb_routed_requests_total{{selected_node="{node_id}"}}[{duration_str}]))'
            node_res = prom.custom_query(query)
            count = float(node_res[0]["value"][1]) if node_res else 0
            
            if fault_type == "benign":
                benign_reqs += count
            else:
                byzantine_reqs += count
        
        metrics["byzantine_traffic_count"] = byzantine_reqs
        metrics["benign_traffic_count"] = benign_reqs
        metrics["mitigation_ratio"] = (benign_reqs / max(1, byzantine_reqs))
        
    except Exception as e:
        print(f"  WARNING: Error collecting metrics: {e}")
    
    return metrics


def run_load_test(duration_seconds: int) -> Dict[str, Any]:
    """
    Run load test by sending requests to the load balancer.
    The LB itself will forward to nodes and track metrics.
    """
    print(f"  Running load test for {duration_seconds}s...")
    
    start_time = time.time()
    request_count = 0
    success_count = 0
    error_count = 0
    latencies = []
    
    while time.time() - start_time < duration_seconds:
        try:
            req_start = time.time()
            # Note: We don't actually make requests here since the LB
            # has its own internal routing loop. We just collect stats.
            # In a real scenario, you'd make external requests to the LB.
            time.sleep(0.1)  # Avoid tight loop
            
        except Exception as e:
            error_count += 1
    
    return {
        "duration_seconds": duration_seconds,
        "completed_at": datetime.now().isoformat()
    }


def run_scenario(
    scenario_name: str,
    config: Dict[str, Any],
    duration_seconds: int,
    output_dir: str,
    export_csv: bool = False
) -> Dict[str, Any]:
    """Run a single scenario and collect results."""
    
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"Description: {config['description']}")
    print(f"{'='*60}")
    
    # Generate configuration
    fault_assignments = generate_env_file(
        config["byzantine_count"],
        config["fault_types"]
    )
    
    # Start stack
    if not start_docker_stack():
        return {"error": "Failed to start Docker stack"}
    
    try:
        # Connect to Prometheus
        prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
        
        # Run load test (let the system run for the duration)
        print(f"  Collecting data for {duration_seconds}s...")
        scenario_start = datetime.now()
        time.sleep(duration_seconds)
        scenario_end = datetime.now() + timedelta(seconds=5) # Buffer for final metrics
        
        # Collect metrics
        print("  Collecting Prometheus metrics...")
        metrics = collect_prometheus_metrics(
            prom, 
            duration_seconds, 
            fault_assignments
        )
        
        # Compile results
        results = {
            "scenario_name": scenario_name,
            "config": config,
            "fault_assignments": fault_assignments,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save scenario results
        output_file = os.path.join(output_dir, f"{scenario_name}_results.json")
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to: {output_file}")
        
        # Optional: Automated CSV export for training
        if export_csv:
            print(f"  [AUTO-EXPORT] Exporting training data for window {scenario_start.strftime('%H:%M:%S')} - {scenario_end.strftime('%H:%M:%S')}...")
            # We call fetch_metrics with the precise window to avoid pollution
            try:
                # Import here to avoid circular dependencies if any
                from data_exporter import fetch_metrics
                df = fetch_metrics(start_time=scenario_start, end_time=scenario_end)
                if df is not None and not df.empty:
                    # Append or create master training file
                    master_file = "byzantine_training_data_automated.csv"
                    write_header = not os.path.exists(master_file)
                    df.to_csv(master_file, mode='a', header=write_header, index=False)
                    print(f"  [AUTO-EXPORT] Appended {len(df)} rows to {master_file}")
            except Exception as e:
                print(f"  [AUTO-EXPORT] ERROR: {e}")
        
        return results
        
    finally:
        stop_docker_stack()


def main():
    parser = argparse.ArgumentParser(description="Run TW-LB experiments")
    parser.add_argument(
        "--duration", 
        type=int, 
        default=300,
        help="Duration per scenario in seconds (default: 300)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./experiment_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=list(SCENARIOS.keys()),
        default=list(SCENARIOS.keys()),
        help="Scenarios to run"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Automate CSV export for each scenario (useful for dataset generation)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("TW-LB EXPERIMENT RUNNER")
    print("="*60)
    print(f"Duration per scenario: {args.duration}s")
    print(f"Output directory: {args.output_dir}")
    print(f"Scenarios to run: {args.scenarios}")
    print(f"Export CSV: {args.export_csv}")
    print("="*60)
    
    all_results = {}
    
    for scenario_name in args.scenarios:
        config = SCENARIOS[scenario_name]
        results = run_scenario(
            scenario_name,
            config,
            args.duration,
            args.output_dir,
            export_csv=args.export_csv
        )
        all_results[scenario_name] = results
    
    # Save combined results
    combined_file = os.path.join(args.output_dir, "all_results.json")
    with open(combined_file, "w", encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "="*60)
    print("EXPERIMENT COMPLETE")
    print("="*60)
    print(f"Combined results: {combined_file}")
    print("\nNext steps:")
    print("  1. Run: python svm_evaluator.py")
    print("  2. Run: python report_generator.py")


if __name__ == "__main__":
    main()
