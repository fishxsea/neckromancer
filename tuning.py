"""Real open-string pitches, including optional scientific octave notation."""

import re

from chords import clean_note, pitch_class

# Standard guitar, extended-range guitar, and bass registers (MIDI pitches).
PRESETS = {
    ('E', 'A', 'D', 'G', 'B', 'E'): (40, 45, 50, 55, 59, 64),
    ('D', 'A', 'D', 'G', 'B', 'E'): (38, 45, 50, 55, 59, 64),
    ('B', 'E', 'A', 'D', 'G', 'B', 'E'): (35, 40, 45, 50, 55, 59, 64),
    ('F#', 'B', 'E', 'A', 'D', 'G', 'B', 'E'): (30, 35, 40, 45, 50, 55, 59, 64),
    ('E', 'A', 'D', 'G'): (28, 33, 38, 43),
}


def parse_tuning(tuning):
    tokens = tuning.split() if isinstance(tuning, str) else tuning
    if not tokens:
        raise ValueError('Tuning must contain at least one string.')
    notes, octaves = [], []
    for token in tokens:
        match = re.fullmatch(r'([^\d\s-]+)(-?\d+)?', token.strip())
        if not match:
            raise ValueError(f'Invalid tuning note: {token}')
        notes.append(clean_note(match[1]))
        octaves.append(int(match[2]) if match[2] is not None else None)
    if any(octave is not None for octave in octaves):
        if any(octave is None for octave in octaves):
            raise ValueError('Include an octave on every tuning note, or on none of them.')
        # Use the written natural-note octave before applying accidentals:
        # B#3 is C4, not C3; Cb4 is B3, not B4.
        from chords import NATURALS
        pitches = tuple(12 * (octave + 1) + NATURALS[note[0]]
                        + note.count('#') - note.count('b')
                        for note, octave in zip(notes, octaves))
    else:
        canonical = tuple(pitch_class(note) for note in notes)
        preset = next((value for names, value in PRESETS.items()
                       if tuple(pitch_class(note) for note in names) == canonical), None)
        if preset is not None:
            pitches = preset
        else:
            # Bare custom tunings assume successively higher open strings.
            # Explicit octaves are required to express re-entrant/unison tunings.
            previous = 23 if len(notes) in (4, 7, 8) else 35
            pitches = []
            for note in notes:
                pitch = pitch_class(note)
                while pitch <= previous:
                    pitch += 12
                pitches.append(pitch)
                previous = pitch
            pitches = tuple(pitches)
    if any(not 0 <= pitch <= 127 for pitch in pitches):
        raise ValueError('Tuning pitches must be in the MIDI range 0–127.')
    normalized_tokens = tuple(note if octave is None else f'{note}{octave}'
                              for note, octave in zip(notes, octaves))
    return normalized_tokens, tuple(notes), pitches
