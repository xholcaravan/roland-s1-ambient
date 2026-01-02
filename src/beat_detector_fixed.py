#!/usr/bin/env python3
"""
Rhythmic Beat Detector for Loop Extraction - FIXED VERSION
Detects 4-bar segments in rhythmic audio files for seamless looping
"""

import os
import sys
import numpy as np
import librosa
import soundfile as sf
import argparse
from typing import List, Tuple

class BeatDetector:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        
    def detect_beats(self, audio_path: str) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Load audio and detect beats.
        Returns: (tempo, beat_times, beat_frames)
        """
        print(f"Loading {os.path.basename(audio_path)}...")
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Estimate tempo and beat frames
        print("Detecting tempo and beats...")
        
        # Try different approaches for beat detection
        try:
            # Method 1: Standard beat tracking
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
        except Exception as e:
            print(f"Standard beat tracking failed: {e}")
            print("Trying onset detection instead...")
            # Method 2: Onset detection as fallback
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
            beat_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, 
                sr=sr, 
                units='frames'
            )
        
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        print(f"Estimated tempo: {tempo:.1f} BPM")
        print(f"Detected {len(beat_times)} beats")
        
        return tempo, beat_times, beat_frames
    
    def find_4_bar_segments(self, beat_times: np.ndarray, 
                           tempo: float, 
                           beats_per_bar: int = 4,
                           bars_per_segment: int = 4) -> List[Tuple[float, float]]:
        """
        Find all possible 4-bar segments (16 beats in 4/4).
        """
        beats_per_segment = beats_per_bar * bars_per_segment  # 16 beats
        
        segments = []
        
        # Check if we have enough beats
        if len(beat_times) < beats_per_segment:
            print(f"Warning: Only {len(beat_times)} beats detected, need at least {beats_per_segment}")
            return segments
        
        # Calculate expected beat spacing
        beat_interval = 60.0 / tempo  # seconds per beat
        
        # Find segments with consistent timing
        for i in range(len(beat_times) - beats_per_segment + 1):
            segment_beats = beat_times[i:i + beats_per_segment]
            
            # Check beat consistency
            is_consistent = self._check_beat_consistency(segment_beats, beat_interval)
            
            if is_consistent:
                start_time = segment_beats[0]
                end_time = segment_beats[-1]
                
                segments.append((start_time, end_time))
                print(f"  Segment {len(segments)}: {start_time:.3f}s - {end_time:.3f}s "
                      f"({end_time-start_time:.2f}s)")
        
        return segments
    
    def _check_beat_consistency(self, beat_times: np.ndarray, 
                               expected_interval: float, 
                               tolerance_ms: float = 50) -> bool:
        """
        Check if beats are consistently spaced within tolerance.
        """
        tolerance_s = tolerance_ms / 1000.0
        
        for i in range(1, len(beat_times)):
            actual_interval = beat_times[i] - beat_times[i-1]
            interval_error = abs(actual_interval - expected_interval)
            
            if interval_error > tolerance_s:
                return False
        
        return True
    
    def save_audacity_labels(self, segments: List[Tuple[float, float]], 
                            output_path: str, 
                            description: str = "4-bar loop"):
        """
        Save segments in Audacity label format.
        Format: start_time\\tend_time\\tdescription
        """
        with open(output_path, 'w') as f:
            for i, (start, end) in enumerate(segments, 1):
                f.write(f"{start:.6f}\t{end:.6f}\t{description} {i}\n")
        
        print(f"\nSaved {len(segments)} segments to {output_path}")
    
    def analyze_audio_file(self, audio_path: str, output_dir: str = None):
        """
        Full analysis pipeline for one audio file.
        """
        if not os.path.exists(audio_path):
            print(f"Error: File not found - {audio_path}")
            return
        
        # Detect beats
        tempo, beat_times, beat_frames = self.detect_beats(audio_path)
        
        if len(beat_times) == 0:
            print("No beats detected!")
            return
        
        # Find 4-bar segments
        print(f"\nFinding 4-bar segments ({4*4}=16 beats)...")
        segments = self.find_4_bar_segments(beat_times, tempo)
        
        if not segments:
            print("No consistent 4-bar segments found.")
            print("Trying with 2-bar segments as fallback...")
            segments = self.find_4_bar_segments(beat_times, tempo, bars_per_segment=2)
        
        # Save results
        if segments:
            if output_dir is None:
                output_dir = os.path.dirname(audio_path)
            
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            labels_path = os.path.join(output_dir, f"{base_name}_loops.txt")
            
            self.save_audacity_labels(segments, labels_path)
            
            # Also save beat positions for reference
            beats_path = os.path.join(output_dir, f"{base_name}_beats.txt")
            with open(beats_path, 'w') as f:
                for i, beat_time in enumerate(beat_times, 1):
                    f.write(f"{beat_time:.6f}\tBeat {i}\n")
            
            print(f"Beat positions saved to {beats_path}")
            
            # Print summary
            print(f"\n=== SUMMARY ===")
            print(f"File: {os.path.basename(audio_path)}")
            print(f"Tempo: {tempo:.1f} BPM")
            print(f"Total beats: {len(beat_times)}")
            print(f"4-bar segments found: {len(segments)}")
            
            if segments:
                avg_length = np.mean([end-start for start, end in segments])
                print(f"Average segment length: {avg_length:.2f}s")
                
        else:
            print("No usable segments found.")

def main():
    parser = argparse.ArgumentParser(description='Detect 4-bar rhythmic segments for looping')
    parser.add_argument('audio_file', help='Path to audio file (WAV/MP3)')
    parser.add_argument('--output-dir', '-o', help='Output directory for label files')
    parser.add_argument('--sample-rate', '-sr', type=int, default=44100, 
                       help='Sample rate for analysis (default: 44100)')
    
    args = parser.parse_args()
    
    detector = BeatDetector(sample_rate=args.sample_rate)
    detector.analyze_audio_file(args.audio_file, args.output_dir)

if __name__ == "__main__":
    main()
