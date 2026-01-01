#!/usr/bin/env python3
"""
Display module for Roland S-1 Controller
Provides terminal interface with live updates.
"""

class Display:
    """Live terminal display interface."""
    
    def __init__(self):
        print("Display initialized (stub)")
    
    def update(self, ambient_file, rhythm_file, 
               ambient_vol, rhythm_vol, fader_pos):
        """Update the display with current state."""
        print("=" * 50)
        print("ROLAND S-1 CROSSFADER (Phase 1)")
        print("=" * 50)
        print(f"Ambient: {ambient_file} ({ambient_vol}%)")
        print(f"Rhythm:  {rhythm_file} ({rhythm_vol}%)")
        print(f"Fader:   {fader_pos}%")
        print("=" * 50)
    
    def clear(self):
        """Clear the display."""
        print("\n" * 10)  # Simple clear

if __name__ == "__main__":
    print("Display module")
