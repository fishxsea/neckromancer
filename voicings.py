"""Scoring and persistence for the terminal chord explorer."""

from dataclasses import dataclass
import json
from pathlib import Path
import re

from chords import (CHORD_TYPES, KEY_KINDS, NOTES, chord_notes, chord_symbol, clean_note,
                    normalize_note, notes_in_key, pitch_class, scale_notes, voicing_tones)
from fretboard import Mapper
from guitar_shapes import contiguous_strings, familiar_shapes
from tab_maker import TabMaker
from tuning import parse_tuning


def finger_count(frets, allow_barre=True):
    """Estimate fingers, allowing a barre across higher fretted/muted strings.

    A lower fret, open string, or muted string interrupts a barre. Partial
    barres above the lowest fret are limited to two adjacent strings. This is an estimate,
    not a full model of wrist position, thumb use, or string muting technique.
    """
    if not allow_barre:
        return sum(fret is not None and fret > 0 for fret in frets)
    lowest_fret = min((f for f in frets if f is not None and f > 0), default=0)
    fingers = 0
    for fret in sorted({f for f in frets if f is not None and f > 0}):
        previous = None
        group_start = None
        for index, pressed in enumerate(frets):
            if pressed != fret:
                continue
            if (previous is None or any(
                f is None or f < fret for f in frets[previous + 1:index]
            ) or (fret != lowest_fret and index - group_start >= 2)):
                fingers += 1
                group_start = index
            previous = index
    return fingers


@dataclass(frozen=True)
class Settings:
    tuning: tuple = ('E', 'A', 'D', 'G', 'B', 'E')
    root: str = 'C'
    quality: str = 'maj'
    frets: int = 24
    max_span: int = 4
    min_score: int = 0
    root_bass: bool = True
    prefer_open: bool = True
    allow_barre: bool = True
    custom_notes: tuple = ()
    style: str = 'all'
    complete: bool = False
    window: int = 5
    key_root: str = ''
    key_kind: str = 'maj'

    def __post_init__(self):
        tokens, _, _ = parse_tuning(self.tuning)
        object.__setattr__(self, 'tuning', tokens)
        object.__setattr__(self, 'root', clean_note(self.root))
        if self.key_root:
            object.__setattr__(self, 'key_root', clean_note(self.key_root))
        object.__setattr__(self, 'custom_notes', tuple(clean_note(n) for n in self.custom_notes))
        if self.custom_notes:
            object.__setattr__(self, 'root', self.custom_notes[0])
        if self.custom_notes and self.style == 'familiar':
            object.__setattr__(self, 'style', 'guitar')

    @property
    def notes(self):
        return self.custom_notes or tuple(chord_notes(self.root, self.quality))

    @property
    def name(self):
        if self.custom_notes:
            return 'Custom'
        return chord_symbol(self.root, self.quality)

    @property
    def allowed_notes(self):
        return self.custom_notes or voicing_tones(self.root, self.quality, self.complete)[0]

    @property
    def required_notes(self):
        return self.custom_notes or voicing_tones(self.root, self.quality, self.complete)[1]

    @property
    def key_notes(self):
        return tuple(scale_notes(self.key_root, self.key_kind)) if self.key_root else ()

    @property
    def key_name(self):
        return f'{self.key_root} {KEY_KINDS[self.key_kind]}' if self.key_root else 'Any key'

    def validate(self):
        if not self.tuning:
            raise ValueError('Enter at least one tuning note.')
        if self.quality not in CHORD_TYPES:
            raise ValueError('Unknown chord quality.')
        if self.key_kind not in KEY_KINDS:
            raise ValueError('Unknown key scale.')
        if self.key_root and not notes_in_key(self.notes, self.key_root, self.key_kind):
            outside = [note for note in self.notes
                       if pitch_class(note) not in {pitch_class(n) for n in self.key_notes}]
            raise ValueError(f'{self.name} is outside {self.key_name}: {" ".join(outside)}. '
                             'Choose an in-key chord or Any key.')
        if self.style not in ('guitar', 'all', 'familiar'):
            raise ValueError('Unknown voicing style.')
        if self.frets < 0 or self.max_span < 0:
            raise ValueError('Frets and stretch must be nonnegative.')
        if type(self.window) is not int or self.window < 1:
            raise ValueError('The fret window must contain at least one fret.')
        if not 0 <= self.min_score <= 100:
            raise ValueError('Minimum score must be between 0 and 100.')


