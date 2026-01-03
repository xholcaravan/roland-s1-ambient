#!/usr/bin/env python3
"""
Real Audio Engine for Roland S-1 Controller
Now with FIXED-TIME loop crossfades (300s buffers) AND delay/reverb effects.
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time
import pedalboard  # For effects

class AudioEngine:
    """Real audio engine with fixed-time loop crossfades and effects."""
    
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
        self.ambient_volume = 1.0  # Start with 100% ambient
        self.rhythm_volume = 0.0   # Start with 0% rhythm
        
        # File info
        self.current_ambient_file = None  # (filename, crossfade_ms, filepath)
        self.current_rhythm_file = None   # (filename, crossfade_ms, filepath)
        
        # Playback state
        self.is_playing = False
        
        # === EFFECTS SYSTEM ===
        # Crossfader position (0.0 = 100% ambient, 1.0 = 100% rhythm)
        self.crossfader = 0.0
        
        # Effects amounts (0.0 to 1.0)
        self.delay_amount = 0.0  # Start with delay off
        self.reverb_amount = 0.0  # Start with reverb off
        
        # Pedalboard effects
        self.delay = pedalboard.Delay(
            delay_seconds=0.2,  # Will be updated based on knob
            feedback=0.3,       # Will be updated based on knob
            mix=0.0            # Controlled by delay_amount
        )
        
        self.reverb = pedalboard.Reverb(
            room_size=0.7,
            damping=0.5,
            wet_level=0.0,     # Controlled by reverb_amount
            dry_level=1.0
        )
        
        print(f"AudioEngine initialized: {sample_rate}Hz, buffer: {buffer_size}")
        print(f"Fixed buffer duration: {self.target_buffer_seconds}s (5min)")
        print(f"Effects system: Delay + Reverb (Pedalboard)")
    
    # ===== EFFECTS METHODS =====
    
    def set_crossfader(self, amount):
        """Set crossfader position (0.0 to 1.0) and update volumes."""
        self.crossfader = max(0.0, min(1.0, amount))
        self._update_volumes_from_crossfader()
    
    def _update_volumes_from_crossfader(self):
        """Calculate volumes based on crossfader position with x^1.5 curve."""
        # Ambient volume: fades from 1 to 0 as crossfader goes 0→1
        ambient_raw = 1.0 - self.crossfader
        self.ambient_volume = ambient_raw ** 1.5
        
        # Rhythm volume: fades from 0 to 1 as crossfader goes 0→1
        rhythm_raw = self.crossfader
        self.rhythm_volume = rhythm_raw ** 1.5
    
    def set_delay_amount(self, amount):
        """Set delay amount (0.0 to 1.0) - Roland S-1 style."""
        self.delay_amount = max(0.0, min(1.0, amount))
        self._update_delay_params()
    
    def _update_delay_params(self):
        """Update delay parameters based on knob position (Roland S-1 style)."""
        if self.delay_amount == 0:
            # Delay is off - set mix to 0
            self.delay.mix = 0.0
            return
        
        # Roland S-1 style: knob controls both time and feedback together
        if self.delay_amount <= 0.3:
            # Short delays (0-30% knob)
            self.delay.delay_seconds = 0.2  # 200ms
            self.delay.feedback = 0.3       # 30% feedback
        elif self.delay_amount <= 0.7:
            # Medium delays (31-70% knob)
            self.delay.delay_seconds = 0.4  # 400ms
            self.delay.feedback = 0.5       # 50% feedback
        else:
            # Long delays (71-100% knob)
            self.delay.delay_seconds = 0.8  # 800ms
            self.delay.feedback = 0.7       # 70% feedback
        
        # Mix follows the knob position directly
        self.delay.mix = self.delay_amount
    
    def set_reverb_amount(self, amount):
        """Set reverb amount (0.0 to 1.0)."""
        self.reverb_amount = max(0.0, min(1.0, amount))
        self._update_reverb_params()
    
    def _update_reverb_params(self):
        """Update reverb parameters based on knob position."""
        self.reverb.wet_level = self.reverb_amount
        self.reverb.dry_level = 1.0 - self.reverb_amount
    
    def _apply_effects(self, audio):
        """Apply delay and reverb effects to audio."""
        try:
            # Apply delay if active
            if self.delay_amount > 0:
                audio = self.delay.process(audio, self.sample_rate)
            
            # Apply reverb if active
            if self.reverb_amount > 0:
                audio = self.reverb.process(audio, self.sample_rate)
            
            return audio
        except Exception as e:
            print(f"Error applying effects: {e}")
            return audio
    
    # ===== ORIGINAL METHODS (updated for effects) =====
    
    def audio_callback(self, outdata, frames, time, status):
        """Callback function for real-time audio playback with crossfades AND effects."""
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
        
        # Apply effects to mixed output
        if self.delay_amount > 0 or self.reverb_amount > 0:
            output = self._apply_effects(output)
        
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
    
    # === ORIGINAL LOADING/RENDERING METHODS ===
    # These remain the same as your original code
    
    def load_audio_file(self, file_info, track='ambient'):
        """Load audio file and create pre-rendered buffer with crossfades."""
        filename, crossfade_ms, filepath = file_info
        print(f"Loading {track}: {filename} (crossfade: {crossfade_ms}ms)")
        
        try:
            # Load audio file
            audio_data, sr = sf.read(filepath, dtype=np.float32)
            
            if sr != self.sample_rate:
                print(f"Warning: File sample rate {sr}Hz doesn't match engine {self.sample_rate}Hz")
            
            # Ensure stereo
            if len(audio_data.shape) == 1:
                audio_data = np.column_stack((audio_data, audio_data))
            
            # Store original data and crossfade
            if track == 'ambient':
                self.ambient_data = audio_data
                self.ambient_crossfade_ms = crossfade_ms
                self.current_ambient_file = file_info
                # Pre-render ambient buffer
                self.ambient_buffer = self._pre_render_buffer(audio_data, crossfade_ms, track)
                self.ambient_buffer_position = 0
            else:  # rhythm
                self.rhythm_data = audio_data
                self.rhythm_crossfade_ms = crossfade_ms
                self.current_rhythm_file = file_info
                # Pre-render rhythm buffer
                self.rhythm_buffer = self._pre_render_buffer(audio_data, crossfade_ms, track)
                self.rhythm_buffer_position = 0
            
            print(f"  → Pre-rendered buffer: {len(self.ambient_buffer if track == 'ambient' else self.rhythm_buffer) / self.sample_rate:.1f}s")
            return True
            
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _pre_render_buffer(self, audio_data, crossfade_ms, track_name):
        """Create pre-rendered buffer with loop crossfades (fixed 300s length)."""
        crossfade_samples = int((crossfade_ms / 1000.0) * self.sample_rate)
        loop_length = len(audio_data)
        
        print(f"  Pre-rendering {track_name} loop:")
        print(f"    Original: {loop_length} samples ({loop_length/self.sample_rate:.2f}s)")
        print(f"    Crossfade: {crossfade_samples} samples ({crossfade_ms}ms)")
        
        # Calculate how many loops fit in 300 seconds
        target_samples = self.target_buffer_seconds * self.sample_rate
        loops_needed = int(np.ceil(target_samples / loop_length))
        
        print(f"    Loops needed for {self.target_buffer_seconds}s: {loops_needed}")
        
        # Create crossfade window (linear ramp)
        if crossfade_samples > 0:
            fade_in = np.linspace(0, 1, crossfade_samples).reshape(-1, 1)
            fade_out = np.linspace(1, 0, crossfade_samples).reshape(-1, 1)
        else:
            fade_in = np.ones((0, 1))
            fade_out = np.ones((0, 1))
        
        # Build the long buffer
        buffer_parts = []
        
        for i in range(loops_needed):
            if i == 0:
                # First loop: no crossfade at start
                buffer_parts.append(audio_data)
            else:
                # Subsequent loops: apply crossfade between end of previous and start of current
                if crossfade_samples > 0:
                    # Get the last crossfade_samples from the previous loop (in buffer_parts[-1])
                    prev_end = buffer_parts[-1][-crossfade_samples:]
                    
                    # Apply fade-out to previous end
                    prev_end_faded = prev_end * fade_out
                    
                    # Apply fade-in to current start
                    current_start = audio_data[:crossfade_samples]
                    current_start_faded = current_start * fade_in
                    
                    # Crossfaded section
                    crossfaded_section = prev_end_faded + current_start_faded
                    
                    # Replace the last crossfade_samples in buffer_parts[-1]
                    buffer_parts[-1] = np.vstack((
                        buffer_parts[-1][:-crossfade_samples],
                        crossfaded_section
                    ))
                    
                    # Add the rest of the current loop (after crossfade)
                    buffer_parts.append(audio_data[crossfade_samples:])
                else:
                    # No crossfade, just concatenate
                    buffer_parts.append(audio_data)
        
        # Combine all parts
        full_buffer = np.vstack(buffer_parts)
        
        # Trim or extend to exactly target_samples
        if len(full_buffer) > target_samples:
            full_buffer = full_buffer[:target_samples]
        elif len(full_buffer) < target_samples:
            # Repeat if needed (shouldn't happen with our calculation)
            repeats = int(np.ceil(target_samples / len(full_buffer)))
            full_buffer = np.tile(full_buffer, (repeats, 1))[:target_samples]
        
        print(f"    Final buffer: {len(full_buffer)} samples ({len(full_buffer)/self.sample_rate:.2f}s)")
        return full_buffer
    
    def load_new_ambient(self, file_info):
        """Load new ambient file (when knob hits 0%)."""
        success = self.load_audio_file(file_info, 'ambient')
        if success:
            print(f"Ambient track changed to: {file_info[0]}")
        return success
    
    def load_new_rhythm(self, file_info):
        """Load new rhythm file (when knob hits 0%)."""
        success = self.load_audio_file(file_info, 'rhythm')
        if success:
            print(f"Rhythm track changed to: {file_info[0]}")
        return success
    
    def start_playback(self):
        """Start audio playback."""
        if not self.is_playing:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=self.channels,
                dtype=np.float32,
                callback=self.audio_callback
            )
            self.stream.start()
            self.is_playing = True
            print("Audio playback started.")
    
    def stop_playback(self):
        """Stop audio playback."""
        if self.is_playing and self.stream:
            self.stream.stop()
            self.stream.close()
            self.is_playing = False
            print("Audio playback stopped.")
