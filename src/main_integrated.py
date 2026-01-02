#!/usr/bin/env python3
"""
Integrated Roland S-1 Controller
Combines audio engine with simulated MIDI and crossfader logic.
"""

import sys
import os
import time
import signal
import tty
import termios

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[SYSTEM] Shutting down...")
    sys.exit(0)

class IntegratedController:
    """Main controller integrating all components."""
    
    def __init__(self):
        print("🎹 Roland S-1 Ambient/Rhythm Controller")
        print("=" * 50)
        print("Phase 1: Integrated System with Simulated MIDI")
        print("=" * 50)
        
        # Add src to path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        
        # Import components
        from audio_engine import AudioEngine
        from midi_handler import MidiHandler
        
        # Initialize components
        print("\n[SYSTEM] Initializing AudioEngine...")
        self.engine = AudioEngine()
        
        print("[SYSTEM] Loading audio files...")
        self.engine.load_audio_file("samples/ambient/a_pad_c.wav", 'ambient')
        self.engine.load_audio_file("samples/rhythm/r_beat_1.wav", 'rhythm')
        
        print("[SYSTEM] Initializing MIDI Handler (simulated)...")
        self.midi = MidiHandler(use_simulation=True)
        
        # State
        self.running = True
        self.ambient_volume = 0.5
        self.rhythm_volume = 0.5
        
        print("\n" + "="*50)
        print("SYSTEM READY!")
        print("="*50)
        print("\nControls:")
        print("  A/D: Crossfader (KNOB 1) - Balance A/R")
        print("  Q: Quit program")
        print("\nCurrent state:")
        self._display_status()
        print("="*50)
    
    def _display_status(self):
        """Display current system status."""
        knob_val = self.midi.get_knob_percentage(1)
        a_percent = knob_val
        r_percent = 100 - knob_val
        
        # Simple bar display
        a_bar = "█" * int(a_percent / 5) + "░" * (20 - int(a_percent / 5))
        r_bar = "█" * int(r_percent / 5) + "░" * (20 - int(r_percent / 5))
        
        print(f"\n[Crossfader] KNOB 1: {knob_val}%")
        print(f"  Ambient:  {a_bar} {a_percent:.0f}%")
        print(f"  Rhythm:   {r_bar} {r_percent:.0f}%")
        
        if knob_val < 40:
            print("  ↳ RHYTHM DOMINANT (A will load new file if goes to 0%)")
        elif knob_val > 60:
            print("  ↳ AMBIENT DOMINANT (R will load new file if goes to 0%)")
        else:
            print("  ↳ BALANCED")
    
    def _update_volumes(self):
        """Update audio volumes based on crossfader position."""
        # Get crossfader position (0-100%)
        crossfader = self.midi.get_knob_percentage(1) / 100.0
        
        # Convert to volumes (when crossfader at 0%: R=100%, A=0%)
        self.rhythm_volume = 1.0 - crossfader  # Left side = more rhythm
        self.ambient_volume = crossfader        # Right side = more ambient
        
        # Apply to audio engine
        self.engine.set_volumes(self.ambient_volume, self.rhythm_volume)
    
    def _check_auto_load(self):
        """Check if we should auto-load new files (when volume reaches 0%)."""
        # TODO: Implement auto-load logic
        pass
    
    def run(self):
        """Main loop."""
        # Start audio playback
        self.engine.play()
        print("[AUDIO] Playback started")
        
        # Main loop
        last_display_time = time.time()
        last_knob_value = self.midi.get_knob_value(1)
        
        try:
            while self.running and self.midi.running:
                # Update volumes based on crossfader
                self._update_volumes()
                
                # Check for knob changes
                current_knob = self.midi.get_knob_value(1)
                if current_knob != last_knob_value:
                    self._display_status()
                    last_knob_value = current_knob
                    last_display_time = time.time()
                
                # Periodic status update
                if time.time() - last_display_time > 5.0:
                    self._display_status()
                    last_display_time = time.time()
                
                # Check auto-load conditions
                self._check_auto_load()
                
                # Small delay
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupted by user")
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown."""
        print("\n[SYSTEM] Shutting down...")
        self.running = False
        self.engine.stop()
        self.midi.close()
        print("[SYSTEM] Goodbye!")

def main():
    """Main entry point."""
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Setup terminal for single char input
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        # Create and run controller
        controller = IntegratedController()
        controller.run()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Restore terminal
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n[SYSTEM] Terminal restored")

if __name__ == "__main__":
    main()
