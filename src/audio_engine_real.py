#!/usr/bin/env python3
"""
Real Audio Engine for Roland S-1 Controller
Uses sounddevice for real-time audio playback.
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time
import queue

class AudioEngine:
    """Real audio engine with WAV loading and playback."""
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.channels = 2  # Stereo
        
        # Audio buffers
        self.ambient_data = None
        self.rhythm_data = None
        self.ambient_position = 0
        self.rhythm_position = 0
        
        # Volume controls (0.0 to 1.0)
        self.ambient_volume = 0.5
        self.rhythm_volume = 0.5
        
        # Playback state
        self.is_playing = False
        self.audio_queue = queue.Queue()
        
        print(f"AudioEngine initialized: {sample_rate}Hz, buffer: {buffer_size}")
    
    def load_audio_file(self, filepath, track='ambient'):
        """Load a WAV file into memory."""
        try:
            data, sr = sf.read(filepath, always_2d=True)
            
            # Convert to target sample rate if needed
            if sr != self.sample_rate:
                print(f"Warning: File {sr}Hz != engine {self.sample_rate}Hz")
                # Simple resample (for testing - would need proper resample in production)
                if len(data) > 0:
                    scale = self.sample_rate / sr
                    new_length = int(len(data) * scale)
                    # This is a simplified resample - use librosa for production
                    indices = np.linspace(0, len(data)-1, new_length).astype(int)
                    data = data[indices]
            
            # Ensure stereo
            if data.shape[1] == 1:  # Mono
                data = np.column_stack((data, data))
            
            if track == 'ambient':
                self.ambient_data = data
                self.ambient_position = 0
                print(f"Loaded ambient: {filepath} ({len(data)/self.sample_rate:.1f}s)")
            else:
                self.rhythm_data = data
                self.rhythm_position = 0
                print(f"Loaded rhythm: {filepath} ({len(data)/self.sample_rate:.1f}s)")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return False
    
    def audio_callback(self, outdata, frames, time, status):
        """Callback function for real-time audio playback."""
        if status:
            print(f"Audio status: {status}")
        
        # Initialize output buffer
        output = np.zeros((frames, self.channels), dtype=np.float32)
        
        # Mix ambient track
        if self.ambient_data is not None:
            end_pos = self.ambient_position + frames
            if end_pos <= len(self.ambient_data):
                ambient_chunk = self.ambient_data[self.ambient_position:end_pos]
                self.ambient_position = end_pos
            else:
                # Loop back to beginning
                remaining = len(self.ambient_data) - self.ambient_position
                ambient_chunk = np.vstack((
                    self.ambient_data[self.ambient_position:],
                    self.ambient_data[:frames - remaining]
                ))
                self.ambient_position = frames - remaining
            
            output += ambient_chunk * self.ambient_volume
        
        # Mix rhythm track
        if self.rhythm_data is not None:
            end_pos = self.rhythm_position + frames
            if end_pos <= len(self.rhythm_data):
                rhythm_chunk = self.rhythm_data[self.rhythm_position:end_pos]
                self.rhythm_position = end_pos
            else:
                # Loop back to beginning
                remaining = len(self.rhythm_data) - self.rhythm_position
                rhythm_chunk = np.vstack((
                    self.rhythm_data[self.rhythm_position:],
                    self.rhythm_data[:frames - remaining]
                ))
                self.rhythm_position = frames - remaining
            
            output += rhythm_chunk * self.rhythm_volume
        
        # Clip to prevent distortion
        output = np.clip(output, -1.0, 1.0)
        
        # Write to output buffer
        outdata[:] = output
    
    def set_volumes(self, ambient_vol, rhythm_vol):
        """Set volume levels (0.0 to 1.0)."""
        self.ambient_volume = max(0.0, min(1.0, ambient_vol))
        self.rhythm_volume = max(0.0, min(1.0, rhythm_vol))
    
    def play(self):
        """Start audio playback."""
        if not self.is_playing:
            self.is_playing = True
            
            # Start audio stream
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=self.channels,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            print("Audio playback started")
    
    def stop(self):
        """Stop audio playback."""
        if self.is_playing:
            self.is_playing = False
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            print("Audio playback stopped")

# Test function
def test_audio_engine():
    """Test the audio engine with our sample files."""
    print("\n" + "="*50)
    print("Testing AudioEngine with sample files")
    print("="*50)
    
    engine = AudioEngine()
    
    # Load test files
    engine.load_audio_file("samples/ambient/a_pad_c.wav", 'ambient')
    engine.load_audio_file("samples/rhythm/r_beat_1.wav", 'rhythm')
    
    # Set volumes (50% each)
    engine.set_volumes(0.5, 0.5)
    
    # Start playback
    engine.play()
    
    print("\nPlaying for 5 seconds...")
    print("Press Ctrl+C to stop early")
    
    try:
        # Play for 5 seconds
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    # Stop playback
    engine.stop()
    print("Test complete!")

if __name__ == "__main__":
    test_audio_engine()
