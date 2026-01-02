#!/usr/bin/env python3
"""
Final Crossfade Tester - Clean version
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
        self.buffer = None
        self.position = 0
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        self.is_playing = False
        self.filename = ""
        self.file_duration = 0
        
        print("\n" + "="*60)
        print("CROSSFADE CONFIGURATION TESTER")
        print("="*60)
    
    def list_files(self):
        """List WAV files in test directory."""
        directory = "samples/real_test"
        files = []
        if os.path.exists(directory):
            for f in sorted(os.listdir(directory)):
                if f.lower().endswith('.wav'):
                    path = os.path.join(directory, f)
                    try:
                        data, sr = sf.read(path)
                        duration = len(data) / sr
                        files.append((f, duration, path))
                    except:
                        files.append((f, 0, path))
        return files
    
    def select_file(self):
        """User selects a file."""
        files = self.list_files()
        
        if not files:
            print("No WAV files found. Create test tone...")
            self._create_test_tone()
            files = self.list_files()
            if not files:
                return False
        
        print("\nAudio files:")
        for i, (name, duration, path) in enumerate(files, 1):
            print(f"[{i}] {name} ({duration:.1f}s)")
        print(f"[{len(files)+1}] Quit")
        
        # Normal terminal mode for input
        old_attr = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        try:
            while True:
                sys.stdout.write(f"\nSelect (1-{len(files)+1}): ")
                sys.stdout.flush()
                choice = sys.stdin.read(1)
                
                if not choice.isdigit():
                    continue
                
                idx = int(choice) - 1
                if idx == len(files):
                    return False
                elif 0 <= idx < len(files):
                    name, duration, path = files[idx]
                    return self.load_file(path, name, duration)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attr)
    
    def _create_test_tone(self):
        """Create test tone if no files."""
        os.makedirs("samples/real_test", exist_ok=True)
        t = np.linspace(0, 5, 44100*5)
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        sf.write("samples/real_test/test.wav", 
                 np.column_stack((audio, audio)), 44100)
        print("Created test.wav")
    
    def load_file(self, path, name, duration):
        """Load file and create buffer."""
        try:
            print(f"\nLoading {name}...")
            data, sr = sf.read(path, always_2d=True)
            
            if sr != self.sample_rate:
                scale = self.sample_rate / sr
                new_len = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_len).astype(int)
                data = data[indices]
            
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            self.audio_data = data
            self.filename = name
            self.file_duration = duration
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Load config
            config_path = path.replace('.wav', '.txt')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'crossfade_ms' in config:
                        self.crossfade_ms = config['crossfade_ms']
                        self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
                        print(f"Loaded crossfade: {self.crossfade_ms}ms")
            
            # Create buffer
            self.create_buffer()
            
            print(f"✓ Loaded: {name}")
            print(f"  Duration: {duration:.1f}s")
            print(f"  Crossfade: {self.crossfade_ms}ms")
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def create_buffer(self, num_loops=10):
        """Create pre-rendered buffer."""
        if self.audio_data is None:
            return
        
        cf = self.crossfade_samples
        loop_len = len(self.audio_data)
        
        total = loop_len + (num_loops - 1) * (loop_len - cf)
        self.buffer = np.zeros((total, 2), dtype=np.float32)
        
        # First loop
        self.buffer[:loop_len] = self.audio_data
        
        # Add loops with crossfade
        for i in range(1, num_loops):
            start = loop_len + (i - 1) * (loop_len - cf)
            
            if cf > 0:
                prev = self.buffer[start - cf:start].copy()
                curr = self.audio_data[:cf].copy()
                t = np.linspace(0, 1, cf).reshape(-1, 1)
                self.buffer[start - cf:start] = prev * (1 - t) + curr * t
            
            remaining = loop_len - cf
            if remaining > 0:
                self.buffer[start:start + remaining] = self.audio_data[cf:]
        
        self.position = 0
        print(f"  Buffer: {num_loops} loops, {total/self.sample_rate:.1f}s")
    
    def audio_callback(self, outdata, frames, time, status):
        """Playback callback."""
        if self.buffer is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        remaining = len(self.buffer) - self.position
        to_read = min(frames, remaining)
        
        if to_read > 0:
            outdata[:to_read] = self.buffer[self.position:self.position + to_read]
            self.position += to_read
        
        if to_read < frames:
            outdata[to_read:] = 0
    
    def run(self):
        """Main loop."""
        if not self.select_file():
            return
        
        # Setup audio
        stream = sd.OutputStream(
            samplerate=self.sample_rate,
            blocksize=1024,
            channels=2,
            callback=self.audio_callback,
            dtype=np.float32
        )
        stream.start()
        
        print("\nControls: P=Play/Pause, Q=Quit")
        print("Press key (no Enter needed)")
        
        # Setup for single key input
        old_attr = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        
        try:
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    
                    if key == 'q':
                        break
                    elif key == 'p':
                        self.is_playing = not self.is_playing
                        print(f"{'▶ Playing' if self.is_playing else '⏸ Paused'}")
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attr)
            stream.stop()
            stream.close()
            print("\nDone")

def main():
    tester = CrossfadeTester()
    tester.run()

if __name__ == "__main__":
    main()
