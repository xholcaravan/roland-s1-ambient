#!/usr/bin/env python3
"""
Proactive Crossfade Scheduler - Fixes the timing bug
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

class ProactiveCrossfade:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.total_samples = 0
        
        # Crossfade settings
        self.crossfade_ms = 1000
        self.crossfade_samples = 0
        
        # PROACTIVE SCHEDULING
        self.current_track_pos = 0.0  # Position in current track
        self.next_track_pos = 0.0     # Position in next track
        
        # Crossfade state
        self.crossfade_active = False
        self.crossfade_start_pos = 0  # Where current track was when crossfade started
        self.crossfade_progress = 0.0  # 0 to 1
        
        # Simple playback
        self.is_playing = False
        self.filename = ""
        
        print("\n" + "="*60)
        print("PROACTIVE CROSSFADE SCHEDULER")
        print("Schedules crossfades in advance to avoid timing bugs")
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
            
            # Reset state
            self.current_track_pos = 0.0
            self.next_track_pos = 0.0
            self.crossfade_active = False
            self.crossfade_start_pos = 0
            self.crossfade_progress = 0.0
            
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            
            print(f"✓ Loaded: {self.filename}")
            print(f"  Duration: {len(data)/sr:.1f}s")
            print(f"  Crossfade: {self.crossfade_ms}ms")
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
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
        if not self.is_playing or self.audio_data is None:
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
                    self.next_track_pos = 0.0  # Next track starts at beginning
                    print(f"[DEBUG] Starting crossfade at pos {self.current_track_pos}")
            
            # Get audio based on state
            if self.crossfade_active:
                # DURING CROSSFADE
                
                # Calculate progress (0 to 1)
                samples_into_crossfade = self.current_track_pos - self.crossfade_start_pos
                self.crossfade_progress = samples_into_crossfade / self.crossfade_samples
                
                # Clamp to 0-1
                self.crossfade_progress = max(0, min(1, self.crossfade_progress))
                
                # Get audio from both tracks
                current_audio = self.get_audio_at(self.current_track_pos)
                next_audio = self.get_audio_at(self.next_track_pos)
                
                # Mix with crossfade curves
                # Current track fades out (1 → 0)
                fade_out = 1.0 - self.crossfade_progress
                # Next track fades in (0 → 1)
                fade_in = self.crossfade_progress
                
                output[i] = current_audio * fade_out + next_audio * fade_in
                
                # Advance both tracks
                self.current_track_pos += 1
                self.next_track_pos += 1
                
                # Check if crossfade complete
                if self.crossfade_progress >= 1.0:
                    # Crossfade complete! Switch to next track
                    print(f"[DEBUG] Crossfade complete, switching to next track")
                    self.current_track_pos = self.next_track_pos
                    self.crossfade_active = False
                    self.crossfade_progress = 0.0
                    
                    # Wrap positions if needed
                    if self.current_track_pos >= self.total_samples:
                        self.current_track_pos -= self.total_samples
                    if self.next_track_pos >= self.total_samples:
                        self.next_track_pos -= self.total_samples
            else:
                # NORMAL PLAYBACK (no crossfade)
                output[i] = self.get_audio_at(self.current_track_pos)
                self.current_track_pos += 1
            
            # Wrap current position if it exceeds total
            if self.current_track_pos >= self.total_samples:
                self.current_track_pos -= self.total_samples
        
        outdata[:] = output
    
    def adjust_crossfade(self, delta_ms):
        """Adjust crossfade time."""
        new_ms = max(0, min(30000, self.crossfade_ms + delta_ms))
        if new_ms != self.crossfade_ms:
            self.crossfade_ms = new_ms
            self.crossfade_samples = int(self.crossfade_ms * self.sample_rate / 1000)
            print(f"Crossfade: {self.crossfade_ms}ms")
            return True
        return False
    
    def run_test(self):
        """Test runner."""
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
        print("Press: P=Play/Pause, +/-=Adjust, Q=Quit")
        
        # Setup terminal for single key input
        old_termios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        
        try:
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    
                    if key == 'q':
                        break
                    elif key == 'p' or key == ' ':
                        self.is_playing = not self.is_playing
                        print(f"{'▶ Playing' if self.is_playing else '⏸ Paused'}")
                    elif key == '+':
                        self.adjust_crossfade(100)
                    elif key == '-':
                        self.adjust_crossfade(-100)
                        
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_termios)
            stream.stop()
            stream.close()
            print("\nDone")

def main():
    tester = ProactiveCrossfade()
    tester.run_test()

if __name__ == "__main__":
    main()
