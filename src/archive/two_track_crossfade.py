#!/usr/bin/env python3
"""
Two-Track Crossfade Loop Tester
Clean implementation with two independent playback tracks
"""

import os
import sys
import json
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import select
import tty
import termios

class TwoTrackCrossfadeTester:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # Two independent playback tracks
        self.track1_pos = 0.0  # Current loop position (in samples, can be fractional)
        self.track2_pos = 0.0  # Next loop position
        self.active_track = 1  # Which track is currently "primary" (not fading out)
        
        # Playback state
        self.is_playing = False
        self.filename = ""
        self.file_duration = 0
        self.loops_completed = 0
        
        # UI state
        self.running = True
        self.old_termios = None
        
        print("\n" + "="*60)
        print("TWO-TRACK CROSSFADE LOOP TESTER")
        print("Clean implementation with independent tracks")
        print("="*60)
    
    def list_audio_files(self, directory):
        """List all audio files in directory with durations."""
        files = []
        if os.path.exists(directory):
            for f in sorted(os.listdir(directory)):
                if f.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                    path = os.path.join(directory, f)
                    try:
                        data, sr = sf.read(path)
                        duration = len(data) / sr
                        files.append((f, duration, path))
                    except:
                        files.append((f, 0, path))
        return files
    
    def select_file(self):
        """Let user select an audio file to test."""
        directory = "samples/real_test"
        files = self.list_audio_files(directory)
        
        if not files:
            print(f"\n❌ No audio files found in {directory}/")
            print("Please place your test files there.")
            return False
        
        print(f"\nAudio files in {directory}/:")
        for i, (name, duration, path) in enumerate(files, 1):
            print(f"[{i}] {name} ({duration:.1f}s)")
        
        print(f"[{len(files)+1}] Quit")
        
        # Restore terminal to normal mode for file selection
        if self.old_termios:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_termios)
            self.old_termios = None
        
        while True:
            try:
                sys.stdout.write(f"\nSelect file (1-{len(files)+1}): ")
                sys.stdout.flush()
                choice = sys.stdin.readline().strip()
                
                if not choice:
                    continue
                
                if choice.lower() == 'q':
                    return False
                
                choice_idx = int(choice) - 1
                
                if choice_idx == len(files):
                    return False
                
                if 0 <= choice_idx < len(files):
                    name, duration, path = files[choice_idx]
                    return self.load_file(path, name, duration)
                
                print(f"Please enter 1-{len(files)+1}")
                
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection")
                return False
    
    def load_file(self, filepath, filename, duration):
        """Load an audio file."""
        try:
            print(f"\nLoading {filename}...")
            data, sr = sf.read(filepath, always_2d=True)
            
            # Resample if needed
            if sr != self.sample_rate:
                print(f"Resampling {sr}Hz → {self.sample_rate}Hz")
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            # Ensure stereo
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            # Store
            self.audio_data = data
            self.total_samples = len(data)
            self.filename = filename
            self.file_duration = duration
            
            # Reset playback state
            self.track1_pos = 0.0
            self.track2_pos = 0.0
            self.active_track = 1
            self.loops_completed = 0
            
            # Update crossfade samples
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Load existing config if available
            config_path = filepath.replace('.wav', '.txt').replace('.mp3', '.txt').replace('.flac', '.txt').replace('.ogg', '.txt')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if 'crossfade_ms' in config:
                            self.crossfade_ms = config['crossfade_ms']
                            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
                            print(f"Loaded saved crossfade: {self.crossfade_ms}ms")
                except:
                    print("Could not load config, using default")
            
            print(f"✅ Loaded: {filename}")
            print(f"   Duration: {duration:.1f} seconds")
            print(f"   Crossfade: {self.crossfade_ms}ms")
            print(f"   Track 2 will start {self.crossfade_ms/1000:.1f}s before Track 1 ends")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return False
    
    def get_audio_at_position(self, position):
        """Get audio at given position (with interpolation)."""
        if self.audio_data is None:
            return np.zeros(2)
        
        # Wrap position to loop length
        pos = position % self.total_samples
        
        # Linear interpolation between samples
        idx0 = int(np.floor(pos))
        idx1 = (idx0 + 1) % self.total_samples
        t = pos - idx0
        
        if idx0 < self.total_samples and idx1 < self.total_samples:
            return (1 - t) * self.audio_data[idx0] + t * self.audio_data[idx1]
        return np.zeros(2)
    
    def audio_callback(self, outdata, frames, time, status):
        """Two-track audio callback with perfect crossfade."""
        if status:
            print(f"Audio status: {status}")
        
        if self.audio_data is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        output = np.zeros((frames, 2), dtype=np.float32)
        
        for i in range(frames):
            # Determine if we should start crossfade
            remaining_track1 = self.total_samples - self.track1_pos
            
            if remaining_track1 <= self.crossfade_samples and self.crossfade_samples > 0:
                # IN CROSSFADE REGION
                
                # Calculate how far through crossfade we are (0 to 1)
                fade_progress = 1.0 - (remaining_track1 / self.crossfade_samples)
                
                # Get audio from both tracks
                audio1 = self.get_audio_at_position(self.track1_pos)
                audio2 = self.get_audio_at_position(self.track2_pos)
                
                # Apply crossfade curves (linear for now)
                fade_out = 1.0 - fade_progress  # Track 1 fades out
                fade_in = fade_progress         # Track 2 fades in
                
                # Mix
                output[i] = audio1 * fade_out + audio2 * fade_in
                
                # Advance both tracks
                self.track1_pos += 1
                self.track2_pos += 1
                
                # Check if crossfade is complete
                if fade_progress >= 1.0:
                    # Crossfade complete! Track 2 is now active
                    self.active_track = 2
                    self.loops_completed += 1
                    
                    # Reset track 1 to prepare for next crossfade
                    self.track1_pos = self.track2_pos - self.crossfade_samples
                    if self.track1_pos < 0:
                        self.track1_pos += self.total_samples
                    
            else:
                # NORMAL PLAYBACK (no crossfade)
                if self.active_track == 1:
                    # Playing track 1 normally
                    output[i] = self.get_audio_at_position(self.track1_pos)
                    self.track1_pos += 1
                    
                    # Position track 2 to start at right time for next crossfade
                    self.track2_pos = self.track1_pos - self.crossfade_samples
                    if self.track2_pos < 0:
                        self.track2_pos += self.total_samples
                        
                else:
                    # Playing track 2 normally (after crossfade)
                    output[i] = self.get_audio_at_position(self.track2_pos)
                    self.track2_pos += 1
                    
                    # Position track 1 to start at right time for next crossfade
                    self.track1_pos = self.track2_pos - self.crossfade_samples
                    if self.track1_pos < 0:
                        self.track1_pos += self.total_samples
            
            # Swap tracks when current track reaches end
            if self.active_track == 1 and self.track1_pos >= self.total_samples:
                self.track1_pos = 0
            elif self.active_track == 2 and self.track2_pos >= self.total_samples:
                self.track2_pos = 0
        
        outdata[:] = output
    
    def adjust_crossfade(self, delta_ms):
        """Adjust crossfade time."""
        old_ms = self.crossfade_ms
        new_ms = max(0, min(30000, self.crossfade_ms + delta_ms))
        
        if new_ms != old_ms:
            self.crossfade_ms = new_ms
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Reset tracks to maintain sync with new crossfade time
            if self.active_track == 1:
                self.track2_pos = self.track1_pos - self.crossfade_samples
                if self.track2_pos < 0:
                    self.track2_pos += self.total_samples
            else:
                self.track1_pos = self.track2_pos - self.crossfade_samples
                if self.track1_pos < 0:
                    self.track1_pos += self.total_samples
            
            # Save config
            self.save_config()
            return True
        
        return False
    
    def save_config(self):
        """Save current crossfade to .txt file."""
        if not self.filename:
            return
        
        directory = "samples/real_test"
        for f in os.listdir(directory):
            if f == self.filename:
                filepath = os.path.join(directory, f)
                config_path = filepath.replace('.wav', '.txt').replace('.mp3', '.txt').replace('.flac', '.txt').replace('.ogg', '.txt')
                
                config = {
                    "crossfade_ms": self.crossfade_ms,
                    "strategy": "two-track",
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": "Two-track implementation with perfect sync"
                }
                
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\n💾 Saved crossfade {self.crossfade_ms}ms")
                except Exception as e:
                    print(f"Error saving config: {e}")
                break
    
    def display_status(self):
        """Display current testing status."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*60)
        print(f"TWO-TRACK TESTING: {self.filename}")
        print("="*60)
        
        if self.audio_data is not None:
            # Calculate positions
            if self.active_track == 1:
                current_pos = self.track1_pos
                next_pos = self.track2_pos
            else:
                current_pos = self.track2_pos
                next_pos = self.track1_pos
            
            current_time = current_pos / self.sample_rate
            next_time = next_pos / self.sample_rate
            remaining = self.total_samples - current_pos
            remaining_time = remaining / self.sample_rate
            
            print(f"Duration: {self.file_duration:.1f} seconds")
            print(f"Active track: {self.active_track}")
            print(f"Current position: {current_time:.1f}s")
            print(f"Next track starts in: {remaining_time:.1f}s")
            print(f"Loops completed: {self.loops_completed}")
            print(f"Crossfade: {self.crossfade_ms}ms")
            
            # Show crossfade indicator
            if remaining_time <= self.crossfade_ms/1000:
                progress = 1.0 - (remaining_time / (self.crossfade_ms/1000))
                bar_length = 30
                filled = int(progress * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"Crossfade active: [{bar}] {progress*100:.0f}%")
        
        print("="*60)
        print("CONTROLS:")
        print("  ↑/↓: Adjust crossfade ±100ms")
        print("  P:   Play/Pause")
        print("  R:   Reset playback")
        print("  S:   Save crossfade to file")
        print("  N:   New file")
        print("  Q:   Quit")
        print("="*60)
        
        if self.is_playing:
            print("⏵ Playing")
        else:
            print("⏸ Paused")
        
        print("\nPress key: ", end='', flush=True)
    
    def setup_terminal(self):
        """Setup terminal for single-character input."""
        self.old_termios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    def restore_terminal(self):
        """Restore terminal settings."""
        if self.old_termios:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_termios)
    
    def handle_key(self, key):
        """Handle keyboard input."""
        # Arrow keys
        if key == '\x1b':
            next1 = sys.stdin.read(1)
            next2 = sys.stdin.read(1)
            if next1 == '[':
                if next2 == 'A':  # Up arrow
                    if self.adjust_crossfade(100):
                        print(f" ↑ Crossfade: {self.crossfade_ms}ms")
                elif next2 == 'B':  # Down arrow
                    if self.adjust_crossfade(-100):
                        print(f" ↓ Crossfade: {self.crossfade_ms}ms")
            return
        
        # Regular keys
        if key == 'q':
            self.running = False
        
        elif key == 'p':
            self.is_playing = not self.is_playing
            print(f" {'⏵ Playing' if self.is_playing else '⏸ Paused'}")
        
        elif key == 'r':  # Reset
            self.track1_pos = 0.0
            self.track2_pos = 0.0
            self.active_track = 1
            self.loops_completed = 0
            print(" ↺ Reset playback")
        
        elif key == 's':  # Save
            self.save_config()
        
        elif key == 'n':  # New file
            self.is_playing = False
            self.restore_terminal()
            if self.select_file():
                self.setup_terminal()
                self.display_status()
        
        elif key == ' ':  # Space also toggles play/pause
            self.is_playing = not self.is_playing
            print(f" {'⏵ Playing' if self.is_playing else '⏸ Paused'}")
    
    def run(self):
        """Main interactive loop."""
        try:
            # Select initial file
            if not self.select_file():
                return
            
            # Setup audio stream
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=1024,
                channels=2,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            
            # Setup terminal for single-character input
            self.setup_terminal()
            
            # Main loop
            last_display = time.time()
            
            while self.running:
                # Display status
                if time.time() - last_display > 0.1:
                    self.display_status()
                    last_display = time.time()
                
                # Check for input
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self.handle_key(key)
            
            # Cleanup
            self.stream.stop()
            self.stream.close()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.restore_terminal()
            print("\nGoodbye!\n")

def main():
    tester = TwoTrackCrossfadeTester()
    tester.run()

if __name__ == "__main__":
    main()
