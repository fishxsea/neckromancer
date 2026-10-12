from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from textual.widgets import Checkbox, Input, Select

from rich.cells import cell_len

from chords import CHORD_TYPES, ROOT_NAMES, pitch_class
from tui import NeckromancerApp, VoicingCard
from voicings import Settings


class TerminalTests(unittest.IsolatedAsyncioTestCase):
    async def settle(self, app, pilot):
        await app.workers.wait_for_complete()
        await pilot.pause()

    async def test_key_controls_restrict_chord_choices_and_regenerate(self):
        app = NeckromancerApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await self.settle(app, pilot)
            key = app.query_one('#key-root', Select)
            root = app.query_one('#root', Select)
            quality = app.query_one('#quality', Select)
            key.value = 'C'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(root._legal_values, {'C', 'D', 'E', 'F', 'G', 'A', 'B'})
            self.assertIn('maj7', quality._legal_values)
            self.assertNotIn('7', quality._legal_values)
            root.value = 'D'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(app.settings.root, 'D')
            self.assertEqual(app.settings.quality, 'min')
            self.assertTrue(app.results)
            self.assertTrue(all({pitch_class(n) for n in v.sounding_notes}
                                <= {0, 2, 4, 5, 7, 9, 11} for v in app.results))
            key.value = 'Bb'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(root._legal_values, {'Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'})
            self.assertEqual(app.settings.quality, 'min')
            key.value = ''
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(root._legal_values, set(ROOT_NAMES))
            self.assertEqual(quality._legal_values, set(CHORD_TYPES))

    async def test_minor_modes_and_out_of_key_custom_tones(self):
        app = NeckromancerApp(Settings(root='E', quality='7'))
        async with app.run_test(size=(160, 60)) as pilot:
            await self.settle(app, pilot)
            app.query_one('#key-root', Select).value = 'A'
            app.query_one('#key-kind', Select).value = 'harmonic_min'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(app.settings.quality, '7')
            self.assertTrue(app.results)
            app.query_one('#key-kind', Select).value = 'min'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertEqual(app.settings.quality, 'min')
            self.assertNotIn('7', app.query_one('#quality', Select)._legal_values)
            app.query_one('#notes', Input).value = 'E G# B'
            app.query_one('#key-root', Select).value = 'C'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertIn('outside C Natural minor', app.query_one('#status').render().plain)
            self.assertEqual(app.results, [])
            self.assertEqual(len(app.query('#cards VoicingCard')), 0)
            app.query_one('#notes', Input).value = ''
            app.action_generate()
            await self.settle(app, pilot)
            self.assertEqual(app.settings.key_root, 'C')

    async def test_wide_progression_diagrams_fit_and_scroll(self):
        app = NeckromancerApp(Settings(window=12))
        async with app.run_test(size=(180, 60)) as pilot:
            await self.settle(app, pilot)
            self.assertEqual(app.columns, 2)
            for card in app.query('#cards VoicingCard'):
                self.assertGreaterEqual(card.content_size.width,
                                        max(map(cell_len, card.voicing.diagram().splitlines())))
            wide = app.results[0]
            app.progression = [wide, replace(wide, window=5), wide]
            await app.render_progression()
            await pilot.pause()
            cards = list(app.query('#progression VoicingCard'))
            for card in cards:
                self.assertGreaterEqual(card.content_size.width,
                                        max(map(cell_len, card.render().plain.splitlines())))
                rendered = [strip.text for strip in card.render_lines(card.region.reset_offset)]
                for line in card.voicing.diagram().splitlines():
                    self.assertTrue(any(line in row for row in rendered), (line, rendered))
            self.assertGreater(cards[0].size.width, cards[1].size.width)
            self.assertTrue(app.query_one('#progression').show_horizontal_scrollbar)
            await pilot.resize_terminal(100, 48)
            await pilot.pause()
            self.assertEqual(app.columns, 1)
            self.assertGreaterEqual(cards[0].content_size.width, 53)

    async def test_navigation_progression_roundtrip_and_reordering(self):
        with TemporaryDirectory() as folder:
            app = NeckromancerApp(Settings(style='guitar'), progression_dir=folder)
            async with app.run_test(size=(160, 60)) as pilot:
                await self.settle(app, pilot)
                cards = list(app.query('#cards VoicingCard'))
                self.assertTrue(cards)
                cards[0].focus()
                await pilot.press('enter', 'right', 'enter')
                await pilot.pause()
                self.assertEqual(len(app.progression), 2)
                original = list(app.progression)
                app.action_reorder(-1)
                await pilot.pause()
                self.assertEqual(app.progression, original[::-1])
                app.action_save()
                self.assertTrue(Path(folder, 'my_progression.json').exists())
                app.action_new()
                await pilot.pause()
                self.assertEqual(app.progression, [])
                app.action_load()
                await pilot.pause()
                self.assertEqual(app.progression, original[::-1])
                strip = list(app.query('#progression VoicingCard'))
                strip[0].focus()
                await pilot.press('delete')
                await pilot.pause()
                self.assertEqual(len(app.progression), 1)
                app.action_next_page()
                await pilot.pause()
                self.assertEqual(app.page, 1)

    async def test_tuning_view_score_and_invalid_settings(self):
        app = NeckromancerApp(Settings(style='guitar', root_bass=False))
        async with app.run_test(size=(120, 48)) as pilot:
            await self.settle(app, pilot)
            app.query_one('#preset', Select).value = 'B E A D G B E'
            await pilot.pause()
            await self.settle(app, pilot)
            self.assertTrue(app.results)
            self.assertTrue(all(len(v.frets) == 7 for v in app.results))
            app.query_one('#view', Select).value = 'tab'
            await pilot.pause()
            self.assertTrue(all(len(c.voicing.diagram('tab').splitlines()) == 7
                                for c in app.query('#cards VoicingCard')))
            app.query_one('#score', Input).value = '100'
            app.action_generate()
            await self.settle(app, pilot)
            self.assertTrue(all(v.score >= 100 for v in app.visible_results))
            previous = app.settings
            app.query_one('#tuning', Input).value = 'invalid'
            app.action_generate()
            self.assertEqual(app.settings, previous)
            self.assertIn('Unknown note', app.query_one('#status').render().plain)

    async def test_mouse_filters_and_layout_resize(self):
        app = NeckromancerApp(Settings(style='guitar', root_bass=False))
        async with app.run_test(size=(160, 60)) as pilot:
            await self.settle(app, pilot)
            self.assertFalse(app.query_one('#root-bass', Checkbox).value)
            await pilot.click('#root-bass')
            await pilot.press('ctrl+g')
            await self.settle(app, pilot)
            self.assertTrue(app.settings.root_bass)
            card = app.query_one('#cards VoicingCard', VoicingCard)
            await pilot.click(card)
            await pilot.pause()
            self.assertEqual(len(app.progression), 1)
            app.query_one('#sort', Select).value = 'position'
            await pilot.pause()
            await pilot.resize_terminal(90, 45)
            await pilot.pause()
            self.assertEqual(app.columns, 1)
            self.assertEqual(len(app.query('#cards VoicingCard')), 2)

    async def test_sliding_fret_windows_cover_the_neck(self):
        app = NeckromancerApp()
        async with app.run_test(size=(140, 54)) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(any(max(f for f in v.frets if f is not None) > 5 for v in app.results))
            position = app.query_one('#position', Select)
            for start in (1, 2, 3, 8, 20):
                position.value = start
                await pilot.pause()
                for card in app.query('#cards VoicingCard'):
                    self.assertTrue(all(start <= fret <= start + 4 for fret in card.voicing.frets
                                        if fret is not None and fret > 0))
                    header = card.voicing.diagram(start_fret=start).splitlines()[0]
                    self.assertEqual(header.split(), [str(fret) for fret in range(start, start + 5)])
            position.value = 'all'
            await pilot.pause()
            self.assertEqual(len(app.visible_results), len(app.results))


if __name__ == '__main__':
    unittest.main()
