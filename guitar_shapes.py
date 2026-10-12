"""Conventional open/CAGED chord shapes, transposed as closed shapes.

These are ranking references, not a claim that other voicings are invalid.
Fret numbers run from lowest string to highest; None means muted.
"""

from chords import pitch_class

STANDARD = ('E', 'A', 'D', 'G', 'B', 'E')
SHAPES = {
    'maj': [('C', (None, 3, 2, 0, 1, 0)), ('A', (None, 0, 2, 2, 2, 0)),
            ('G', (3, 2, 0, 0, 0, 3)), ('E', (0, 2, 2, 1, 0, 0)),
            ('D', (None, None, 0, 2, 3, 2))],
    'min': [('A', (None, 0, 2, 2, 1, 0)), ('E', (0, 2, 2, 0, 0, 0)),
            ('D', (None, None, 0, 2, 3, 1))],
    '7': [('E', (0, 2, 0, 1, 0, 0)), ('A', (None, 0, 2, 0, 2, 0)),
           ('D', (None, None, 0, 2, 1, 2)), ('C', (None, 3, 2, 3, 1, 0)),
           ('G', (3, 2, 0, 0, 0, 1))],
    'maj7': [('C', (None, 3, 2, 0, 0, 0)), ('A', (None, 0, 2, 1, 2, 0)),
              ('E', (0, 2, 1, 1, 0, 0)), ('D', (None, None, 0, 2, 2, 2))],
    'min7': [('E', (0, 2, 0, 0, 0, 0)), ('A', (None, 0, 2, 0, 1, 0)),
              ('D', (None, None, 0, 2, 1, 1)), ('E', (0, 2, 2, 0, 3, 0)),
              ('E', (0, 2, 2, 0, 3, 3))],
    '6': [('E', (0, 2, 2, 1, 2, 0)), ('A', (None, 0, 2, 2, 2, 2)),
           ('D', (None, None, 0, 2, 0, 2)), ('G', (3, 2, 0, 0, 0, 0))],
    'min6': [('E', (0, 2, 2, 0, 2, 0)), ('A', (None, 0, 2, 2, 1, 2)),
              ('D', (None, None, 0, 2, 0, 1))],
    'sus2': [('A', (None, 0, 2, 2, 0, 0)), ('D', (None, None, 0, 2, 3, 0))],
    'sus4': [('E', (0, 2, 2, 2, 0, 0)), ('A', (None, 0, 2, 2, 3, 0)),
              ('D', (None, None, 0, 2, 3, 3))],
    '5': [('E', (0, 2, 2, None, None, None)),
           ('A', (None, 0, 2, 2, None, None))],
    '9': [('C', (None, 3, 2, 3, 3, 3)), ('A', (None, 0, 2, 4, 2, 3))],
    'maj9': [('C', (None, 3, 2, 4, 3, 3))],
    'min9': [('E', (0, 2, 0, 0, 0, 2)), ('A', (None, 0, 2, 4, 1, 3))],
    '13': [('E', (0, 2, 0, 1, 2, 0)), ('A', (None, 0, 2, 0, 2, 2)),
            ('C', (None, 3, 2, 3, 3, 5))],
    'maj13': [('C', (None, 3, None, 4, 5, 5)), ('E', (0, 2, 1, 1, 2, 0))],
    'min11': [('E', (0, 0, 0, 0, 0, 0)), ('A', (None, 0, 0, 0, 1, 0))],
    'minmaj7': [('E', (0, 2, 1, 0, 0, 0)), ('A', (None, 0, 2, 1, 1, 0))],
    'dim': [('C', (None, 3, 4, 5, 4, None))],
    'aug': [('C', (None, 3, 2, 1, 1, 0))],
    'dim7': [('C', (None, 3, 4, 2, 4, None)), ('D', (None, None, 0, 1, 0, 1)),
              ('E', (0, 1, 2, 0, 2, 0))],
    'm7b5': [('A', (None, 0, 1, 0, 1, None)), ('C', (None, 3, 4, 3, 4, None))],
    'add9': [('C', (None, 3, 2, 0, 3, 0)), ('A', (None, 0, 2, 4, 2, 0)),
              ('E', (0, 2, 2, 1, 0, 2))],
    'minadd9': [('A', (None, 0, 2, 4, 1, 0)), ('E', (0, 2, 2, 0, 0, 2))],
    '9sus4': [('C', (None, 3, 3, 3, 3, 3)), ('A', (None, 0, 2, 4, 3, 3))],
    '11': [('C', (None, 3, 2, 3, 3, 1))],
    'maj11': [('E', (None, None, 2, 1, 4, 5))],
    'min13': [('A', (None, 0, 2, 0, 1, 2)), ('E', (0, 2, 0, 0, 2, 0))],
}


def familiar_shapes(root, quality, tuning, highest_fret):
    from tuning import parse_tuning
    _, _, pitches = parse_tuning(tuning)
    standard = (40, 45, 50, 55, 59, 64)
    if len(pitches) >= 6 and pitches[-6:] == standard:
        def adapt(shape):
            return (None,) * (len(pitches) - 6) + shape
    elif pitches == (28, 33, 38, 43):
        def adapt(shape):
            return shape[:4]
    else:
        return set()
    result = set()
    for shape_root, shape in SHAPES.get(quality, ()):
        offset = (pitch_class(root) - pitch_class(shape_root)) % 12
        lowest = min(fret for fret in shape if fret is not None)
        while offset - 12 >= -lowest:
            offset -= 12
        while offset <= highest_fret:
            moved = adapt(tuple(None if fret is None else fret + offset for fret in shape))
            if max(fret for fret in moved if fret is not None) <= highest_fret:
                result.add(moved)
            offset += 12
    return result


def contiguous_strings(frets):
    sounded = [i for i, fret in enumerate(frets) if fret is not None]
    return bool(sounded) and len(sounded) == sounded[-1] - sounded[0] + 1
