#!/usr/bin/env python3
"""
Quick Test Script for Realistic Node Simulation

This script sends test requests to individual nodes and shows their responses
to verify that the realistic simulation features are working.
"""

import requests
import time
import statistics
from typing import List, Dict
import json


# Configuration
NODE_BASE_URL = "http://localhost"
NODE_PORTS = {f"node-{i}": 8000 + i for i in range(1, 16)}


def test_single_node(node_id: str, num_requests: int = 20) -> Dict:
    """
    Test a single node with multiple requests to observe behavior.
    """
    port = NODE_PORTS.get(node_id)
    if not port:
        return {"error": "Invalid node ID"}
    
    url = f"{NODE_BASE_URL}:{port}/process"
    
    print(f"\nTesting {node_id} ({url})...")
    print("-" * 60)
    
    latencies = []
    errors = 0
    timeouts = 0
    load_factors = []
    
    for i in range(num_requests):
        try:
            start = time.time()
            response = requests.get(url, timeout=8.0)
            latency = (time.time() - start) * 1000  # Convert to ms
            
            if response.status_code == 200:
                data = response.json()
                latencies.append(latency)
                
                # Extract load factor if available
                if "load_factor" in data:
                    load_factors.append(float(data["load_factor"]))
                
                # Show sample responses
                if i < 3 or i % 5 == 0:
                    print(f"  Request {i+1}: {latency:.2f}ms - {data}")
            else:
                errors += 1
                print(f"  Request {i+1}: ERROR {response.status_code}")
                
        except requests.exceptions.Timeout:
            timeouts += 1
            print(f"  Request {i+1}: TIMEOUT")
        except requests.exceptions.ConnectionError:
            print(f"  Request {i+1}: CONNECTION ERROR (node crashed?)")
            break
        except Exception as e:
            print(f"  Request {i+1}: Exception - {e}")
        
        time.sleep(0.1)  # Small delay between requests
    
    # Calculate statistics
    results = {
        "node": node_id,
        "total_requests": num_requests,
        "successful": len(latencies),
        "errors": errors,
        "timeouts": timeouts,
    }
    
    if latencies:
        results["avg_latency_ms"] = statistics.mean(latencies)
        results["std_latency_ms"] = statistics.stdev(latencies) if len(latencies) > 1 else 0
        results["min_latency_ms"] = min(latencies)
        results["max_latency_ms"] = max(latencies)
    
    if load_factors:
        results["avg_load_factor"] = statistics.mean(load_factors)
        results["std_load_factor"] = statistics.stdev(load_factors) if len(load_factors) > 1 else 0
    
    print("\nSummary:")
    print(f"  Successful: {results['successful']}/{num_requests}")
    print(f"  Errors: {errors}")
    print(f"  Timeouts: {timeouts}")
    
    if latencies:
        print(f"  Avg Latency: {results['avg_latency_ms']:.2f} ± {results['std_latency_ms']:.2f}ms")
        print(f"  Range: {results['min_latency_ms']:.2f} - {results['max_latency_ms']:.2f}ms")
    
    if load_factors:
        print(f"  Avg Load Factor: {results['avg_load_factor']:.2f} ± {results['std_load_factor']:.2f}")
    
    return results


def test_health_endpoint(node_id: str) -> Dict:
    """
    Test the health endpoint to see node status.
    """
    port = NODE_PORTS.get(node_id)
    if not port:
        return {"error": "Invalid node ID"}
    
    url = f"{NODE_BASE_URL}:{port}/health"
    
    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def compare_nodes(node_ids: List[str], num_requests: int = 20):
    """
    Compare multiple nodes side by side.
    """
    print("\n" + "="*80)
    print("COMPARING MULTIPLE NODES")
    print("="*80)
    
    results = []
    
    for node_id in node_ids:
        result = test_single_node(node_id, num_requests)
        results.append(result)
        time.sleep(1)  # Pause between nodes
    
    # Summary comparison
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Node':<12} {'Success Rate':<15} {'Avg Latency':<20} {'Latency StdDev':<15}")
    print("-" * 80)
    
    for r in results:
        success_rate = f"{r['successful']}/{r['total_requests']} ({r['successful']/r['total_requests']*100:.1f}%)"
        avg_lat = f"{r.get('avg_latency_ms', 0):.2f}ms" if 'avg_latency_ms' in r else "N/A"
        std_lat = f"{r.get('std_latency_ms', 0):.2f}ms" if 'std_latency_ms' in r else "N/A"
        
        print(f"{r['node']:<12} {success_rate:<15} {avg_lat:<20} {std_lat:<15}")


