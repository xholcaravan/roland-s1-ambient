#!/usr/bin/env python3
"""
Convert WAV files to MP3 (192kbps) for testing.
"""

import os
from pathlib import Path
from pydub import AudioSegment

def convert_directory(wav_dir, mp3_dir):
    """Convert all WAV files in directory to MP3."""
    wav_path = Path(wav_dir)
    mp3_path = Path(mp3_dir)
    
    mp3_path.mkdir(exist_ok=True)
    
    for wav_file in wav_path.glob("*.wav"):
        mp3_file = mp3_path / f"{wav_file.stem}.mp3"
        
        print(f"Converting: {wav_file.name} -> {mp3_file.name}")
        
        try:
            audio = AudioSegment.from_wav(str(wav_file))
            audio.export(str(mp3_file), format="mp3", bitrate="192k")
            print(f"  ✓ Done")
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    # Convert ambient files
    print("Converting ambient files...")
    convert_directory("../samples/ambient", "../samples/ambient_mp3")
    
    print("\nConverting rhythm files...")
    convert_directory("../samples/rhythm", "../samples/rhythm_mp3")
    
    print("\nDone!")
