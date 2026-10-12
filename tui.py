"""Textual chord explorer with a settings sidebar and saved progressions."""

from pathlib import Path

from rich.cells import cell_len
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, HorizontalScroll, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Checkbox, Footer, Input, Label, Select, Static
from textual.worker import get_current_worker

from chords import (CHORD_TYPES, KEY_KINDS, ROOT_NAMES, chord_symbol, chords_in_key,
                    clean_note, pitch_class, scale_notes)
from tuning import parse_tuning
from voicings import ProgressionStore, Settings, iter_ranked_voicings, sort_voicings


class VoicingCard(Static, can_focus=True):
    BINDINGS = [
        Binding('enter', 'choose', 'Add chord'),
        Binding('right', 'move(1)', show=False), Binding('left', 'move(-1)', show=False),
        Binding('down', 'row(1)', show=False), Binding('up', 'row(-1)', show=False),
        Binding('delete,backspace', 'remove', show=False),
    ]

    class Chosen(Message):
        def __init__(self, card):
            super().__init__()
            self.card = card

    def __init__(self, voicing, index, mode, progression=False, start_fret=None):
        super().__init__(classes='voicing-card progression-card' if progression else 'voicing-card')
        self.voicing = voicing
        self.index = index
        self.progression = progression
        stars = round(voicing.score / 20)
        text = Text(no_wrap=True, overflow='crop')
        text.append(f'{index + 1}. {voicing.name}', style='bold #b990ff')
        text.append(f'  {voicing.score}\n', style='#ace36c')
        text.append('★' * stars + '☆' * (5 - stars), style='#ace36c')
        text.append('\n')
        diagram = Text(voicing.diagram(mode, start_fret=start_fret), style='#c5c0d2')
        diagram.highlight_regex('●', style='bold #ace36c')
        diagram.highlight_regex('[║│┼┤]', style='#76618f')
        diagram.highlight_regex(r'\bo\b', style='#67dce2')
        text.append_text(diagram)
        text.append(f'\n{voicing.numbers}\n', style='bold #f3ecff')
        fingers = 'finger' if voicing.fingers == 1 else 'fingers'
        text.append(f'{voicing.fingers} {fingers} (est.) · span {voicing.span}', style='#99909f')
        if voicing.omitted_notes:
            text.append('\nOmitted: ' + ' '.join(voicing.omitted_notes), style='#99909f')
        if progression:
            # Include both borders and horizontal padding in the card width.
            self.styles.width = max(32, max(map(cell_len, text.plain.splitlines())) + 4)
        self.update(text)

    def on_click(self, event):
        event.stop()
        self.focus()
        self.action_choose()

    def action_choose(self):
        self.post_message(self.Chosen(self))

    def action_move(self, direction):
        self.app.move_card(self, direction)

    def action_row(self, direction):
        self.app.move_card(self, direction if self.progression else direction * self.app.columns)

    def action_remove(self):
        if self.progression:
            self.app.remove_progression(self.index)


