"""
Simple MIDI monitoring for Roland S-1
"""

import mido
import time

def list_midi_ports():
    """List all available MIDI ports"""
    print("\n🔍 Available MIDI ports:")
    inputs = mido.get_input_names()
    
    if not inputs:
        print("   No MIDI devices found!")
        print("\n   Make sure:")
        print("   1. Roland S-1 is connected via USB")
        print("   2. S-1 is powered on")
        print("   3. Check MIDI settings on S-1:")
        print("      - SHIFT + OCTAVE - → Utility")
        print("      - MIDI TX Switch: ON")
        return []
    
    for i, name in enumerate(inputs):
        print(f"   {i}: {name}")
    return inputs

def test_midi_connection():
    """Simple MIDI monitor for Roland S-1"""
    print("\n🎛️  Roland S-1 MIDI Monitor")
    print("=" * 50)
    
    ports = list_midi_ports()
    if not ports:
        return
    
    # Try to auto-detect Roland S-1
    port_name = None
    for name in ports:
        if any(keyword in name.lower() for keyword in ['s-1', 's1', 'roland']):
            port_name = name
            print(f"\n✅ Auto-detected: {name}")
            break
    
    if not port_name:
        port_name = ports[0]
        print(f"\n⚠️  Using first available port: {port_name}")
    
    print("\n📝 Now listening...")
    print("   - Turn knobs")
    print("   - Press keys")
    print("   - Move pitch bend")
    print("\n   Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        with mido.open_input(port_name) as port:
            print("   Waiting for MIDI messages...\n")
            
            # Simple counter to show it's alive
            message_count = 0
            
            for message in port:
                message_count += 1
                print(f"[{message_count}] {message}")
                
                # Simple interpretation
                if message.type == 'control_change':
                    if 16 <= message.control <= 19:
                        knob_num = message.control - 15
                        value = message.value
                        percent = int((value / 127) * 100)
                        print(f"     → KNOB {knob_num}: {value} ({percent}%)")
                
                elif message.type == 'note_on' and message.velocity > 0:
                    # Basic note name conversion
                    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    note_name = notes[message.note % 12]
                    octave = (message.note // 12) - 1
                    print(f"     → KEY: {note_name}{octave} (vel: {message.velocity})")
                
                print()  # Empty line for readability
                
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_midi_connection()