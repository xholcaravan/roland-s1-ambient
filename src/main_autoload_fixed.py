#!/usr/bin/env python3
"""
Roland S-1 Controller with Fixed Auto-Load Logic
Auto-loads at exactly 0% volume (with deadzone to prevent jitter).
"""

import sys
import os
import time
import signal
import tty
import termios
import random

def signal_handler(sig, frame):
    print("\n\n[SYSTEM] Shutting down...")
    sys.exit(0)

class FixedAutoLoadController:
    """Controller with precise 0% auto-load."""
    
    def __init__(self):
        print("🎹 Roland S-1 Ambient/Rhythm Controller")
        print("=" * 50)
        print("Phase 1: Auto-Loading at 0% Volume")
        print("=" * 50)
        
        # Add src to path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        
        # Import components
        from audio_engine import AudioEngine
        from midi_handler import MidiHandler
        
        # Initialize
        print("\n[SYSTEM] Initializing...")
        self.engine = AudioEngine()
        self.midi = MidiHandler(use_simulation=True)
        
        # File management
        self.ambient_files = self._get_audio_files("samples/ambient/")
        self.rhythm_files = self._get_audio_files("samples/rhythm/")
        
        # Play counts
        self.play_counts = {f: 0 for f in self.ambient_files + self.rhythm_files}
        
        # Current files
        self.current_ambient = None
        self.current_rhythm = None
        self.next_ambient = None
        self.next_rhythm = None
        
        # Load initial files
        self._load_initial_files()
        
        # State
        self.running = True
        
        # Auto-load state (to prevent multiple triggers)
        self.ambient_at_zero = False
        self.rhythm_at_zero = False
        
        # Deadzone to prevent jitter (must stay at 0% for this many seconds)
        self.deadzone_time = 0.1  # 100ms
        
        print("\n" + "="*50)
        print("SYSTEM READY - AUTO-LOAD AT 0%!")
        print("="*50)
        print("\nControls:")
        print("  A: Move crossfader LEFT (more Rhythm)")
        print("  D: Move crossfader RIGHT (more Ambient)")
        print("  Q: Quit")
        print("\nAuto-load triggers WHEN:")
        print("  • Ambient volume = 0% (fader fully LEFT)")
        print("  • Rhythm volume = 0% (fader fully RIGHT)")
        print("="*50)
    
    def _get_audio_files(self, directory):
        """Get list of WAV files in directory."""
        files = []
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.lower().endswith('.wav'):
                    files.append(os.path.join(directory, f))
        return sorted(files)
    
    def _load_initial_files(self):
        """Load initial audio files."""
        if self.ambient_files:
            self.current_ambient = self._select_least_played(self.ambient_files)
            self.engine.load_audio_file(self.current_ambient, 'ambient')
            self.play_counts[self.current_ambient] += 1
            print(f"[AMBIENT] Loaded: {os.path.basename(self.current_ambient)}")
        
        if self.rhythm_files:
            self.current_rhythm = self._select_least_played(self.rhythm_files)
            self.engine.load_audio_file(self.current_rhythm, 'rhythm')
            self.play_counts[self.current_rhythm] += 1
            print(f"[RHYTHM]  Loaded: {os.path.basename(self.current_rhythm)}")
        
        # Pre-load next files
        self._preload_next_files()
    
    def _select_least_played(self, file_list):
        """Select file with lowest play count."""
        if not file_list:
            return None
        
        # Get minimum play count
        min_count = min(self.play_counts.get(f, 0) for f in file_list)
        
        # Get files with minimum count
        candidates = [f for f in file_list if self.play_counts.get(f, 0) == min_count]
        
        # Random choice among candidates
        return random.choice(candidates) if candidates else file_list[0]
    
    def _preload_next_files(self):
        """Pre-load next candidate files."""
        if self.ambient_files:
            available = [f for f in self.ambient_files if f != self.current_ambient]
            if available:
                self.next_ambient = self._select_least_played(available)
        
        if self.rhythm_files:
            available = [f for f in self.rhythm_files if f != self.current_rhythm]
            if available:
                self.next_rhythm = self._select_least_played(available)
    
    def _load_new_ambient(self):
        """Load new ambient file."""
        if not self.ambient_files or not self.next_ambient:
            return
        
        print(f"\n[⚡ AUTO-LOAD] New Ambient: {os.path.basename(self.next_ambient)}")
        
        # Update play count
        self.play_counts[self.next_ambient] += 1
        
        # Load new file
        self.engine.load_audio_file(self.next_ambient, 'ambient')
        self.current_ambient = self.next_ambient
        
        # Pre-load next
        self._preload_next_files()
    
    def _load_new_rhythm(self):
        """Load new rhythm file."""
        if not self.rhythm_files or not self.next_rhythm:
            return
        
        print(f"\n[⚡ AUTO-LOAD] New Rhythm: {os.path.basename(self.next_rhythm)}")
        
        # Update play count
        self.play_counts[self.next_rhythm] += 1
        
        # Load new file
        self.engine.load_audio_file(self.next_rhythm, 'rhythm')
        self.current_rhythm = self.next_rhythm
        
        # Pre-load next
        self._preload_next_files()
    
    def _display_status(self, crossfader_percent, show_files=True):
        """Display current system status."""
        a_percent = crossfader_percent
        r_percent = 100 - crossfader_percent
        
        # Bars with precision
        a_bar = "█" * int(a_percent / 5) + "░" * (20 - int(a_percent / 5))
        r_bar = "█" * int(r_percent / 5) + "░" * (20 - int(r_percent / 5))
        
        print(f"\n[Crossfader] {crossfader_percent}%")
        print(f"  Ambient:  {a_bar} {a_percent:.1f}%")
        print(f"  Rhythm:   {r_bar} {r_percent:.1f}%")
        
        if show_files:
            if self.current_ambient:
                a_name = os.path.basename(self.current_ambient)
                a_plays = self.play_counts.get(self.current_ambient, 0)
                print(f"  ↳ Ambient: {a_name} (plays: {a_plays})")
            
            if self.current_rhythm:
                r_name = os.path.basename(self.current_rhythm)
                r_plays = self.play_counts.get(self.current_rhythm, 0)
                print(f"  ↳ Rhythm:  {r_name} (plays: {r_plays})")
        
        # Auto-load status
        if crossfader_percent == 0:
            print("  ⚡ AMBIENT AT 0% - Will load new file when moved away")
        elif crossfader_percent == 100:
            print("  ⚡ RHYTHM AT 0% - Will load new file when moved away")
        elif crossfader_percent < 10:
            print("  → Moving LEFT to trigger Ambient auto-load")
        elif crossfader_percent > 90:
            print("  → Moving RIGHT to trigger Rhythm auto-load")
    
    def run(self):
        """Main loop."""
        # Start audio
        self.engine.play()
        
        # Main loop
        last_display_time = time.time()
        last_crossfader = -1  # Force initial display
        zero_start_time = None
        at_zero_type = None  # 'ambient' or 'rhythm'
        
        try:
            while self.running and self.midi.running:
                # Get crossfader position (0-100%)
                crossfader = self.midi.get_knob_percentage(1)
                
                # Update volumes
                ambient_vol = crossfader / 100.0
                rhythm_vol = 1.0 - ambient_vol
                self.engine.set_volumes(ambient_vol, rhythm_vol)
                
                # Check for 0% positions
                if crossfader == 0:  # Ambient at 0%
                    if at_zero_type != 'ambient':
                        at_zero_type = 'ambient'
                        zero_start_time = time.time()
                        print(f"\n[0% DETECTED] Ambient volume = 0%")
                        print("[INFO] Move crossfader RIGHT to load new Ambient file")
                    
                    # Check if we've been at 0% long enough (deadzone)
                    elif zero_start_time and (time.time() - zero_start_time > self.deadzone_time):
                        if not self.ambient_at_zero:
                            self._load_new_ambient()
                            self.ambient_at_zero = True
                
                elif crossfader == 100:  # Rhythm at 0%
                    if at_zero_type != 'rhythm':
                        at_zero_type = 'rhythm'
                        zero_start_time = time.time()
                        print(f"\n[0% DETECTED] Rhythm volume = 0%")
                        print("[INFO] Move crossfader LEFT to load new Rhythm file")
                    
                    # Check deadzone
                    elif zero_start_time and (time.time() - zero_start_time > self.deadzone_time):
                        if not self.rhythm_at_zero:
                            self._load_new_rhythm()
                            self.rhythm_at_zero = True
                
                else:
                    # Not at 0%, reset states
                    at_zero_type = None
                    zero_start_time = None
                    self.ambient_at_zero = False
                    self.rhythm_at_zero = False
                
                # Display updates
                if crossfader != last_crossfader:
                    show_files = (abs(crossfader - last_crossfader) > 5) or (last_crossfader == -1)
                    self._display_status(crossfader, show_files)
                    last_crossfader = crossfader
                    last_display_time = time.time()
                elif time.time() - last_display_time > 2.0:
                    self._display_status(crossfader, show_files=False)
                    last_display_time = time.time()
                
                # Small delay
                time.sleep(0.02)  # 50Hz update
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupted")
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown."""
        print("\n[SYSTEM] Shutting down...")
        self.running = False
        self.engine.stop()
        self.midi.close()
        print("[SYSTEM] Session summary:")
        print("  Files played:")
        for file, count in self.play_counts.items():
            if count > 0:
                print(f"    {os.path.basename(file)}: {count} times")
        print("[SYSTEM] Goodbye!")

def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, signal_handler)
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setcbreak(sys.stdin.fileno())
        controller = FixedAutoLoadController()
        controller.run()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n[SYSTEM] Terminal restored")

if __name__ == "__main__":
    main()
