#!/usr/bin/env python3
"""
Roland S-1 Ambient/Rhythm Controller
Phase 1: Auto-Loading Crossfader

Main entry point for the application.
"""

import sys
import os
import time
import signal

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down...")
    sys.exit(0)

def main():
    print("🎹 Roland S-1 Ambient/Rhythm Controller")
    print("=" * 50)
    print("Phase 1: Auto-Loading Crossfader")
    print("=" * 50)
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Add src directory to Python path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    
    print("\nInitializing components...")
    
    try:
        # Import components
        from audio_engine import AudioEngine
        from file_manager import FileManager
        from display import Display
        from midi_handler import MidiHandler
        
        print("✅ All modules imported successfully")
        
        # Initialize components
        print("\nInitializing AudioEngine...")
        engine = AudioEngine()
        
        print("Loading test files...")
        engine.load_audio_file("samples/ambient/a_pad_c.wav", 'ambient')
        engine.load_audio_file("samples/rhythm/r_beat_1.wav", 'rhythm')
        
        print("Starting playback...")
        engine.set_volumes(0.7, 0.3)  # 70% ambient, 30% rhythm
        engine.play()
        
        print("\n" + "="*50)
        print("SYSTEM IS RUNNING!")
        print("="*50)
        print("\nYou should hear:")
        print("  • Ambient pad (C note)")
        print("  • Rhythm beat pattern")
        print("\nPress Ctrl+C to stop")
        print("="*50)
        
        # Keep running until Ctrl+C
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
        
        # Clean up
        engine.stop()
        print("System stopped.")
        
    except ImportError as e:
        print(f"\n❌ Missing module: {e}")
        print("Make sure all Python files exist in src/ directory")
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
