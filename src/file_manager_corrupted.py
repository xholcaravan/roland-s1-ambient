#!/usr/bin/env python3
"""
File Manager for Roland S-1 Controller
Handles scanning and selection of audio files with crossfade configs.
"""

import os
import random
from pathlib import Path

class FileManager:
    """Manages audio files and their crossfade configurations."""
    
    def __init__(self, ambient_dir=None, rhythm_dir=None):
        self.ambient_dir = Path(ambient_dir) if ambient_dir else None
        self.rhythm_dir = Path(rhythm_dir) if rhythm_dir else None
        
        # Cache of available files
        self.ambient_files = []  # List of tuples: (filename, crossfade_ms, filepath)
        self.rhythm_files = []   # List of tuples: (filename, crossfade_ms, filepath)
        
        # Cache for next files (for auto-loading)
        self.next_ambient = None
        self.next_rhythm = None
        
        print("FileManager initialized")
        if ambient_dir:
            print(f"  Ambient: {ambient_dir}")
        if rhythm_dir:
            print(f"  Rhythm: {rhythm_dir}")
    
    def scan_ambient_files(self):
        """Scan for ambient files and their crossfade configs."""
        self.ambient_files = []
        
        if not self.ambient_dir or not self.ambient_dir.exists():
            print(f"⚠️ Warning: Ambient path not found: {self.ambient_dir}")
            return []
        
        print(f"Scanning ambient files in: {self.ambient_dir}")
        
        # Use more flexible pattern matching
        for wav_file in self.ambient_dir.glob("*.wav"):
            if not wav_file.name.startswith(('a_', 'a ')):  # Skip non-ambient files
                continue
                
            txt_file = wav_file.with_suffix('.txt')
            filename = wav_file.name
            
            if txt_file.exists():
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        # Look for crossfade_ms in the file
                        if "crossfade_ms=" in content:
                            # Extract the crossfade value
                            for line in content.split('\n'):
                                if line.strip().startswith("crossfade_ms="):
                                    crossfade_str = line.split('=')[1].strip()
                                    crossfade_ms = int(crossfade_str)
                                    self.ambient_files.append((filename, crossfade_ms, str(wav_file)))
                                    print(f"  ✅ {filename[:30]:30} (xfade: {crossfade_ms:4}ms)")
                                    break
                except Exception as e:
                    print(f"  ❌ Error reading {txt_file.name}: {e}")
            else:
                print(f"  ⚠️ No config file for {filename[:30]}...")
        
        print(f"Found {len(self.ambient_files)} ambient files with configs")
        return self.ambient_files
    
    def scan_rhythm_files(self):
        """Scan for rhythm files and their crossfade configs."""
        self.rhythm_files = []
        
        if not self.rhythm_dir or not self.rhythm_dir.exists():
            print(f"⚠️ Warning: Rhythm path not found: {self.rhythm_dir}")
            return []
        
        print(f"Scanning rhythm files in: {self.rhythm_dir}")
        
        # Use more flexible pattern matching
        for wav_file in self.rhythm_dir.glob("*.wav"):
            if not wav_file.name.startswith(('r_', 'r ')):  # Skip non-rhythm files
                continue
                
            txt_file = wav_file.with_suffix('.txt')
            filename = wav_file.name
            
            if txt_file.exists():
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        # Look for crossfade_ms in the file
                        if "crossfade_ms=" in content:
                            # Extract the crossfade value
                            for line in content.split('\n'):
                                if line.strip().startswith("crossfade_ms="):
                                    crossfade_str = line.split('=')[1].strip()
                                    crossfade_ms = int(crossfade_str)
                                    self.rhythm_files.append((filename, crossfade_ms, str(wav_file)))
                                    print(f"  ✅ {filename[:30]:30} (xfade: {crossfade_ms:4}ms)")
                                    break
                except Exception as e:
                    print(f"  ❌ Error reading {txt_file.name}: {e}")
            else:
                print(f"  ⚠️ No config file for {filename[:30]}...")
        
        print(f"Found {len(self.rhythm_files)} rhythm files with configs")
        return self.rhythm_files
    
    def get_random_ambient(self):
        """Get a random ambient file with its crossfade value."""
        if not self.ambient_files:
            self.scan_ambient_files()
        
        if not self.ambient_files:
            return None
        
        return random.choice(self.ambient_files)
    
    def get_random_rhythm(self):
        """Get a random rhythm file with its crossfade value."""
        if not self.rhythm_files:
            self.scan_rhythm_files()
        
        if not self.rhythm_files:
            return None
        
        return random.choice(self.rhythm_files)
    
    # Legacy methods for compatibility
    def get_next_ambient(self):
        """Legacy method - alias for get_random_ambient."""
        return self.get_random_ambient()
    
    def get_next_rhythm(self):
        """Legacy method - alias for get_random_rhythm."""
        return self.get_random_rhythm()
    
    def get_next_ambient_info(self):
        """Get info about next ambient file (for display)."""
        if not self.ambient_files:
            return None
        
        if not self.next_ambient:
            self.next_ambient = self.get_random_ambient()
        
        return self.next_ambient
    
    def get_next_rhythm_info(self):
        """Get info about next rhythm file (for display)."""
        if not self.rhythm_files:
            return None
        
        if not self.next_rhythm:
            self.next_rhythm = self.get_random_rhythm()
        
        return self.next_rhythm
    
    def get_all_ambient_filenames(self):
        """Get just the filenames of ambient files."""
        return [filename for filename, _, _ in self.ambient_files]
    
    def get_all_rhythm_filenames(self):
        """Get just the filenames of rhythm files."""
        return [filename for filename, _, _ in self.rhythm_files]