@dataclass(frozen=True)
class Voicing:
    name: str
    tuning: tuple
    notes: tuple
    frets: tuple
    score: int
    fingers: int
    root: str = ''
    quality: str = ''
    complete: bool = False
    highest_fret: int = 24
    window: int = 5

    @property
    def sounding_notes(self):
        mapper = Mapper(tuning=self.tuning, fret_amount=0)
        sounding = {((pitch + fret) % 12) for pitch, fret in zip(mapper.open_pitches, self.frets)
                    if fret is not None}
        return tuple(note for note in self.notes if pitch_class(note) in sounding)

    @property
    def omitted_notes(self):
        return tuple(note for note in self.notes if note not in self.sounding_notes)

    @property
    def numbers(self):
        return TabMaker.number_string(self.frets)

    @property
    def span(self):
        fretted = [f for f in self.frets if f is not None and f > 0]
        return max(fretted, default=0) - min(fretted, default=0)

    def diagram(self, mode='fretboard', start_fret=None):
        highest = max((f for f in self.frets if f is not None), default=0)
        mapper = Mapper(tuning=' '.join(self.tuning), fret_amount=max(self.highest_fret, highest))
        tab = TabMaker(mapper.fretboard, self.notes, tab_size=self.window,
                       string_labels=mapper.tuning_labels)
        if mode == 'tab':
            return tab.tablature(self.frets)
        if mode == 'both':
            return tab.graphic_tab(self.frets, compact=True, start_fret=start_fret) + '\n\n' + tab.tablature(self.frets)
        return tab.graphic_tab(self.frets, compact=True, start_fret=start_fret)

    def to_dict(self):
        return dict(name=self.name, tuning=list(self.tuning), notes=list(self.notes),
                    frets=list(self.frets), score=self.score, fingers=self.fingers,
                    root=self.root, quality=self.quality, complete=self.complete,
                    highest_fret=self.highest_fret, window=self.window)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError('Invalid saved voicing.')
        name = data.get('name')
        tuning, notes, frets = (data.get(key) for key in ('tuning', 'notes', 'frets'))
        if not isinstance(name, str) or not name or len(name) > 80:
            raise ValueError('Invalid chord name.')
        if not all(isinstance(value, list) and value for value in (tuning, notes, frets)):
            raise ValueError('Saved chord must include tuning, notes, and frets.')
        if not all(isinstance(note, str) for note in tuning + notes):
            raise ValueError('Invalid note in saved chord.')
        tuning, _, pitches = parse_tuning(tuning)
        notes = tuple(dict.fromkeys(clean_note(note) for note in notes))
        if len(tuning) != len(frets) or any(
            fret is not None and (type(fret) is not int or not 0 <= fret <= 100)
            for fret in frets
        ):
            raise ValueError('Invalid string positions in saved chord.')
        sounding = {(pitch + fret) % 12 for pitch, fret in zip(pitches, frets) if fret is not None}
        root, quality = data.get('root', ''), data.get('quality', '')
        complete = data.get('complete', False)
        if type(complete) is not bool:
            raise ValueError('Invalid chord voicing policy.')
        if quality:
            root = clean_note(root)
            if notes != tuple(chord_notes(root, quality)):
                raise ValueError('Saved chord spelling does not match its quality.')
            allowed, required = voicing_tones(root, quality, complete)
        else:
            allowed = required = notes
        if not {pitch_class(n) for n in required} <= sounding <= {pitch_class(n) for n in allowed}:
            raise ValueError('Saved frets do not match the chord tones.')
        score = data.get('score')
        if type(score) is not int or not 0 <= score <= 100:
            raise ValueError('Invalid voicing score.')
        fingers = data.get('fingers', finger_count(frets))
        if type(fingers) is not int or not finger_count(frets) <= fingers <= len(frets):
            raise ValueError('Invalid finger count.')
        highest_fret = data.get('highest_fret', max(24, max((f for f in frets if f is not None), default=0)))
        window = data.get('window', 5)
        if type(highest_fret) is not int or highest_fret < 0 or type(window) is not int or window < 1:
            raise ValueError('Invalid saved fret window.')
        return cls(name, tuning, notes, tuple(frets), score, fingers, root, quality, complete,
                   highest_fret, window)


