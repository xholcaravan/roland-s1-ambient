#!/usr/bin/env python3
"""
Display module for Roland S-1 Controller
Shows volume levels, current files, crossfade info in a nice UI.
"""

import os
import time
import threading
from datetime import datetime

class Display:
    """Handles display output for the controller."""
    
    def __init__(self, audio_engine=None, file_manager=None):
        self.audio_engine = audio_engine
        self.file_manager = file_manager
        self.running = False
        self.display_thread = None
        
        # Display state
        self.last_update = time.time()
        self.update_interval = 0.1  # Update every 100ms
        
        print("Display initialized")
    
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
    
    def render_display(self):
        """Render the main display."""
        # Get current time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        
        # Get audio engine info
        ambient_info = rhythm_info = None
        if self.audio_engine:
            ambient_info, rhythm_info = self.audio_engine.get_current_files_info()
        
        # Get file manager info
        next_ambient = next_rhythm = None
        if self.file_manager:
            next_ambient = self.file_manager.get_next_ambient_info()
            next_rhythm = self.file_manager.get_next_rhythm_info()
        
        print("\n" + "="*60)
        print("🎹 ROLAND S-1 AMBIENT/RHYTHM CONTROLLER")
        print(f"⏰ {current_time}")
        print("="*60)
        
        # Volume bars
        print("\n🎚️  VOLUME LEVELS:")
        if self.audio_engine:
            self._draw_volume_bar("AMBIENT", self.audio_engine.ambient_volume, "🎹")
            self._draw_volume_bar("RHYTHM", self.audio_engine.rhythm_volume, "🥁")
        else:
            print("  🎹 AMBIENT: No audio engine")
            print("  🥁 RHYTHM: No audio engine")
        
        print("\n" + "-"*60)
        
        # Currently playing
        print("🎵 NOW PLAYING:")
        
        if ambient_info:
            filename = ambient_info['filename']
            crossfade = ambient_info['crossfade_ms']
            volume = ambient_info['volume']
            
            # Remove prefix and extension for display
            display_name = filename[2:] if filename.startswith(('a_', 'r_')) else filename
            display_name = os.path.splitext(display_name)[0]
            
            print(f"  �� AMBIENT: {display_name}")
            print(f"    📊 Volume: {volume*100:.0f}%  |  🔄 Crossfade: {crossfade}ms")
        else:
            print("  🎹 AMBIENT: No file loaded")
        
        if rhythm_info:
            filename = rhythm_info['filename']
            crossfade = rhythm_info['crossfade_ms']
            volume = rhythm_info['volume']
            
            # Remove prefix and extension for display
            display_name = filename[2:] if filename.startswith(('a_', 'r_')) else filename
            display_name = os.path.splitext(display_name)[0]
            
            print(f"  🥁 RHYTHM: {display_name}")
            print(f"    📊 Volume: {volume*100:.0f}%  |  🔄 Crossfade: {crossfade}ms")
        else:
            print("  🥁 RHYTHM: No file loaded")
        
        print("\n" + "-"*60)
        
        # Next in queue
        print("⏭️  NEXT IN QUEUE:")
        
        if next_ambient:
            next_name = next_ambient['filename'][2:] if next_ambient['filename'].startswith('a_') else next_ambient['filename']
            next_name = os.path.splitext(next_name)[0]
            print(f"  🎹 Next ambient: {next_name}")
        else:
            print("  🎹 Next ambient: None")
        
        if next_rhythm:
            next_name = next_rhythm['filename'][2:] if next_rhythm['filename'].startswith('r_') else next_rhythm['filename']
            next_name = os.path.splitext(next_name)[0]
            print(f"  🥁 Next rhythm: {next_name}")
        else:
            print("  🥁 Next rhythm: None")
        
        print("\n" + "-"*60)
        
        # Status
        if self.audio_engine:
            status = "▶️ PLAYING" if self.audio_engine.is_playing else "⏸️ PAUSED"
            print(f"STATUS: {status}")
        else:
            print("STATUS: No audio engine")
        
        # Controls reminder
        print("\n" + "="*60)
        print("CONTROLS:")
        print("  • Use MIDI controller to adjust volumes")
        print("  • When volume hits 0%, next file loads automatically")
        print("  • Ctrl+C to quit")
        print("="*60)
    
    def _draw_volume_bar(self, label, volume, icon):
        """Draw a volume bar."""
        bar_length = 40
        filled_length = int(volume * bar_length)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        percentage = volume * 100
        
        # Add color indicator
        if percentage >= 80:
            color_indicator = "🔴"
        elif percentage >= 50:
            color_indicator = "🟡"
        else:
            color_indicator = "🟢"
        
        print(f"  {icon} {label}: {color_indicator} [{bar}] {percentage:3.0f}%")
    
    def update(self):
        """Force an immediate display update."""
        self.clear_screen()
        self.render_display()

def test_display():
    """Test the display module."""
    print("\n" + "="*60)
    print("Testing Display Module")
    print("="*60)
    
    # Mock objects for testing
    class MockAudioEngine:
        def __init__(self):
            self.ambient_volume = 0.7
            self.rhythm_volume = 0.3
            self.is_playing = True
        
        def get_current_files_info(self):
            ambient_info = {
                'filename': 'a_Azaleas - Wangjaesan light music band.wav',
                'crossfade_ms': 1000,
                'volume': 0.7
            }
            rhythm_info = {
                'filename': 'r_Are We Living Like in Those Days - Pochonbo Electronic Ensemble.wav',
                'crossfade_ms': 100,
                'volume': 0.3
            }
            return ambient_info, rhythm_info
    
    class MockFileManager:
        def get_next_ambient_info(self):
            return {
                'filename': 'a_Dancing Dolls.wav',
                'crossfade_ms': 500,
                'filepath': 'samples/ambient/a_Dancing Dolls.wav'
            }
        
        def get_next_rhythm_info(self):
            return {
                'filename': 'r_Ecstasy.wav',
                'crossfade_ms': 50,
                'filepath': 'samples/rhythm/r_Ecstasy.wav'
            }
    
    # Create display
    mock_engine = MockAudioEngine()
    mock_fm = MockFileManager()
    display = Display(mock_engine, mock_fm)
    
    # Render once
    display.render_display()
    
    print("\nDisplay test complete!")
    print("="*60)

if __name__ == "__main__":
    test_display()
