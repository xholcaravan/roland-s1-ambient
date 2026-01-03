#!/usr/bin/env python3
"""
Real Audio Engine for Roland S-1 Controller
Now with FIXED-TIME loop crossfades (300s buffers).
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time

class AudioEngine:
    """Real audio engine with fixed-time loop crossfades."""
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.channels = 2  # Stereo
        
        # Audio data and positions
        self.ambient_data = None
        self.rhythm_data = None
        self.ambient_position = 0
        self.rhythm_position = 0
        self.ambient_crossfade_ms = 0
        self.rhythm_crossfade_ms = 0
        
        # Pre-rendered buffers for crossfades (FIXED 300s/5min)
        self.ambient_buffer = None
        self.rhythm_buffer = None
        self.ambient_buffer_position = 0
        self.rhythm_buffer_position = 0
        self.target_buffer_seconds = 300  # 5 minutes fixed buffer
        
        # Volume controls (0.0 to 1.0)
        self.ambient_volume = 0.5
        self.rhythm_volume = 0.5
        
        # File info
        self.current_ambient_file = None  # (filename, crossfade_ms, filepath)
        self.current_rhythm_file = None   # (filename, crossfade_ms, filepath)
        
        # Playback state
        self.is_playing = False
        
        print(f"AudioEngine initialized: {sample_rate}Hz, buffer: {buffer_size}")
        print(f"Fixed buffer duration: {self.target_buffer_seconds}s (5min)")
    
    def load_audio_file(self, file_info, track='ambient'):
        """Load a WAV file and create fixed-time buffer with crossfade."""
        if not file_info:
            print(f"Error: No file info provided for {track}")
            return False
        
        filename, crossfade_ms, filepath = file_info
        
        try:
            print(f"Loading {track}: {filename} ({crossfade_ms}ms crossfade)...")
            data, sr = sf.read(filepath, always_2d=True)
            
            # Convert to target sample rate if needed
            if sr != self.sample_rate:
                print(f"  Resampling {sr}Hz → {self.sample_rate}Hz")
                scale = self.sample_rate / sr
                new_length = int(len(data) * scale)
                indices = np.linspace(0, len(data)-1, new_length).astype(int)
                data = data[indices]
            
            # Ensure stereo
            if data.shape[1] == 1:  # Mono
                data = np.column_stack((data, data))
            
            if track == 'ambient':
                self.ambient_data = data
                self.ambient_position = 0
                self.ambient_crossfade_ms = crossfade_ms
                self.current_ambient_file = file_info
                
                # Create fixed-time buffer with crossfade
                self.ambient_buffer = self._create_fixed_time_buffer(data, crossfade_ms)
                self.ambient_buffer_position = 0
                
                if self.ambient_buffer is not None:
                    print(f"  ✅ Ambient loaded: {len(data)/self.sample_rate:.1f}s file")
                    print(f"     Buffer: {len(self.ambient_buffer)/self.sample_rate:.1f}s ({len(self.ambient_buffer)/self.sample_rate/60:.1f}min)")
            else:
                self.rhythm_data = data
                self.rhythm_position = 0
                self.rhythm_crossfade_ms = crossfade_ms
                self.current_rhythm_file = file_info
                
                # Create fixed-time buffer with crossfade
                self.rhythm_buffer = self._create_fixed_time_buffer(data, crossfade_ms)
                self.rhythm_buffer_position = 0
                
                if self.rhythm_buffer is not None:
                    print(f"  ✅ Rhythm loaded: {len(data)/self.sample_rate:.1f}s file")
                    print(f"     Buffer: {len(self.rhythm_buffer)/self.sample_rate:.1f}s ({len(self.rhythm_buffer)/self.sample_rate/60:.1f}min)")
            
            return True
            
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_fixed_time_buffer(self, audio_data, crossfade_ms):
        """Create buffer with fixed duration (default 300s/5min)."""
        if audio_data is None or len(audio_data) == 0:
            return None
        
        sample_rate = self.sample_rate
        total_samples = len(audio_data)
        crossfade_samples = int(crossfade_ms * sample_rate / 1000)
        
        # Calculate loop parameters
        file_duration = total_samples / sample_rate  # seconds
        effective_loop_samples = total_samples - crossfade_samples
        
        # Safety check
        if crossfade_samples >= total_samples:
            print(f"  ⚠️  Crossfade {crossfade_ms}ms >= file duration {file_duration:.1f}s!")
            print(f"  Reducing crossfade to {file_duration*500:.0f}ms (50% of file)")
            crossfade_samples = int(total_samples * 0.5)
            crossfade_ms = crossfade_samples * 1000 / sample_rate
        
        effective_loop_duration = effective_loop_samples / sample_rate  # seconds
        
        if effective_loop_duration <= 0:
            print(f"  ⚠️  Crossfade {crossfade_ms}ms >= file duration {file_duration:.1f}s!")
            return None
        
        # Calculate how many loops fit in target time
        loops_needed = int(np.ceil(self.target_buffer_seconds / effective_loop_duration))
        
        # Calculate total buffer samples
        # First loop: full length
        # Subsequent loops: full length minus crossfade (overlap)
        total_buffer_samples = total_samples + (loops_needed - 1) * effective_loop_samples
        
        # Ensure buffer is at least target_seconds
        target_samples = int(self.target_buffer_seconds * sample_rate)
        if total_buffer_samples < target_samples:
            # Add partial final loop if needed
            remaining_samples = target_samples - total_buffer_samples
            if remaining_samples > 0:
                # Add what we can from the beginning (after crossfade)
                add_from_start = min(remaining_samples, effective_loop_samples)
                total_buffer_samples += add_from_start
        
        print(f"    File: {file_duration:.1f}s, Crossfade: {crossfade_ms:.0f}ms")
        print(f"    Effective loop: {effective_loop_duration:.1f}s")
        print(f"    Loops needed: {loops_needed}")
        print(f"    Buffer: {total_buffer_samples/sample_rate:.1f}s")
        
        # Create buffer
        buffer = np.zeros((total_buffer_samples, 2), dtype=np.float32)
        
        # Render first loop (full)
        buffer[:total_samples] = audio_data
        
        # Render subsequent loops with crossfade
        for loop in range(1, loops_needed):
            start_sample = total_samples + (loop - 1) * effective_loop_samples
            
            # Get the overlapping region from previous loop
            prev_end = buffer[start_sample - crossfade_samples:start_sample].copy()
            curr_start = audio_data[:crossfade_samples].copy()
            
            # Apply crossfade
            t = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
            crossfade_region = prev_end * (1 - t) + curr_start * t
            
            # Write crossfade region
            buffer[start_sample - crossfade_samples:start_sample] = crossfade_region
            
            # Write rest of current loop
            remaining = total_samples - crossfade_samples
            if remaining > 0:
                buffer[start_sample:start_sample + remaining] = audio_data[crossfade_samples:]
        
        # If we added a partial final loop
        if total_buffer_samples > total_samples + (loops_needed - 1) * effective_loop_samples:
            extra_start = total_samples + (loops_needed - 1) * effective_loop_samples
            extra_needed = total_buffer_samples - extra_start
            
            # Copy from after crossfade of the file
            copy_from = crossfade_samples
            copy_to = min(copy_from + extra_needed, total_samples)
            
            buffer[extra_start:extra_start + (copy_to - copy_from)] = \
                audio_data[copy_from:copy_to]
        
        return buffer
    
    def audio_callback(self, outdata, frames, time, status):
        """Callback function for real-time audio playback with crossfades."""
        if status:
            print(f"Audio status: {status}")
        
        # Initialize output buffer
        output = np.zeros((frames, self.channels), dtype=np.float32)
        
        # Mix ambient track from pre-rendered buffer
        if self.ambient_buffer is not None and self.ambient_volume > 0:
            ambient_output = self._get_audio_chunk(self.ambient_buffer, self.ambient_buffer_position, frames)
            self.ambient_buffer_position = (self.ambient_buffer_position + frames) % len(self.ambient_buffer)
            output += ambient_output * self.ambient_volume
        
        # Mix rhythm track from pre-rendered buffer
        if self.rhythm_buffer is not None and self.rhythm_volume > 0:
            rhythm_output = self._get_audio_chunk(self.rhythm_buffer, self.rhythm_buffer_position, frames)
            self.rhythm_buffer_position = (self.rhythm_buffer_position + frames) % len(self.rhythm_buffer)
            output += rhythm_output * self.rhythm_volume
        
        # Clip to prevent distortion
        output = np.clip(output, -1.0, 1.0)
        
        # Write to output buffer
        outdata[:] = output
    
    def _get_audio_chunk(self, buffer, position, frames):
        """Get audio chunk from buffer, handling wrap-around."""
        buffer_len = len(buffer)
        
        if position + frames <= buffer_len:
            # Simple case: all frames fit without wrap
            return buffer[position:position + frames]
        else:
            # Need to wrap around
            remaining = buffer_len - position
            chunk = np.vstack((
                buffer[position:],
                buffer[:frames - remaining]
            ))
            return chunk
    
    def set_volumes(self, ambient_vol, rhythm_vol):
        """Set volume levels (0.0 to 1.0)."""
        self.ambient_volume = max(0.0, min(1.0, ambient_vol))
        self.rhythm_volume = max(0.0, min(1.0, rhythm_vol))
        
        # When volume hits 0, we should load next file immediately
        # (This will be triggered from main.py based on knob position)
    
    def load_new_ambient(self, file_info):
        """Load new ambient file (when knob hits 0%)."""
        success = self.load_audio_file(file_info, 'ambient')
        if success:
            print(f"🔄 Ambient channel: Loaded {file_info[0]}")
        return success
    
    def load_new_rhythm(self, file_info):
        """Load new rhythm file (when knob hits 100%)."""
        success = self.load_audio_file(file_info, 'rhythm')
        if success:
            print(f"�� Rhythm channel: Loaded {file_info[0]}")
        return success
    
    def get_current_files_info(self):
        """Get info about currently loaded files."""
        ambient_info = None
        rhythm_info = None
        
        if self.current_ambient_file:
            filename, crossfade_ms, filepath = self.current_ambient_file
            ambient_info = {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'volume': self.ambient_volume
            }
        
        if self.current_rhythm_file:
            filename, crossfade_ms, filepath = self.current_rhythm_file
            rhythm_info = {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'volume': self.rhythm_volume
            }
        
        return ambient_info, rhythm_info
    
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
            print("🎵 Audio playback started")
    
    def stop(self):
        """Stop audio playback."""
        if self.is_playing:
            self.is_playing = False
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            print("⏹️ Audio playback stopped")

# Test function
def test_audio_engine():
    """Test the audio engine with fixed-time crossfades."""
    print("\n" + "="*50)
    print("Testing AudioEngine with FIXED-TIME crossfades")
    print("="*50)
    
    # Create test file info (simulating FileManager output)
    test_ambient = ("a_test.wav", 1000, "samples/ambient/a_test.wav")
    test_rhythm = ("r_test.wav", 100, "samples/rhythm/r_test.wav")
    
    # Create dummy test files
    import os
    os.makedirs("samples/ambient", exist_ok=True)
    os.makedirs("samples/rhythm", exist_ok=True)
    
    # Create a simple sine wave for testing
    def create_test_wav(filepath, freq=440, duration=2.0):
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration))
        signal = 0.3 * np.sin(2 * np.pi * freq * t)
        stereo = np.column_stack((signal, signal))
        
        # Save as WAV
        import soundfile as sf
        sf.write(filepath, stereo, sr)
        
        # Create config file
        config_path = filepath.replace('.wav', '.txt')
        import json
        with open(config_path, 'w') as f:
            json.dump({"crossfade_ms": 1000 if "ambient" in filepath else 100}, f)
    
    create_test_wav("samples/ambient/a_test.wav", freq=220, duration=3.0)
    create_test_wav("samples/rhythm/r_test.wav", freq=440, duration=1.5)
    
    print("Created test files")
    
    # Test the engine
    engine = AudioEngine()
    
    print("\nLoading files...")
    engine.load_audio_file(test_ambient, 'ambient')
    engine.load_audio_file(test_rhythm, 'rhythm')
    
    print("\nStarting playback (5 seconds)...")
    print("You should hear two sine waves crossfading at their loop points")
    
    engine.set_volumes(0.5, 0.5)
    engine.play()
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    engine.stop()
    print("\nTest complete!")

if __name__ == "__main__":
    test_audio_engine()
