#!/usr/bin/env python3
"""
Debug version to find the 'NoneType' error
"""

import os
import json
import time
import numpy as np
import soundfile as sf

# Just test the loading and pre-rendering
print("Testing file loading...")

try:
    filepath = "samples/real_test/soldiers road.wav"
    print(f"Loading {filepath}...")
    
    # Test basic loading
    data, sr = sf.read(filepath, always_2d=True)
    print(f"✓ Loaded: shape={data.shape}, sr={sr}")
    
    # Test the pre-render logic
    sample_rate = 44100
    if sr != sample_rate:
        print(f"Resampling {sr}Hz → {sample_rate}Hz")
        scale = sample_rate / sr
        new_length = int(len(data) * scale)
        indices = np.linspace(0, len(data)-1, new_length).astype(int)
        data = data[indices]
    
    if data.shape[1] == 1:
        data = np.column_stack((data, data))
    
    print(f"✓ Processed: shape={data.shape}")
    
    # Test crossfade calculation
    crossfade_ms = 1000
    crossfade_samples = int(crossfade_ms * sample_rate / 1000)
    buffer_loops = 10
    total_samples = len(data)
    
    print(f"Creating buffer with {buffer_loops} loops...")
    print(f"Crossfade samples: {crossfade_samples}")
    print(f"Total samples per loop: {total_samples}")
    
    # Calculate buffer size
    total_buffer = total_samples + (buffer_loops - 1) * (total_samples - crossfade_samples)
    print(f"Total buffer size: {total_buffer}")
    
    # Create buffer
    buffer = np.zeros((total_buffer, 2), dtype=np.float32)
    
    # First loop
    buffer[:total_samples] = data
    print("✓ Added first loop")
    
    # Test one crossfade
    if crossfade_samples > 0:
        start_sample = total_samples
        print(f"Testing crossfade at sample {start_sample}")
        
        prev_end = buffer[start_sample - crossfade_samples:start_sample].copy()
        curr_start = data[:crossfade_samples].copy()
        
        print(f"prev_end shape: {prev_end.shape}")
        print(f"curr_start shape: {curr_start.shape}")
        
        t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
        print(f"t shape: {t.shape}")
        
        crossfade_region = prev_end * (1 - t) + curr_start * t
        print(f"crossfade_region shape: {crossfade_region.shape}")
        
        buffer[start_sample - crossfade_samples:start_sample] = crossfade_region
        print("✓ Crossfade test passed")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
