# Roland S-1 Ambient/Rhythm Controller
# Phase 1: Auto-Loading Crossfader

## CORE CONCEPT
Dual-layer sampler with intelligent auto-loading based on volume fader position.
When a track's volume reaches 0%, it automatically loads a new file.
Both tracks loop continuously throughout.

## HARDWARE MAPPING (PHASE 1)
### Roland S-1 Controls:
- **KNOB 1**: A/R Crossfader
  - Left: 100% Rhythm, 0% Ambient
  - Right: 0% Rhythm, 100% Ambient
- All other knobs/pads: Reserved for future phases

### Auto-Loading Logic:
- When Ambient volume reaches 0% → Load new Ambient file
- When Rhythm volume reaches 0% → Load new Rhythm file
- File selection: Least-played-first algorithm
- Immediate load (no dwell time at 0%)

## AUDIO SPECIFICATIONS
### File Format:
- WAV format, 44.1kHz, 16-bit
- Stereo or Mono (auto-converted)
- Ambient: 15-30 seconds, pads/textures
- Rhythm: 2-4 seconds, rhythmic loops

### Playback:
- Both layers loop continuously
- Simple wrap-around at end (no crossfade)
- Linear volume crossfade
- Hybrid RAM loading (current + next 2 files)

## TERMINAL INTERFACE
Live updating display showing:
- Current Ambient file + volume
- Current Rhythm file + volume  
- Fader position with visual bar
- Next candidate files
- Clean, minimal information

Example:
╔══════════════════════════════════════╗
║  🎹 ROLAND S-1 CROSSFADER (Phase 1)  ║
╠══════════════════════════════════════╣
║                                      ║
║  AMBIENT: pad_forest.wav             ║
║    Volume: 10%                       ║
║                                      ║
║  RHYTHM:  break_funk.wav             ║
║    Volume: 90%                       ║
║                                      ║
║  FADER: ███████░░░ 70%               ║
║  [░░░░░░░░░░] ←A     R→ [██████████] ║
║                                      ║
║  Next A: drones.wav                  ║
║  Next R: beat_120.wav                ║
║                                      ║
║  Press Q to quit                     ║
╚══════════════════════════════════════╝

## SOFTWARE ARCHITECTURE
### Core Components:
1. **Audio Engine**: WAV loading, playback, mixing
2. **File Manager**: File selection, play tracking, pre-loading
3. **MIDI Handler**: Roland S-1 communication
4. **Display**: Live terminal interface
5. **Main Controller**: Orchestrates all components

### Development Order:
1. Audio engine (load/play/loop WAV)
2. File manager (selection logic)
3. Terminal display (static then dynamic)
4. MIDI handler (crossfader control)
5. Auto-load logic (integration)

## FILE STRUCTURE
roland-s1-ambient/
├── samples/
│   ├── ambient/          # A files (15-30s)
│   └── rhythm/           # R files (2-4s)
├── src/
│   ├── audio_engine.py   # Playback, mixing
│   ├── file_manager.py   # Selection, pre-loading
│   ├── midi_handler.py   # Roland S-1 communication
│   ├── display.py        # Terminal interface
│   └── main.py          # Main controller
├── config/
│   └── phase1.yaml      # Phase 1 configuration
└── PROJECT_SPEC.md      # This document

## FUTURE PHASES
### Phase 2: Ambient Time-Stretch
- KNOB 2: Stretch ratio (0.5x to 4x)
- KNOB 3: Grain size (texture)
- Real-time PaulStretch/granular engine

### Phase 3: Effects Processing
- KNOB 4: Filter cutoff
- KNOB 5: Reverb amount
- Shared effects on both layers

### Phase 4: Advanced Features
- Beat-aware rhythm playback
- Key/BPM matching (smart pairing)
- Preset system

### Phase 5: Polish
- Performance optimization
- MIDI learn/remapping
- Session save/load

## GETTING STARTED
1. Place test WAV files in samples/ambient/ and samples/rhythm/
2. Run: python src/main.py
3. Turn KNOB 1 on Roland S-1 to control crossfader
4. Move to extreme positions to trigger auto-loading

## NOTES
- First focus: Get audio playing without MIDI
- Test with simulated knob values
- Add MIDI once audio engine works
- Terminal display helps debugging
