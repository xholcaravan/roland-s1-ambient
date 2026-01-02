#!/usr/bin/env python3
"""
Fixed Crossfade Logic - Starts fading BEFORE the end.
"""

import numpy as np
import sounddevice as sd
import soundfile as sf
import time

def test_fixed_crossfade():
    """Test the fixed crossfade logic."""
    
    # Load your test file
    filepath = "samples/real_test/test_audio.wav"
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        print("Please place your test file there.")
        return
    
    # Load audio
    data, sr = sf.read(filepath, always_2d=True)
    sample_rate = 44100
    buffer_size = 1024
    
    # Resample if needed
    if sr != sample_rate:
        scale = sample_rate / sr
        new_length = int(len(data) * scale)
        indices = np.linspace(0, len(data)-1, new_length).astype(int)
        data = data[indices]
    
    # Ensure stereo
    if data.shape[1] == 1:
        data = np.column_stack((data, data))
    
    print(f"Loaded: {os.path.basename(filepath)}")
    print(f"Duration: {len(data)/sample_rate:.1f}s")
    print(f"Sample rate: {sample_rate}Hz")
    print(f"Buffer size: {buffer_size} samples ({buffer_size/sample_rate*1000:.1f}ms)")
    
    # Test parameters
    crossfade_ms = 5000
    crossfade_samples = int(crossfade_ms * sample_rate / 1000)
    print(f"\nTesting {crossfade_ms}ms crossfade = {crossfade_samples} samples")
    
    # Simulate what happens near the end
    test_position = len(data) - int(2 * sample_rate)  # 2 seconds before end
    print(f"\nSimulating playback 2 seconds before end...")
    print(f"Position: {test_position} samples ({test_position/sample_rate:.1f}s)")
    
    # Calculate what SHOULD happen
    remaining = len(data) - test_position
    print(f"Remaining until end: {remaining} samples ({remaining/sample_rate:.1f}s)")
    
    # The key insight: We need to check if we'll enter crossfade zone
    # during THIS buffer or FUTURE buffers
    frames_needed_until_crossfade = remaining - crossfade_samples
    print(f"\nWill enter crossfade zone in: {frames_needed_until_crossfade} samples")
    print(f"That's {frames_needed_until_crossfade/sample_rate:.1f} seconds from now")
    
    if frames_needed_until_crossfade <= buffer_size:
        print("✅ CORRECT: Should start crossfade in this buffer!")
    else:
        print("❌ WRONG: Should NOT start crossfade yet")
    
    # Demonstrate the fixed logic
    print("\n" + "="*60)
    print("FIXED CROSSFADE LOGIC:")
    print("="*60)
    
    class FixedCrossfadeEngine:
        def __init__(self, data, sample_rate, buffer_size, crossfade_ms):
            self.data = data
            self.sample_rate = sample_rate
            self.buffer_size = buffer_size
            self.crossfade_ms = crossfade_ms
            self.crossfade_samples = int(crossfade_ms * sample_rate / 1000)
            self.position = test_position
            self.crossfade_active = False
            self.crossfade_position = 0  # Position within crossfade
            
        def get_next_chunk(self):
            """Get next audio chunk with proper crossfade logic."""
            frames = self.buffer_size
            
            # Check if we're in crossfade mode
            if self.crossfade_active:
                return self._get_crossfade_chunk(frames)
            
            # Check if we should START crossfade
            remaining = len(self.data) - self.position
            if remaining <= self.crossfade_samples + frames:
                # We're about to enter or already in crossfade zone
                print(f"🎯 STARTING CROSSFADE! Remaining: {remaining/sample_rate:.1f}s")
                self.crossfade_active = True
                self.crossfade_position = self.crossfade_samples - remaining
                return self._get_crossfade_chunk(frames)
            
            # Normal playback
            chunk = self.data[self.position:self.position + frames]
            self.position += frames
            return chunk
        
        def _get_crossfade_chunk(self, frames):
            """Get chunk during crossfade period."""
            # Calculate how much to take from end and beginning
            end_remaining = len(self.data) - self.position
            start_needed = frames - end_remaining
            
            if end_remaining > 0:
                end_chunk = self.data[self.position:]
            else:
                end_chunk = np.array([])
            
            if start_needed > 0:
                start_chunk = self.data[:start_needed]
            else:
                start_chunk = np.array([])
            
            # Combine
            if len(end_chunk) > 0 and len(start_chunk) > 0:
                chunk = np.vstack((end_chunk, start_chunk))
            elif len(end_chunk) > 0:
                chunk = end_chunk
            else:
                chunk = start_chunk
            
            # Apply crossfade
            if len(chunk) > 0:
                # Create fade curves for THIS chunk
                fade_start = max(0, self.crossfade_position)
                fade_end = min(self.crossfade_samples, self.crossfade_position + frames)
                
                if fade_end > fade_start:
                    fade_length = fade_end - fade_start
                    fade_out = np.linspace(1.0, 0.0, fade_length).reshape(-1, 1)
                    fade_in = np.linspace(0.0, 1.0, fade_length).reshape(-1, 1)
                    
                    # Apply to appropriate sections
                    if len(end_chunk) > 0 and fade_start < len(end_chunk):
                        end_fade_start = max(0, len(end_chunk) - (self.crossfade_samples - fade_start))
                        end_fade_end = min(len(end_chunk), end_fade_start + fade_length)
                        if end_fade_end > end_fade_start:
                            chunk[end_fade_start:end_fade_end] *= fade_out[:end_fade_end-end_fade_start]
                    
                    if len(start_chunk) > 0:
                        start_fade_end = min(len(start_chunk), fade_end)
                        if start_fade_end > 0:
                            chunk[len(end_chunk):len(end_chunk)+start_fade_end] *= fade_in[:start_fade_end]
            
            # Update positions
            self.crossfade_position += frames
            self.position += min(frames, end_remaining)
            
            # If crossfade complete, reset
            if self.crossfade_position >= self.crossfade_samples:
                self.crossfade_active = False
                self.position = start_needed  # Wrap to correct position
            
            return chunk
    
    # Test the fixed engine
    print("\nSimulating 5 buffers (to see crossfade start):")
    engine = FixedCrossfadeEngine(data, sample_rate, buffer_size, crossfade_ms)
    
    for i in range(5):
        chunk = engine.get_next_chunk()
        pos_seconds = engine.position / sample_rate
        remaining = len(data) - engine.position
        print(f"Buffer {i+1}: Position {pos_seconds:.1f}s, Remaining {remaining/sample_rate:.1f}s, Crossfade active: {engine.crossfade_active}")
        
        if len(chunk) < buffer_size:
            print(f"  Warning: Got {len(chunk)} samples instead of {buffer_size}")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    print("The key fix: Start crossfade WHEN remaining samples <= crossfade_samples")
    print("Not: Wait until we actually wrap around.")
    print("\nThis ensures smooth transition that starts BEFORE the end.")

if __name__ == "__main__":
    import os
    test_fixed_crossfade()
