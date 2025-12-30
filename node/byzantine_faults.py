
import random
import time
import asyncio
from typing import Dict, Any, Optional

class AdvancedByzantine:
    """
    Implements sophisticated Byzantine fault behaviors that are harder to detect
    than simple crashes or 500 errors.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        
    def subtle_data_corruption(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify numeric values in JSON responses by ±10%.
        Keeps the structure valid so schema validation passes.
        """
        corrupted = response_data.copy()
        
        # Corrupt numeric fields
        for key, value in corrupted.items():
            if isinstance(value, (int, float)) and key != "request_num":
                # Apply small random deviation (±10%)
                deviation = random.uniform(0.9, 1.1)
                corrupted[key] = value * deviation
                
        # Occasionally flip boolean flags
        if "healthy" in corrupted:
            if random.random() < 0.2:
                corrupted["healthy"] = not corrupted["healthy"]
                
        print(f"[{self.node_id}] SUBTLE_CORRUPTION applied")
        return corrupted

    def selective_lying(self, request_num: int, original_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return different responses based on client characteristics or patterns.
        Behaves normally for most requests, lies for others.
        """
        # Lie for 30% of requests randomly
        if random.random() < 0.3:
            print(f"[{self.node_id}] SELECTIVE_LYING triggered (Req #{request_num})")
            return {
                "node": self.node_id,
                "status": "ok", # Look healthy
                "result": -1,   # Invalid result logic
                "request_num": request_num,
                "note": "This data is fabricated"
            }
        return original_response

    async def strategic_timing_attack(self) -> None:
        """
        Delay only specific types of requests or at random critical intervals.
        """
        # Add 2-5s delay probability (simulating state change or heavy load)
        delay = random.uniform(2.0, 5.0)
        print(f"[{self.node_id}] STRATEGIC_TIMING triggered (delay: {delay:.2f}s)")
        await asyncio.sleep(delay)

    def consistency_attack(self, original_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return stale or inconsistent data (e.g. from the past).
        """
        print(f"[{self.node_id}] CONSISTENCY_ATTACK triggered")
        stale = original_response.copy()
        stale["timestamp"] = "2020-01-01T00:00:00" # Old timestamp
        stale["version"] = 1 # Stale version
        return stale
