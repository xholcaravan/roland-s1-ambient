#!/usr/bin/env python3
import os
import sys

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
sys.path.insert(0, src_dir)

from file_manager import FileManager

# Test with REAL directories
project_root = script_dir
ambient_dir = os.path.join(project_root, "samples", "ambient")
rhythm_dir = os.path.join(project_root, "samples", "rhythm")

print("Testing FileManager with REAL files...")
print(f"Ambient dir: {ambient_dir}")
print(f"Rhythm dir: {rhythm_dir}")

fm = FileManager(ambient_dir=ambient_dir, rhythm_dir=rhythm_dir)

print(f"\nFound {len(fm.ambient_files)} ambient files:")
for filename, crossfade_ms, filepath in fm.ambient_files:
    print(f"  - {filename} ({crossfade_ms}ms)")

print(f"\nFound {len(fm.rhythm_files)} rhythm files:")
for filename, crossfade_ms, filepath in fm.rhythm_files:
    print(f"  - {filename} ({crossfade_ms}ms)")

# Get random files
ambient = fm.get_next_ambient()
rhythm = fm.get_next_rhythm()

if ambient:
    filename, crossfade_ms, filepath = ambient
    print(f"\nRandom ambient selected: {filename} ({crossfade_ms}ms)")
else:
    print("\nNo ambient files found!")

if rhythm:
    filename, crossfade_ms, filepath = rhythm
    print(f"Random rhythm selected: {filename} ({crossfade_ms}ms)")
else:
    print("No rhythm files found!")
