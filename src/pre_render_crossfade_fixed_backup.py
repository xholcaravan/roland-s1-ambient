#!/usr/bin/env python3
"""
Pre-Render Crossfade Tester - FIXED VERSION
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

class PreRenderCrossfadeFixed:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # Pre-rendered buffer
        self.pre_render_buffer = None
        self.buffer_position = 0
        self.buffer_loops = 10
        
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
        print("PRE-RENDER CROSSFADE TESTER - FIXED")
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
        """Load an audio file and pre-render buffer."""
        try:
            print(f"\nLoading {filename}...")
            data, sr = sf.read(filepath, always_2d=True)
            
            if sr != self.sample_rate:
                print(f"Resampling {sr}Hz → {self.sample_rate}Hz")
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            self.audio_data = data
            self.total_samples = len(data)
            self.filename = filename
            self.file_duration = duration
            
            self.buffer_position = 0
            self.loops_completed = 0
            
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Load config
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
            
            # Pre-render
            print("Pre-rendering buffer...")
            self.pre_render_buffer = self._create_pre_render_buffer()
            
            print(f"✅ Loaded: {filename}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Crossfade: {self.crossfade_ms}ms")
            print(f"   Buffer: {self.buffer_loops} loops")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_pre_render_buffer(self):
        """Create pre-rendered buffer with crossfades."""
        if self.audio_data is None:
            return None
        
        crossfade_samples = self.crossfade_samples
        
        # Calculate total length
        total_buffer = self.total_samples + (self.buffer_loops - 1) * (self.total_samples - crossfade_samples)
        
        # Create buffer
        buffer = np.zeros((total_buffer, 2), dtype=np.float32)
        
        # First loop
        buffer[:self.total_samples] = self.audio_data
        
        # Subsequent loops
        for loop in range(1, self.buffer_loops):
            start_sample = self.total_samples + (loop - 1) * (self.total_samples - crossfade_samples)
            
            # Crossfade region
            if crossfade_samples > 0:
                prev_end = buffer[start_sample - crossfade_samples:start_sample].copy()
                curr_start = self.audio_data[:crossfade_samples].copy()
                
                t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
                crossfade_region = prev_end * (1 - t) + curr_start * t
                
                buffer[start_sample - crossfade_samples:start_sample] = crossfade_region
            
            # Rest of loop
            remaining = self.total_samples - crossfade_samples
            if remaining > 0:
                buffer[start_sample:start_sample + remaining] = self.audio_data[crossfade_samples:]
        
        print(f"  Created buffer: {total_buffer/self.sample_rate:.1f}s")
        return buffer
    
    def audio_callback(self, outdata, frames, time, status):
        """Playback of pre-rendered buffer."""
        if self.pre_render_buffer is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        # How much can we read?
        remaining = len(self.pre_render_buffer) - self.buffer_position
        to_read = min(frames, remaining)
        
        if to_read > 0:
            outdata[:to_read] = self.pre_render_buffer[self.buffer_position:self.buffer_position + to_read]
            self.buffer_position += to_read
            
            # Track loops
            # Simple loop counting: check if we passed loop boundaries
            loop_length = self.total_samples
            crossfade = self.crossfade_samples
            
            prev_pos = self.buffer_position - to_read
            for loop in range(self.buffer_loops):
                if loop == 0:
                    loop_end = loop_length
                else:
                    loop_end = loop_length + loop * (loop_length - crossfade)
                
                if prev_pos < loop_end <= self.buffer_position:
                    self.loops_completed += 1
        
        # Fill remainder
        if to_read < frames:
            outdata[to_read:] = 0
            
            # Loop if continuous
            if self.continuous_mode:
                self.buffer_position = 0
                remaining_frames = frames - to_read
                if remaining_frames > 0:
                    outdata[to_read:] = self.pre_render_buffer[:remaining_frames]
                    self.buffer_position = remaining_frames
        
        # Stop if play-once
        if self.play_once_mode and self.loops_completed >= 1:
            self.is_playing = False
            self.play_once_mode = False
    
    def adjust_crossfade(self, delta_ms):
        """Adjust crossfade and re-render."""
        new_ms = max(0, min(30000, self.crossfade_ms + delta_ms))
        
        if new_ms != self.crossfade_ms:
            self.crossfade_ms = new_ms
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            if self.audio_data is not None:
                print(f"Re-rendering with {self.crossfade_ms}ms crossfade...")
                self.pre_render_buffer = self._create_pre_render_buffer()
                self.buffer_position = 0
            
            self.save_config()
            return True
        
        return False
    
    def save_config(self):
        """Save config."""
        if not self.filename:
            return
        
        directory = "samples/real_test"
        for f in os.listdir(directory):
            if f == self.filename:
                filepath = os.path.join(directory, f)
                config_path = filepath.replace('.wav', '.txt').replace('.mp3', '.txt').replace('.flac', '.txt').replace('.ogg', '.txt')
                
                config = {
                    "crossfade_ms": self.crossfade_ms,
                    "strategy": "pre-render",
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"\n💾 Saved {self.crossfade_ms}ms")
                except Exception as e:
                    print(f"Error: {e}")
                break
    
    def generate_test_wav(self):
        """Generate WAV file."""
        if self.audio_data is None:
            print("No audio!")
            return
        
        print(f"\nGenerating test WAV...")
        
        try:
            # Create 3-loop version
            test_buffer = self._create_test_buffer(3)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(self.filename)[0]
            test_filename = f"{base_name}_3loops_{self.crossfade_ms}ms_{timestamp}.wav"
            test_path = os.path.join("samples/real_test", test_filename)
            
            sf.write(test_path, test_buffer, self.sample_rate)
            
            print(f"✅ Generated: {test_filename}")
            print(f"   Duration: {len(test_buffer)/self.sample_rate:.1f}s")
            
        except Exception as e:
            print(f"Error: {e}")
    
    def _create_test_buffer(self, num_loops):
        """Create buffer for WAV export."""
        crossfade_samples = self.crossfade_samples
        
        total_samples = self.total_samples + (num_loops - 1) * (self.total_samples - crossfade_samples)
        buffer = np.zeros((total_samples, 2), dtype=np.float32)
        
        buffer[:self.total_samples] = self.audio_data
        
        for loop in range(1, num_loops):
            start_sample = self.total_samples + (loop - 1) * (self.total_samples - crossfade_samples)
            
            if crossfade_samples > 0:
                prev_end = buffer[start_sample - crossfade_samples:start_sample].copy()
                curr_start = self.audio_data[:crossfade_samples].copy()
                
                t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
                crossfade_region = prev_end * (1 - t) + curr_start * t
                
                buffer[start_sample - crossfade_samples:start_sample] = crossfade_region
            
            remaining = self.total_samples - crossfade_samples
            if remaining > 0:
                buffer[start_sample:start_sample + remaining] = self.audio_data[crossfade_samples:]
        
        return buffer
    
    def display_status(self):
        """Display status."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*60)
        print(f"TESTING: {self.filename}")
        print("="*60)
        
        if self.pre_render_buffer is not None:
            buf_pos = self.buffer_position / self.sample_rate
            buf_len = len(self.pre_render_buffer) / self.sample_rate
            percent = (self.buffer_position / len(self.pre_render_buffer)) * 100
            
            print(f"File: {self.file_duration:.1f}s")
            print(f"Buffer: {buf_pos:.1f}s / {buf_len:.1f}s ({percent:.0f}%)")
            print(f"Loops: {self.loops_completed}")
            print(f"Crossfade: {self.crossfade_ms}ms")
            
            bar_len = 40
            filled = int(percent * bar_len / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"[{bar}]")
        
        print("="*60)
        print("CONTROLS:")
        print("  ↑/↓: Adjust crossfade")
        print("  P: Play/Pause")
        print("  L: Play once")
        print("  C: Continuous")
        print("  G: Generate WAV")
        print("  R: Reset")
        print("  S: Save")
        print("  N: New file")
        print("  Q: Quit")
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
        self.old_termios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    def restore_terminal(self):
        if self.old_termios:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_termios)
    
    def handle_key(self, key):
        if key == '\x1b':
            next1 = sys.stdin.read(1)
            next2 = sys.stdin.read(1)
            if next1 == '[':
                if next2 == 'A':
                    if self.adjust_crossfade(100):
                        print(f" ↑ {self.crossfade_ms}ms")
                elif next2 == 'B':
                    if self.adjust_crossfade(-100):
                        print(f" ↓ {self.crossfade_ms}ms")
            return
        
        if key == 'q':
            self.running = False
        
        elif key == 'p':
            self.is_playing = not self.is_playing
            self.continuous_mode = False
            self.play_once_mode = False
            print(f" {'⏵ Playing' if self.is_playing else '⏸ Paused'}")
        
        elif key == 'l':
            self.is_playing = True
            self.continuous_mode = False
            self.play_once_mode = True
            self.loops_completed = 0
            print(" ⏵ Playing once")
        
        elif key == 'c':
            self.is_playing = True
            self.continuous_mode = True
            self.play_once_mode = False
            print(" ⏵ Continuous")
        
        elif key == 'g':
            self.is_playing = False
            self.generate_test_wav()
            input("\nPress Enter...")
        
        elif key == 'r':
            self.buffer_position = 0
            self.loops_completed = 0
            print(" ↺ Reset")
        
        elif key == 's':
            self.save_config()
        
        elif key == 'n':
            self.is_playing = False
            self.restore_terminal()
            if self.select_file():
                self.setup_terminal()
                self.display_status()
        
        elif key == ' ':
            self.is_playing = not self.is_playing
            print(f" {'⏵ Playing' if self.is_playing else '⏸ Paused'}")
    
    def run(self):
        try:
            if not self.select_file():
                return
            
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=1024,
                channels=2,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            
            self.setup_terminal()
            
            last_display = time.time()
            
            while self.running:
                if time.time() - last_display > 0.1:
                    self.display_status()
                    last_display = time.time()
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    self.handle_key(key)
            
            self.stream.stop()
            self.stream.close()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.restore_terminal()
            print("\nGoodbye!\n")

def main():
    tester = PreRenderCrossfadeFixed()
    tester.run()

if __name__ == "__main__":
    main()
