#!/usr/bin/env python3
"""
Audio Engine with Crossfade Looping
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import json
import os
import time

class CrossfadeAudioEngine:
    """Audio engine with configurable crossfade looping."""
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Audio data and state
        self.ambient_data = None
        self.rhythm_data = None
        self.ambient_position = 0
        self.rhythm_position = 0
        
        # Crossfade configurations
        self.ambient_config = {"crossfade_ms": 2000, "strategy": "crossfade"}
        self.rhythm_config = {"crossfade_ms": 100, "strategy": "crossfade"}
        
        # Volume
        self.ambient_volume = 0.5
        self.rhythm_volume = 0.5
        
        # Playback
        self.is_playing = False
    
    def load_config(self, wav_path):
        """Load configuration from .txt file if it exists."""
        config_path = wav_path.replace('.wav', '.txt')
        default = {"crossfade_ms": 1000, "strategy": "crossfade"}
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    print(f"Loaded config: {config}")
                    return config
            except:
                print(f"Error loading {config_path}, using defaults")
        
        return default
    
    def load_audio_file(self, filepath, track='ambient'):
        """Load WAV file with its configuration."""
        try:
            # Load audio
            data, sr = sf.read(filepath, always_2d=True)
            
            # Resample if needed
            if sr != self.sample_rate:
                print(f"Resampling {sr}Hz → {self.sample_rate}Hz")
                # Simple resample (use librosa for production)
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            # Ensure stereo
            if data.shape[1] == 1:
                data = np.column_stack((data, data))
            
            # Load configuration
            config = self.load_config(filepath)
            
            # Store
            if track == 'ambient':
                self.ambient_data = data
                self.ambient_config = config
                self.ambient_position = 0
                print(f"Loaded ambient: {os.path.basename(filepath)}")
                print(f"  Duration: {len(data)/self.sample_rate:.1f}s")
                print(f"  Crossfade: {config['crossfade_ms']}ms")
            else:
                self.rhythm_data = data
                self.rhythm_config = config
                self.rhythm_position = 0
                print(f"Loaded rhythm: {os.path.basename(filepath)}")
                print(f"  Duration: {len(data)/self.sample_rate:.1f}s")
                print(f"  Crossfade: {config['crossfade_ms']}ms")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return False
    
    def _get_chunk_with_crossfade(self, data, position, config):
        """Get audio chunk with crossfade at loop points."""
        frames = self.buffer_size
        crossfade_samples = int(config.get('crossfade_ms', 1000) * self.sample_rate / 1000)
        
        end_pos = position + frames
        
        # Normal playback (no loop needed)
        if end_pos <= len(data):
            return data[position:end_pos], end_pos
        
        # Need to loop with crossfade
        remaining = len(data) - position
        wrap_amount = frames - remaining
        
        # Get the two segments
        end_segment = data[position:]
        start_segment = data[:wrap_amount]
        
        # Apply crossfade if we have enough samples
        if crossfade_samples > 0 and remaining >= crossfade_samples and wrap_amount >= crossfade_samples:
            # Create fade curves
            fade_out = np.linspace(1.0, 0.0, crossfade_samples).reshape(-1, 1)
            fade_in = np.linspace(0.0, 1.0, crossfade_samples).reshape(-1, 1)
            
            # Apply fades
            end_segment[-crossfade_samples:] *= fade_out
            start_segment[:crossfade_samples] *= fade_in
        
        # Combine segments
        chunk = np.vstack((end_segment, start_segment))
        new_position = wrap_amount
        
        return chunk, new_position
    
    def audio_callback(self, outdata, frames, time, status):
        """Audio callback with crossfade looping."""
        if status:
            print(f"Audio status: {status}")
        
        output = np.zeros((frames, 2), dtype=np.float32)
        
        # Process ambient track
        if self.ambient_data is not None:
            chunk, new_pos = self._get_chunk_with_crossfade(
                self.ambient_data, 
                self.ambient_position,
                self.ambient_config
            )
            self.ambient_position = new_pos
            output += chunk * self.ambient_volume
        
        # Process rhythm track
        if self.rhythm_data is not None:
            chunk, new_pos = self._get_chunk_with_crossfade(
                self.rhythm_data,
                self.rhythm_position,
                self.rhythm_config
            )
            self.rhythm_position = new_pos
            output += chunk * self.rhythm_volume
        
        # Clip and output
        output = np.clip(output, -1.0, 1.0)
        outdata[:] = output
    
    def set_volumes(self, ambient_vol, rhythm_vol):
        self.ambient_volume = max(0.0, min(1.0, ambient_vol))
        self.rhythm_volume = max(0.0, min(1.0, rhythm_vol))
    
    def play(self):
        if not self.is_playing:
            self.is_playing = True
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=2,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            print("Audio playback started")
    
    def stop(self):
        if self.is_playing:
            self.is_playing = False
            self.stream.stop()
            self.stream.close()
            print("Audio playback stopped")

# Test function
def test_crossfade():
    """Test crossfade with your real file."""
    print("="*60)
    print("TEST: Crossfade Looping Engine")
    print("="*60)
    
    # Create a test configuration
    test_config = {
        "crossfade_ms": 5000,  # 5 second crossfade for ambient
        "strategy": "crossfade"
    }
    
    # Save test config
    config_path = "samples/real_test/test_config.txt"
    os.makedirs("samples/real_test", exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(test_config, f, indent=2)
    
    print(f"\nCreated test config: {config_path}")
    print(json.dumps(test_config, indent=2))
    
    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("="*60)
    print("1. Place your real WAV file in: samples/real_test/")
    print("2. Rename it to: test_audio.wav")
    print("3. The engine will use: test_config.txt for crossfade settings")
    print("4. We'll test with 5 second crossfade (adjust in config)")
    print("="*60)
    
    # Check if file exists
    test_file = "samples/real_test/test_audio.wav"
    if os.path.exists(test_file):
        print(f"\nFound: {test_file}")
        
        # Load and test
        engine = CrossfadeAudioEngine()
        engine.load_audio_file(test_file, 'ambient')
        
        print("\nPlaying for 15 seconds (should loop with crossfade)...")
        print("Press Ctrl+C to stop")
        
        engine.play()
        try:
            time.sleep(15)
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            engine.stop()
    else:
        print(f"\n⚠️  File not found: {test_file}")
        print("Please place your WAV file there and run again.")

if __name__ == "__main__":
    test_crossfade()
