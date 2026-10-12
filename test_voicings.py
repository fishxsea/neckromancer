from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from chords import NOTES
from voicings import Settings, Voicing, ProgressionStore, finger_count, iter_ranked_voicings


class PlayabilityTests(unittest.TestCase):
    def test_barres_cannot_cross_open_or_lower_fretted_strings(self):
        self.assertEqual(finger_count((1, 3, 3, 2, 1, 1)), 3)
        self.assertEqual(finger_count((1, 0, 1, None, None, None)), 2)
        self.assertEqual(finger_count((3, 2, 3, None, None, None)), 3)
        self.assertEqual(finger_count((1, 3, 3, 2, 1, 1), allow_barre=False), 6)

    def test_higher_neck_keeps_span_finger_and_tone_constraints(self):
        settings = Settings(frets=24, root_bass=True, style='all', complete=True)
        results = list(iter_ranked_voicings(settings))
        self.assertTrue(results)
        self.assertTrue(any(22 in v.frets for v in results))
        for voicing in results:
            sounding = [NOTES[(NOTES.index(note) + fret) % 12]
                        for note, fret in zip(voicing.tuning, voicing.frets) if fret is not None]
            self.assertEqual(set(sounding), set(settings.notes))
            open_pitches = (4, 9, 14, 19, 23, 28)
            bass = min(pitch + fret for pitch, fret in zip(open_pitches, voicing.frets)
                       if fret is not None)
            self.assertEqual(NOTES[bass % 12], 'C')
            self.assertLessEqual(voicing.span, 4)
            self.assertLessEqual(voicing.fingers, 4)
            self.assertEqual(len(voicing.diagram().splitlines()[0].split()), 5)
        self.assertEqual(list(iter_ranked_voicings(settings, cancelled=lambda: True)), [])
        # Low E fretted at 20 is above the open G; G is the actual bass.
        self.assertFalse(any(v.frets == (20, None, None, 0, None, 0) for v in results))

    def test_default_known_open_chord_and_custom_string_count(self):
        results = list(iter_ranked_voicings(Settings(frets=5)))
        self.assertTrue(any(v.frets == (None, 3, 2, 0, 1, 0) for v in results))
        self.assertTrue(all(f <= 5 for v in results for f in v.frets if f is not None))
        settings = Settings(tuning=('C', 'E', 'G'), frets=0, style='all')
        self.assertEqual([v.frets for v in iter_ranked_voicings(settings)], [(0, 0, 0)])

    def test_score_prefers_open_strings_when_enabled(self):
        settings = Settings()
        with_preference = {v.frets: v.score for v in iter_ranked_voicings(settings)}
        without = {v.frets: v.score for v in iter_ranked_voicings(replace(settings, prefer_open=False))}
        open_c = (None, 3, 2, 0, 1, 0)
        self.assertGreater(with_preference[open_c], without[open_c])

    def test_standard_tab_aligns_simultaneous_multidigit_frets(self):
        voicing = Voicing('C', ('E', 'A', 'D', 'G', 'B', 'E'), ('C', 'E', 'G'),
                          (None, 3, 2, 0, 1, 12), 50, 4)
        tab = voicing.diagram('tab').splitlines()
        self.assertEqual(tab[0], 'E|--12--|')
        self.assertEqual(tab[-1], 'E|--x---|')
        self.assertEqual(len(set(map(len, tab))), 1)


class ProgressionTests(unittest.TestCase):
    def test_roundtrip_preserves_different_tunings_and_muted_strings(self):
        with TemporaryDirectory() as folder:
            store = ProgressionStore(folder)
            six = next(iter_ranked_voicings(Settings()))
            seven = next(iter_ranked_voicings(Settings(tuning=('B', 'E', 'A', 'D', 'G', 'B', 'E'))))
            store.save('test_loop', [six, seven])
            self.assertEqual(store.names(), ['test_loop'])
            self.assertEqual(store.load('test_loop'), [six, seven])
            with self.assertRaises(ValueError):
                store.save('../escape', [six])

    def test_bad_files_are_rejected_before_using_their_positions(self):
        voicing = next(iter_ranked_voicings(Settings())).to_dict()
        voicing['frets'] = [0]
        with self.assertRaises(ValueError):
            Voicing.from_dict(voicing)
        with TemporaryDirectory() as folder:
            Path(folder, 'broken.json').write_text(json.dumps({'version': 99, 'chords': []}))
            with self.assertRaises(ValueError):
                ProgressionStore(folder).load('broken')


if __name__ == '__main__':
    unittest.main()
