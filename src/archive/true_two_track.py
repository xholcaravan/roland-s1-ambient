#!/usr/bin/env python3
"""
TRUE Two-Track Crossfade - Simple and Clean
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

class TrueTwoTrack:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # SIMPLE: Two continuous playback positions
        self.pos_a = 0.0  # Track A position (continuous)
        self.pos_b = 0.0  # Track B position (continuous)
        
        # SIMPLE: Which track is fading in/out
        self.fading_out = 'A'  # Track A is currently playing (will fade out)
        self.fading_in = 'B'   # Track B will fade in
        
        # Playback state
        self.is_playing = False
        self.filename = ""
        
        print("\n" + "="*60)
        print("TRUE TWO-TRACK CROSSFADE")
        print("Simple continuous playback with mixing")
        print("="*60)
    
    def load_file(self, filepath):
        """Load audio file."""
        try:
            data, sr = sf.read(filepath, always_2d=True)
            
            if sr != self.sample_rate:
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            self.audio_data = data
            self.total_samples = len(data)
            self.filename = os.path.basename(filepath)
            
            # Reset positions
            self.pos_a = 0.0
            self.pos_b = -self.crossfade_samples  # Track B starts early!
            self.fading_out = 'A'
            self.fading_in = 'B'
            
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            print(f"Loaded {self.filename}")
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def get_audio_at(self, position):
        """Get audio at continuous position (with interpolation)."""
        if self.audio_data is None:
            return np.zeros(2)
        
        # Continuous position - no wrapping!
        idx = int(position) % self.total_samples
        next_idx = (idx + 1) % self.total_samples
        t = position - int(position)
        
        return (1-t) * self.audio_data[idx] + t * self.audio_data[next_idx]
    
    def audio_callback(self, outdata, frames, time, status):
        """TRUE two-track mixing - no complex state."""
        if not self.is_playing or self.audio_data is None:
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            return
        
        output = np.zeros((frames, 2), dtype=np.float32)
        
        for i in range(frames):
            # Get audio from both tracks at their current positions
            audio_a = self.get_audio_at(self.pos_a)
            audio_b = self.get_audio_at(self.pos_b)
            
            # Determine if we're in crossfade region
            # Crossfade happens when Track B position is between -crossfade and 0
            if -self.crossfade_samples <= self.pos_b < 0:
                # IN CROSSFADE: Track B is negative (starting early), Track A is positive
                fade_progress = (self.pos_b + self.crossfade_samples) / self.crossfade_samples
                # fade_progress goes from 0 (start of crossfade) to 1 (end of crossfade)
                
                # Mix: A fades out, B fades in
                mix = audio_a * (1 - fade_progress) + audio_b * fade_progress
                output[i] = mix
                
            elif self.pos_b >= 0:
                # AFTER CROSSFADE: Track B is now positive (playing normally)
                # Track A has faded out completely
                output[i] = audio_b  # Only track B plays
                
                # When Track B gets ahead enough, prepare for next crossfade
                if self.pos_b >= self.total_samples - self.crossfade_samples:
                    # Reset Track A to start at right offset for next crossfade
                    self.pos_a = self.pos_b - self.total_samples
                    self.fading_out, self.fading_in = 'B', 'A'  # Swap roles
            else:
                # BEFORE CROSSFADE: Only Track A plays
                output[i] = audio_a
            
            # Advance both tracks continuously
            self.pos_a += 1
            self.pos_b += 1
        
        outdata[:] = output
    
    def run_test(self):
        """Simple test runner."""
        # Find a file to test
        test_dir = "samples/real_test"
        files = [f for f in os.listdir(test_dir) if f.endswith('.wav')]
        
        if not files:
            print(f"No WAV files in {test_dir}")
            return
        
        filepath = os.path.join(test_dir, files[0])
        if not self.load_file(filepath):
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
        
        print(f"\nPlaying {self.filename}")
        print(f"Crossfade: {self.crossfade_ms}ms")
        print("Track B starts {self.crossfade_ms/1000:.1f}s before Track A ends")
        print("\nPress Enter to start/stop, Q to quit...")
        
        self.is_playing = True
        
        try:
            while True:
                key = input()
                if key.lower() == 'q':
                    break
                self.is_playing = not self.is_playing
                print(f"{'Playing' if self.is_playing else 'Paused'}")
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()
            print("\nDone")

def main():
    tester = TrueTwoTrack()
    tester.run_test()

if __name__ == "__main__":
    main()
