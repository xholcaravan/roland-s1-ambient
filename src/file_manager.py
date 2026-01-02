#!/usr/bin/env python3
"""
File Manager for Roland S-1 Controller
Handles file scanning, crossfade config loading, and random selection.
"""

import os
import json
import random

class FileManager:
    """Manages audio files with crossfade configs."""
    
    def __init__(self, ambient_dir="samples/ambient", rhythm_dir="samples/rhythm"):
        self.ambient_dir = ambient_dir
        self.rhythm_dir = rhythm_dir
        
        # Store files with their crossfade values
        self.ambient_files = []  # List of tuples: (filename, crossfade_ms, filepath)
        self.rhythm_files = []   # Same structure
        
        # Currently loaded/queued files
        self.current_ambient = None
        self.current_rhythm = None
        self.next_ambient = None   # Pre-loaded for when channel is silent
        self.next_rhythm = None    # Pre-loaded for when channel is silent
        
        print(f"FileManager initialized:")
        print(f"  Ambient dir: {ambient_dir}")
        print(f"  Rhythm dir: {rhythm_dir}")
        
        # Scan directories on startup
        self.scan_directories()
    
    def scan_directories(self):
        """Scan ambient and rhythm directories for valid files."""
        print("\nScanning for audio files...")
        
        # Scan ambient directory
        ambient_count = self._scan_directory(self.ambient_dir, self.ambient_files, "ambient")
        
        # Scan rhythm directory  
        rhythm_count = self._scan_directory(self.rhythm_dir, self.rhythm_files, "rhythm")
        
        print(f"\n✅ Found {ambient_count} ambient files, {rhythm_count} rhythm files")
        
        # If we have files, pre-load initial ones
        if self.ambient_files:
            self.next_ambient = self._get_random_file(self.ambient_files)
        
        if self.rhythm_files:
            self.next_rhythm = self._get_random_file(self.rhythm_files)
    
    def _scan_directory(self, directory, file_list, file_type):
        """Scan a directory for .wav files with valid .txt configs."""
        if not os.path.exists(directory):
            print(f"⚠️  Directory not found: {directory}")
            return 0
        
        count = 0
        for filename in sorted(os.listdir(directory)):
            # Check for .wav files
            if filename.lower().endswith('.wav'):
                filepath = os.path.join(directory, filename)
                
                # Look for corresponding .txt config
                txt_path = filepath.replace('.wav', '.txt').replace('.WAV', '.txt')
                
                crossfade_ms = 0  # Default if no config
                has_config = False
                
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, 'r') as f:
                            config = json.load(f)
                            if 'crossfade_ms' in config:
                                crossfade_ms = config['crossfade_ms']
                                has_config = True
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"  Warning: Could not read config for {filename}: {e}")
                
                if has_config:
                    # Store file info
                    file_list.append((filename, crossfade_ms, filepath))
                    count += 1
                    print(f"  ✓ {file_type}: {filename} ({crossfade_ms}ms crossfade)")
                else:
                    print(f"  ✗ {file_type}: {filename} (no valid config)")
        
        return count
    
    def _get_random_file(self, file_list):
        """Get a random file from list."""
        if not file_list:
            return None
        
        return random.choice(file_list)  # Returns (filename, crossfade_ms, filepath)
    
    def get_next_ambient(self):
        """Get next ambient file (random selection)."""
        if not self.ambient_files:
            return None
        
        # If we have a pre-loaded next ambient, use it
        if self.next_ambient:
            self.current_ambient = self.next_ambient
        else:
            # Otherwise get a new random one
            self.current_ambient = self._get_random_file(self.ambient_files)
        
        # Pre-load the next one for future use
        self.next_ambient = self._get_random_file(self.ambient_files)
        
        return self.current_ambient
    
    def get_next_rhythm(self):
        """Get next rhythm file (random selection)."""
        if not self.rhythm_files:
            return None
        
        # If we have a pre-loaded next rhythm, use it
        if self.next_rhythm:
            self.current_rhythm = self.next_rhythm
        else:
            # Otherwise get a new random one
            self.current_rhythm = self._get_random_file(self.rhythm_files)
        
        # Pre-load the next one for future use
        self.next_rhythm = self._get_random_file(self.rhythm_files)
        
        return self.current_rhythm
    
    def get_current_ambient_info(self):
        """Get info about currently loaded ambient file."""
        if self.current_ambient:
            filename, crossfade_ms, filepath = self.current_ambient
            return {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'filepath': filepath
            }
        return None
    
    def get_current_rhythm_info(self):
        """Get info about currently loaded rhythm file."""
        if self.current_rhythm:
            filename, crossfade_ms, filepath = self.current_rhythm
            return {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'filepath': filepath
            }
        return None
    
    def get_next_ambient_info(self):
        """Get info about pre-loaded next ambient file."""
        if self.next_ambient:
            filename, crossfade_ms, filepath = self.next_ambient
            return {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'filepath': filepath
            }
        return None
    
    def get_next_rhythm_info(self):
        """Get info about pre-loaded next rhythm file."""
        if self.next_rhythm:
            filename, crossfade_ms, filepath = self.next_rhythm
            return {
                'filename': filename,
                'crossfade_ms': crossfade_ms,
                'filepath': filepath
            }
        return None
    
    def get_file_counts(self):
        """Get counts of available files."""
        return {
            'ambient': len(self.ambient_files),
            'rhythm': len(self.rhythm_files)
        }

def test_file_manager():
    """Test the file manager."""
    print("\n" + "="*50)
    print("Testing FileManager")
    print("="*50)
    
    # Create test directories if they don't exist
    os.makedirs("samples/ambient", exist_ok=True)
    os.makedirs("samples/rhythm", exist_ok=True)
    
    # Create some test files
    test_files = [
        ("samples/ambient/a_pad_c.wav", "samples/ambient/a_pad_c.txt", '{"crossfade_ms": 1000}'),
        ("samples/ambient/a_drone_d.wav", "samples/ambient/a_drone_d.txt", '{"crossfade_ms": 500}'),
        ("samples/rhythm/r_beat_1.wav", "samples/rhythm/r_beat_1.txt", '{"crossfade_ms": 50}'),
        ("samples/rhythm/r_beat_2.wav", "samples/rhythm/r_beat_2.txt", '{"crossfade_ms": 100}'),
    ]
    
    for wav_path, txt_path, txt_content in test_files:
        # Create dummy WAV file (just empty)
        with open(wav_path, 'wb') as f:
            f.write(b'WAV dummy')
        
        # Create config file
        with open(txt_path, 'w') as f:
            f.write(txt_content)
    
    print("Created test files")
    
    # Test the file manager
    fm = FileManager()
    
    print("\n" + "="*50)
    print("Getting random files...")
    
    ambient = fm.get_next_ambient()
    rhythm = fm.get_next_rhythm()
    
    if ambient:
        filename, crossfade_ms, filepath = ambient
        print(f"Ambient: {filename} ({crossfade_ms}ms crossfade)")
    
    if rhythm:
        filename, crossfade_ms, filepath = rhythm
        print(f"Rhythm: {filename} ({crossfade_ms}ms crossfade)")
    
    print("\nGetting next queued files...")
    
    next_ambient = fm.get_next_ambient_info()
    next_rhythm = fm.get_next_rhythm_info()
    
    if next_ambient:
        print(f"Next ambient: {next_ambient['filename']}")
    
    if next_rhythm:
        print(f"Next rhythm: {next_rhythm['filename']}")
    
    print("\nFile counts:", fm.get_file_counts())
    print("="*50)

if __name__ == "__main__":
    test_file_manager()
