#!/usr/bin/env python3
"""
Roland S-1 Controller with Auto-Load Logic
When a track volume reaches 0%, it loads a new file.
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

class AutoLoadController:
    """Controller with auto-load functionality."""
    
    def __init__(self):
        print("🎹 Roland S-1 Ambient/Rhythm Controller")
        print("=" * 50)
        print("Phase 1: Auto-Loading Crossfader")
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
        
        # Play counts for least-played selection
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
        self.last_ambient_load_time = time.time()
        self.last_rhythm_load_time = time.time()
        
        print("\n" + "="*50)
        print("SYSTEM READY WITH AUTO-LOAD!")
        print("="*50)
        print("\nControls:")
        print("  A/D: Crossfader - fade to extremes to trigger auto-load")
        print("  Q: Quit")
        print("\nAuto-load triggers when:")
        print("  • Ambient volume reaches 0% (fader left)")
        print("  • Rhythm volume reaches 0% (fader right)")
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
            self.next_ambient = self._select_least_played(
                [f for f in self.ambient_files if f != self.current_ambient]
            )
        
        if self.rhythm_files:
            self.next_rhythm = self._select_least_played(
                [f for f in self.rhythm_files if f != self.current_rhythm]
            )
    
    def _load_new_ambient(self):
        """Load new ambient file."""
        if not self.ambient_files or not self.next_ambient:
            return
        
        print(f"\n[AUTO-LOAD] Ambient → {os.path.basename(self.next_ambient)}")
        
        # Update play count
        self.play_counts[self.next_ambient] += 1
        
        # Load new file
        self.engine.load_audio_file(self.next_ambient, 'ambient')
        self.current_ambient = self.next_ambient
        
        # Pre-load next
        self._preload_next_files()
        self.last_ambient_load_time = time.time()
    
    def _load_new_rhythm(self):
        """Load new rhythm file."""
        if not self.rhythm_files or not self.next_rhythm:
            return
        
        print(f"\n[AUTO-LOAD] Rhythm → {os.path.basename(self.next_rhythm)}")
        
        # Update play count
        self.play_counts[self.next_rhythm] += 1
        
        # Load new file
        self.engine.load_audio_file(self.next_rhythm, 'rhythm')
        self.current_rhythm = self.next_rhythm
        
        # Pre-load next
        self._preload_next_files()
        self.last_rhythm_load_time = time.time()
    
    def _display_status(self, crossfader_percent):
        """Display current system status."""
        a_percent = crossfader_percent
        r_percent = 100 - crossfader_percent
        
        # Bars
        a_bar = "█" * int(a_percent / 5) + "░" * (20 - int(a_percent / 5))
        r_bar = "█" * int(r_percent / 5) + "░" * (20 - int(r_percent / 5))
        
        print(f"\n[Crossfader] {crossfader_percent}%")
        print(f"  Ambient:  {a_bar} {a_percent:.0f}%")
        print(f"  Rhythm:   {r_bar} {r_percent:.0f}%")
        
        # Current files
        if self.current_ambient:
            a_name = os.path.basename(self.current_ambient)
            a_plays = self.play_counts.get(self.current_ambient, 0)
            print(f"  ↳ {a_name} (played: {a_plays})")
        
        if self.current_rhythm:
            r_name = os.path.basename(self.current_rhythm)
            r_plays = self.play_counts.get(self.current_rhythm, 0)
            print(f"  ↳ {r_name} (played: {r_plays})")
        
        # Auto-load hint
        if crossfader_percent < 5:
            print("  ⚡ READY: Move fader right to load new Ambient")
        elif crossfader_percent > 95:
            print("  ⚡ READY: Move fader left to load new Rhythm")
    
    def run(self):
        """Main loop."""
        # Start audio
        self.engine.play()
        
        # Main loop
        last_display_time = time.time()
        last_crossfader = self.midi.get_knob_percentage(1)
        ambient_loaded_at_zero = False
        rhythm_loaded_at_zero = False
        
        try:
            while self.running and self.midi.running:
                # Get crossfader position
                crossfader = self.midi.get_knob_percentage(1)
                
                # Update volumes (inverse relationship)
                ambient_vol = crossfader / 100.0
                rhythm_vol = 1.0 - ambient_vol
                self.engine.set_volumes(ambient_vol, rhythm_vol)
                
                # Check for auto-load conditions
                if crossfader < 5:  # Ambient volume ~0%
                    if not ambient_loaded_at_zero:
                        self._load_new_ambient()
                        ambient_loaded_at_zero = True
                else:
                    ambient_loaded_at_zero = False
                
                if crossfader > 95:  # Rhythm volume ~0%
                    if not rhythm_loaded_at_zero:
                        self._load_new_rhythm()
                        rhythm_loaded_at_zero = True
                else:
                    rhythm_loaded_at_zero = False
                
                # Display updates
                if crossfader != last_crossfader:
                    self._display_status(crossfader)
                    last_crossfader = crossfader
                    last_display_time = time.time()
                elif time.time() - last_display_time > 3.0:
                    self._display_status(crossfader)
                    last_display_time = time.time()
                
                # Small delay
                time.sleep(0.05)
                
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
        print("[SYSTEM] Goodbye!")

def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, signal_handler)
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setcbreak(sys.stdin.fileno())
        controller = AutoLoadController()
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
