#!/usr/bin/env python3
"""
Interactive Crossfade Loop Tester - FIXED with WAV Export
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

class CrossfadeTester:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.position = 0
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        self.is_playing = False
        self.filename = ""
        self.file_duration = 0
        self.continuous_mode = False
        self.play_once_mode = False
        self.loops_completed = 0
        self.running = True
        self.old_termios = None
        
        print("\n" + "="*60)
        print("INTERACTIVE CROSSFADE LOOP TESTER - FIXED")
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
            print("\nCreating a test tone...")
            self.create_test_tone()
            files = self.list_audio_files(directory)
            if not files:
                return False
        
        print(f"\nAudio files in {directory}/:")
        for i, (name, duration, path) in enumerate(files, 1):
            print(f"[{i}] {name} ({duration:.1f}s)")
        
        print(f"[{len(files)+1}] Quit")
        
        # RESTORE terminal to normal mode for file selection
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
                    return False  # Quit option
                
                if 0 <= choice_idx < len(files):
                    name, duration, path = files[choice_idx]
                    return self.load_file(path, name, duration)
                
                print(f"Please enter 1-{len(files)+1}")
                
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection")
                return False
    
    def create_test_tone(self):
        """Create a test tone if no files exist."""
        directory = "samples/real_test"
        os.makedirs(directory, exist_ok=True)
        
        # Generate a simple test tone
        duration = 5  # seconds
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Create a more interesting tone with envelope
        freq1 = 440  # Hz (A4)
        freq2 = 550  # Hz (C#5)
        
        # Main tone with slight vibrato
        vibrato = 0.01 * np.sin(2 * np.pi * 5 * t)  # 5Hz vibrato
        tone1 = 0.25 * np.sin(2 * np.pi * (freq1 + freq1 * vibrato) * t)
        tone2 = 0.15 * np.sin(2 * np.pi * freq2 * t)
        
        # Apply envelope to avoid clicks
        envelope = np.ones_like(t)
        attack_len = int(0.05 * self.sample_rate)  # 50ms attack
        release_len = int(0.1 * self.sample_rate)  # 100ms release
        
        envelope[:attack_len] = np.linspace(0, 1, attack_len)
        envelope[-release_len:] = np.linspace(1, 0, release_len)
        
        audio = (tone1 + tone2) * envelope
        audio_stereo = np.column_stack((audio, audio))
        
        test_file = os.path.join(directory, "test_tone.wav")
        sf.write(test_file, audio_stereo, self.sample_rate)
        print(f"Created {test_file}")
    
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
            self.filename = filename
            self.file_duration = duration
            self.position = 0
            self.loops_completed = 0
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
            print(f"   Crossfade: {self.crossfade_ms}ms ({self.crossfade_samples} samples)")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return False
    
    def save_config(self):
        """Save current crossfade to .txt file."""
        if not self.filename:
            return
        
        # Find the original file path
        directory = "samples/real_test"
        for f in os.listdir(directory):
            if f == self.filename:
                filepath = os.path.join(directory, f)
                config_path = filepath.replace('.wav', '.txt').replace('.mp3', '.txt').replace('.flac', '.txt').replace('.ogg', '.txt')
                
                config = {
                    "crossfade_ms": self.crossfade_ms,
                    "strategy": "crossfade",
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": f"Starts fading {self.crossfade_ms/1000:.1f}s before end"
                }
                
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\n💾 Saved crossfade {self.crossfade_ms}ms to {os.path.basename(config_path)}")
                except Exception as e:
                    print(f"Error saving config: {e}")
                break
    
    def audio_callback(self, outdata, frames, time, status):
        """Audio callback for crossfade looping - FIXED VERSION."""
        if status:
            print(f"Audio status: {status}")
        
        if self.audio_data is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        crossfade_samples = self.crossfade_samples
        total_samples = len(self.audio_data)
        
        # Initialize output
        output = np.zeros((frames, 2), dtype=np.float32)
        
        for i in range(frames):
            current_loop_pos = self.position % total_samples
            loop_number = self.position // total_samples
            
            # Check if we're in crossfade region
            remaining_in_current_loop = total_samples - current_loop_pos
            
            if remaining_in_current_loop <= crossfade_samples and crossfade_samples > 0:
                # In crossfade region
                fade_pos = crossfade_samples - remaining_in_current_loop
                t = fade_pos / crossfade_samples if crossfade_samples > 0 else 0
                
                # End of current loop (fading out)
                sample_end = self.audio_data[current_loop_pos]
                
                # Position in NEXT loop (fading in)
                # CRITICAL FIX: Use fade_pos directly, not modulo total_samples
                # This ensures we continue from where crossfade left off
                pos_in_next_loop = fade_pos
                sample_start = self.audio_data[pos_in_next_loop % total_samples]
                
                # Crossfade mix
                output[i] = sample_end * (1 - t) + sample_start * t
            else:
                # Normal playback
                output[i] = self.audio_data[current_loop_pos]
            
            self.position += 1
            
            # Check if we completed a loop
            if self.position % total_samples == 0 and self.position > 0:
                self.loops_completed += 1
                
                # Stop if in play-once mode
                if self.play_once_mode and self.loops_completed >= 1:
                    self.is_playing = False
                    self.play_once_mode = False
                    # Fill rest with silence
                    if i + 1 < frames:
                        output[i+1:] = 0
                    break
        
        outdata[:] = output
    
    def generate_test_wav(self, num_loops=3):
        """Generate a test WAV file with specified number of loops."""
        if self.audio_data is None:
            print("No audio loaded!")
            return False
        
        print(f"\nGenerating test WAV with {num_loops} loops...")
        print(f"Crossfade: {self.crossfade_ms}ms")
        
        try:
            total_samples = len(self.audio_data)
            crossfade_samples = self.crossfade_samples
            
            # Calculate total length
            # Each loop after the first starts with crossfade_samples already played
            total_output_samples = total_samples + (num_loops - 1) * (total_samples - crossfade_samples)
            
            print(f"Total output samples: {total_output_samples}")
            print(f"Output duration: {total_output_samples/self.sample_rate:.1f}s")
            
            # Initialize output array
            output = np.zeros((total_output_samples, 2), dtype=np.float32)
            
            # Render first loop (full)
            output[:total_samples] = self.audio_data
            print(f"  Rendered loop 1/3")
            
            # Render subsequent loops with crossfade
            for loop in range(1, num_loops):
                # Start position for this loop in output
                start_sample = total_samples + (loop - 1) * (total_samples - crossfade_samples)
                
                # We need to create crossfade between previous loop and this one
                # The last 'crossfade_samples' of previous loop should fade out
                # The first 'crossfade_samples' of this loop should fade in
                
                # Get the overlapping region from previous loop (end portion)
                prev_loop_end = start_sample - crossfade_samples
                prev_fade_out = output[prev_loop_end:start_sample].copy()
                
                # Get the beginning of current loop
                curr_fade_in = self.audio_data[:crossfade_samples].copy()
                
                # Apply crossfade to overlapping region
                t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
                crossfade_region = prev_fade_out * (1 - t) + curr_fade_in * t
                
                # Write crossfade region
                output[prev_loop_end:start_sample] = crossfade_region
                
                # Write the rest of the current loop (after crossfade)
                remaining_samples = total_samples - crossfade_samples
                if remaining_samples > 0:
                    output[start_sample:start_sample + remaining_samples] = self.audio_data[crossfade_samples:]
                
                print(f"  Rendered loop {loop+1}/3")
            
            # Create filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(self.filename)[0]
            test_filename = f"{base_name}_{num_loops}loops_{self.crossfade_ms}ms_{timestamp}.wav"
            test_path = os.path.join("samples/real_test", test_filename)
            
            # Save the file
            sf.write(test_path, output, self.sample_rate)
            
            print(f"\n✅ Generated: {test_filename}")
            print(f"   Duration: {len(output)/self.sample_rate:.1f}s ({num_loops} loops)")
            print(f"   Crossfade: {self.crossfade_ms}ms")
            print(f"   Check this file in Audacity to verify seamless looping.")
            
            # Create markers file
            markers_path = test_path.replace('.wav', '_markers.txt')
            with open(markers_path, 'w') as f:
                f.write(f"Crossfade test for {self.filename}\n")
                f.write(f"Crossfade: {self.crossfade_ms}ms\n")
                f.write(f"Loops: {num_loops}\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Calculate marker positions
                for i in range(num_loops + 1):
                    if i == 0:
                        sample_pos = 0
                        f.write(f"Start: {sample_pos/self.sample_rate:.3f}s (sample {sample_pos})\n")
                    elif i < num_loops:
                        sample_pos = i * total_samples - (i - 1) * crossfade_samples
                        f.write(f"Loop {i} crossfade start: {sample_pos/self.sample_rate:.3f}s (sample {sample_pos})\n")
                    else:
                        sample_pos = total_output_samples
                        f.write(f"End: {sample_pos/self.sample_rate:.3f}s (sample {sample_pos})\n")
            
            print(f"   Markers saved to: {os.path.basename(markers_path)}")
            
            return True
            
        except Exception as e:
            print(f"Error generating test WAV: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
            total_samples = len(self.audio_data)
            current_loop_pos = self.position % total_samples
            loop_number = self.position // total_samples + 1
            
            pos_seconds = current_loop_pos / self.sample_rate
            remaining = total_samples - current_loop_pos
            remaining_seconds = remaining / self.sample_rate
            
            print(f"Duration: {self.file_duration:.1f} seconds")
            print(f"Loop: {loop_number}, Position in loop: {pos_seconds:.1f}s")
            print(f"Remaining in loop: {remaining_seconds:.1f}s")
            print(f"Total loops completed: {self.loops_completed}")
            print(f"Crossfade: {self.crossfade_ms}ms (starts {self.crossfade_ms/1000:.1f}s before end)")
            
            # Show crossfade zone indicator
            if remaining_seconds <= self.crossfade_ms/1000:
                progress = 1.0 - (remaining_seconds / (self.crossfade_ms/1000))
                bar_length = 30
                filled = int(progress * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"Crossfade: [{bar}] {progress*100:.0f}%")
        
        print("="*60)
        print("CONTROLS:")
        print("  ↑/↓: Adjust crossfade ±100ms")
        print("  U/D: Adjust crossfade ±1000ms")
        print("  P:   Play/Pause")
        print("  L:   Play loop once (hear crossfade)")
        print("  C:   Continuous play")
        print("  G:   Generate test WAV (3 loops)")
        print("  R:   Reset playback position")
        print("  S:   Save current crossfade to file")
        print("  N:   New file")
        print("  Q:   Quit")
        print("="*60)
        
        if self.is_playing:
            if self.play_once_mode:
                print("⏵ Playing ONCE (will stop after loop)")
            elif self.continuous_mode:
                print("⏵ CONTINUOUS play")
            else:
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
        # Arrow keys (escape sequences)
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
            print(" ⏵ Playing ONCE (will stop after loop)")
        
        elif key == 'c':  # Continuous
            self.is_playing = True
            self.continuous_mode = True
            self.play_once_mode = False
            print(" ⏵ CONTINUOUS play")
        
        elif key == 'g':  # Generate test WAV
            self.is_playing = False
            self.generate_test_wav(3)
            input("\nPress Enter to continue...")
        
        elif key == 'r':  # Reset position
            self.position = 0
            self.loops_completed = 0
            print(" ↺ Reset position to start")
        
        elif key == 's':  # Save
            self.save_config()
        
        elif key == 'n':  # New file
            self.is_playing = False
            self.restore_terminal()  # Restore terminal for file selection
            if self.select_file():
                self.setup_terminal()  # Setup again for interactive mode
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
            # Select initial file (in normal terminal mode)
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
            
            # NOW setup terminal for single-character input
            self.setup_terminal()
            
            # Main interactive loop
            last_display = time.time()
            
            while self.running:
                # Display status periodically
                if time.time() - last_display > 0.1:
                    self.display_status()
                    last_display = time.time()
                
                # Check for keyboard input
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self.handle_key(key)
                
                # If continuous mode and not playing, restart
                if (self.continuous_mode and 
                    not self.is_playing and 
                    self.audio_data is not None):
                    self.position = 0
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
    tester = CrossfadeTester()
    tester.run()

if __name__ == "__main__":
    main()