EOF# Update the file_manager.py to handle your file naming pattern
cat > /home/nando/Music/Software/roland-s1-ambient/src/file_manager.py << 'EOF'
#!/usr/bin/env python3
"""
File Manager for Roland S-1 Controller
Handles scanning and selection of audio files with crossfade configs.
"""

import os
import random
from pathlib import Path

class FileManager:
    """Manages audio files and their crossfade configurations."""
    
    def __init__(self, ambient_dir=None, rhythm_dir=None):
        self.ambient_dir = Path(ambient_dir) if ambient_dir else None
        self.rhythm_dir = Path(rhythm_dir) if rhythm_dir else None
        
        # Cache of available files
        self.ambient_files = []  # List of tuples: (filename, crossfade_ms, filepath)
        self.rhythm_files = []   # List of tuples: (filename, crossfade_ms, filepath)
        
        # Cache for next files (for auto-loading)
        self.next_ambient = None
        self.next_rhythm = None
        
        print("FileManager initialized")
        if ambient_dir:
            print(f"  Ambient: {ambient_dir}")
        if rhythm_dir:
            print(f"  Rhythm: {rhythm_dir}")
    
    def scan_ambient_files(self):
        """Scan for ambient files and their crossfade configs."""
        self.ambient_files = []
        
        if not self.ambient_dir or not self.ambient_dir.exists():
            print(f"⚠️ Warning: Ambient path not found: {self.ambient_dir}")
            return []
        
        print(f"Scanning ambient files in: {self.ambient_dir}")
        
        # Use more flexible pattern matching
        for wav_file in self.ambient_dir.glob("*.wav"):
            if not wav_file.name.startswith(('a_', 'a ')):  # Skip non-ambient files
                continue
                
            txt_file = wav_file.with_suffix('.txt')
            filename = wav_file.name
            
            if txt_file.exists():
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        # Look for crossfade_ms in the file
                        if "crossfade_ms=" in content:
                            # Extract the crossfade value
                            for line in content.split('\n'):
                                if line.strip().startswith("crossfade_ms="):
                                    crossfade_str = line.split('=')[1].strip()
                                    crossfade_ms = int(crossfade_str)
                                    self.ambient_files.append((filename, crossfade_ms, str(wav_file)))
                                    print(f"  ✅ {filename[:30]:30} (xfade: {crossfade_ms:4}ms)")
                                    break
                except Exception as e:
                    print(f"  ❌ Error reading {txt_file.name}: {e}")
            else:
                print(f"  ⚠️ No config file for {filename[:30]}...")
        
        print(f"Found {len(self.ambient_files)} ambient files with configs")
        return self.ambient_files
    
    def scan_rhythm_files(self):
        """Scan for rhythm files and their crossfade configs."""
        self.rhythm_files = []
        
        if not self.rhythm_dir or not self.rhythm_dir.exists():
            print(f"⚠️ Warning: Rhythm path not found: {self.rhythm_dir}")
            return []
        
        print(f"Scanning rhythm files in: {self.rhythm_dir}")
        
        # Use more flexible pattern matching
        for wav_file in self.rhythm_dir.glob("*.wav"):
            if not wav_file.name.startswith(('r_', 'r ')):  # Skip non-rhythm files
                continue
                
            txt_file = wav_file.with_suffix('.txt')
            filename = wav_file.name
            
            if txt_file.exists():
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        # Look for crossfade_ms in the file
                        if "crossfade_ms=" in content:
                            # Extract the crossfade value
                            for line in content.split('\n'):
                                if line.strip().startswith("crossfade_ms="):
                                    crossfade_str = line.split('=')[1].strip()
                                    crossfade_ms = int(crossfade_str)
                                    self.rhythm_files.append((filename, crossfade_ms, str(wav_file)))
                                    print(f"  ✅ {filename[:30]:30} (xfade: {crossfade_ms:4}ms)")
                                    break
                except Exception as e:
                    print(f"  ❌ Error reading {txt_file.name}: {e}")
            else:
                print(f"  ⚠️ No config file for {filename[:30]}...")
        
        print(f"Found {len(self.rhythm_files)} rhythm files with configs")
        return self.rhythm_files
    
    def get_random_ambient(self):
        """Get a random ambient file with its crossfade value."""
        if not self.ambient_files:
            self.scan_ambient_files()
        
        if not self.ambient_files:
            return None
        
        return random.choice(self.ambient_files)
    
    def get_random_rhythm(self):
        """Get a random rhythm file with its crossfade value."""
        if not self.rhythm_files:
            self.scan_rhythm_files()
        
        if not self.rhythm_files:
            return None
        
        return random.choice(self.rhythm_files)
    
    # Legacy methods for compatibility
    def get_next_ambient(self):
        """Legacy method - alias for get_random_ambient."""
        return self.get_random_ambient()
    
    def get_next_rhythm(self):
        """Legacy method - alias for get_random_rhythm."""
        return self.get_random_rhythm()
    
    def get_next_ambient_info(self):
        """Get info about next ambient file (for display)."""
        if not self.ambient_files:
            return None
        
        if not self.next_ambient:
            self.next_ambient = self.get_random_ambient()
        
        return self.next_ambient
    
    def get_next_rhythm_info(self):
        """Get info about next rhythm file (for display)."""
        if not self.rhythm_files:
            return None
        
        if not self.next_rhythm:
            self.next_rhythm = self.get_random_rhythm()
        
        return self.next_rhythm
    
    def get_all_ambient_filenames(self):
        """Get just the filenames of ambient files."""
        return [filename for filename, _, _ in self.ambient_files]
    
    def get_all_rhythm_filenames(self):
        """Get just the filenames of rhythm files."""
        return [filename for filename, _, _ in self.rhythm_files]
