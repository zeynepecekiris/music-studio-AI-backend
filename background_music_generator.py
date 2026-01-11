#!/usr/bin/env python3
"""
Background Music Generator for Musician App
Creates instrumental tracks based on style, instruments, and mood
"""

import os
import random
from typing import List, Dict, Any
from pydub import AudioSegment
from pydub.generators import Sine, Sawtooth, Square
import numpy as np

class BackgroundMusicGenerator:
    def __init__(self):
        self.base_tempo = 120  # BPM
        self.base_key = "C"
        
        # Musical scales
        self.scales = {
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "blues": [0, 3, 5, 6, 7, 10],
            "pentatonic": [0, 2, 4, 7, 9]
        }
        
        # Chord progressions by style
        self.progressions = {
            "pop": [[0, 2, 3, 1], [0, 3, 2, 1]],  # I-V-vi-IV, I-vi-V-IV
            "rock": [[0, 2, 3, 1], [0, 5, 2, 3]],  # I-V-vi-IV, I-bVII-V-vi
            "jazz": [[0, 2, 1, 4], [0, 1, 2, 4]],  # ii-V-I variations
            "classical": [[0, 4, 1, 0], [0, 2, 1, 0]],  # I-V-ii-I
            "folk": [[0, 3, 2, 0], [0, 1, 2, 0]],  # Simple progressions
            "electronic": [[0, 2, 3, 1], [3, 1, 0, 2]],  # Modern progressions
            "blues": [[0, 0, 0, 0], [3, 3, 0, 0]],  # 12-bar blues base
            "country": [[0, 0, 3, 2], [0, 2, 3, 0]]  # Country style
        }
    
    def generate_chord_progression(self, style: str, duration: int) -> List[int]:
        """Generate chord progression for given style and duration"""
        progression = random.choice(self.progressions.get(style, self.progressions["pop"]))
        
        # Repeat progression to fill duration
        measures = max(8, duration // 4)  # At least 8 measures
        full_progression = []
        
        for i in range(measures // len(progression) + 1):
            full_progression.extend(progression)
        
        return full_progression[:measures]
    
    def get_frequencies_for_chord(self, chord_degree: int, scale_type: str = "major") -> List[float]:
        """Get frequencies for a chord based on scale degree"""
        base_freq = 220.0  # A3
        scale = self.scales[scale_type]
        
        # Get chord tones (1st, 3rd, 5th)
        root = scale[chord_degree % len(scale)]
        third = scale[(chord_degree + 2) % len(scale)]
        fifth = scale[(chord_degree + 4) % len(scale)]
        
        # Convert to frequencies
        frequencies = []
        for semitone in [root, third, fifth]:
            freq = base_freq * (2 ** (semitone / 12.0))
            frequencies.extend([freq, freq * 2, freq * 4])  # Multiple octaves
        
        return frequencies
    
    def create_instrument_track(self, instrument: str, chord_progression: List[int], 
                              duration: int, mood: str) -> AudioSegment:
        """Create instrumental track for specific instrument"""
        
        track = AudioSegment.empty()
        measure_duration = 2000  # 2 seconds per measure
        
        # Instrument characteristics
        if instrument == "guitar":
            generator = Sawtooth
            volume_db = -20
        elif instrument == "piano":
            generator = Sine
            volume_db = -15
        elif instrument == "drums":
            # Simplified drum pattern
            return self.create_drum_track(len(chord_progression), measure_duration, mood)
        elif instrument == "bass":
            generator = Sine
            volume_db = -10
        else:
            generator = Sine
            volume_db = -18
        
        # Adjust volume based on mood
        mood_adjustments = {
            "happy": 0,
            "sad": -10,
            "romantic": -5,
            "energetic": +5,
            "calm": -8,
            "melancholic": -12
        }
        volume_db += mood_adjustments.get(mood, 0)
        
        for chord_degree in chord_progression:
            frequencies = self.get_frequencies_for_chord(chord_degree)
            
            # Create chord
            chord_segment = AudioSegment.empty()
            for freq in frequencies[:3]:  # Use first 3 frequencies
                tone = generator(freq).to_audio_segment(duration=measure_duration)
                tone = tone + volume_db
                
                if len(chord_segment) == 0:
                    chord_segment = tone
                else:
                    chord_segment = chord_segment.overlay(tone)
            
            track += chord_segment
        
        return track
    
    def create_drum_track(self, measures: int, measure_duration: int, mood: str) -> AudioSegment:
        """Create simple drum pattern"""
        # Simple kick and snare pattern
        kick_freq = 60
        snare_freq = 200
        
        beat_duration = measure_duration // 4  # 4 beats per measure
        
        track = AudioSegment.empty()
        
        for measure in range(measures):
            measure_track = AudioSegment.empty()
            
            for beat in range(4):
                beat_segment = AudioSegment.empty()
                
                # Kick on beats 1 and 3
                if beat in [0, 2]:
                    kick = Sine(kick_freq).to_audio_segment(duration=100) + (-25)
                    beat_segment += kick
                
                # Snare on beats 2 and 4
                if beat in [1, 3]:
                    snare = Square(snare_freq).to_audio_segment(duration=80) + (-30)
                    if len(beat_segment) == 0:
                        beat_segment = snare
                    else:
                        beat_segment = beat_segment.overlay(snare)
                
                # Fill rest of beat with silence
                if len(beat_segment) < beat_duration:
                    silence = AudioSegment.silent(beat_duration - len(beat_segment))
                    beat_segment += silence
                
                measure_track += beat_segment
            
            track += measure_track
        
        return track
    
    def generate_background_music(self, style: str, instruments: List[str], 
                                duration: int, mood: str) -> AudioSegment:
        """Generate complete background music track"""
        
        # Generate chord progression
        chord_progression = self.generate_chord_progression(style, duration)
        
        # Create tracks for each instrument
        final_track = AudioSegment.empty()
        
        for instrument in instruments:
            instrument_track = self.create_instrument_track(
                instrument, chord_progression, duration, mood
            )
            
            if len(final_track) == 0:
                final_track = instrument_track
            else:
                # Mix instruments together
                final_track = final_track.overlay(instrument_track)
        
        # Apply style-specific effects
        if style == "electronic":
            # Add some distortion/effects for electronic
            final_track = final_track + 3  # Slightly louder
        elif style == "classical":
            # Softer, more reverb-like
            final_track = final_track - 5
        
        # Ensure minimum duration
        target_duration = max(duration * 1000, len(final_track))
        if len(final_track) < target_duration:
            # Loop the track if too short
            loops_needed = (target_duration // len(final_track)) + 1
            extended_track = final_track
            for _ in range(loops_needed - 1):
                extended_track += final_track
            final_track = extended_track[:target_duration]
        
        return final_track
    
    def save_track(self, track: AudioSegment, output_path: str) -> str:
        """Save track to file"""
        track.export(output_path, format="mp3", bitrate="128k")
        return output_path

# Test function
def test_generator():
    generator = BackgroundMusicGenerator()
    
    # Test different combinations
    test_cases = [
        {"style": "pop", "instruments": ["guitar", "piano"], "duration": 30, "mood": "happy"},
        {"style": "rock", "instruments": ["guitar", "drums"], "duration": 45, "mood": "energetic"},
        {"style": "jazz", "instruments": ["piano", "bass"], "duration": 60, "mood": "calm"}
    ]
    
    for i, case in enumerate(test_cases):
        track = generator.generate_background_music(**case)
        output_path = f"test_track_{i}.mp3"
        generator.save_track(track, output_path)
        print(f"Generated: {output_path} - {case}")

if __name__ == "__main__":
    test_generator()
