#!/usr/bin/env python3
"""
Simple working crossfade tester - minimal version
"""

import os
import numpy as np
import sounddevice as sd
import soundfile as sf

class SimpleCrossfade:
    def __init__(self):
        self.sample_rate = 44100
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        self.audio_data = None
        self.buffer = None
        self.position = 0
        self.is_playing = False
        
        print("\n" + "="*60)
        print("SIMPLE CROSSFADE TESTER")
        print("="*60)
    
    def load_file(self, filename):
        """Load a file and create buffer."""
        try:
            print(f"Loading {filename}...")
            data, sr = sf.read(filename, always_2d=True)
            
            if sr != self.sample_rate:
                print(f"Resampling {sr}Hz → {self.sample_rate}Hz")
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            self.audio_data = data
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            # Create buffer with 3 loops
            print("Creating buffer...")
            self.buffer = self._create_buffer(3)
            self.position = 0
            
            print(f"✓ Loaded: {os.path.basename(filename)}")
            print(f"  Duration: {len(data)/sr:.1f}s")
            print(f"  Crossfade: {self.crossfade_ms}ms")
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_buffer(self, num_loops):
        """Create pre-rendered buffer."""
        crossfade = self.crossfade_samples
        loop_len = len(self.audio_data)
        
        total_len = loop_len + (num_loops - 1) * (loop_len - crossfade)
        buffer = np.zeros((total_len, 2), dtype=np.float32)
        
        # First loop
        buffer[:loop_len] = self.audio_data
        
        # Add loops with crossfade
        for i in range(1, num_loops):
            start = loop_len + (i - 1) * (loop_len - crossfade)
            
            if crossfade > 0:
                prev = buffer[start - crossfade:start].copy()
                curr = self.audio_data[:crossfade].copy()
                t = np.linspace(0, 1, crossfade).reshape(-1, 1)
                buffer[start - crossfade:start] = prev * (1 - t) + curr * t
            
            remaining = loop_len - crossfade
            if remaining > 0:
                buffer[start:start + remaining] = self.audio_data[crossfade:]
        
        print(f"  Buffer: {num_loops} loops, {total_len/self.sample_rate:.1f}s")
        return buffer
    
    def audio_callback(self, outdata, frames, time, status):
        """Simple playback."""
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
        """Simple test."""
        # Load a file
        test_file = "samples/real_test/a_pad_c.wav"
        if not self.load_file(test_file):
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
        print("Press Enter after each command")
        
        self.is_playing = True
        
        try:
            while True:
                cmd = input("> ").lower().strip()
                if cmd == 'q':
                    break
                elif cmd == 'p':
                    self.is_playing = not self.is_playing
                    print(f"{'▶ Playing' if self.is_playing else '⏸ Paused'}")
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()
            print("\nDone")

def main():
    tester = SimpleCrossfade()
    tester.run()

if __name__ == "__main__":
    main()
