#!/usr/bin/env python3
"""
Better Simulated MIDI with all knobs always visible.
"""

import sys
import threading
import time

class BetterSimulatedMidi:
    """Simulated MIDI with proper display."""
    
    def __init__(self):
        self.knob_values = {1: 64, 2: 64, 3: 64, 4: 64}
        self.running = True
        
        print("\n" + "="*50)
        print("SIMULATED ROLAND S-1 (Better Display)")
        print("="*50)
        print("CONTROLS:")
        print("  A/D: KNOB 1 (Crossfader A← →R)")
        print("  W/S: KNOB 2")
        print("  I/K: KNOB 3")
        print("  O/L: KNOB 4")
        print("  R: Reset all to middle")
        print("  Q: Quit")
        print("="*50)
        
        # Start display thread
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        
        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
    
    def _get_knob_display(self, knob_num):
        """Get display string for a knob."""
        value = self.knob_values[knob_num]
        percent = int((value / 127) * 100)
        
        # Bar graph (20 characters)
        bar_length = int(percent / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        
        # For knob 1 (crossfader), show A/R labels
        if knob_num == 1:
            if percent < 40:
                label = "R<<<"
            elif percent > 60:
                label = ">>>A"
            else:
                label = "A<>R"
            return f"KNOB 1 [{label}]: {bar} {percent}%"
        else:
            return f"KNOB {knob_num}: {bar} {percent}%"
    
    def _display_loop(self):
        """Continuously update the display."""
        last_display = ""
        
        while self.running:
            # Build new display
            display_lines = []
            for i in range(1, 5):
                display_lines.append(self._get_knob_display(i))
            
            display = "\n".join(display_lines)
            
            # Only update if changed
            if display != last_display:
                # Move cursor up 4 lines and clear
                sys.stdout.write("\033[4A\033[0J")
                sys.stdout.write(display)
                sys.stdout.flush()
                last_display = display
            
            time.sleep(0.1)
    
    def _input_loop(self):
        """Read keyboard input."""
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
        # KNOB 1: A/D
        if key == 'a':
            self._adjust_knob(1, -5)
        elif key == 'd':
            self._adjust_knob(1, +5)
        
        # KNOB 2: W/S
        elif key == 'w':
            self._adjust_knob(2, +5)
        elif key == 's':
            self._adjust_knob(2, -5)
        
        # KNOB 3: I/K
        elif key == 'i':
            self._adjust_knob(3, +5)
        elif key == 'k':
            self._adjust_knob(3, -5)
        
        # KNOB 4: O/L
        elif key == 'o':
            self._adjust_knob(4, +5)
        elif key == 'l':
            self._adjust_knob(4, -5)
        
        # Reset
        elif key == 'r':
            for i in range(1, 5):
                self.knob_values[i] = 64
            print("\n" + "="*20 + " RESET " + "="*20)
        
        # Quit
        elif key == 'q':
            self.running = False
    
    def _adjust_knob(self, knob_num, delta):
        """Adjust knob value."""
        old = self.knob_values[knob_num]
        new = max(0, min(127, old + delta))
        self.knob_values[knob_num] = new
    
    def get_knob_value(self, knob_num):
        return self.knob_values.get(knob_num, 64)
    
    def get_knob_percentage(self, knob_num):
        return int((self.get_knob_value(knob_num) / 127) * 100)
    
    def is_connected(self):
        return True
    
    def close(self):
        self.running = False
        # Restore cursor position
        sys.stdout.write("\n" * 5)
        sys.stdout.flush()

# Test
if __name__ == "__main__":
    import tty, termios
    
    print("Starting better simulated MIDI...")
    print("Press any key to begin, Q to quit")
    print("="*50)
    
    # Make space for display
    for _ in range(4):
        print()
    
    # Setup terminal
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        midi = BetterSimulatedMidi()
        
        # Keep running
        while midi.running:
            time.sleep(0.1)
        
        midi.close()
        
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    print("\n" + "="*50)
    print("Simulation ended. Goodbye!")
    print("="*50)
