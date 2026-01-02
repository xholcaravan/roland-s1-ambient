#!/usr/bin/env python3
"""
Simulate Roland S-1 for development testing
"""

import time
import random

class SimulatedS1:
    """Simulates Roland S-1 knobs and keys."""
    
    def __init__(self):
        self.knob_values = {1: 64, 2: 64, 3: 64, 4: 64}  # Middle position
        print("Simulated Roland S-1 Ready")
        print("Controls:")
        print("  Number keys 1-4: Simulate knobs 1-4")
        print("  Space: Randomize all knobs")
        print("  Q: Quit")
    
    def get_knob_value(self, knob_num):
        """Get simulated knob value (0-127)."""
        return self.knob_values.get(knob_num, 64)
    
    def randomize_knobs(self):
        """Randomize all knob positions."""
        for i in range(1, 5):
            self.knob_values[i] = random.randint(0, 127)
        print(f"Knobs randomized: {self.knob_values}")

# Test it
if __name__ == "__main__":
    s1 = SimulatedS1()
    print(f"Knob 1 value: {s1.get_knob_value(1)}")
