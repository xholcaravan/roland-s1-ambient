#!/usr/bin/env python3
"""
Debug crossfade timing and overlaps.
"""

import numpy as np
import matplotlib.pyplot as plt

def visualize_crossfade(total_samples=44100,  # 1 second at 44.1kHz
                        position=40000,       # Near the end
                        buffer_size=1024,     # Standard buffer
                        crossfade_ms=5000):   # 5 seconds
    
    sample_rate = 44100
    crossfade_samples = int(crossfade_ms * sample_rate / 1000)
    
    print(f"Total audio: {total_samples} samples ({total_samples/sample_rate:.1f}s)")
    print(f"Current position: {position} samples ({position/sample_rate:.1f}s)")
    print(f"Buffer size: {buffer_size} samples")
    print(f"Crossfade: {crossfade_ms}ms = {crossfade_samples} samples")
    
    # Calculate what happens
    end_pos = position + buffer_size
    remaining = total_samples - position
    
    print(f"\nRemaining samples until end: {remaining}")
    print(f"Would need to wrap: {end_pos > total_samples}")
    
    if end_pos > total_samples:
        wrap_amount = buffer_size - remaining
        print(f"Wrap amount: {wrap_amount} samples")
        
        # Create visualization arrays
        full_audio = np.zeros(total_samples + wrap_amount)
        
        # Mark original audio (end portion)
        full_audio[position:position+remaining] = 1.0
        
        # Mark wrapped audio (start portion)
        full_audio[total_samples:total_samples+wrap_amount] = 0.5
        
        # Mark crossfade regions
        if remaining >= crossfade_samples:
            # Fade out region (end of original)
            fade_out_start = position + remaining - crossfade_samples
            full_audio[fade_out_start:position+remaining] = 0.8  # Highlight
            
            # Fade in region (start of wrapped)
            fade_in_end = total_samples + crossfade_samples
            full_audio[total_samples:fade_in_end] = 0.3  # Highlight
        
        # Plot
        plt.figure(figsize=(12, 4))
        plt.plot(full_audio, label='Audio Signal')
        plt.axvline(x=position, color='r', linestyle='--', label='Current Position')
        plt.axvline(x=total_samples, color='g', linestyle='--', label='End of File')
        plt.axvline(x=total_samples+wrap_amount, color='b', linestyle='--', label='End of Buffer')
        
        if remaining >= crossfade_samples:
            plt.axvspan(fade_out_start, position+remaining, alpha=0.3, color='red', label='Fade Out')
            plt.axvspan(total_samples, fade_in_end, alpha=0.3, color='blue', label='Fade In')
        
        plt.xlabel('Samples')
        plt.ylabel('Amplitude')
        plt.title(f'Crossfade Visualization ({crossfade_ms}ms)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
        print(f"\nFade out: Samples {fade_out_start} to {position+remaining}")
        print(f"Fade in:  Samples {total_samples} to {fade_in_end}")
        print(f"Overlap:  {crossfade_samples} samples ({crossfade_samples/sample_rate:.2f}s)")

# Test with realistic numbers
visualize_crossfade(
    total_samples=44100 * 30,  # 30 second file
    position=44100 * 28,       # 28 seconds in (2 seconds before end)
    buffer_size=1024,
    crossfade_ms=5000
)
