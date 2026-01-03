#!/usr/bin/env python3
"""
MIDI Handler for Roland S-1 Controller
Now with delay/reverb effects controls.
"""

import sys
import threading
import time
import select
import tty
import termios

class MidiHandler:
    """MIDI handler with simulation for development."""
    
    def __init__(self, audio_engine, display, use_simulation=True):
        self.audio_engine = audio_engine
        self.display = display
        self.use_simulation = use_simulation
        
        # Terminal settings for raw input
        self.old_settings = None
        self.running = True
        
        # Control step sizes
        self.crossfade_step = 0.05  # 5% per keypress
        self.effect_step = 0.1      # 10% per keypress
        
        if use_simulation:
            print("Using SIMULATED MIDI controls")
            self._init_simulation()
        else:
            print("WARNING: Real MIDI not implemented yet")
            print("Falling back to simulation")
            self._init_simulation()
    
    def _init_simulation(self):
        """Initialize simulated MIDI controls."""
        print("\n" + "="*50)
        print("SIMULATED ROLAND S-1 CONTROLS")
        print("="*50)
        print("  Q/A: Channel Crossfader (Q=↑Ambient, A=↑Rhythm)")
        print("  W/S: Delay amount (W=↑, S=↓)")
        print("  E/D: Reverb amount (E=↑, D=↓)")
        print("  ESC: Quit program")
        print("="*50)
        print("\nWaiting for input...")
        
        # Set terminal to raw mode for immediate key reading
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        
        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
    
    def _input_loop(self):
        """Read keyboard input in background."""
        while self.running:
            try:
                # Use select to check if input is available (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self._handle_key(key)
            except Exception as e:
                print(f"Input error: {e}")
                break
            time.sleep(0.01)
    
    def _handle_key(self, key):
        """Handle keyboard input."""
        # CHANNEL CROSSFADER (Q/A)
        if key == 'q':  # More Ambient
            new_value = self.audio_engine.crossfader - self.crossfade_step
            self.audio_engine.set_crossfader(max(0.0, new_value))
            print(f"[XFADE] Ambient↑ {self.audio_engine.crossfader:.2f}")
            
        elif key == 'a':  # More Rhythm
            new_value = self.audio_engine.crossfader + self.crossfade_step
            self.audio_engine.set_crossfader(min(1.0, new_value))
            print(f"[XFADE] Rhythm↑ {self.audio_engine.crossfader:.2f}")
        
        # DELAY (W/S)
        elif key == 'w':  # Increase delay
            new_value = self.audio_engine.delay_amount + self.effect_step
            self.audio_engine.set_delay_amount(min(1.0, new_value))
            self._print_delay_status()
            
        elif key == 's':  # Decrease delay
            new_value = self.audio_engine.delay_amount - self.effect_step
            self.audio_engine.set_delay_amount(max(0.0, new_value))
            self._print_delay_status()
        
        # REVERB (E/D)
        elif key == 'e':  # Increase reverb
            new_value = self.audio_engine.reverb_amount + self.effect_step
            self.audio_engine.set_reverb_amount(min(1.0, new_value))
            print(f"[REVERB] {int(self.audio_engine.reverb_amount * 100)}%")
            
        elif key == 'd':  # Decrease reverb
            new_value = self.audio_engine.reverb_amount - self.effect_step
            self.audio_engine.set_reverb_amount(max(0.0, new_value))
            print(f"[REVERB] {int(self.audio_engine.reverb_amount * 100)}%")
        
        # ESC to quit
        elif ord(key) == 27:  # ESC key
            self.running = False
            print("\n[QUIT] ESC pressed")
        
        # Update display
        self.display.update_crossfader(self.audio_engine.crossfader)
        self.display.update_delay(self.audio_engine.delay_amount)
        self.display.update_reverb(self.audio_engine.reverb_amount)
        self.display.update_volumes(
            self.audio_engine.ambient_volume,
            self.audio_engine.rhythm_volume
        )
        self.display.render()
    
    def _print_delay_status(self):
        """Print delay status with descriptive text."""
        amount = self.audio_engine.delay_amount
        percent = int(amount * 100)
        
        if amount == 0:
            desc = "OFF"
        elif amount <= 0.3:
            desc = f"SHORT ({percent}%)"
        elif amount <= 0.7:
            desc = f"MEDIUM ({percent}%)"
        else:
            desc = f"LONG ({percent}%)"
        
        print(f"[DELAY] {desc}")
    
    def cleanup(self):
        """Clean up terminal settings."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def wait_for_exit(self):
        """Wait for the input thread to finish."""
        if hasattr(self, 'input_thread'):
            self.input_thread.join(timeout=1.0)
