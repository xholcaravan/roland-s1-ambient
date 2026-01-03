# DELAY & REVERB IMPLEMENTATION

## CONTROLS
- Q/A: Channel crossfader (Q=more Ambient, A=more Rhythm)
- W/S: Delay amount (0-100%) - controls BOTH time and mix together
- E/D: Reverb amount (0-100%) - wet/dry mix

## DELAY BEHAVIOR (Roland S-1 style)
Knob Position → Delay Settings:
  0%:     Mix=0%  (completely dry, time irrelevant)
  1-30%:  Time=200ms, Mix=knob%, Feedback=30%
  31-70%: Time=400ms, Mix=knob%, Feedback=50%
  71-100%: Time=800ms, Mix=knob%, Feedback=70%

## REVERB BEHAVIOR
Knob Position → Reverb Settings:
  0%:    Mix=0% (dry)
  100%:  Mix=100% (fully wet)
  Room size fixed at 0.7 (medium), damping at 0.5

## STARTUP STATE
- Crossfader: 0.0 (100% Ambient, 0% Rhythm)
- Delay: 0.0 (off/dry)
- Reverb: 0.0 (off/dry)

## TECHNICAL IMPLEMENTATION
1. Add pedalboard to requirements.txt
2. Update audio_engine.py with delay/reverb processors
3. Update midi_handler.py with new key mappings
4. Update display.py to show effect levels
5. Effects applied to mixed output (post-crossfade)
