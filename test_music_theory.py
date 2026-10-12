from dataclasses import replace
import unittest

from chords import (chord_notes, chords_in_key, notes_in_key, pitch_class,
                    scale_notes, voicing_tones)
from fretboard import Mapper
from guitar_shapes import SHAPES, contiguous_strings
from tuning import parse_tuning
from voicings import Settings, iter_ranked_voicings, sort_voicings


class TheoryTests(unittest.TestCase):
    def test_major_and_minor_key_triads_and_sevenths(self):
        self.assertEqual([(root, quality) for root, quality in chords_in_key('C')
                          if quality in ('maj', 'min', 'dim', 'aug')],
                         [('C', 'maj'), ('D', 'min'), ('E', 'min'), ('F', 'maj'),
                          ('G', 'maj'), ('A', 'min'), ('B', 'dim')])
        self.assertEqual([(root, quality) for root, quality in chords_in_key('A', 'min')
                          if quality in ('maj', 'min', 'dim', 'aug')],
                         [('A', 'min'), ('B', 'dim'), ('C', 'maj'), ('D', 'min'),
                          ('E', 'min'), ('F', 'maj'), ('G', 'maj')])
        sevenths = [(root, quality) for root, quality in chords_in_key('C')
                    if quality in ('maj7', 'min7', '7', 'm7b5')]
        self.assertEqual(sevenths, [('C', 'maj7'), ('D', 'min7'), ('E', 'min7'),
                                    ('F', 'maj7'), ('G', '7'), ('A', 'min7'), ('B', 'm7b5')])
        self.assertNotIn(('E', '7'), chords_in_key('A', 'min'))
        self.assertIn(('E', '7'), chords_in_key('A', 'harmonic_min'))
        self.assertEqual(scale_notes('Bb'), ['Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'])
        self.assertTrue(notes_in_key(['A#', 'D', 'F'], 'Bb'))

    def test_key_filter_checks_full_formula_and_custom_tones(self):
        # Fmaj13's optional Bb is out of C major, even when a grip omits it.
        self.assertNotIn(('F', 'maj13'), chords_in_key('C'))
        with self.assertRaisesRegex(ValueError, 'outside C Major: Bb'):
            list(iter_ranked_voicings(Settings(root='F', quality='maj13', key_root='C')))
        with self.assertRaisesRegex(ValueError, 'outside C Major: C#'):
            Settings(custom_notes=('C', 'C#', 'G'), key_root='C').validate()
        Settings(custom_notes=('C', 'E', 'G'), key_root='C').validate()
        Settings(root='F', quality='maj13').validate()  # Any key remains unrestricted.
        with self.assertRaisesRegex(ValueError, 'Unknown key scale'):
            Settings(key_kind='invalid').validate()

    def test_key_filtered_shapes_across_tunings(self):
        for root, quality, key_root, key_kind, tuning in [
            ('G', '7', 'C', 'maj', ('E', 'A', 'D', 'G', 'B', 'E')),
            ('E', '7', 'A', 'harmonic_min', ('B', 'E', 'A', 'D', 'G', 'B', 'E')),
        ]:
            with self.subTest(root=root, key=key_root, mode=key_kind):
                settings = Settings(root=root, quality=quality, key_root=key_root,
                                    key_kind=key_kind, tuning=tuning)
                results = list(iter_ranked_voicings(settings))
                self.assertTrue(results)
                key_pitches = {pitch_class(n) for n in settings.key_notes}
                for voicing in results:
                    pitches = parse_tuning(voicing.tuning)[2]
                    self.assertTrue({(pitch + fret) % 12 for pitch, fret in zip(pitches, voicing.frets)
                                     if fret is not None} <= key_pitches)

    def test_chord_spelling_and_defining_intervals(self):
        cases = {
            ('C', 'maj'): ['C', 'E', 'G'],
            ('A', 'min'): ['A', 'C', 'E'],
            ('C', '7'): ['C', 'E', 'G', 'Bb'],
            ('C', 'maj7'): ['C', 'E', 'G', 'B'],
            ('E', 'min7'): ['E', 'G', 'B', 'D'],
            ('Bb', '7'): ['Bb', 'D', 'F', 'Ab'],
            ('C', 'dim7'): ['C', 'Eb', 'Gb', 'Bbb'],
            ('F#', 'maj'): ['F#', 'A#', 'C#'],
            ('G#', 'maj'): ['G#', 'B#', 'D#'],
            ('C', '9'): ['C', 'E', 'G', 'Bb', 'D'],
            ('C', '13'): ['C', 'E', 'G', 'Bb', 'D', 'F', 'A'],
        }
        for (root, quality), expected in cases.items():
            with self.subTest(root=root, quality=quality):
                self.assertEqual(chord_notes(root, quality), expected)

    def test_diatonic_stacks_and_absolute_quality_are_distinct(self):
        mapper = Mapper(scale_root='C')
        self.assertEqual(mapper.build_chord('C', '9th'), ['C', 'E', 'G', 'B', 'D'])
        self.assertEqual(mapper.build_chord('C', '13th'), ['C', 'E', 'G', 'B', 'D', 'F', 'A'])
        self.assertEqual(mapper.build_chord('G', '7th'), ['G', 'B', 'D', 'F'])
        self.assertEqual(mapper.build_chord('C', '7'), ['C', 'E', 'G', 'Bb'])
        mapper = Mapper(scale_root='Bb')
        self.assertEqual(mapper.build_scale(), ['Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'])
        self.assertEqual(mapper.build_chord('C', 'triad'), ['C', 'Eb', 'G'])
        with self.assertRaises(ValueError):
            mapper.build_chord('F#', 'triad')

    def test_practical_thirteenths_keep_the_third_seventh_and_thirteenth(self):
        allowed, required = voicing_tones('C', '13')
        self.assertEqual(set(required), {'C', 'E', 'Bb', 'A'})
        self.assertNotIn('F', allowed)
        results = list(iter_ranked_voicings(Settings(root='C', quality='13', style='guitar')))
        self.assertTrue(results)
        for voicing in results:
            self.assertTrue(set(required) <= set(voicing.sounding_notes) <= set(allowed))
        self.assertEqual(list(iter_ranked_voicings(Settings(root='C', quality='13',
                                                          style='all', complete=True))), [])
        self.assertEqual(voicing_tones('C', 'm7b5')[1], ('C', 'Eb', 'Gb', 'Bb'))

    def test_reference_shapes_have_their_advertised_chord_tones(self):
        pitches = (40, 45, 50, 55, 59, 64)
        for quality, shapes in SHAPES.items():
            for root, frets in shapes:
                with self.subTest(root=root, quality=quality, frets=frets):
                    allowed, required = voicing_tones(root, quality)
                    sounding = {(pitch + fret) % 12 for pitch, fret in zip(pitches, frets)
                                if fret is not None}
                    self.assertTrue({pitch_class(n) for n in required} <= sounding
                                    <= {pitch_class(n) for n in allowed})

    def test_real_registers_and_reentrant_tunings(self):
        self.assertEqual(parse_tuning('E A D G B E')[2], (40, 45, 50, 55, 59, 64))
        self.assertEqual(parse_tuning('E A D G')[2], (28, 33, 38, 43))
        self.assertEqual(parse_tuning('G4 C4 E4 A4')[2], (67, 60, 64, 69))
        self.assertEqual(parse_tuning('B#3 Cb4')[2], (60, 59))
        with self.assertRaises(ValueError):
            parse_tuning('E2 A D G B E')


