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
        
        print("Initializing FileManager...")
        # Get the project root directory (one level up from src/)
        project_root = os.path.dirname(script_dir)
        
        # Set correct paths relative to project root
        ambient_dir = os.path.join(project_root, "samples", "ambient")
        rhythm_dir = os.path.join(project_root, "samples", "rhythm")
        
        print(f"  Ambient dir: {ambient_dir}")
        print(f"  Rhythm dir: {rhythm_dir}")
        
        file_mgr = FileManager(ambient_dir=ambient_dir, rhythm_dir=rhythm_dir)
        
        print("Initializing Display...")
        display = Display(engine, file_mgr)
        
        print("Initializing MIDI Handler...")
        midi = MidiHandler(use_simulation=True)
        
        print("\nLoading test files...")
        
        # Get initial files from FileManager (returns 3-tuple)
        ambient_info = file_mgr.get_next_ambient()
        rhythm_info = file_mgr.get_next_rhythm()
        
        if ambient_info:
            filename, crossfade_ms, filepath = ambient_info
            print(f"  ✅ Ambient: {filename}")
            engine.load_audio_file(ambient_info, 'ambient')
        else:
            print("⚠️  No ambient files found!")
        
        if rhythm_info:
            filename, crossfade_ms, filepath = rhythm_info
            print(f"  ✅ Rhythm: {filename}")
            engine.load_audio_file(rhythm_info, 'rhythm')
        else:
            print("⚠️  No rhythm files found!")
        
        print("\nStarting display...")
        display.start()
        
        print("Starting playback...")
        engine.set_volumes(0.5, 0.5)  # Start at 50%/50%
        engine.play()
        
        print("\n" + "="*50)
        print("SYSTEM IS RUNNING!")
        print("="*50)
        print("\nUse A/D keys to control crossfader (Ambient ↔ Rhythm)")
        print("Press Ctrl+C to stop")
        print("="*50)
        
        # Track previous volumes for auto-load detection
        prev_ambient_vol = 0.5
        prev_rhythm_vol = 0.5
        
        # Keep running until Ctrl+C or MIDI handler says to quit
        try:
            while midi.running:
                # Read knob values and update volumes
                knob1 = midi.get_knob_percentage(1)
                
                # Convert knob1 percentage (0-100) to volumes
                # Knob at 0%: Ambient 0%, Rhythm 100%
                # Knob at 50%: Both 50%
                # Knob at 100%: Ambient 100%, Rhythm 0%
                
                ambient_vol = knob1 / 100.0  # 0.0 to 1.0
                rhythm_vol = 1.0 - ambient_vol  # Inverse
                
                # Apply some curve for smoother transition
                ambient_vol = ambient_vol ** 1.5  # Gentle curve
                rhythm_vol = rhythm_vol ** 1.5
                
                # Update engine volumes
                engine.set_volumes(ambient_vol, rhythm_vol)
                
                # Check for auto-load conditions
                if ambient_vol <= 0.1 and prev_ambient_vol > 0.1:
                    print("\n�� Ambient volume low! Loading next ambient file...")
                    next_ambient = file_mgr.get_next_ambient()
                    if next_ambient:
                        engine.load_new_ambient(next_ambient)
                
                if rhythm_vol <= 0.1 and prev_rhythm_vol > 0.1:
                    print("\n🥁 Rhythm volume low! Loading next rhythm file...")
                    next_rhythm = file_mgr.get_next_rhythm()
                    if next_rhythm:
                        engine.load_new_rhythm(next_rhythm)
                
                # Update previous volumes
                prev_ambient_vol = ambient_vol
                prev_rhythm_vol = rhythm_vol
                
                # Small delay to avoid CPU overload
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\nStopping...")
        
        # Clean up
        print("\nShutting down components...")
        display.stop()
        engine.stop()
        midi.close()
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
