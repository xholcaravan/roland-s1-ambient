ROLAND S-1 CONTROLLER - SYSTEM OVERVIEW
Save this as SYSTEM_OVERVIEW.txt in your main folder

PROJECT STRUCTURE

main.py                 # Main entry point
src/
├── audio_engine.py     # Real-time audio with FIXED-TIME loop crossfades
├── file_manager.py     # File scanning and random selection
├── display.py         # Terminal UI
└── midi_handler.py    # MIDI simulation (keyboard controls)

samples/
├── ambient/           # a_*.wav files with a_*.txt crossfade configs
└── rhythm/            # r_*.wav files with r_*.txt crossfade configs

CORE LOGIC

1. FILE MANAGEMENT
   - On startup: Scan samples/ambient/ for a_*.wav files
   - On startup: Scan samples/rhythm/ for r_*.wav files
   - Load matching .txt config for each .wav (contains "crossfade_ms")
   - If .txt missing → skip that .wav file
   - Track selection: RANDOM from available files

2. AUDIO ENGINE (audio_engine.py)
   - TWO independent channels: Ambient (A) and Rhythm (R)
   - Each channel plays ONE .wav file in loop
   - At loop point: Apply saved crossfade_ms from .txt config
   - **FIXED-TIME BUFFERS**: All buffers = 300s (5 minutes) regardless of file length
   - Crossfade method: End overlaps with beginning (pre-rendered in buffer)

3. CHANNEL CROSSFADE (KNOB 1)
   - Non-linear volume balance between A and R channels (x^1.5 curve)
   - 0% = A at 100%, R at 0% (silent) → Loads new random R file immediately
   - 100% = R at 100%, A at 0% (silent) → Loads new random A file immediately
   - 50% = Both at ~35% volume (due to non-linear curve)
   - Silent channels: Continue looping (with crossfades) at volume 0

4. DISPLAY
   Shows:
   - Current playing files (A and R)
   - Next queued files (when channel is silent)
   - Volume levels with visual bars
   - Loop crossfade value for each track
   - File durations in seconds

5. CONTROLS (via keyboard simulation)
   - A/D: Knob 1 (Channel crossfader: A← →R)
   - W/S: Knob 2 (Future use)
   - I/K: Knob 3 (Future use)
   - O/L: Knob 4 (Future use)
   - R: Reset all knobs to middle
   - Q: Quit program

IMPORTANT NOTES

TWO TYPES OF CROSSFADE:
   1. LOOP CROSSFADE: Within single track (end→beginning overlap)
      - Stored in .txt config as "crossfade_ms"
      - Pre-rendered into FIXED 300s buffers
      - Guarantees seamless loops
      - Buffers always same length → consistent wrap-around

   2. CHANNEL CROSSFADE: Between A and R tracks
      - Controlled by Knob 1
      - Non-linear volume balance (x^1.5 curve)
      - Triggers new file loading at 0% volume threshold

FILE LOADING RULES:
   - Load happens WHEN volume hits 0% (previously > 0%)
   - New file starts playing IMMEDIATELY (at volume 0)
   - File loading is SYNCHRONOUS (no background thread)
   - Audio glitch during load is acceptable (volume is 0)

FIXED-TIME BUFFER SYSTEM:
   - All audio buffers = 300 seconds (5 minutes)
   - Regardless of original file length (5s to 40s)
   - Renders as many loops as fit in 300s
   - Ensures consistent wrap-around logic
   - Fixes "sometimes works" crossfade bug
   - Memory: ~100MB per track (300s @ 44.1kHz stereo)

MEMORY USAGE:
   - Only 2 files loaded at once (current A + current R)
   - Each: ~100MB for 5-minute fixed buffer
   - Total: ~200MB RAM → Safe for 8GB systems

DEVELOPMENT HISTORY

Phase 1: Auto-Loading Crossfader ✓
   - Basic audio engine with two channels
   - MIDI simulation via keyboard
   - Terminal display

Phase 2: Loop Crossfade Integration ✓
   - Integrate saved crossfade_ms from .txt configs
   - Apply seamless loop crossfades during playback
   - Auto-scan samples directories
   - **FIX: Fixed-time buffers (300s) for consistent crossfades**

Phase 3: (Future)
   - Real MIDI hardware support
   - Advanced crossfade curves
   - Visual waveform display
   - Effects processing

NORMALIZATION WORKFLOW:
   1. Batch normalize all WAV files to consistent RMS (0.2) using separate script
   2. Crossfade tester applies normalization during testing
   3. Main app plays pre-normalized files as-is (no runtime normalization)

TROUBLESHOOTING

Q: No audio?
A: Check samples/ directories have a_*.wav and r_*.wav files

Q: File not loading?
A: Check .txt config exists with "crossfade_ms" value

Q: Crossfade inconsistent (sometimes works, sometimes not)?
A: **FIXED** - Now uses fixed-time buffers (300s) for consistent wrap-around

Q: Knob controls not working?
A: Terminal must be in focus for keyboard simulation

Q: Audio glitches?
A: Normal when loading new files at volume 0

Q: Volume too quiet/loud?
A: Files should be pre-normalized to RMS 0.2 using batch script
