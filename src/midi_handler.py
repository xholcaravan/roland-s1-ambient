#!/usr/bin/env python3
"""
MIDI Handler for Roland S-1 Controller
Uses simulated input for development, can switch to real hardware later.
"""

import sys
import threading
import time

class MidiHandler:
    """MIDI handler with simulation for development."""
    
    def __init__(self, use_simulation=True):
        self.use_simulation = use_simulation
        
        if use_simulation:
            print("Using SIMULATED MIDI controls")
            self._init_simulation()
        else:
            print("WARNING: Real MIDI not implemented yet")
            print("Falling back to simulation")
            self._init_simulation()
    
    def _init_simulation(self):
        """Initialize simulated MIDI controls."""
        self.knob_values = {1: 64, 2: 64, 3: 64, 4: 64}  # Middle
        self.running = True
        
        print("\n" + "="*50)
        print("SIMULATED ROLAND S-1 CONTROLS")
        print("="*50)
        print("  A/D: KNOB 1 (Crossfader A← →R)")
        print("  W/S: KNOB 2")
        print("  I/K: KNOB 3")
        print("  O/L: KNOB 4")
        print("  R:   Reset all knobs")
        print("  Q:   Quit program")
        print("="*50)
        print("\nWaiting for input...")
        
        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
    
    def _input_loop(self):
        """Read keyboard input in background."""
        while self.running:
            try:
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self._handle_key(key)
            except:
                pass
            time.sleep(0.01)
    
    def _handle_key(self, key):
        """Handle keyboard input."""
        # KNOB 1: Crossfader
        if key == 'a':
            self._adjust_knob(1, -5)
        elif key == 'd':
            self._adjust_knob(1, +5)
        
        # Other knobs
        elif key == 'w':
            self._adjust_knob(2, +5)
        elif key == 's':
            self._adjust_knob(2, -5)
        elif key == 'i':
            self._adjust_knob(3, +5)
        elif key == 'k':
            self._adjust_knob(3, -5)
        elif key == 'o':
            self._adjust_knob(4, +5)
        elif key == 'l':
            self._adjust_knob(4, -5)
        
        # Reset
        elif key == 'r':
            for i in range(1, 5):
                self.knob_values[i] = 64
            print("\n[RESET] All knobs to middle position")
        
        # Quit
        elif key == 'q':
            self.running = False
            print("\n[QUIT] Signal received")
    
    def _adjust_knob(self, knob_num, delta):
        """Adjust knob value."""
        old = self.knob_values[knob_num]
        new = max(0, min(127, old + delta))
        
        if new != old:
            self.knob_values[knob_num] = new
            percent = int((new / 127) * 100)
            
            # For knob 1, show A/R direction
            if knob_num == 1:
                if percent < 40:
                    direction = "R dominant"
                elif percent > 60:
                    direction = "A dominant"
                else:
                    direction = "balanced"
                print(f"[KNOB 1] {percent}% ({direction})")
            else:
                print(f"[KNOB {knob_num}] {percent}%")
    
    def get_knob_value(self, knob_num):
        """Get knob value (0-127)."""
        return self.knob_values.get(knob_num, 64)
    
    def get_knob_percentage(self, knob_num):
        """Get knob as percentage (0-100)."""
        return int((self.get_knob_value(knob_num) / 127) * 100)
    
    def is_connected(self):
        """Always true for simulation."""
        return True
    
    def close(self):
        """Clean up."""
        self.running = False
        if self.input_thread.is_alive():
            self.input_thread.join(timeout=0.1)

if __name__ == "__main__":
    # Test the handler
    import tty, termios
    
    print("Testing MIDI Handler...")
    
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        handler = MidiHandler()
        
        print("\nTesting for 10 seconds...")
        print("Try pressing A/D to control KNOB 1")
        
        start = time.time()
        while time.time() - start < 10 and handler.running:
            time.sleep(0.1)
        
        handler.close()
        
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    print("\nTest complete!")
