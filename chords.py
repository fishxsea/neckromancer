"""Chord spelling, interval formulas, and explicit guitar-voicing policies.

Chord formulas describe harmony; required tones describe a particular voicing
policy. Pitch classes are used for matching, spelled notes for presentation.
"""

import re

NOTES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
ROOT_NAMES = ('C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb',
              'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B')
LETTERS = 'CDEFGAB'
NATURALS = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))
CHORD_TYPES = {
    'maj': (0, 4, 7), 'min': (0, 3, 7), 'dim': (0, 3, 6),
    'aug': (0, 4, 8), 'sus2': (0, 2, 7), 'sus4': (0, 5, 7), '5': (0, 7),
    '6': (0, 4, 7, 9), 'min6': (0, 3, 7, 9),
    '7': (0, 4, 7, 10), 'maj7': (0, 4, 7, 11), 'min7': (0, 3, 7, 10),
    'minmaj7': (0, 3, 7, 11), 'dim7': (0, 3, 6, 9), 'm7b5': (0, 3, 6, 10),
    'add9': (0, 4, 7, 14), 'minadd9': (0, 3, 7, 14),
    '9': (0, 4, 7, 10, 14), 'maj9': (0, 4, 7, 11, 14),
    'min9': (0, 3, 7, 10, 14), '9sus4': (0, 5, 7, 10, 14),
    '11': (0, 4, 7, 10, 14, 17), 'maj11': (0, 4, 7, 11, 14, 17),
    'min11': (0, 3, 7, 10, 14, 17),
    '13': (0, 4, 7, 10, 14, 17, 21),
    'maj13': (0, 4, 7, 11, 14, 17, 21),
    'min13': (0, 3, 7, 10, 14, 17, 21),
}
DEGREES = {quality: (1, 3, 5, 7, 9, 11, 13)[:len(intervals)]
           for quality, intervals in CHORD_TYPES.items()}
DEGREES.update({'5': (1, 5), 'sus2': (1, 2, 5), 'sus4': (1, 4, 5),
                '6': (1, 3, 5, 6), 'min6': (1, 3, 5, 6),
                'add9': (1, 3, 5, 9), 'minadd9': (1, 3, 5, 9),
                '9sus4': (1, 4, 5, 7, 9)})
SCALES = {'maj': (0, 2, 4, 5, 7, 9, 11), 'min': (0, 2, 3, 5, 7, 8, 10),
          'harmonic_min': (0, 2, 3, 5, 7, 8, 11),
          'melodic_min': (0, 2, 3, 5, 7, 9, 11)}
KEY_KINDS = {'maj': 'Major', 'min': 'Natural minor',
             'harmonic_min': 'Harmonic minor', 'melodic_min': 'Melodic minor (ascending)'}


def clean_note(note):
    """Validate a pitch-class name without discarding its theoretical spelling."""
    if not isinstance(note, str):
        raise ValueError('A note name must be text.')
    note = note.strip().replace('♭', 'b').replace('♯', '#').replace('𝄫', 'bb').replace('𝄪', '##')
    if note:
        note = note[0].upper() + note[1:]
    if not re.fullmatch(r'[A-G](?:#{1,3}|b{1,3}|x)?', note):
        raise ValueError(f'Unknown note: {note or "(empty)"}')
    return note.replace('x', '##')


def pitch_class(note):
    note = clean_note(note)
    return (NATURALS[note[0]] + note.count('#') - note.count('b')) % 12


def normalize_note(note):
    """Canonical chromatic name, for matching rather than chord spelling."""
    return NOTES[pitch_class(note)]


def spell_interval(root, degree, semitones):
    root = clean_note(root)
    letter = LETTERS[(LETTERS.index(root[0]) + degree - 1) % 7]
    accidental = (pitch_class(root) + semitones - NATURALS[letter] + 6) % 12 - 6
    return letter + ('#' * accidental if accidental >= 0 else 'b' * -accidental)


def chord_notes(root, quality):
    if quality not in CHORD_TYPES:
        raise ValueError(f'Unknown chord quality: {quality}')
    return [spell_interval(root, degree, interval)
            for degree, interval in zip(DEGREES[quality], CHORD_TYPES[quality])]


def chord_symbol(root, quality):
    suffix = {'maj': '', 'min': 'm', 'min6': 'm6', 'min7': 'm7',
              'min9': 'm9', 'min11': 'm11', 'min13': 'm13',
              'minadd9': 'm(add9)', 'minmaj7': 'm(maj7)', 'm7b5': 'm7b5'}.get(quality, quality)
    return clean_note(root) + suffix


def voicing_tones(root, quality, complete=False):
    """Return (allowed, required) spelled tones for a standalone guitar chord.

    Keep roots and defining thirds, sevenths, and highest extensions. An
    unaltered fifth may be omitted from chords beyond a triad. Lower extensions
    are optional in 11ths/13ths. The natural 11th is excluded from practical
    major/dominant 13ths because it clashes with the major third. Complete
    mode instead requires the entire theoretical stack, including that 11th.
    """
    notes = chord_notes(root, quality)
    intervals = CHORD_TYPES[quality]
    if complete or len(intervals) <= 3:
        return tuple(notes), tuple(notes)
    optional = {7}
    excluded = set()
    if intervals[-1] >= 17:
        optional.add(14)
    if intervals[-1] >= 21:
        optional.add(17)
        if 4 in intervals:
            excluded.add(17)
    allowed = tuple(note for note, interval in zip(notes, intervals) if interval not in excluded)
    required = tuple(note for note, interval in zip(notes, intervals)
                     if interval not in optional and interval not in excluded)
    return allowed, required


def scale_notes(root, kind='maj'):
    if kind not in SCALES:
        raise ValueError(f'Unknown scale type: {kind}')
    return [spell_interval(root, degree, interval)
            for degree, interval in enumerate(SCALES[kind], 1)]


def notes_in_key(notes, root, kind='maj'):
    """Test pitch classes against one explicitly chosen scale."""
    return {pitch_class(note) for note in notes} <= {
        pitch_class(note) for note in scale_notes(root, kind)}


def chords_in_key(root, kind='maj'):
    """Supported named chords whose full formulas stay inside the scale.

    Check the entire chord, including optional guitar tones: omitting an
    out-of-key fifth or extension must not turn a chromatic chord into a
    diatonic choice. Scale spelling is retained for each chord root.
    """
    return [(note, quality) for note in scale_notes(root, kind)
            for quality in CHORD_TYPES if notes_in_key(chord_notes(note, quality), root, kind)]
