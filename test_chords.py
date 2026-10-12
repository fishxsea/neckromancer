import itertools
import unittest

from chords import chord_notes
from fretboard import Mapper
from tab_maker import TabMaker


class VoicingTests(unittest.TestCase):
    def test_generator_matches_independent_brute_force(self):
        board = Mapper(tuning='C E G C', fret_amount=5).fretboard
        required = {'C', 'E', 'G'}
        expected = set()
        for voicing in itertools.product([None, *range(6)], repeat=4):
            sounding = {board[i][fret][1] for i, fret in enumerate(voicing)
                        if fret is not None}
            if sounding == required:
                expected.add(voicing)
        generated = list(TabMaker(board, required).iter_voicings())
        self.assertEqual(set(generated), expected)
        self.assertEqual(len(generated), len(expected))

    def test_known_open_chord_and_span(self):
        tab = TabMaker(Mapper(fret_amount=12).fretboard, ['C', 'E', 'G'])
        unrestricted = set(tab.iter_voicings())
        self.assertIn((None, 3, 2, 0, 1, 0), unrestricted)
        expected = {v for v in unrestricted
                    if max([f for f in v if f is not None and f > 0], default=0)
                    - min([f for f in v if f is not None and f > 0], default=0) <= 2}
        self.assertEqual(set(tab.iter_voicings(max_span=2)), expected)

    def test_muted_and_double_digit_tab(self):
        tab = TabMaker(Mapper().fretboard, ['C', 'E', 'G'])
        voicing = (None, 3, 2, 0, 1, 12)
        self.assertEqual(tab.number_string(voicing), 'x 3 2 0 1 12')
        lines = tab.graphic_tab(voicing).splitlines()
        self.assertEqual(lines[0].split(), [str(fret) for fret in range(1, 13)])
        self.assertTrue(lines[1].startswith('E   ║'))
        self.assertTrue(lines[1].endswith('─●─┤'))
        self.assertTrue(lines[-1].startswith('E x ║'))
        self.assertEqual(sum(line.count('●') for line in lines), 4)
        self.assertEqual(len(set(map(len, lines[1:]))), 1)

    def test_impossible_chord_and_all_open(self):
        tab = TabMaker(Mapper(fret_amount=0).fretboard, ['C', 'E', 'G'])
        self.assertEqual(list(tab.iter_voicings()), [])
        tab = TabMaker(Mapper(tuning='C E G', fret_amount=0).fretboard, ['C', 'E', 'G'])
        self.assertEqual(list(tab.iter_voicings(max_span=0)), [(0, 0, 0)])

    def test_chromatic_chords_and_flat_tuning(self):
        self.assertEqual(chord_notes('Bb', '7'), ['Bb', 'D', 'F', 'Ab'])
        self.assertEqual(Mapper(tuning='Eb Ab Db Gb Bb Eb').tuning,
                         ['D#', 'G#', 'C#', 'F#', 'A#', 'D#'])


if __name__ == '__main__':
    unittest.main()
