#!/usr/bin/env python3
"""
Test Roland S-1 connection with new cable
"""

import mido
import time

print("=" * 60)
print("TEST: Roland S-1 Connection with New Cable")
print("=" * 60)
print()

# 1. List all MIDI ports
ports = mido.get_input_names()
print(f"Found {len(ports)} MIDI port(s):")

if not ports:
    print("❌ NO MIDI PORTS FOUND!")
    print("\nTroubleshooting:")
    print("1. Is the cable a DATA cable (not just charging)?")
    print("2. Is S-1 powered ON (blue/white light)?")
    print("3. Try different USB port")
    print("4. On S-1: SHIFT + OCTAVE - → Utility → MIDI TX Switch: ON")
    exit()

for i, port in enumerate(ports):
    print(f"  [{i}] {port}")

print()

# 2. Look for Roland S-1
roland_port = None
for port in ports:
    port_lower = port.lower()
    if any(keyword in port_lower for keyword in ['s-1', 's1', 'roland', 'usb audio']):
        roland_port = port
        print(f"✅ Found Roland S-1: {port}")
        break

if not roland_port:
    print("⚠️  Roland S-1 not found by name")
    print("Trying all ports...")
    roland_port = ports[0]
    print(f"Using: {roland_port}")

print()

# 3. Test listening
print("=" * 60)
print("LISTENING TEST: Turn knobs or press keys on S-1")
print("=" * 60)
print("You should see messages below when you:")
print("  • Turn any knob")
print("  • Press any key/pad")
print("  • Move pitch bend")
print()
print("Press Ctrl+C to stop")
print("-" * 60)

try:
    with mido.open_input(roland_port) as port:
        message_count = 0
        start_time = time.time()
        
        while True:
            # Check for messages
            msg = port.poll()
            if msg:
                message_count += 1
                elapsed = time.time() - start_time
                
                print(f"[{elapsed:.1f}s] Message #{message_count}: {msg}")
                
                # Simple interpretation
                if msg.type == 'control_change':
                    print(f"     → KNOB/Controller #{msg.control} = {msg.value}/127")
                    
                    # Roland S-1 knobs are typically 16-19
                    if 16 <= msg.control <= 19:
                        knob_num = msg.control - 15
                        percent = int((msg.value / 127) * 100)
                        print(f"     → Likely KNOB {knob_num}: {percent}%")
                
                elif msg.type == 'note_on' and msg.velocity > 0:
                    # Convert note number to name
                    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    note_name = notes[msg.note % 12]
                    octave = (msg.note // 12) - 1
                    print(f"     → KEY: {note_name}{octave} (velocity: {msg.velocity})")
                
                elif msg.type == 'pitchwheel':
                    # Pitch bend ranges from -8192 to 8191
                    print(f"     → PITCH BEND: {msg.pitch}")
                
                print()  # Empty line
            
            time.sleep(0.01)  # Small delay to not hog CPU

except KeyboardInterrupt:
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    if message_count > 0:
        print(f"✅ SUCCESS! Received {message_count} MIDI messages")
        print("Your S-1 is working correctly!")
    else:
        print("⚠️  No messages received")
        print("Check: Are you turning knobs/pressing keys?")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
