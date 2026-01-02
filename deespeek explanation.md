# ROLAND S-1 CONTROLLER - SYSTEM OVERVIEW
# Save this as SYSTEM_OVERVIEW.txt in your main folder

## PROJECT STRUCTURE
main.py              # Main entry point
src/
├── audio_engine.py  # Real-time audio with loop crossfades
├── file_manager.py  # File scanning and random selection
├── display.py       # Terminal UI
└── midi_handler.py  # MIDI simulation (keyboard controls)

samples/
├── ambient/         # a_*.wav files with a_*.txt crossfade configs
└── rhythm/          # r_*.wav files with r_*.txt crossfade configs

## CORE LOGIC

### 1. FILE MANAGEMENT
- On startup: Scan samples/ambient/ for a_*.wav files
- On startup: Scan samples/rhythm/ for r_*.wav files  
- Load matching .txt config for each .wav (contains "crossfade_ms")
- If .txt missing → skip that .wav file
- Track selection: RANDOM from available files

### 2. AUDIO ENGINE (audio_engine.py)
- TWO independent channels: Ambient (A) and Rhythm (R)
- Each channel plays ONE .wav file in loop
- At loop point: Apply saved crossfade_ms from .txt config
- Crossfade method: End overlaps with beginning (same as testing scripts)

### 3. CHANNEL CROSSFADE (KNOB 1)
- Linear volume balance between A and R channels
- 0% = A at 100%, R at 0% (silent) → Loads new random R file immediately
- 100% = R at 100%, A at 0% (silent) → Loads new random A file immediately  
- 50% = Both at 50% volume
- Silent channels: Continue looping (with crossfades) at volume 0

### 4. DISPLAY
Shows:
- Current playing files (A and R)
- Next queued files (when channel is silent)
- Knob 1 position (0-100%)
- Loop crossfade value for each track

### 5. CONTROLS (via keyboard simulation)
- A/D: Knob 1 (Channel crossfader: A← →R)
- W/S: Knob 2 (Future use)
- I/K: Knob 3 (Future use)  
- O/L: Knob 4 (Future use)
- R: Reset all knobs to middle
- Q: Quit program

## IMPORTANT NOTES

### TWO TYPES OF CROSSFADE:
1. LOOP CROSSFADE: Within single track (end→beginning overlap)
   - Stored in .txt config as "crossfade_ms"
   - Applied automatically during playback
   - Guarantees seamless loops

2. CHANNEL CROSSFADE: Between A and R tracks  
   - Controlled by Knob 1
   - Linear volume balance
   - Triggers new file loading at extremes

### FILE LOADING RULES:
- Load happens WHEN knob hits 0% or 100%
- New file starts playing IMMEDIATELY (at volume 0)
- File loading is SYNCHRONOUS (no background thread)
- Audio glitch during load is acceptable (volume is 0)

### MEMORY USAGE:
- Only 2 files loaded at once (current A + current R)
- Typical WAV file: ~30MB for 3-minute stereo
- Total: ~60MB RAM → Very safe

## DEVELOPMENT HISTORY

Phase 1: Auto-Loading Crossfader ✓
- Basic audio engine with two channels
- MIDI simulation via keyboard
- Terminal display

Phase 2: Loop Crossfade Integration (CURRENT)
- Integrate saved crossfade_ms from .txt configs
- Apply seamless loop crossfades during playback
- Auto-scan samples directories

Phase 3: (Future)
- Real MIDI hardware support
- Advanced crossfade curves
- Visual waveform display
- Effects processing

## TROUBLESHOOTING

Q: No audio?
A: Check samples/ directories have a_*.wav and r_*.wav files

Q: File not loading?  
A: Check .txt config exists with "crossfade_ms" value

Q: Knob controls not working?
A: Terminal must be in focus for keyboard simulation

Q: Audio glitches?
A: Normal when loading new files at volume 0