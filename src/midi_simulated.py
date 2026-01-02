#!/usr/bin/env python3
"""
Simulated MIDI Handler for development testing.
Simulates Roland S-1 knobs using keyboard input.
"""

import sys
import select
import tty
import termios
import threading
import time

class SimulatedMidiHandler:
    """Simulates Roland S-1 knobs for development."""
    
    def __init__(self):
        self.knob_values = {1: 64, 2: 64, 3: 64, 4: 64}  # Middle position (64/127)
        self.running = True
        self.last_knob_change = {1: 0, 2: 0, 3: 0, 4: 0}
        
        print("\n" + "="*50)
        print("SIMULATED ROLAND S-1 CONTROLS")
        print("="*50)
        print("Keyboard Controls:")
        print("  1-4: Select knob 1-4")
        print("  ↑/↓: Increase/decrease selected knob")
        print("  Space: Randomize all knobs")
        print("  R: Reset all knobs to middle")
        print("  Q: Quit")
        print("="*50)
        print(f"Initial knob positions: {self.knob_values}")
        print("="*50 + "\n")
        
        self.selected_knob = 1
        self._setup_nonblocking_input()
        
        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
    
    def _setup_nonblocking_input(self):
        """Set up terminal for non-blocking input."""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    def _restore_terminal(self):
        """Restore terminal settings."""
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def _input_loop(self):
        """Read keyboard input in background thread."""
        while self.running:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                self._handle_key(key)
            time.sleep(0.01)
    
    def _handle_key(self, key):
        """Handle keyboard input."""
        key = key.lower()
        
        # Select knob 1-4
        if key in ['1', '2', '3', '4']:
            self.selected_knob = int(key)
            print(f"Selected knob {self.selected_knob}")
        
        # Adjust knob value
        elif key == '\x1b':  # Escape sequence for arrows
            # Read next two chars for arrow keys
            next1 = sys.stdin.read(1)
            next2 = sys.stdin.read(1)
            if next1 == '[':
                if next2 == 'A':  # Up arrow
                    self._adjust_knob(self.selected_knob, +5)
                elif next2 == 'B':  # Down arrow
                    self._adjust_knob(self.selected_knob, -5)
        
        # Simple up/down with u/d keys (alternative to arrows)
        elif key == 'u':
            self._adjust_knob(self.selected_knob, +10)
        elif key == 'd':
            self._adjust_knob(self.selected_knob, -10)
        
        # Randomize
        elif key == ' ':
            import random
            for i in range(1, 5):
                self.knob_values[i] = random.randint(0, 127)
            print(f"Randomized: {self.knob_values}")
        
        # Reset
        elif key == 'r':
            for i in range(1, 5):
                self.knob_values[i] = 64
            print(f"Reset to middle: {self.knob_values}")
        
        # Quit
        elif key == 'q':
            self.running = False
            print("\nQuitting...")
    
    def _adjust_knob(self, knob_num, delta):
        """Adjust knob value with bounds checking."""
        old_value = self.knob_values[knob_num]
        new_value = max(0, min(127, old_value + delta))
        
        if new_value != old_value:
            self.knob_values[knob_num] = new_value
            percent = int((new_value / 127) * 100)
            print(f"Knob {knob_num}: {new_value}/127 ({percent}%)")
            self.last_knob_change[knob_num] = time.time()
    
    def get_knob_value(self, knob_num):
        """Get current knob value (0-127)."""
        return self.knob_values.get(knob_num, 64)
    
    def get_knob_percentage(self, knob_num):
        """Get knob value as percentage (0-100)."""
        value = self.get_knob_value(knob_num)
        return int((value / 127) * 100)
    
    def is_connected(self):
        """Simulated - always connected."""
        return True
    
    def close(self):
        """Clean up."""
        self.running = False
        self._restore_terminal()
        if self.input_thread.is_alive():
            self.input_thread.join(timeout=0.1)

# Test function
def test_simulated_midi():
    """Test the simulated MIDI handler."""
    print("Testing simulated MIDI...")
    print("Press keys to control, Q to quit")
    
    midi = SimulatedMidiHandler()
    
    try:
        while midi.running:
            # Display current state
            values = [midi.get_knob_value(i) for i in range(1, 5)]
            percents = [midi.get_knob_percentage(i) for i in range(1, 5)]
            
            # Simple ASCII bar display
            bars = []
            for percent in percents:
                bar_length = int(percent / 5)  # 0-20 characters
                bars.append("█" * bar_length + "░" * (20 - bar_length))
            
            print(f"\rKnobs: 1[{bars[0]}] 2[{bars[1]}] 3[{bars[2]}] 4[{bars[3]}]", end="")
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        midi.close()
    
    print("\nTest complete!")

if __name__ == "__main__":
    test_simulated_midi()
