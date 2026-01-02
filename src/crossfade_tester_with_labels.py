#!/usr/bin/env python3
"""
Crossfade Tester with Audacity Label Support
For rhythmic files: Uses labels to set beat-aligned crossfade
For ambient files: Manual ms adjustment
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
from typing import List, Tuple, Optional

class LabelInfo:
    """Represents an Audacity label."""
    def __init__(self, start_time: float, end_time: float, description: str = ""):
        self.start_time = start_time
        self.end_time = end_time
        self.description = description.strip()
    
    @property
    def crossfade_duration(self, total_duration: float) -> float:
        """Calculate crossfade duration from label start time."""
        return total_duration - self.start_time
    
    def __str__(self):
        if self.description:
            return f"{self.description} (starts at {self.start_time:.3f}s)"
        return f"Label at {self.start_time:.3f}s"

class CrossfadeTesterWithLabels:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # Pre-rendered buffer
        self.buffer = None
        self.buffer_position = 0
        self.buffer_loops = 10
        
        # Label support
        self.labels: List[LabelInfo] = []
        self.selected_label_index = 0
        self.is_rhythmic = False
        
        # Playback state
        self.is_playing = False
        self.continuous_mode = False
        self.play_once_mode = False
        self.filename = ""
        self.file_duration = 0
        self.loops_completed = 0
        
        # UI state
        self.running = True
        self.old_termios = None
        
        print("\n" + "="*60)
        print("CROSSFADE TESTER with AUDACITY LABELS")
        print("r_ files: Beat-aligned crossfade from labels")
        print("a_ files: Manual crossfade adjustment")
        print("="*60)
    
    def list_audio_files(self, directory: str) -> List[Tuple[str, float, str]]:
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
    
    def find_label_file(self, audio_path: str) -> Optional[str]:
        """Find corresponding label file for audio file."""
        base_name = os.path.splitext(audio_path)[0]
        
        # Try different naming conventions
        possible_names = [
            f"{base_name}_label.txt",
            f"{base_name}.txt",
            base_name.replace('.wav', '_label.txt'),
            base_name.replace('.mp3', '_label.txt'),
            base_name.replace('.flac', '_label.txt'),
            base_name.replace('.ogg', '_label.txt'),
        ]
        
        for label_path in possible_names:
            if os.path.exists(label_path):
                return label_path
        
        return None
    
    def parse_audacity_labels(self, label_path: str) -> List[LabelInfo]:
        """Parse Audacity label file (tab-separated: start, end, description)."""
        labels = []
        
        try:
            with open(label_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            start_time = float(parts[0])
                            end_time = float(parts[1]) if len(parts) > 1 else start_time
                            description = parts[2] if len(parts) > 2 else f"Label {line_num}"
                            
                            labels.append(LabelInfo(start_time, end_time, description))
                        except ValueError as e:
                            print(f"Warning: Could not parse line {line_num}: {line}")
                            print(f"  Error: {e}")
        
        except Exception as e:
            print(f"Error reading label file {label_path}: {e}")
        
        return labels
    
    def select_file(self) -> bool:
        """Let user select an audio file to test."""
        directory = "samples/real_test"
        files = self.list_audio_files(directory)
        
        if not files:
            print(f"\n❌ No audio files found in {directory}/")
            print("Please place your test files there.")
            return False
        
        print(f"\nAudio files in {directory}/:")
        for i, (name, duration, path) in enumerate(files, 1):
            # Check if rhythmic
            is_rhythmic = name.lower().startswith('r_')
            type_indicator = " [RHYTHM]" if is_rhythmic else " [AMBIENT]"
            print(f"[{i}] {name} ({duration:.1f}s){type_indicator}")
        
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
    
    def load_file(self, filepath: str, filename: str, duration: float) -> bool:
        """Load an audio file and detect label file if exists."""
        try:
            print(f"\nLoading {filename}...")
            data, sr = sf.read(filepath, always_2d=True)
            
            # === APPLY -3dB PEAK NORMALIZATION ===
            print(f"  Original peak: {np.max(np.abs(data)):.3f}")
            
            # Peak normalize to -3dB (0.707)
            peak = np.max(np.abs(data))
            target_peak = 0.707  # -3dB
            
            if peak > 0:
                gain_change_db = 20 * np.log10(target_peak / peak)
                data = data * (target_peak / peak)
                print(f"  Normalized to: {np.max(np.abs(data)):.3f} ({gain_change_db:.1f}dB change)")
            # === END NORMALIZATION ===
            
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
            self.buffer_position = 0
            self.loops_completed = 0
            self.labels = []
            self.selected_label_index = 0
            
            # Determine file type
            self.is_rhythmic = filename.lower().startswith('r_')
            
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
            
            # Check for label file
            label_path = self.find_label_file(filepath)
            if label_path and os.path.exists(label_path):
                print(f"Found label file: {os.path.basename(label_path)}")
                self.labels = self.parse_audacity_labels(label_path)
                
                if self.labels:
                    print(f"  Found {len(self.labels)} labels")
                    
                    # For rhythmic files, use first label by default
                    if self.is_rhythmic and self.labels:
                        self.select_label_from_menu()
                    elif not self.is_rhythmic:
                        print("  (Ambient file: labels available but manual adjustment used)")
                else:
                    print("  No valid labels found in file")
            
            # Create buffer
            print("Creating crossfade buffer...")
            self.create_buffer()
            
            print(f"✅ Loaded: {filename}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Type: {'RHYTHMIC' if self.is_rhythmic else 'AMBIENT'}")
            
            if self.is_rhythmic and self.labels:
                selected = self.labels[self.selected_label_index]
                crossfade_s = self.file_duration - selected.start_time
                print(f"   Crossfade: {crossfade_s*1000:.0f}ms (from label: {selected.description})")
            else:
                print(f"   Crossfade: {self.crossfade_ms}ms")
            
            print(f"   Buffer: {self.buffer_loops} loops pre-rendered")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def select_label_from_menu(self):
        """Let user select which label to use for crossfade."""
        if not self.labels:
            return
        
        print(f"\nSelect label for crossfade calculation:")
        for i, label in enumerate(self.labels, 1):
            crossfade_s = self.file_duration - label.start_time
            print(f"[{i}] {label} → {crossfade_s*1000:.0f}ms crossfade")
        
        print(f"[{len(self.labels)+1}] Use manual crossfade (not recommended for rhythm)")
        
        while True:
            try:
                sys.stdout.write(f"\nSelect label (1-{len(self.labels)+1}): ")
                sys.stdout.flush()
                choice = sys.stdin.readline().strip()
                
                if not choice:
                    continue
                
                choice_idx = int(choice) - 1
                
                if choice_idx == len(self.labels):
                    print("Using manual crossfade adjustment")
                    return
                
                if 0 <= choice_idx < len(self.labels):
                    self.selected_label_index = choice_idx
                    selected = self.labels[choice_idx]
                    
                    # Calculate and set crossfade
                    crossfade_s = self.file_duration - selected.start_time
                    self.crossfade_ms = crossfade_s * 1000
                    self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
                    
                    print(f"Selected: {selected.description}")
                    print(f"Crossfade set to: {self.crossfade_ms:.0f}ms")
                    
                    # Recreate buffer with new crossfade
                    self.create_buffer()
                    return
                
                print(f"Please enter 1-{len(self.labels)+1}")
                
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection")
                return
    
    def create_buffer(self):
        """Create pre-rendered buffer with crossfades."""
        if self.audio_data is None:
            return
        
        crossfade_samples = self.crossfade_samples
        
        # Calculate total buffer length
        total_buffer_samples = self.total_samples + (self.buffer_loops - 1) * (self.total_samples - crossfade_samples)
        
        # Create buffer
        self.buffer = np.zeros((total_buffer_samples, 2), dtype=np.float32)
        
        # Render first loop (full)
        self.buffer[:self.total_samples] = self.audio_data
        
        # Render subsequent loops with crossfade
        for loop in range(1, self.buffer_loops):
            start_sample = self.total_samples + (loop - 1) * (self.total_samples - crossfade_samples)
            
            # Get the overlapping region from previous loop
            prev_end = self.buffer[start_sample - crossfade_samples:start_sample].copy()
            curr_start = self.audio_data[:crossfade_samples].copy()
            
            # Apply crossfade
            t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
            crossfade_region = prev_end * (1 - t) + curr_start * t
            
            # Write crossfade region
            self.buffer[start_sample - crossfade_samples:start_sample] = crossfade_region
            
            # Write rest of current loop
            remaining = self.total_samples - crossfade_samples
            if remaining > 0:
                self.buffer[start_sample:start_sample + remaining] = self.audio_data[crossfade_samples:]
        
        print(f"  Created buffer: {self.buffer_loops} loops ({total_buffer_samples/self.sample_rate:.1f}s)")
    
    def audio_callback(self, outdata, frames, time, status):
        """Simple playback of pre-rendered buffer."""
        if status:
            print(f"Audio status: {status}")
        
        if self.buffer is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        # Calculate how much we can read from buffer
        remaining_in_buffer = len(self.buffer) - self.buffer_position
        frames_to_read = min(frames, remaining_in_buffer)
        
        if frames_to_read > 0:
            # Read from buffer
            outdata[:frames_to_read] = self.buffer[self.buffer_position:self.buffer_position + frames_to_read]
            self.buffer_position += frames_to_read
            
            # Count loops completed
            crossfade_samples = self.crossfade_samples
            loop_length = self.total_samples
            
            # Check if we passed any loop boundaries
            prev_pos = self.buffer_position - frames_to_read
            for loop in range(self.buffer_loops):
                if loop == 0:
                    loop_end = loop_length
                else:
                    loop_end = loop_length + loop * (loop_length - crossfade_samples)
                
                if prev_pos < loop_end <= self.buffer_position:
                    self.loops_completed += 1
        
        # Fill any remaining frames with silence
        if frames_to_read < frames:
            outdata[frames_to_read:] = 0
            
            # If in continuous mode, loop the buffer
            if self.continuous_mode:
                self.buffer_position = 0
                remaining_frames = frames - frames_to_read
                outdata[frames_to_read:] = self.buffer[:remaining_frames]
                self.buffer_position = remaining_frames
        
        # Stop if in play-once mode and completed a loop
        if self.play_once_mode and self.loops_completed >= 1:
            self.is_playing = False
            self.play_once_mode = False
    
    def adjust_crossfade(self, delta_ms: float) -> bool:
        """Adjust crossfade time and re-render buffer."""
        if self.is_rhythmic and self.labels:
            print("Rhythmic file: Use label selection (L) not arrow keys")
            return False
        
        old_ms = self.crossfade_ms
        new_ms = max(0, min(30000, self.crossfade_ms + delta_ms))
        
        if new_ms != old_ms:
            self.crossfade_ms = new_ms
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Re-render buffer with new crossfade time
            if self.audio_data is not None:
                print(f"Re-rendering with {self.crossfade_ms}ms crossfade...")
                self.create_buffer()
                self.buffer_position = 0
            
            self.save_config()
            return True
        
        return False
    
    def select_next_label(self):
        """Cycle to next label for rhythmic files."""
        if not self.is_rhythmic or not self.labels:
            print("No labels available or not a rhythmic file")
            return
        
        self.selected_label_index = (self.selected_label_index + 1) % len(self.labels)
        selected = self.labels[self.selected_label_index]
        
        # Calculate and set crossfade
        crossfade_s = self.file_duration - selected.start_time
        self.crossfade_ms = crossfade_s * 1000
        self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
        
        print(f"Selected label: {selected.description}")
        print(f"Crossfade: {self.crossfade_ms:.0f}ms")
        
        # Recreate buffer
        self.create_buffer()
        self.buffer_position = 0
    
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
                    "type": "rhythmic" if self.is_rhythmic else "ambient",
                    "selected_label": self.labels[self.selected_label_index].description if self.labels else None,
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": "Auto-crossfade from label" if (self.is_rhythmic and self.labels) else "Manual crossfade"
                }
                
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\n💾 Saved crossfade {self.crossfade_ms}ms")
                except Exception as e:
                    print(f"Error saving config: {e}")
                break
    
    def generate_test_wav(self, num_loops: int = 3):
        """Generate a test WAV file."""
        if self.audio_data is None:
            print("No audio loaded!")
            return
        
        print(f"\nGenerating test WAV with {num_loops} loops...")
        
        try:
            crossfade_samples = self.crossfade_samples
            
            # Calculate total length
            total_output = self.total_samples + (num_loops - 1) * (self.total_samples - crossfade_samples)
            output = np.zeros((total_output, 2), dtype=np.float32)
            
            # Render loops
            output[:self.total_samples] = self.audio_data
            
            for loop in range(1, num_loops):
                start_sample = self.total_samples + (loop - 1) * (self.total_samples - crossfade_samples)
                
                prev_end = output[start_sample - crossfade_samples:start_sample].copy()
                curr_start = self.audio_data[:crossfade_samples].copy()
                
                t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
                crossfade_region = prev_end * (1 - t) + curr_start * t
                
                output[start_sample - crossfade_samples:start_sample] = crossfade_region
                
                remaining = self.total_samples - crossfade_samples
                if remaining > 0:
                    output[start_sample:start_sample + remaining] = self.audio_data[crossfade_samples:]
            
            # Save
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(self.filename)[0]
            test_filename = f"{base_name}_{num_loops}loops_{self.crossfade_ms}ms_{timestamp}.wav"
            test_path = os.path.join("samples/real_test", test_filename)
            
            sf.write(test_path, output, self.sample_rate)
            
            print(f"\n✅ Generated: {test_filename}")
            print(f"   Duration: {len(output)/self.sample_rate:.1f}s")
            
        except Exception as e:
            print(f"Error generating WAV: {e}")
    
    def display_status(self):
        """Display current testing status."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*60)
        print(f"TESTING: {self.filename}")
        print("="*60)
        
        if self.buffer is not None:
            buffer_time = self.buffer_position / self.sample_rate
            buffer_duration = len(self.buffer) / self.sample_rate
            buffer_percent = (self.buffer_position / len(self.buffer)) * 100
            
            print(f"File duration: {self.file_duration:.1f}s")
            print(f"Type: {'RHYTHMIC' if self.is_rhythmic else 'AMBIENT'}")
            print(f"Buffer: {buffer_time:.1f}s / {buffer_duration:.1f}s ({buffer_percent:.0f}%)")
            print(f"Loops in buffer: {self.buffer_loops}")
            print(f"Loops completed: {self.loops_completed}")
            
            if self.is_rhythmic and self.labels:
                selected = self.labels[self.selected_label_index]
                crossfade_s = self.file_duration - selected.start_time
                print(f"Crossfade: {crossfade_s*1000:.0f}ms (from label: {selected.description})")
                print(f"Label: {selected.start_time:.3f}s → {crossfade_s*1000:.0f}ms crossfade")
            else:
                print(f"Crossfade: {self.crossfade_ms}ms")
            
            # Buffer progress bar
            bar_length = 40
            filled = int(buffer_percent * bar_length / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"Buffer: [{bar}] {buffer_percent:.0f}%")
        
        print("="*60)
        print("CONTROLS:")
        
        if self.is_rhythmic and self.labels:
            print("  L:     Select next label")
            print("  P:     Play/Pause")
            print("  C:     Continuous play")
            print("  G:     Generate test WAV")
            print("  R:     Reset playback")
            print("  S:     Save config")
            print("  N:     New file")
            print("  Q:     Quit")
        else:
            print("  ↑/↓:   Adjust crossfade ±100ms")
            print("  U/D:   Adjust crossfade ±1000ms")
            print("  P:     Play/Pause")
            print("  L:     Play once")
            print("  C:     Continuous play")
            print("  G:     Generate test WAV")
            print("  R:     Reset playback")
            print("  S:     Save config")
            print("  N:     New file")
            print("  Q:     Quit")
        
        print("="*60)
        
        if self.is_playing:
            mode = ""
            if self.play_once_mode:
                mode = " (once)"
            elif self.continuous_mode:
                mode = " (continuous)"
            print(f"⏵ Playing{mode}")
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
    
    def handle_key(self, key: str):
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
        
        elif key == 'l':
            if self.is_rhythmic and self.labels:
                self.select_next_label()
            else:
                # For ambient files, L = play once
                self.is_playing = True
                self.continuous_mode = False
                self.play_once_mode = True
                self.loops_completed = 0
                print(" ⏵ Playing once")
        
        elif key == 'c':
            self.is_playing = True
            self.continuous_mode = True
            self.play_once_mode = False
            print(" ⏵ Continuous play")
        
        elif key == 'g':
            self.is_playing = False
            self.generate_test_wav(3)
            input("\nPress Enter to continue...")
        
        elif key == 'r':
            self.buffer_position = 0
            self.loops_completed = 0
            print(" ↺ Reset to buffer start")
        
        elif key == 's':
            self.save_config()
        
        elif key == 'n':
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
            
            # Cleanup
            self.stream.stop()
            self.stream.close()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.restore_terminal()
            print("\nGoodbye!\n")

def main():
    tester = CrossfadeTesterWithLabels()
    tester.run()

if __name__ == "__main__":
    main()