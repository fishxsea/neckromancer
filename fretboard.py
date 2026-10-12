"""Fretboard pitches and correctly spelled diatonic chords."""

from chords import NOTES, chord_notes, clean_note, normalize_note, pitch_class, scale_notes
from tuning import parse_tuning


class Mapper:
    def __init__(self, tuning='E A D G B E', fret_amount=24,
                 scale_root='C', scale_type='maj'):
        self.tuning_tokens, self.tuning_labels, self.open_pitches = parse_tuning(tuning)
        self.tuning = [normalize_note(note) for note in self.tuning_labels]
        if type(fret_amount) is not int or fret_amount < 0:
            raise ValueError('The fret count must be a nonnegative integer.')
        self.string_amount = len(self.tuning)
        self.fret_amount = fret_amount
        self.notes = list(NOTES)
        self.fretboard = self.build_fretboard()
        self.pitch_fretboard = [[pitch + fret for fret in range(fret_amount + 1)]
                               for pitch in self.open_pitches]
        self.scale_root = clean_note(scale_root)
        self.scale_type = scale_type
        self.scale = None
        self.chord = None
        self.chord_qualities = {'triad': (0, 2, 4), '7th': (0, 2, 4, 6),
                                '9th': (0, 2, 4, 6, 8),
                                '11th': (0, 2, 4, 6, 8, 10),
                                '13th': (0, 2, 4, 6, 8, 10, 12)}

    def build_fretboard(self):
        return [[(fret, NOTES[(pitch + fret) % 12])
                 for fret in range(self.fret_amount + 1)]
                for pitch in self.open_pitches]

    def build_scale(self):
        self.scale = scale_notes(self.scale_root, self.scale_type)
        return self.scale

    def build_chord(self, chord_name, quality):
        """Legacy '7th' stacks diatonic thirds; '7' means dominant seventh.

        Named qualities ('maj', 'min7', etc.) are relative to the chord root,
        independently of the selected key. A key's tonic need not be this root.
        """
        if quality in self.chord_qualities:
            if self.scale is None:
                self.build_scale()
            index = next((i for i, note in enumerate(self.scale)
                          if pitch_class(note) == pitch_class(chord_name)), None)
            if index is None:
                raise ValueError(f'{chord_name} is not in the selected scale.')
            self.chord = [self.scale[(index + degree) % 7]
                          for degree in self.chord_qualities[quality]]
        else:
            self.chord = chord_notes(chord_name, quality)
        return self.chord
