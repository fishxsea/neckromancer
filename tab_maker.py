"""Enumerate chord voicings and render plain-text guitar tablature."""

from chords import normalize_note


class TabMaker:
    def __init__(self, fretboard, chord, tab_size=5, string_labels=None):
        if not fretboard or any(not string for string in fretboard):
            raise ValueError('The fretboard must contain nonempty strings.')
        if not chord:
            raise ValueError('A chord must contain at least one note.')
        self.fretboard = fretboard
        self.chord = chord
        self.tab_size = tab_size
        self.open_notes = (list(string_labels) if string_labels is not None else
                           [string[0][1] for string in fretboard])
        if len(self.open_notes) != len(fretboard):
            raise ValueError('There must be one label per string.')
        self.string_amount = len(self.open_notes)
        self.all_string_tabs = []

    def iter_voicings(self, max_span=None, cancelled=None, required_notes=None):
        """Yield every voicing containing all chord tones, low string first.

        None represents a muted string. Repeated tones, inversions and open
        strings are allowed. Optional span measures fretted notes only.
        """
        if max_span is not None and max_span < 0:
            raise ValueError('Maximum fret span must be nonnegative.')
        allowed = frozenset(normalize_note(note) for note in self.chord)
        required = (allowed if required_notes is None else
                    frozenset(normalize_note(note) for note in required_notes))
        if not required or not required <= allowed:
            raise ValueError('Required chord tones must be a nonempty subset of the allowed tones.')
        choices = [
            [(None, None)] + [(fret, normalize_note(note)) for fret, note in string
                              if normalize_note(note) in allowed]
            for string in self.fretboard
        ]
        remaining = [frozenset() for _ in range(len(choices) + 1)]
        for index in range(len(choices) - 1, -1, -1):
            remaining[index] = remaining[index + 1] | frozenset(
                note for _, note in choices[index] if note is not None
            )

        def visit(index, voicing, covered, low, high):
            if cancelled is not None and cancelled():
                return
            missing = required - covered
            if len(missing) > len(choices) - index or not missing <= remaining[index]:
                return
            if index == len(choices):
                yield tuple(voicing)
                return
            for fret, note in choices[index]:
                next_low, next_high = low, high
                if fret is not None and fret > 0:
                    next_low = fret if low is None else min(low, fret)
                    next_high = fret if high is None else max(high, fret)
                    if max_span is not None and next_high - next_low > max_span:
                        continue
                voicing.append(fret)
                yield from visit(index + 1, voicing,
                                 covered if note is None else covered | {note},
                                 next_low, next_high)
                voicing.pop()

        yield from visit(0, [], frozenset(), None, None)

    @staticmethod
    def number_string(voicing):
        return ' '.join('x' if fret is None else str(fret) for fret in voicing)

    def graphic_tab(self, voicing, compact=False, start_fret=None):
        """Draw one horizontal string per tuning note, high to low."""
        if len(voicing) != self.string_amount:
            raise ValueError(f'A voicing must have {self.string_amount} string positions.')
        fretted = [fret for fret in voicing if fret is not None and fret > 0]
        highest_fret = max(len(string) - 1 for string in self.fretboard)
        first = min(fretted) if fretted and max(fretted) > self.tab_size else 1
        first = min(first, max(1, highest_fret - self.tab_size + 1))
        last = max(first + self.tab_size - 1, max(fretted, default=0))
        last = min(last, highest_fret)
        if start_fret is not None:
            if type(start_fret) is not int or not 1 <= start_fret <= max(1, highest_fret):
                raise ValueError('Invalid starting fret for the diagram.')
            first = start_fret
            last = min(first + self.tab_size - 1, highest_fret)
            if any(not first <= fret <= last for fret in fretted):
                raise ValueError('This voicing does not fit in the selected fret window.')
        frets = range(first, last + 1)
        label_width = max(map(len, self.open_notes))
        prefix_width = label_width + 3
        lines = [(' ' * (prefix_width + 1)
                  + ''.join(f'{fret:^3} ' for fret in frets)).rstrip()]
        boundary = '║' if first == 1 else '│'
        for index, string_index in enumerate(reversed(range(self.string_amount))):
            note, pressed = self.open_notes[string_index], voicing[string_index]
            marker = 'x' if pressed is None else 'o' if pressed == 0 else ' '
            cells = ['─●─' if pressed == fret else '───' for fret in frets]
            lines.append(f'{note:>{label_width}} {marker} {boundary}'
                         + '┼'.join(cells) + ('┤' if cells else ''))
            if not compact and index < self.string_amount - 1:
                lines.append(' ' * prefix_width + boundary
                             + '   │' * len(cells))
        return '\n'.join(lines)

    def tablature(self, voicing):
        """A simultaneous chord in standard tablature, highest string on top."""
        if len(voicing) != self.string_amount:
            raise ValueError(f'A voicing must have {self.string_amount} string positions.')
        tokens = ['x' if fret is None else str(fret) for fret in voicing]
        width = max(map(len, tokens))
        label_width = max(map(len, self.open_notes))
        return '\n'.join(
            f'{note:>{label_width}}|--{token.center(width, "-")}--|'
            for note, token in reversed(list(zip(self.open_notes, tokens)))
        )

    def build_str_tab(self, max_span=None):
        """Compatibility helper; prefer iter_voicings for large fretboards."""
        self.all_string_tabs = [self.number_string(v).split()
                                for v in self.iter_voicings(max_span)]
        return self.all_string_tabs

    def build_graphic_tab(self):
        for tab in self.all_string_tabs:
            voicing = tuple(None if fret == 'x' else int(fret) for fret in tab)
            print(self.graphic_tab(voicing))
            print(self.number_string(voicing))
            print()