class GuitarPracticalityTests(unittest.TestCase):
    def test_default_c_major_shows_conventional_shapes_and_ranks_open_c_first(self):
        results = sort_voicings(iter_ranked_voicings(Settings(frets=5)))
        self.assertEqual([v.frets for v in results], [
            (None, 3, 2, 0, 1, 0), (None, 3, 5, 5, 5, 3)])
        self.assertNotIn((None, 3, None, 0, None, 0), [v.frets for v in results])

    def test_common_open_and_barre_chords_survive_filters(self):
        examples = [('A', 'min', (None, 0, 2, 2, 1, 0)),
                    ('E', 'min', (0, 2, 2, 0, 0, 0)),
                    ('E', 'min7', (0, 2, 0, 0, 0, 0)),
                    ('F', 'maj', (1, 3, 3, 2, 1, 1)),
                    ('G', 'maj', (3, 2, 0, 0, 0, 3)),
                    ('D', 'maj', (None, None, 0, 2, 3, 2))]
        for root, quality, frets in examples:
            with self.subTest(root=root, quality=quality):
                results = list(iter_ranked_voicings(Settings(root=root, quality=quality)))
                self.assertIn(frets, [v.frets for v in results])
        # A closed C diminished reference can move down one fret to Bdim.
        results = list(iter_ranked_voicings(Settings(root='B', quality='dim')))
        self.assertIn((None, 2, 3, 4, 3, None), [v.frets for v in results])

    def test_strumming_filter_and_full_enumeration_are_explicit_choices(self):
        settings = Settings(style='guitar')
        strummable = list(iter_ranked_voicings(settings))
        self.assertTrue(strummable)
        self.assertTrue(all(contiguous_strings(v.frets) for v in strummable))
        all_voicings = list(iter_ranked_voicings(replace(settings, style='all')))
        self.assertGreater(len(all_voicings), len(strummable))
        self.assertTrue(any(not contiguous_strings(v.frets) for v in all_voicings))

    def test_inversions_are_labeled_by_the_actual_lowest_pitch(self):
        results = list(iter_ranked_voicings(Settings(style='all', root_bass=False)))
        inversion = next(v for v in results if v.frets == (0, 3, 2, 0, 1, 0))
        self.assertEqual(inversion.name, 'C/E')
        reentrant = Settings(tuning=('G4', 'C4', 'E4', 'A4'), frets=0,
                             root='C', quality='maj', style='guitar')
        results = list(iter_ranked_voicings(reentrant))
        self.assertEqual([v.frets for v in results], [(0, 0, 0, None)])
        self.assertEqual(results[0].name, 'C')

    def test_common_shapes_transpose_up_to_the_highest_fret_in_five_fret_windows(self):
        results = list(iter_ranked_voicings(Settings(root='C', quality='maj', frets=24)))
        self.assertTrue(any(min(f for f in v.frets if f is not None and f > 0) >= 15 for v in results))
        for voicing in results:
            self.assertLessEqual(max(f for f in voicing.frets if f is not None), 24)
            self.assertLessEqual(voicing.span, 4)
            self.assertEqual(len(voicing.diagram().splitlines()[0].split()), 5)


if __name__ == '__main__':
    unittest.main()
