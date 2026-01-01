#!/usr/bin/env python3
"""
File Manager for Roland S-1 Controller
Handles file selection, play tracking, and pre-loading.
"""

class FileManager:
    """Manages audio files and selection logic."""
    
    def __init__(self, ambient_dir, rhythm_dir):
        self.ambient_dir = ambient_dir
        self.rhythm_dir = rhythm_dir
        print(f"FileManager initialized with:")
        print(f"  Ambient dir: {ambient_dir}")
        print(f"  Rhythm dir: {rhythm_dir}")
    
    def get_next_ambient(self):
        """Get next ambient file (least-played-first)."""
        print("Would get next ambient file")
        return "ambient_stub.wav"
    
    def get_next_rhythm(self):
        """Get next rhythm file (least-played-first)."""
        print("Would get next rhythm file")
        return "rhythm_stub.wav"

if __name__ == "__main__":
    print("File Manager module")
