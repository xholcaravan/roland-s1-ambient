#!/usr/bin/env python3
"""
Create simple test WAV files for development
"""

import numpy as np
import wave
import os

def create_sine_wave(filename, duration=2.0, freq=440.0, sample_rate=44100):
    """Create a simple sine wave WAV file."""
    # Create samples
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = 0.5 * np.sin(2 * np.pi * freq * t)
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Create stereo (2 channels)
    stereo_data = np.column_stack((wave_data, wave_data))
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())
    
    print(f"Created: {filename} ({duration}s, {freq}Hz)")

def create_rhythm(filename, duration=2.0, sample_rate=44100):
    """Create a simple rhythm (kick drum pattern)."""
    # Create time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create kick drum hits (4 beats)
    wave_data = np.zeros_like(t)
    
    # Add kicks at 0, 0.5, 1.0, 1.5 seconds
    for beat_time in [0.0, 0.5, 1.0, 1.5]:
        if beat_time < duration:
            start_idx = int(beat_time * sample_rate)
            end_idx = min(start_idx + int(0.1 * sample_rate), len(wave_data))
            
            # Create a short sine burst for kick
            burst_t = np.linspace(0, 0.1, end_idx - start_idx, False)
            burst = 0.7 * np.sin(2 * np.pi * 100 * burst_t) * np.exp(-15 * burst_t)
            wave_data[start_idx:end_idx] += burst
    
    # Convert to 16-bit PCM
    wave_data = np.clip(wave_data, -1, 1)
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Create stereo
    stereo_data = np.column_stack((wave_data, wave_data))
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())
    
    print(f"Created: {filename} ({duration}s rhythm pattern)")

# Create directories if they don't exist
os.makedirs("samples/ambient", exist_ok=True)
os.makedirs("samples/rhythm", exist_ok=True)

# Create test files
print("Creating test WAV files...")
print("-" * 40)

# Ambient files (pads/drones)
create_sine_wave("samples/ambient/a_pad_c.wav", duration=10.0, freq=261.63)  # C4
create_sine_wave("samples/ambient/a_pad_g.wav", duration=12.0, freq=392.00)  # G4
create_sine_wave("samples/ambient/a_drone.wav", duration=15.0, freq=220.00)  # A3

# Rhythm files (beats)
create_rhythm("samples/rhythm/r_beat_1.wav", duration=4.0)
create_rhythm("samples/rhythm/r_beat_2.wav", duration=2.0)

print("-" * 40)
print("Done! Test files created in samples/ directory")
