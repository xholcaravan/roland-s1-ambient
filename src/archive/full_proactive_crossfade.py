#!/usr/bin/env python3
"""
Full Interactive Proactive Crossfade Tester
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

class FullProactiveCrossfade:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # Playback state
        self.current_track_pos = 0.0
        self.next_track_pos = 0.0
        self.crossfade_active = False
        self.crossfade_start_pos = 0
        self.crossfade_progress = 0.0
        
        self.is_playing = False
        self.continuous_mode = False
        self.play_once_mode = False
        self.loops_completed = 0
        self.filename = ""
        self.file_duration = 0
        
        # UI state
        self.running = True
        self.old_termios = None
        
        print("\n" + "="*60)
        print("FULL INTERACTIVE CROSSFADE TESTER")
        print("Proactive scheduling to fix timing bugs")
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
            
            # Reset state
            self.current_track_pos = 0.0
            self.next_track_pos = 0.0
            self.crossfade_active = False
            self.crossfade_start_pos = 0
            self.crossfade_progress = 0.0
            self.loops_completed = 0
            
            # Update crossfade
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Load existing config
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
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
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
                    "strategy": "proactive",
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": "Proactive scheduling avoids timing bugs"
                }
                
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\n💾 Saved crossfade {self.crossfade_ms}ms")
                except Exception as e:
                    print(f"Error saving config: {e}")
                break
    
    def generate_test_wav(self, num_loops=3):
        """Generate a test WAV file with seamless loops."""
        if self.audio_data is None:
            print("No audio loaded!")
            return False
        
        print(f"\nGenerating test WAV with {num_loops} loops...")
        print(f"Crossfade: {self.crossfade_ms}ms")
        
        try:
            crossfade_samples = self.crossfade_samples
            
            # Calculate total output length
            # First loop: full length
            # Subsequent loops: full length minus crossfade (since overlap)
            total_output = self.total_samples + (num_loops - 1) * (self.total_samples - crossfade_samples)
            
            output = np.zeros((total_output, 2), dtype=np.float32)
            
            # Render first loop
            output[:self.total_samples] = self.audio_data
            print(f"  Rendered loop 1/{num_loops}")
            
            # Render subsequent loops with crossfade
            for loop in range(1, num_loops):
                start_sample = self.total_samples + (loop - 1) * (self.total_samples - crossfade_samples)
                
                # Get the overlapping region
                prev_end = output[start_sample - crossfade_samples:start_sample].copy()
                curr_start = self.audio_data[:crossfade_samples].copy()
                
                # Apply crossfade
                t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
                crossfade_region = prev_end * (1 - t) + curr_start * t
                
                # Write crossfade region
                output[start_sample - crossfade_samples:start_sample] = crossfade_region
                
                # Write rest of current loop
                remaining = self.total_samples - crossfade_samples
                if remaining > 0:
                    output[start_sample:start_sample + remaining] = self.audio_data[crossfade_samples:]
                
                print(f"  Rendered loop {loop+1}/{num_loops}")
            
            # Create filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(self.filename)[0]
            test_filename = f"{base_name}_{num_loops}loops_{self.crossfade_ms}ms_{timestamp}.wav"
            test_path = os.path.join("samples/real_test", test_filename)
            
            # Save
            sf.write(test_path, output, self.sample_rate)
            
            print(f"\n✅ Generated: {test_filename}")
            print(f"   Duration: {len(output)/self.sample_rate:.1f}s ({num_loops} loops)")
            print(f"   Crossfade: {self.crossfade_ms}ms")
            
            return True
            
        except Exception as e:
            print(f"Error generating WAV: {e}")
            return False
    
    def get_audio_at(self, position):
        """Get audio at position with interpolation."""
        if self.audio_data is None:
            return np.zeros(2)
        
        idx = int(position) % self.total_samples
        next_idx = (idx + 1) % self.total_samples
        t = position - int(position)
        
        return (1-t) * self.audio_data[idx] + t * self.audio_data[next_idx]
    
    def audio_callback(self, outdata, frames, time, status):
        """Proactive crossfade scheduling."""
        if status:
            print(f"Audio status: {status}")
        
        if self.audio_data is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        output = np.zeros((frames, 2), dtype=np.float32)
        
        for i in range(frames):
            # PROACTIVE: Check if we should START crossfade
            if not self.crossfade_active:
                remaining = self.total_samples - self.current_track_pos
                if remaining <= self.crossfade_samples:
                    # SCHEDULE crossfade NOW
                    self.crossfade_active = True
                    self.crossfade_start_pos = self.current_track_pos
                    self.next_track_pos = 0.0
                    # Debug: Uncomment to see when crossfade starts
                    # print(f"[DEBUG] Crossfade started at pos {self.current_track_pos}")
            
            # Get audio based on state
            if self.crossfade_active:
                # DURING CROSSFADE
                samples_into_crossfade = self.current_track_pos - self.crossfade_start_pos
                self.crossfade_progress = samples_into_crossfade / self.crossfade_samples
                self.crossfade_progress = max(0, min(1, self.crossfade_progress))
                
                # Get audio from both tracks
                current_audio = self.get_audio_at(self.current_track_pos)
                next_audio = self.get_audio_at(self.next_track_pos)
                
                # Mix with crossfade
                fade_out = 1.0 - self.crossfade_progress
                fade_in = self.crossfade_progress
                
                output[i] = current_audio * fade_out + next_audio * fade_in
                
                # Advance both tracks
                self.current_track_pos += 1
                self.next_track_pos += 1
                
                # Check if crossfade complete
                if self.crossfade_progress >= 1.0:
                    # Crossfade complete
                    self.current_track_pos = self.next_track_pos
                    self.crossfade_active = False
                    self.crossfade_progress = 0.0
                    self.loops_completed += 1
                    
                    # Stop if in play-once mode
                    if self.play_once_mode and self.loops_completed >= 1:
                        self.is_playing = False
                        self.play_once_mode = False
                        if i + 1 < frames:
                            output[i+1:] = 0
                        break
                    
                    # Wrap positions
                    if self.current_track_pos >= self.total_samples:
                        self.current_track_pos -= self.total_samples
                    if self.next_track_pos >= self.total_samples:
                        self.next_track_pos -= self.total_samples
            else:
                # NORMAL PLAYBACK
                output[i] = self.get_audio_at(self.current_track_pos)
                self.current_track_pos += 1
            
            # Wrap current position
            if self.current_track_pos >= self.total_samples:
                self.current_track_pos -= self.total_samples
        
        outdata[:] = output
    
    def adjust_crossfade(self, delta_ms):
        """Adjust crossfade time."""
        old_ms = self.crossfade_ms
        new_ms = max(0, min(30000, self.crossfade_ms + delta_ms))
        
        if new_ms != old_ms:
            self.crossfade_ms = new_ms
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            self.save_config()
            return True
        
        return False
    
    def display_status(self):
        """Display current testing status."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*60)
        print(f"TESTING: {self.filename}")
        print("="*60)
        
        if self.audio_data is not None:
            current_time = self.current_track_pos / self.sample_rate
            remaining = self.total_samples - self.current_track_pos
            remaining_time = remaining / self.sample_rate
            
            print(f"Duration: {self.file_duration:.1f} seconds")
            print(f"Position: {current_time:.1f}s")
            print(f"Remaining in loop: {remaining_time:.1f}s")
            print(f"Loops completed: {self.loops_completed}")
            print(f"Crossfade: {self.crossfade_ms}ms (starts {self.crossfade_ms/1000:.1f}s before end)")
            
            if self.crossfade_active:
                bar_length = 30
                filled = int(self.crossfade_progress * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"Crossfade active: [{bar}] {self.crossfade_progress*100:.0f}%")
        
        print("="*60)
        print("CONTROLS:")
        print("  ↑/↓: Adjust crossfade ±100ms")
        print("  U/D: Adjust crossfade ±1000ms")
        print("  P:   Play/Pause")
        print("  L:   Play loop once")
        print("  C:   Continuous play")
        print("  G:   Generate test WAV (3 loops)")
        print("  R:   Reset playback")
        print("  S:   Save crossfade")
        print("  N:   New file")
        print("  Q:   Quit")
        print("="*60)
        
        if self.is_playing:
            mode = "ONCE" if self.play_once_mode else "CONTINUOUS" if self.continuous_mode else ""
            print(f"⏵ Playing {mode}")
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
            self.continuous_mode = False
            self.play_once_mode = False
            print(f" {'⏵ Playing' if self.is_playing else '⏸ Paused'}")
        
        elif key == 'l':  # Play once
            self.is_playing = True
            self.continuous_mode = False
            self.play_once_mode = True
            self.loops_completed = 0
            print(" ⏵ Playing ONCE")
        
        elif key == 'c':  # Continuous
            self.is_playing = True
            self.continuous_mode = True
            self.play_once_mode = False
            print(" ⏵ CONTINUOUS")
        
        elif key == 'g':  # Generate WAV
            self.is_playing = False
            self.generate_test_wav(3)
            input("\nPress Enter to continue...")
        
        elif key == 'r':  # Reset
            self.current_track_pos = 0.0
            self.next_track_pos = 0.0
            self.crossfade_active = False
            self.crossfade_progress = 0.0
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
        
        elif key == 'u':  # Big increase
            if self.adjust_crossfade(1000):
                print(f" ↗ Crossfade: {self.crossfade_ms}ms")
        
        elif key == 'd':  # Big decrease
            if self.adjust_crossfade(-1000):
                print(f" ↘ Crossfade: {self.crossfade_ms}ms")
        
        elif key == ' ':
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
                
                # Auto-restart if in continuous mode
                if self.continuous_mode and not self.is_playing:
                    self.current_track_pos = 0.0
                    self.next_track_pos = 0.0
                    self.crossfade_active = False
                    self.loops_completed = 0
                    self.is_playing = True
            
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
    tester = FullProactiveCrossfade()
    tester.run()

if __name__ == "__main__":
    main()
