#!/usr/bin/env python3
"""
Display module for Roland S-1 Controller
Now shows crossfade values and next queued files.
"""

import os

class Display:
    """Live terminal display interface with crossfade info."""
    
    def __init__(self):
        self.clear()
        print("Display initialized with crossfade support")
    
    def update(self, ambient_info, rhythm_info, 
               next_ambient_info, next_rhythm_info,
               ambient_vol, rhythm_vol, fader_pos):
        """Update the display with current state."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*60)
        print("ROLAND S-1 CROSSFADER (Phase 1 - Loop Crossfade Enabled)")
        print("="*60)
        
        # Ambient channel
        if ambient_info:
            vol_bar = self._volume_bar(ambient_vol)
            print(f"AMBIENT (A):")
            print(f"  File:    {ambient_info.get('filename', 'None')}")
            print(f"  Crossfade: {ambient_info.get('crossfade_ms', 0)}ms")
            print(f"  Volume:  {vol_bar} {int(ambient_vol*100)}%")
        else:
            print(f"AMBIENT (A): No file loaded")
        
        # Rhythm channel  
        if rhythm_info:
            vol_bar = self._volume_bar(rhythm_vol)
            print(f"\nRHYTHM (R):")
            print(f"  File:    {rhythm_info.get('filename', 'None')}")
            print(f"  Crossfade: {rhythm_info.get('crossfade_ms', 0)}ms")
            print(f"  Volume:  {vol_bar} {int(rhythm_vol*100)}%")
        else:
            print(f"\nRHYTHM (R): No file loaded")
        
        # Next queued files
        print("\n" + "-"*60)
        print("NEXT QUEUED (load when channel silent):")
        
        if next_ambient_info:
            print(f"  Next A: {next_ambient_info.get('filename', 'None')}")
        else:
            print(f"  Next A: None")
            
        if next_rhythm_info:
            print(f"  Next R: {next_rhythm_info.get('filename', 'None')}")
        else:
            print(f"  Next R: None")
        
        # Fader position
        print("\n" + "-"*60)
        print("CROSSFADER (Knob 1):")
        
        # Visual fader
        fader_width = 30
        a_pos = int(fader_pos * fader_width / 100)
        r_pos = fader_width - a_pos
        
        fader_display = "A" + "="*a_pos + "|" + "="*r_pos + "R"
        print(f"  Position: {fader_display} {fader_pos}%")
        
        # Status message
        if fader_pos == 0:
            print(f"  Status: A only → R will load new file")
        elif fader_pos == 100:
            print(f"  Status: R only → A will load new file")
        elif fader_pos < 40:
            print(f"  Status: A dominant ({100-fader_pos}% A, {fader_pos}% R)")
        elif fader_pos > 60:
            print(f"  Status: R dominant ({100-fader_pos}% A, {fader_pos}% R)")
        else:
            print(f"  Status: Balanced ({100-fader_pos}% A, {fader_pos}% R)")
        
        print("\n" + "="*60)
        print("CONTROLS: A/D=Crossfader  W/S=Knob2  I/K=Knob3  O/L=Knob4")
        print("          R=Reset knobs   Q=Quit")
        print("="*60)
    
    def _volume_bar(self, volume):
        """Create a visual volume bar."""
        bar_length = 20
        filled = int(volume * bar_length)
        return "█" * filled + "░" * (bar_length - filled)
    
    def clear(self):
        """Clear the display."""
        print("\n" * 3)

if __name__ == "__main__":
    # Test the display
    print("Testing Display module...")
    
    display = Display()
    
    test_ambient = {
        'filename': 'a_pad_c.wav',
        'crossfade_ms': 1000,
        'volume': 0.7
    }
    
    test_rhythm = {
        'filename': 'r_beat_1.wav',
        'crossfade_ms': 50,
        'volume': 0.3
    }
    
    test_next_ambient = {
        'filename': 'a_drone_d.wav',
        'crossfade_ms': 500
    }
    
    test_next_rhythm = {
        'filename': 'r_beat_2.wav', 
        'crossfade_ms': 100
    }
    
    display.update(
        ambient_info=test_ambient,
        rhythm_info=test_rhythm,
        next_ambient_info=test_next_ambient,
        next_rhythm_info=test_next_rhythm,
        ambient_vol=0.7,
        rhythm_vol=0.3,
        fader_pos=70  # 70% towards R
    )
    
    print("\nDisplay test complete!")