def iter_ranked_voicings(settings, cancelled=None):
    """Yield candidates passing the reach and estimated four-finger filters."""
    settings.validate()
    mapper = Mapper(tuning=settings.tuning, fret_amount=settings.frets)
    tab = TabMaker(mapper.fretboard, settings.allowed_notes)
    familiar = familiar_shapes(settings.root, settings.quality, settings.tuning, settings.frets)
    if settings.custom_notes:
        familiar = set()
    candidates = (sorted(familiar, key=repr) if settings.style == 'familiar' else
                  tab.iter_voicings(min(settings.max_span, settings.window - 1), cancelled=cancelled,
                                   required_notes=settings.required_notes))
    allowed_pcs = {pitch_class(note) for note in settings.allowed_notes}
    required_pcs = {pitch_class(note) for note in settings.required_notes}
    for frets in candidates:
        if cancelled is not None and cancelled():
            return
        sounding = {(pitch + fret) % 12 for pitch, fret in zip(mapper.open_pitches, frets)
                    if fret is not None}
        if not required_pcs <= sounding <= allowed_pcs:
            continue
        if settings.style == 'guitar' and not contiguous_strings(frets):
            continue
        if settings.style == 'familiar' and frets not in familiar:
            continue
        fingers = finger_count(frets, settings.allow_barre)
        if fingers > 4:
            continue
        bass_pitch = min(pitch + fret for pitch, fret in zip(mapper.open_pitches, frets)
                         if fret is not None)
        bass = NOTES[bass_pitch % 12]
        root_bass = pitch_class(bass) == pitch_class(settings.root)
        if settings.root_bass and not root_bass:
            continue
        pressed = [f for f in frets if f is not None and f > 0]
        span = max(pressed, default=0) - min(pressed, default=0)
        if span > min(settings.max_span, settings.window - 1):
            continue
        sounded = len(frets) - frets.count(None)
        score = 60 + sounded * 2 - span * 3 - fingers * 3
        score += 20 if frets in familiar else 0
        score += 5 if root_bass else 0
        score += frets.count(0) * 2 if settings.prefer_open else 0
        score -= 10 if not contiguous_strings(frets) else 0
        score -= min(pressed, default=0) // 2
        name = settings.name
        if not root_bass and not settings.custom_notes:
            spelled_bass = next(n for n in settings.notes if pitch_class(n) == pitch_class(bass))
            name += f'/{spelled_bass}'
        yield Voicing(name, settings.tuning, tuple(settings.notes), frets,
                      max(0, min(100, score)), fingers,
                      '' if settings.custom_notes else settings.root,
                      '' if settings.custom_notes else settings.quality, settings.complete,
                      settings.frets, settings.window)


def sort_voicings(voicings, order='score'):
    if order == 'position':
        return sorted(voicings, key=lambda v: (
            min((f for f in v.frets if f is not None and f > 0), default=0), -v.score))
    return sorted(voicings, key=lambda v: (-v.score, v.span, v.fingers, v.numbers))


class ProgressionStore:
    def __init__(self, directory):
        self.directory = Path(directory)

    def names(self):
        return sorted(path.stem for path in self.directory.glob('*.json'))

    def path(self, name):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', name):
            raise ValueError('Use letters, numbers, underscores, or hyphens for the file name.')
        return self.directory / f'{name}.json'

    def save(self, name, voicings):
        path = self.path(name)
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(dict(version=1, chords=[v.to_dict() for v in voicings]),
                                        indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)

    def load(self, name):
        data = json.loads(self.path(name).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('chords'), list):
            raise ValueError('Unsupported progression file.')
        return [Voicing.from_dict(item) for item in data['chords']]
