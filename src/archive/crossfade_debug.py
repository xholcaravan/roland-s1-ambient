#!/usr/bin/env python3
"""
Interactive Crossfade Loop Tester - SIMPLE VERSION
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
        self.is_playing = False
        
        print("\n" + "="*60)
        print("CROSSFADE LOOP TESTER")
        print("="*60)
    
    def load_file(self, filepath):
        try:
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
            self.position = 0
            print(f"Loaded: {os.path.basename(filepath)}")
            print(f"Duration: {len(data)/sr:.1f}s")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def audio_callback(self, outdata, frames, time, status):
        if self.audio_data is None or not self.is_playing:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
        total_samples = len(self.audio_data)
        
        # Generate the audio chunk
        chunk = np.zeros((frames, 2), dtype=np.float32)
        
        for i in range(frames):
            pos = self.position % total_samples
            
            # Check if we're in crossfade region
            remaining = total_samples - (self.position % total_samples)
            if remaining <= crossfade_samples and crossfade_samples > 0:
                # In crossfade: mix end with beginning
                fade_pos = crossfade_samples - remaining
                t = fade_pos / crossfade_samples  # 0 to 1
                
                # End of current loop (fading out)
                sample_end = self.audio_data[pos]
                # Start of next loop (fading in)
                sample_start = self.audio_data[fade_pos % total_samples]
                
                # Crossfade mix
                chunk[i] = sample_end * (1 - t) + sample_start * t
            else:
                # Normal playback
                chunk[i] = self.audio_data[pos]
            
            self.position += 1
        
        outdata[:] = chunk
    
    def run(self):
        # Load a test file
        test_file = "samples/real_test/test.wav"
        if not os.path.exists(test_file):
            print(f"Create {test_file} first!")
            return
        
        if not self.load_file(test_file):
            return
        
        # Setup audio
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            blocksize=1024,
            channels=2,
            callback=self.audio_callback,
            dtype=np.float32
        )
        self.stream.start()
        
        print("\nControls:")
        print("  P: Play/Pause")
        print("  +: Increase crossfade")
        print("  -: Decrease crossfade")
        print("  Q: Quit")
        print("\nPress keys (then Enter)")
        
        self.setup_terminal()
        
        try:
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    
                    if key == 'q':
                        break
                    elif key == 'p':
                        self.is_playing = not self.is_playing
                        print(f" {'Playing' if self.is_playing else 'Paused'}")
                    elif key == '+':
                        self.crossfade_ms = min(5000, self.crossfade_ms + 100)
                        print(f"Crossfade: {self.crossfade_ms}ms")
                    elif key == '-':
                        self.crossfade_ms = max(0, self.crossfade_ms - 100)
                        print(f"Crossfade: {self.crossfade_ms}ms")
        
        except KeyboardInterrupt:
            print("\nStopped")
        finally:
            self.restore_terminal()
            self.stream.stop()
            self.stream.close()
    
    def setup_terminal(self):
        self.old_termios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    def restore_terminal(self):
        if self.old_termios:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_termios)

def main():
    tester = CrossfadeTester()
    tester.run()

if __name__ == "__main__":
    main()
