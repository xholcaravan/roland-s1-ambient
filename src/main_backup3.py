#!/usr/bin/env python3
"""
Roland S-1 Ambient Controller with Delay/Reverb Effects

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
    print("WITH DELAY & REVERB EFFECTS")
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
        midi = MidiHandler(audio_engine=engine, display=display, use_simulation=True)
        
        print("\nLoading initial files...")
        
        # Get initial files from FileManager
        ambient_files = file_mgr.scan_ambient_files()
        rhythm_files = file_mgr.scan_rhythm_files()
        
        if not ambient_files:
            print("❌ ERROR: No ambient files found!")
            print(f"   Check directory: {ambient_dir}")
            print(f"   Files should be: a_*.wav with a_*.txt configs")
            return
        
        if not rhythm_files:
            print("❌ ERROR: No rhythm files found!")
            print(f"   Check directory: {rhythm_dir}")
            print(f"   Files should be: r_*.wav with r_*.txt configs")
            return
        
        print(f"✅ Found {len(ambient_files)} ambient files")
        print(f"✅ Found {len(rhythm_files)} rhythm files")
        
        # Load first files
        ambient_info = file_mgr.get_random_ambient()
        rhythm_info = file_mgr.get_random_rhythm()
        
        if ambient_info:
            filename, crossfade_ms, filepath = ambient_info
            print(f"  🎹 Ambient: {filename} (xfade: {crossfade_ms}ms)")
            engine.load_audio_file(ambient_info, 'ambient')
        else:
            print("⚠️  Failed to load ambient file!")
        
        if rhythm_info:
            filename, crossfade_ms, filepath = rhythm_info
            print(f"  🥁 Rhythm: {filename} (xfade: {crossfade_ms}ms)")
            engine.load_audio_file(rhythm_info, 'rhythm')
        else:
            print("⚠️  Failed to load rhythm file!")
        
        # Update display with initial filenames
        display.update_files(ambient_info[0] if ambient_info else None, rhythm_info[0] if rhythm_info else None)
        
        # Set initial state (100% ambient, effects off)
        engine.set_crossfader(0.0)  # 100% ambient
        engine.set_delay_amount(0.0)  # Delay off
        engine.set_reverb_amount(0.0)  # Reverb off
        
        print("\nStarting display...")
        display.start()
        
        print("Starting audio playback...")
        engine.start_playback()
        
        print("\n" + "="*50)
        print("🎵 SYSTEM IS RUNNING!")
        print("="*50)
        print("\nCONTROLS:")
        print("  Q/A: Channel crossfader (Q=↑Ambient, A=↑Rhythm)")
        print("  W/S: Delay amount (W=↑, S=↓)")
        print("  E/D: Reverb amount (E=↑, D=↓)")
        print("  ESC: Quit program")
        print("  Ctrl+C: Emergency quit")
        print("="*50)
        
        # Track previous crossfader position for auto-load detection
        prev_crossfader = 0.0
        
        # Keep running until Ctrl+C or MIDI handler says to quit
        try:
            while midi.running:
                # Check for auto-load conditions (when channel becomes silent)
                if engine.crossfader >= 0.95 and prev_crossfader < 0.95:
                    # Ambient is silent (or nearly silent), load new ambient
                    print("\n🔁 Ambient silent, loading new ambient file...")
                    next_ambient = file_mgr.get_random_ambient()
                    if next_ambient and engine.current_ambient_file != next_ambient:
                        engine.load_new_ambient(next_ambient)
                        display.update_files(next_ambient[0], rhythm_info[0] if rhythm_info else "None")
                
                elif engine.crossfader <= 0.05 and prev_crossfader > 0.05:
                    # Rhythm is silent (or nearly silent), load new rhythm
                    print("\n🔁 Rhythm silent, loading new rhythm file...")
                    next_rhythm = file_mgr.get_random_rhythm()
                    if next_rhythm and engine.current_rhythm_file != next_rhythm:
                        engine.load_new_rhythm(next_rhythm)
                        display.update_files(ambient_info[0] if ambient_info else "None", next_rhythm[0])
                
                # Update previous crossfader
                prev_crossfader = engine.crossfader
                
                # Small delay to avoid CPU overload
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received...")
        
        # Clean up
        print("\nShutting down components...")
        display.stop()
        engine.stop_playback()
        midi.cleanup()
        print("✅ System stopped gracefully.")
        
    except ImportError as e:
        print(f"\n❌ Missing module: {e}")
        print("Make sure all Python files exist in src/ directory")
        print("Try: pip install -r requirements.txt")
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
