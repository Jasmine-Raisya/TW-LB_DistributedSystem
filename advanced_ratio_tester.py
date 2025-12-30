import time
import statistics
import json
import os
import subprocess
import requests
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from prometheus_api_client import PrometheusConnect

# --- Configuration (Sync with scenario_runner.py) ---
PROMETHEUS_URL = "http://localhost:9094"
LB_URL = "http://localhost:8080/process"
TOTAL_NODES = 15
OUTPUT_DIR = "./experiment_results/ratio_focused"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class AdvancedRatioTester:
    def __init__(self):
        # Use ONLY advanced_mixed behavior (the most sophisticated)
        self.byzantine_behavior = "advanced_mixed"
        
        self.scenarios = [
            {
                'id': 'R0',
                'name': '0% Byzantine',
                'byzantine_count': 0,
                'iterations': 5,
                'duration': 180,  # seconds
                'cooldown': 15,   # seconds between iterations
                'trust_eval_interval': 10  # evaluate trust every 10s (matches LB)
            },
            {
                'id': 'R10', 
                'name': '10% Byzantine',
                'byzantine_count': 2,  # 2 of 15 = 13.3%
                'iterations': 5,
                'duration': 180,
                'cooldown': 15,
                'trust_eval_interval': 10
            },
            {
                'id': 'R20',
                'name': '20% Byzantine',
                'byzantine_count': 3,  # 3 of 15 = 20%
                'iterations': 5,
                'duration': 180,
                'cooldown': 15,
                'trust_eval_interval': 10
            }
        ]
        
        self.results = {}
        self.prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

    def generate_env_file(self, byzantine_count: int, behavior: str) -> Dict[str, str]:
        """Generate .env file with specific Byzantine ratio."""
        node_ids = list(range(1, TOTAL_NODES + 1))
        random.shuffle(node_ids)
        byzantine_nodes = node_ids[:byzantine_count]
        
        fault_assignments = {}
        env_lines = []
        for i in range(1, TOTAL_NODES + 1):
            if i in byzantine_nodes:
                env_lines.append(f"NODE_{i}_FAULT={behavior}")
                fault_assignments[f"node-{i}"] = behavior
            else:
                env_lines.append(f"NODE_{i}_FAULT=benign")
                fault_assignments[f"node-{i}"] = "benign"
        
        with open(".env", "w", encoding='utf-8') as f:
            f.write("\n".join(env_lines) + "\n")
        
        return fault_assignments

    def start_docker_stack(self):
        print("    Starting Docker Compose stack...")
        try:
            subprocess.run(["docker-compose", "up", "-d"], capture_output=True, timeout=120)
        except:
            subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, timeout=120)
        time.sleep(15) # Warm-up

    def stop_docker_stack(self):
        print("    Stopping Docker Compose stack...")
        try:
            subprocess.run(["docker-compose", "down"], capture_output=True, timeout=60)
        except:
            subprocess.run(["docker", "compose", "down"], capture_output=True, timeout=60)

    def run_load_test(self, duration: int):
        """Simulate traffic for the duration of the experiment."""
        start_time = time.time()
        print(f"    Sending requests for {duration}s...")
        while time.time() - start_time < duration:
            try:
                # Concurrent-ish requests
                for _ in range(5):
                    requests.get(LB_URL, timeout=5)
                time.sleep(0.5)
            except:
                pass

    def collect_metrics(self, duration: int, fault_assignments: Dict[str, str]) -> Dict[str, Any]:
        """Query Prometheus for live performance metrics."""
        duration_str = f"{duration}s"
        metrics = {}
        
        try:
            # TPS and Errors
            total_success = self.prom.custom_query(f'sum(increase(lb_routed_requests_total{{status="200"}}[{duration_str}]))')
            total_others = self.prom.custom_query(f'sum(increase(lb_routed_requests_total{{status!="200"}}[{duration_str}]))')
            
            success_val = float(total_success[0]["value"][1]) if total_success else 0
            error_val = float(total_others[0]["value"][1]) if total_others else 0
            total_val = success_val + error_val
            
            metrics["tps"] = total_val / duration if duration > 0 else 0
            metrics["error_rate"] = (error_val / total_val * 100) if total_val > 0 else 0
            metrics["availability"] = (success_val / total_val * 100) if total_val > 0 else 100
            
            # Latency
            lat_sum_q = self.prom.custom_query(f'sum(increase(request_latency_seconds_sum[{duration_str}]))')
            lat_count_q = self.prom.custom_query(f'sum(increase(request_latency_seconds_count[{duration_str}]))')
            lat_sum = float(lat_sum_q[0]["value"][1]) if lat_sum_q else 0
            lat_count = float(lat_count_q[0]["value"][1]) if lat_count_q else 0
            metrics["avg_latency_ms"] = (lat_sum / lat_count * 1000) if lat_count > 0 else 0
            
            # Mitigation Ratio
            byzantine_reqs = 0
            benign_reqs = 0
            for node_id, fault in fault_assignments.items():
                res = self.prom.custom_query(f'sum(increase(lb_routed_requests_total{{selected_node="{node_id}"}}[{duration_str}]))')
                count = float(res[0]["value"][1]) if res else 0
                if fault == "benign": benign_reqs += count
                else: byzantine_reqs += count
            
            metrics["mitigation_ratio"] = (benign_reqs / max(1, byzantine_reqs))
            metrics["byzantine_traffic_count"] = byzantine_reqs
            metrics["benign_traffic_count"] = benign_reqs
            
            # Resource Overhead
            lb_cpu = self.prom.custom_query('lb_cpu_usage_percent')
            lb_mem = self.prom.custom_query('lb_memory_mb')
            metrics["lb_cpu_percent"] = float(lb_cpu[0]["value"][1]) if lb_cpu else 0
            metrics["lb_memory_mb"] = float(lb_mem[0]["value"][1]) if lb_mem else 0
            
        except Exception as e:
            print(f"    Error: {e}")
            
        return metrics

    def aggregate_metrics(self, iteration_results):
        """Calculate mean ± std deviation and CI95 across iterations."""
        if not iteration_results: return {}
        
        def calc_stats(key):
            values = [r.get(key, 0) for r in iteration_results]
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0
            ci95 = 2.776 * (std / (len(values)**0.5)) if len(values) > 1 else 0
            return {"mean": round(mean, 4), "std": round(std, 4), "ci95": round(ci95, 4)}

        keys = ["tps", "avg_latency_ms", "error_rate", "availability", "mitigation_ratio", "lb_cpu_percent", "lb_memory_mb"]
        return {key: calc_stats(key) for key in keys}

    def run_all(self):
        """Execute the 3x5 matrix experiment."""
        print(f"Starting Ratio-Focused Experiment: {self.byzantine_behavior}")
        
        for scenario in self.scenarios:
            print(f"\nSCENARIO: {scenario['name']} ({scenario['byzantine_count']} Byzantine nodes)")
            iteration_results = []
            
            for i in range(scenario['iterations']):
                print(f"  Iteration {i+1}/5")
                
                # Setup
                faults = self.generate_env_file(scenario['byzantine_count'], self.byzantine_behavior)
                self.start_docker_stack()
                
                # Test
                self.run_load_test(scenario['duration'])
                
                # Collect
                metrics = self.collect_metrics(scenario['duration'], faults)
                iteration_results.append(metrics)
                print(f"    Result: {metrics.get('tps', 0):.2f} TPS, {metrics.get('error_rate', 0):.2f}% Error")
                
                # Cleanup
                self.stop_docker_stack()
                if i < scenario['iterations'] - 1:
                    time.sleep(scenario['cooldown'])
            
            # Aggregate and Save
            self.results[scenario['id']] = {
                'scenario': scenario['name'],
                'byzantine_ratio': scenario['byzantine_count'] / TOTAL_NODES * 100,
                'aggregated': self.aggregate_metrics(iteration_results),
                'raw': iteration_results
            }
            
            with open(f"{OUTPUT_DIR}/ratio_results.json", "w") as f:
                json.dump(self.results, f, indent=2)

if __name__ == "__main__":
    tester = AdvancedRatioTester()
    tester.run_all()