def observe_load_variation(node_id: str, duration_seconds: int = 60):
    """
    Observe how load factor varies over time for a single node.
    """
    port = NODE_PORTS.get(node_id)
    if not port:
        print("Invalid node ID")
        return
    
    url = f"{NODE_BASE_URL}:{port}/process"
    
    print(f"\n" + "="*80)
    print(f"OBSERVING LOAD VARIATION ON {node_id} for {duration_seconds}s")
    print("="*80)
    print("Time (s)  | Latency (ms) | Load Factor | Status")
    print("-" * 60)
    
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        elapsed = time.time() - start_time
        
        try:
            req_start = time.time()
            response = requests.get(url, timeout=8.0)
            latency = (time.time() - req_start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                load_factor = data.get("load_factor", "N/A")
                status = "✓"
            else:
                load_factor = "N/A"
                status = f"ERROR {response.status_code}"
            
            print(f"{elapsed:>7.1f}   | {latency:>12.2f} | {load_factor:>11} | {status}")
            
        except requests.exceptions.Timeout:
            print(f"{elapsed:>7.1f}   | {'TIMEOUT':>12} | {'N/A':>11} | ✗")
        except Exception as e:
            print(f"{elapsed:>7.1f}   | {'ERROR':>12} | {'N/A':>11} | ✗")
        
        time.sleep(2)  # Check every 2 seconds


def main():
    """
    Main test function with menu.
    """
    print("\n" + "="*80)
    print("REALISTIC NODE SIMULATION - QUICK TEST")
    print("="*80)
    print("""
Choose a test:
1. Test single node (observe realistic behavior)
2. Compare multiple nodes (see varying characteristics)
3. Observe load variation over time
4. Check all node health endpoints
5. Run comprehensive test suite
""")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == "1":
        node_id = input("Enter node ID (e.g., node-1): ").strip() or "node-1"
        num_req = input("Number of requests (default 20): ").strip() or "20"
        test_single_node(node_id, int(num_req))
        
    elif choice == "2":
        nodes = input("Enter node IDs separated by commas (e.g., node-1,node-2,node-3): ").strip()
        if not nodes:
            nodes = "node-1,node-5,node-10"
        node_list = [n.strip() for n in nodes.split(",")]
        num_req = input("Number of requests per node (default 20): ").strip() or "20"
        compare_nodes(node_list, int(num_req))
        
    elif choice == "3":
        node_id = input("Enter node ID (e.g., node-1): ").strip() or "node-1"
        duration = input("Duration in seconds (default 60): ").strip() or "60"
        observe_load_variation(node_id, int(duration))
        
    elif choice == "4":
        print("\n" + "="*80)
        print("HEALTH CHECK - ALL NODES")
        print("="*80)
        for node_id in [f"node-{i}" for i in range(1, 16)]:
            health = test_health_endpoint(node_id)
            status = "✓" if "status" in health and health["status"] == "healthy" else "✗"
            print(f"{status} {node_id}: {json.dumps(health, indent=2)}")
            
    elif choice == "5":
        print("\nRunning comprehensive test suite...")
        print("\n[1/3] Testing benign nodes...")
        compare_nodes(["node-1", "node-2", "node-3"], 15)
        
        print("\n[2/3] Testing potentially Byzantine nodes...")
        compare_nodes(["node-10", "node-11", "node-12"], 15)
        
        print("\n[3/3] Observing load variation...")
        observe_load_variation("node-1", 30)
        
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
