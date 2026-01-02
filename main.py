#!/usr/bin/env python3
"""
Roland S-1 Ambient/Rhythm Controller
Phase 1: Auto-Loading Crossfader with Loop Crossfades

Main entry point - now integrates loop crossfades from .txt configs.
"""

import sys
import os
import time
import signal
import termios
import tty

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down...")
    sys.exit(0)

def main():
    print("🎹 Roland S-1 Ambient/Rhythm Controller")
    print("=" * 50)
    print("Phase 1: Auto-Loading Crossfader with Loop Crossfades")
    print("=" * 50)
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Add src directory to Python path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    
    print("\nInitializing components...")
    
    # Store terminal settings for cleanup
    old_terminal_settings = None
    
    try:
        # Save terminal settings before any changes
        old_terminal_settings = termios.tcgetattr(sys.stdin)
        
        # Import components
        from src.audio_engine import AudioEngine
        from src.file_manager import FileManager
        from src.display import Display
        from src.midi_handler import MidiHandler
        
        print("✅ All modules imported successfully")
        
        # Initialize components
        print("\nInitializing FileManager...")
        file_manager = FileManager()
        
        print("Initializing AudioEngine...")
        engine = AudioEngine()
        
        print("Initializing Display...")
        display = Display()
        
        print("Initializing MIDI Handler...")
        midi = MidiHandler()
        
        # Load initial files
        print("\nLoading initial files...")
        ambient_file = file_manager.get_next_ambient()
        rhythm_file = file_manager.get_next_rhythm()
        
        if ambient_file:
            engine.load_audio_file(ambient_file, 'ambient')
        
        if rhythm_file:
            engine.load_audio_file(rhythm_file, 'rhythm')
        
        # Start audio playback
        print("\nStarting audio playback...")
        engine.play()
        
        # Main control variables
        last_fader_pos = 50  # Start at 50%
        engine.set_volumes(0.5, 0.5)  # 50% each
        
        # Track loading triggers
        ambient_loaded_at_zero = False
        rhythm_loaded_at_hundred = False
        
        print("\n" + "="*50)
        print("SYSTEM IS RUNNING!")
        print("="*50)
        print("\nYou should hear both tracks with loop crossfades")
        print("Move crossfader (A/D keys) to extremes to trigger new file loading")
        print("\nPress Q to stop (or Ctrl+C)")
        print("="*50)
        
        # Main loop
        while midi.running:
            # Get current knob positions
            fader_pos = midi.get_knob_percentage(1)  # 0-100%
            
            # Convert knob position to volumes (linear crossfade)
            ambient_vol = (100 - fader_pos) / 100.0
            rhythm_vol = fader_pos / 100.0
            
            # Apply volumes to engine
            engine.set_volumes(ambient_vol, rhythm_vol)
            
            # Check for fader at 0% (A only) -> load new R file
            if fader_pos == 0 and not rhythm_loaded_at_hundred:
                print(f"\n🎚️  Fader at 0% - Loading new rhythm file...")
                next_rhythm = file_manager.get_next_rhythm()
                if next_rhythm:
                    engine.load_new_rhythm(next_rhythm)
                rhythm_loaded_at_hundred = True
                ambient_loaded_at_zero = False
            
            # Check for fader at 100% (R only) -> load new A file
            elif fader_pos == 100 and not ambient_loaded_at_zero:
                print(f"\n🎚️  Fader at 100% - Loading new ambient file...")
                next_ambient = file_manager.get_next_ambient()
                if next_ambient:
                    engine.load_new_ambient(next_ambient)
                ambient_loaded_at_zero = True
                rhythm_loaded_at_hundred = False
            
            # Reset triggers when fader moves away from extremes
            elif 0 < fader_pos < 100:
                ambient_loaded_at_zero = False
                rhythm_loaded_at_hundred = False
            
            # Get current file info for display
            ambient_info, rhythm_info = engine.get_current_files_info()
            next_ambient_info = file_manager.get_next_ambient_info()
            next_rhythm_info = file_manager.get_next_rhythm_info()
            
            # Update display (but not too fast)
            if fader_pos != last_fader_pos or True:  # Always update for now
                display.update(
                    ambient_info=ambient_info,
                    rhythm_info=rhythm_info,
                    next_ambient_info=next_ambient_info,
                    next_rhythm_info=next_rhythm_info,
                    ambient_vol=ambient_vol,
                    rhythm_vol=rhythm_vol,
                    fader_pos=fader_pos
                )
                last_fader_pos = fader_pos
            
            # Small delay to prevent CPU overload
            time.sleep(0.05)
        
        print("\nMIDI handler stopped")
        
    except KeyboardInterrupt:
        print("\n\nStopping (KeyboardInterrupt)...")
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            if 'engine' in locals():
                engine.stop()
            if 'midi' in locals():
                midi.close()
            
            # Restore terminal settings
            if old_terminal_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)
            
            print("\nSystem stopped. Terminal restored.")
        except:
            pass

if __name__ == "__main__":
    main()