class NeckromancerApp(App):
    TITLE = 'Neckromancer'
    CSS_PATH = 'tui.tcss'
    BINDINGS = [
        Binding('ctrl+g', 'generate', 'Generate'),
        Binding('pageup', 'previous_page', 'Prev page'),
        Binding('pagedown', 'next_page', 'Next page'),
        Binding('ctrl+s', 'save', 'Save'),
        Binding('ctrl+l', 'load', 'Load'),
        Binding('ctrl+n', 'new', 'New progression'),
        Binding('ctrl+left', 'reorder(-1)', 'Move left', show=False),
        Binding('ctrl+right', 'reorder(1)', 'Move right', show=False),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    def __init__(self, settings=None, progression_dir=None):
        super().__init__()
        self.settings = settings or Settings()
        self.store = ProgressionStore(progression_dir or Path.cwd() / 'progressions')
        self.results = []
        self.visible_results = []
        self.progression = []
        self.selected_progression = None
        self.columns = 2
        self.page = 0
        self.generation = 0
        self.searching = False
        self.generation_error = ''
        self.ready = False

    def compose(self) -> ComposeResult:
        s = self.settings
        with Horizontal(id='masthead'):
            yield Static('NECKROMANCER [dim]v0.2[/]', id='brand')
            yield Static('THE CHORD EXPLORER', id='tagline')
        with Horizontal(id='workspace'):
            with VerticalScroll(id='settings'):
                yield Label('SETTINGS', classes='section-title')
                yield Label('TUNING · LOW → HIGH', classes='field-label')
                yield Input(' '.join(s.tuning), id='tuning', compact=True)
                yield Select([
                    ('Standard · 6 strings', 'E A D G B E'),
                    ('Drop D · 6 strings', 'D A D G B E'),
                    ('Standard · 7 strings', 'B E A D G B E'),
                    ('Standard · 8 strings', 'F# B E A D G B E'),
                    ('Bass · 4 strings', 'E A D G'),
                ], prompt='Tuning presets', id='preset', compact=True)
                yield Label('KEY', classes='field-label')
                yield Select([('Any key', '')] + [
                    (note, note) for note in dict.fromkeys((*ROOT_NAMES, s.key_root)) if note],
                    value=s.key_root, allow_blank=False, id='key-root', compact=True)
                yield Select([(label, kind) for kind, label in KEY_KINDS.items()],
                             value=s.key_kind, allow_blank=False, id='key-kind', compact=True)
                yield Static('', id='key-info', classes='hint')
                yield Label('CHORD ROOT', classes='field-label')
                yield Select([(note, note) for note in dict.fromkeys((*ROOT_NAMES, s.root))], value=s.root,
                             allow_blank=False, id='root', compact=True)
                yield Label('CHORD QUALITY', classes='field-label')
                yield Select([(quality, quality) for quality in CHORD_TYPES], value=s.quality,
                             allow_blank=False, id='quality', compact=True)
                yield Label('CUSTOM TONES · OPTIONAL', classes='field-label')
                yield Input(' '.join(s.custom_notes), placeholder='e.g. C E G Bb', id='notes', compact=True)
                yield Label('HIGHEST FRET', classes='field-label')
                yield Input(str(s.frets), type='integer', id='frets', compact=True)
                yield Label('FRETS PER WINDOW', classes='field-label')
                yield Input(str(s.window), type='integer', id='window', compact=True)
                yield Label('MAXIMUM FRET STRETCH', classes='field-label')
                yield Input(str(s.max_span), type='integer', id='span', compact=True)
                yield Label('MINIMUM SCORE · 0–100', classes='field-label')
                yield Input(str(s.min_score), type='integer', id='score', compact=True)
                yield Label('VOICING SET', classes='field-label')
                yield Select([('Common guitar shapes', 'familiar'),
                              ('Strummable shapes', 'guitar'),
                              ('All tone combinations', 'all')],
                             value=s.style, allow_blank=False, id='style', compact=True)
                yield Label('FILTERS', classes='field-label')
                yield Checkbox('Root in bass', value=s.root_bass, id='root-bass', compact=True)
                yield Checkbox('Prefer open strings', value=s.prefer_open, id='open', compact=True)
                yield Checkbox('Allow barre chords', value=s.allow_barre, id='barre', compact=True)
                yield Checkbox('Require every chord tone', value=s.complete, id='complete', compact=True)
                yield Static('Up to 4 fingers; open strings do not count toward stretch.',
                             classes='hint')
                yield Button('Apply settings  ^G', id='generate', variant='primary')
                yield Label('SAVED PROGRESSIONS', classes='field-label')
                yield Select([(name, name) for name in self.store.names()],
                             prompt='Choose a progression', id='saved', compact=True)
                yield Input(placeholder='progression_name', value='my_progression', id='filename', compact=True)
                with Horizontal(classes='button-row'):
                    yield Button('Load', id='load')
                    yield Button('Save', id='save')
                    yield Button('New', id='new')
            with Vertical(id='main'):
                with Vertical(id='voicings-panel'):
                    with Horizontal(id='toolbar'):
                        yield Static('VOICINGS', id='result-title')
                        yield Select([('Score ↓', 'score'), ('Position ↑', 'position')],
                                     allow_blank=False, value='score', id='sort', compact=True)
                        yield Select([('Fretboard', 'fretboard'), ('Tablature', 'tab'), ('Both', 'both')],
                                     allow_blank=False, value='fretboard', id='view', compact=True)
                        yield Select([('All positions', 'all')], allow_blank=False,
                                     value='all', id='position', compact=True)
                    yield Static('', id='chord-info')
                    with VerticalScroll(id='results-scroll'):
                        yield Grid(id='cards')
                        yield Static('', id='empty')
                    with Horizontal(id='pagination'):
                        yield Static('Click a voicing or press Enter to add it.', id='card-help')
                        yield Button('‹', id='previous')
                        yield Static('Page 1 / 1', id='page-label')
                        yield Button('›', id='next')
                with Vertical(id='progression-panel'):
                    with Horizontal(id='progression-heading'):
                        yield Static('PROGRESSION / PLAYLIST', id='progression-title')
                        yield Button('Remove', id='remove')
                        yield Button('←', id='move-left')
                        yield Button('→', id='move-right')
                    yield HorizontalScroll(id='progression')
        yield Static('Ready', id='status')
        yield Footer()

    def on_mount(self):
        self.ready = True
        self.resize_columns()
        self.sync_key_choices()
        self.action_generate()
        self.call_later(self.render_progression)

    def on_resize(self, event):
        if self.ready:
            self.resize_columns(event.size.width)

    def resize_columns(self, width=None):
        sidebar_width = int(self.query_one('#settings').styles.width.value)
        label_width = max(map(cell_len, parse_tuning(self.settings.tuning)[1]))
        card_width = max(32, label_width + 8 + 4 * min(self.settings.window, self.settings.frets))
        # Workspace padding, sidebar margin, panel border/padding, grid gutter.
        columns = max(1, min(5, ((width or self.size.width) - sidebar_width - 6) // (card_width + 1)))
        if columns != self.columns:
            self.columns = columns
            self.page = 0
            self.query_one('#cards', Grid).styles.grid_size_columns = columns
            self.call_later(self.render_results)

    def status(self, message, error=False):
        self.query_one('#status', Static).update(Text(message, style='#ff9898' if error else '#aaa0ba'))

    def sync_key_choices(self):
        """Keep chord menus inside the chosen scale without emitting changes."""
        key_root = self.query_one('#key-root', Select).value
        kind = self.query_one('#key-kind', Select).value
        root_select = self.query_one('#root', Select)
        quality_select = self.query_one('#quality', Select)
        current_root, current_quality = root_select.value, quality_select.value
        if key_root:
            choices = chords_in_key(key_root, kind)
            roots = scale_notes(key_root, kind)
            selected_root = next((note for note in roots
                                  if pitch_class(note) == pitch_class(current_root)), roots[0])
            qualities = [quality for note, quality in choices if note == selected_root]
            triads = [chord_symbol(note, quality) for note, quality in choices
                      if quality in ('maj', 'min', 'dim', 'aug')]
            hint = f'{key_root} {KEY_KINDS[kind]} · {" ".join(roots)}\nTriads: {" · ".join(triads)}'
        else:
            roots = list(dict.fromkeys((*ROOT_NAMES, current_root)))
            selected_root = current_root
            qualities = list(CHORD_TYPES)
            hint = 'Any key · all chord roots and qualities available.'
        with self.prevent(Select.Changed):
            root_select.set_options([(note, note) for note in roots])
            root_select.value = selected_root
            quality_select.set_options([(quality, quality) for quality in qualities])
            quality_select.value = current_quality if current_quality in qualities else qualities[0]
        self.query_one('#key-info', Static).update(hint)

    def read_settings(self):
        def number(selector):
            try:
                return int(self.query_one(selector, Input).value)
            except ValueError:
                raise ValueError('Frets, stretch, and score must be whole numbers.') from None
        tuning, _, _ = parse_tuning(self.query_one('#tuning', Input).value)
        custom = tuple(dict.fromkeys(clean_note(n) for n in self.query_one('#notes', Input).value.split()))
        settings = Settings(
            tuning=tuning, root=str(self.query_one('#root', Select).value),
            quality=str(self.query_one('#quality', Select).value),
            frets=number('#frets'), max_span=number('#span'), min_score=number('#score'),
            root_bass=self.query_one('#root-bass', Checkbox).value,
            prefer_open=self.query_one('#open', Checkbox).value,
            allow_barre=self.query_one('#barre', Checkbox).value, custom_notes=custom,
            style=str(self.query_one('#style', Select).value),
            complete=self.query_one('#complete', Checkbox).value,
            window=number('#window'),
            key_root=str(self.query_one('#key-root', Select).value),
            key_kind=str(self.query_one('#key-kind', Select).value),
        )
        settings.validate()
        return settings

    def action_generate(self):
        try:
            settings = self.read_settings()
        except (ValueError, KeyError) as error:
            self.status(str(error), error=True)
            # Do not leave old out-of-key results visible after a key change.
            if self.query_one('#key-root', Select).value != self.settings.key_root or \
                    self.query_one('#key-kind', Select).value != self.settings.key_kind:
                self.generation += 1
                self.workers.cancel_group(self, 'generation')
                self.searching = False
                self.generation_error = str(error)
                self.results = []
                self.query_one('#chord-info', Static).update(str(error))
                self.call_later(self.render_results)
            return
        self.generation_error = ''
        self.settings = settings
        self.resize_columns()
        self.query_one('#style', Select).value = settings.style
        if not settings.key_root:
            root_select = self.query_one('#root', Select)
            with self.prevent(Select.Changed):
                root_select.set_options([(note, note) for note in dict.fromkeys((*ROOT_NAMES, settings.root))])
                root_select.value = settings.root
        positions = [('All positions', 'all')] + [
            (f'Frets {start}–{min(start + settings.window - 1, settings.frets)}', start)
            for start in range(1, max(1, settings.frets - settings.window + 1) + 1)
            if settings.frets > 0
        ]
        position = self.query_one('#position', Select)
        current = position.value
        position.set_options(positions)
        position.value = current if current in {value for _, value in positions} else 'all'
        self.generation += 1
        self.searching = True
        self.results = []
        self.page = 0
        self.query_one('#chord-info', Static).update(
            Text(f'{settings.name}  ·  {" ".join(settings.notes)}  |  '
                 f'key: {settings.key_name}  |  '
                 f'{len(settings.tuning)} strings  |  frets 0–{settings.frets}  |  '
                 f'{settings.window}-fret window  |  stretch ≤ {min(settings.max_span, settings.window - 1)}'))
        self.status('Finding voicings…')
        self.call_later(self.render_results)
        self.generate_voicings(settings, self.generation)

    @work(thread=True, exclusive=True, group='generation', exit_on_error=False)
    def generate_voicings(self, settings, generation):
        worker = get_current_worker()
        results = []
        for voicing in iter_ranked_voicings(settings, cancelled=lambda: worker.is_cancelled):
            if worker.is_cancelled:
                return
            results.append(voicing)
            if len(results) % 1000 == 0:
                self.call_from_thread(self.generation_progress, generation, len(results))
        if not worker.is_cancelled:
            self.call_from_thread(self.generation_finished, generation, sort_voicings(results))

    def generation_progress(self, generation, count):
        if generation == self.generation:
            self.status(f'Finding voicings… {count:,} candidates checked. Change settings to restart.')

    def generation_finished(self, generation, results):
        if generation != self.generation:
            return
        self.searching = False
        self.results = results
        self.call_later(self.render_results)
        self.status(f'{len(results):,} voicings found · {self.settings.style}. Finger counts and scores are estimates.')

    @on(Select.Changed, '#preset')
    def preset_changed(self, event):
        if event.value is not Select.NULL:
            self.query_one('#tuning', Input).value = str(event.value)
            if self.ready:
                self.action_generate()

    @on(Select.Changed, '#key-root')
    @on(Select.Changed, '#key-kind')
    def key_changed(self, event):
        if self.ready and event.value == event.select.value:
            self.sync_key_choices()
            self.action_generate()

    @on(Select.Changed, '#root')
    @on(Select.Changed, '#quality')
    def chord_changed(self, event):
        if self.ready and self.query_one('#key-root', Select).value and event.value == event.select.value:
            self.sync_key_choices()
            self.action_generate()

    @on(Select.Changed, '#sort')
    @on(Select.Changed, '#view')
    @on(Select.Changed, '#position')
    async def display_changed(self):
        if self.ready:
            await self.render_results()
            await self.render_progression()

    @on(Button.Pressed)
    def button_pressed(self, event):
        actions = {
            'generate': self.action_generate, 'previous': self.action_previous_page,
            'next': self.action_next_page, 'save': self.action_save, 'load': self.action_load,
            'new': self.action_new, 'remove': self.action_remove,
            'move-left': lambda: self.action_reorder(-1),
            'move-right': lambda: self.action_reorder(1),
        }
        if event.button.id in actions:
            actions[event.button.id]()

    @on(Input.Submitted)
    def input_submitted(self, event):
        if event.input.id == 'filename':
            self.action_save()
        else:
            self.action_generate()

    @property
    def page_size(self):
        return self.columns * 2

    @property
    def page_count(self):
        return max(1, (len(self.visible_results) + self.page_size - 1) // self.page_size)

    async def render_results(self):
        order = str(self.query_one('#sort', Select).value)
        self.visible_results = sort_voicings(
            [v for v in self.results if v.score >= self.settings.min_score], order)
        position = self.query_one('#position', Select).value
        if isinstance(position, int):
            end = min(position + self.settings.window - 1, self.settings.frets)
            self.visible_results = [v for v in self.visible_results
                                    if all(position <= fret <= end for fret in v.frets
                                           if fret is not None and fret > 0)
                                    and (position == 1 or any(f is not None and f > 0 for f in v.frets))]
        self.page = min(self.page, self.page_count - 1)
        self.query_one('#result-title', Static).update(Text(
            f'VOICINGS · {self.settings.name} ({len(self.visible_results):,})', style='bold #b990ff'))
        grid = self.query_one('#cards', Grid)
        await grid.remove_children()
        mode = str(self.query_one('#view', Select).value)
        start = self.page * self.page_size
        cards = [VoicingCard(v, start + i, mode, start_fret=position if isinstance(position, int) else None)
                 for i, v in enumerate(self.visible_results[start:start + self.page_size])]
        if cards:
            await grid.mount(*cards)
        empty = self.query_one('#empty', Static)
        empty.display = not cards
        empty.update(self.generation_error or ('Finding voicings…' if self.searching else
                     ('No common reference shapes match these settings.\n'
                      'Try a lower score, a higher fret limit, or Strummable shapes, then Apply settings.'
                      if self.settings.style == 'familiar' else
                      'No matching voicings.\nTry a lower score, a higher fret limit, or fewer custom tones.')))
        self.query_one('#page-label', Static).update(f'Page {self.page + 1} / {self.page_count}')
        self.query_one('#previous', Button).disabled = self.page == 0
        self.query_one('#next', Button).disabled = self.page >= self.page_count - 1

    async def render_progression(self):
        strip = self.query_one('#progression', HorizontalScroll)
        await strip.remove_children()
        mode = str(self.query_one('#view', Select).value)
        cards = [VoicingCard(v, index, mode, progression=True)
                 for index, v in enumerate(self.progression)]
        if cards:
            await strip.mount(*cards)
            if self.selected_progression is not None and self.selected_progression < len(cards):
                cards[self.selected_progression].add_class('selected')
        else:
            await strip.mount(Static('＋\nChoose voicings above to build a progression.', id='progression-empty'))
        self.query_one('#progression-title', Static).update(
            f'PROGRESSION / PLAYLIST · {len(self.progression)} chords')
        for selector in ('#remove', '#move-left', '#move-right'):
            self.query_one(selector, Button).disabled = not self.progression

    @on(VoicingCard.Chosen)
    async def card_chosen(self, event):
        card = event.card
        if card.progression:
            self.selected_progression = card.index
            for item in self.query('.progression-card'):
                item.set_class(item.index == card.index, 'selected')
            self.status(f'Selected chord {card.index + 1}. Delete removes; Ctrl+←/→ reorders.')
        else:
            self.progression.append(card.voicing)
            self.selected_progression = len(self.progression) - 1
            await self.render_progression()
            self.status(f'Added {card.voicing.name}: {card.voicing.numbers}')

    def move_card(self, card, offset):
        container = '#progression' if card.progression else '#cards'
        cards = list(self.query_one(container).query(VoicingCard))
        index = cards.index(card)
        target = index + offset
        if 0 <= target < len(cards):
            cards[target].focus()
            if card.progression:
                self.selected_progression = cards[target].index
                for item in cards:
                    item.set_class(item.index == self.selected_progression, 'selected')

    def action_next_page(self):
        if self.page + 1 < self.page_count:
            self.page += 1
            self.call_later(self.render_results)

    def action_previous_page(self):
        if self.page:
            self.page -= 1
            self.call_later(self.render_results)

    def remove_progression(self, index):
        if 0 <= index < len(self.progression):
            self.progression.pop(index)
            self.selected_progression = min(index, len(self.progression) - 1) if self.progression else None
            self.call_later(self.render_progression)
            self.status('Chord removed from progression.')

    def action_remove(self):
        if self.selected_progression is not None:
            self.remove_progression(self.selected_progression)

    def action_reorder(self, offset):
        index = self.selected_progression
        if index is not None and 0 <= index + offset < len(self.progression):
            self.progression[index], self.progression[index + offset] = (
                self.progression[index + offset], self.progression[index])
            self.selected_progression += offset
            self.call_later(self.render_progression)

    def action_new(self):
        self.progression = []
        self.selected_progression = None
        self.call_later(self.render_progression)
        self.status('New progression. Saved files are available in the sidebar.')

    def action_save(self):
        name = self.query_one('#filename', Input).value.strip()
        try:
            self.store.save(name, self.progression)
        except (ValueError, OSError) as error:
            self.status(str(error), error=True)
            return
        saved = self.query_one('#saved', Select)
        saved.set_options([(name, name) for name in self.store.names()])
        saved.value = name
        self.status(f'Saved {name}.json ({len(self.progression)} chords).')

    def action_load(self):
        selected = self.query_one('#saved', Select).value
        name = (self.query_one('#filename', Input).value.strip()
                if selected is Select.NULL else str(selected))
        try:
            progression = self.store.load(name)
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.status(f'Could not load progression: {error}', error=True)
            return
        self.progression = progression
        self.selected_progression = 0 if progression else None
        self.query_one('#filename', Input).value = name
        self.call_later(self.render_progression)
        self.status(f'Loaded {name}.json ({len(progression)} chords).')


if __name__ == '__main__':
    NeckromancerApp().run()
