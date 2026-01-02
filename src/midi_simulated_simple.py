#!/usr/bin/env python3
"""
Simple Simulated MIDI Handler with working arrow keys.
"""

import sys
import threading
import time

class SimpleSimulatedMidi:
    """Simple simulated MIDI with working controls."""
    
    def __init__(self):
        # Knob 1: Crossfader (A/R balance) - start in middle
        # Knob 2-4: Other controls (for future)
        self.knob_values = {1: 64, 2: 64, 3: 64, 4: 64}
        
        print("\n" + "="*50)
        print("SIMPLE SIMULATED ROLAND S-1")
        print("="*50)
        print("CONTROLS:")
        print("  A/D: Move KNOB 1 (Crossfader) left/right")
        print("  W/S: Move KNOB 2 up/down")
        print("  I/K: Move KNOB 3 up/down")
        print("  O/L: Move KNOB 4 up/down")
        print("  R:   Reset all to middle")
        print("  Q:   Quit")
        print("="*50)
        print("Current values:")
        self._display_knobs()
        print("="*50)
        
        # Start input thread
        self.running = True
        self.thread = threading.Thread(target=self._input_thread, daemon=True)
        self.thread.start()
    
    def _display_knobs(self):
        """Display current knob values."""
        for i in range(1, 5):
            value = self.knob_values[i]
            percent = int((value / 127) * 100)
            bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
            print(f"  KNOB {i}: {bar} {percent}%")
    
    def _input_thread(self):
        """Thread to read keyboard input."""
        while self.running:
            try:
                # Non-blocking input
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self._handle_key(key)
            except:
                pass
            time.sleep(0.01)
    
    def _handle_key(self, key):
        """Handle keyboard input."""
        # KNOB 1: Crossfader (A/D for left/right)
        if key == 'a':  # Move left (more rhythm)
            self._adjust_knob(1, -5)
        elif key == 'd':  # Move right (more ambient)
            self._adjust_knob(1, +5)
        
        # KNOB 2: Future control (W/S)
        elif key == 'w':
            self._adjust_knob(2, +5)
        elif key == 's':
            self._adjust_knob(2, -5)
        
        # KNOB 3: Future control (I/K)
        elif key == 'i':
            self._adjust_knob(3, +5)
        elif key == 'k':
            self._adjust_knob(3, -5)
        
        # KNOB 4: Future control (O/L)
        elif key == 'o':
            self._adjust_knob(4, +5)
        elif key == 'l':
            self._adjust_knob(4, -5)
        
        # Reset
        elif key == 'r':
            for i in range(1, 5):
                self.knob_values[i] = 64
            print("\n" + "="*20)
            print("RESET: All knobs to middle")
            self._display_knobs()
            print("="*20)
        
        # Quit
        elif key == 'q':
            self.running = False
            print("\nQuitting simulation...")
    
    def _adjust_knob(self, knob_num, delta):
        """Adjust knob value."""
        old = self.knob_values[knob_num]
        new = max(0, min(127, old + delta))
        
        if new != old:
            self.knob_values[knob_num] = new
            percent = int((new / 127) * 100)
            
            # Clear line and update display
            sys.stdout.write(f"\rKNOB {knob_num}: {'█' * int(percent/5)}{'░' * (20-int(percent/5))} {percent}%")
            sys.stdout.flush()
    
    def get_knob_value(self, knob_num):
        """Get knob value (0-127)."""
        return self.knob_values.get(knob_num, 64)
    
    def get_knob_percentage(self, knob_num):
        """Get knob as percentage (0-100)."""
        return int((self.get_knob_value(knob_num) / 127) * 100)
    
    def is_connected(self):
        return True
    
    def close(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=0.1)

# Test
if __name__ == "__main__":
    print("Starting simple simulated MIDI...")
    print("Press Enter to begin...")
    input()
    
    # Setup terminal for single char input
    import tty, termios
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        midi = SimpleSimulatedMidi()
        
        # Keep running
        while midi.running:
            time.sleep(0.1)
        
        midi.close()
        
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    print("\nSimulation ended.")
