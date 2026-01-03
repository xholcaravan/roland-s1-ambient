#!/usr/bin/env python3
"""
Display module for Roland S-1 Controller
Now includes delay/reverb effects display.
"""

import os
import time
import threading
from datetime import datetime
import soundfile as sf  # Add this to get audio duration

class Display:
    """Handles display output for the controller."""
    
    def __init__(self, audio_engine=None, file_manager=None):
        self.audio_engine = audio_engine
        self.file_manager = file_manager
        self.running = False
        self.display_thread = None
        
        # Cache for file durations to avoid reading files every frame
        self.duration_cache = {}
        
        # Display state for effects
        self.crossfader = 0.0
        self.delay_amount = 0.0
        self.reverb_amount = 0.0
        self.ambient_volume = 1.0
        self.rhythm_volume = 0.0
        
        # Store current filenames
        self.current_ambient_filename = "None"
        self.current_rhythm_filename = "None"
        
        self.last_update = time.time()
        self.update_interval = 0.1  # Update every 100ms
        
        print("Display initialized (with effects)")
    
    # ===== UPDATE METHODS =====
    
    def update_crossfader(self, value):
        self.crossfader = value
    
    def update_delay(self, value):
        self.delay_amount = value
    
    def update_reverb(self, value):
        self.reverb_amount = value
    
    def update_volumes(self, ambient_vol, rhythm_vol):
        self.ambient_volume = ambient_vol
        self.rhythm_volume = rhythm_vol
    
    def update_files(self, ambient_filename, rhythm_filename):
        """Update the current filenames for display."""
        self.current_ambient_filename = ambient_filename[:30] if ambient_filename else "None"
        self.current_rhythm_filename = rhythm_filename[:30] if rhythm_filename else "None"
    
    # ===== DISPLAY METHODS =====
    
    def start(self):
        """Start the display thread."""
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        print("Display started")
    
    def stop(self):
        """Stop the display thread."""
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
        print("Display stopped")
    
    def _display_loop(self):
        """Main display update loop."""
        while self.running:
            self.clear_screen()
            self.render_display()
            time.sleep(self.update_interval)
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_audio_duration(self, filepath):
        """Get duration of audio file in seconds, with caching."""
        if filepath in self.duration_cache:
            return self.duration_cache[filepath]
        
        try:
            with sf.SoundFile(filepath) as f:
                duration = len(f) / f.samplerate
                self.duration_cache[filepath] = duration
                return duration
        except:
            return 0.0
    
    def format_duration(self, seconds):
        """Format duration as seconds with 1 decimal place."""
        return f"{seconds:.1f}s"
    
    def _draw_progress_bar(self, value, width=20):
        """Draw a progress bar for values 0-1."""
        filled = int(value * width)
        bar = '█' * filled + '░' * (width - filled)
        percentage = int(value * 100)
        return f"[{bar}] {percentage:3d}%"
    
    def _draw_crossfader_bar(self, value, width=30):
        """Draw a crossfader visualization."""
        pos = int(value * (width - 1))
        bar = ' ' * pos + '█' + ' ' * (width - pos - 1)
        return f"A ◄─{bar}► R"
    
    def _draw_volume_bar(self, label, volume, icon="🎹"):
        """Draw a volume bar with icon."""
        bar = self._draw_progress_bar(volume)
        print(f"  {icon} {label:10} {bar}")
    
    def get_delay_description(self, amount):
        """Get description of current delay settings."""
        if amount == 0:
            return "OFF"
        elif amount <= 0.3:
            return f"SHORT ({int(amount*100)}%)"
        elif amount <= 0.7:
            return f"MEDIUM ({int(amount*100)}%)"
        else:
            return f"LONG ({int(amount*100)}%)"
    
    def render_display(self):
        """Render the main display."""
        # Get current time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        
        # Get audio engine info
        ambient_duration = rhythm_duration = 0
        if self.audio_engine:
            # Try to get durations if files are loaded
            if hasattr(self.audio_engine, 'current_ambient_file') and self.audio_engine.current_ambient_file:
                _, _, ambient_path = self.audio_engine.current_ambient_file
                ambient_duration = self.get_audio_duration(ambient_path)
            
            if hasattr(self.audio_engine, 'current_rhythm_file') and self.audio_engine.current_rhythm_file:
                _, _, rhythm_path = self.audio_engine.current_rhythm_file
                rhythm_duration = self.get_audio_duration(rhythm_path)
        
        # Terminal width
        terminal_width = 80
        
        # Build display
        lines = []
        lines.append("┌" + "─" * (terminal_width - 2) + "┐")
        lines.append(f"│ 🎹 ROLAND S-1 AMBIENT ENGINE  ⏰ {current_time}".ljust(terminal_width - 2) + "│")
        lines.append("├" + "─" * (terminal_width - 2) + "┤")
        
        # Currently playing files - use stored filenames
        ambient_name = self.current_ambient_filename
        rhythm_name = self.current_rhythm_filename
        
        # Ambient track
        amb_bar = self._draw_progress_bar(self.ambient_volume)
        lines.append(f"│ AMBIENT:  {ambient_name:30} {amb_bar:25} │")
        
        # Rhythm track
        rhy_bar = self._draw_progress_bar(self.rhythm_volume)
        lines.append(f"│ RHYTHM:   {rhythm_name:30} {rhy_bar:25} │")
        
        lines.append("│" + " " * (terminal_width - 2) + "│")
        
        # Crossfader
        fader_bar = self._draw_crossfader_bar(self.crossfader)
        lines.append(f"│ CROSSFADE: {fader_bar}".ljust(terminal_width - 2) + "│")
        
        # Delay
        delay_desc = self.get_delay_description(self.delay_amount)
        delay_bar = self._draw_progress_bar(self.delay_amount)
        lines.append(f"│ DELAY:    {delay_desc:15} {delay_bar:25} │")
        
        # Reverb
        reverb_bar = self._draw_progress_bar(self.reverb_amount)
        reverb_percent = int(self.reverb_amount * 100)
        lines.append(f"│ REVERB:   {reverb_percent:3}%{' ':12} {reverb_bar:25} │")
        
        lines.append("│" + " " * (terminal_width - 2) + "│")
        
        # File info (if available)
        if ambient_duration > 0 or rhythm_duration > 0:
            lines.append(f"│ DURATION: Ambient={self.format_duration(ambient_duration):6}  Rhythm={self.format_duration(rhythm_duration):6}".ljust(terminal_width - 2) + "│")
        
        # Crossfade info (if available)
        if hasattr(self.audio_engine, 'ambient_crossfade_ms') and self.audio_engine.ambient_crossfade_ms:
            lines.append(f"│ LOOP XFADE: A={self.audio_engine.ambient_crossfade_ms:4}ms  R={self.audio_engine.rhythm_crossfade_ms:4}ms".ljust(terminal_width - 2) + "│")
        
        lines.append("│" + " " * (terminal_width - 2) + "│")
        
        # Controls reminder
        controls = "CONTROLS: Q=↑A A=↑R W/S=Delay E/D=Reverb ESC=Quit"
        lines.append(f"│ {controls}".ljust(terminal_width - 2) + "│")
        
        lines.append("└" + "─" * (terminal_width - 2) + "┘")
        
        # Print everything
        print("\n".join(lines))
    
    def render(self):
        """Render display (for manual updates from midi_handler)."""
        self.clear_screen()
        self.render_display()
