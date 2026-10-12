"""Explore guitar chord voicings in a Textual terminal interface."""

import argparse
from itertools import islice

from chords import CHORD_TYPES, chord_notes, clean_note, voicing_tones
from tuning import parse_tuning
from fretboard import Mapper
from tab_maker import TabMaker

DEFAULT_FRETS = 24
DEFAULT_WINDOW = 5
DEFAULT_MAX_SPAN = 4


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', action='store_true', help='print voicings instead of opening the TUI')
    parser.add_argument('--root', default='C', help='chord root, e.g. C or Bb')
    parser.add_argument('--quality', choices=CHORD_TYPES, default='maj')
    parser.add_argument('--voicings', choices=('familiar', 'guitar', 'all'), default='all',
                        help='TUI voicing set (default: all tone combinations)')
    parser.add_argument('--inversions', action='store_true', help='allow non-root bass notes in the TUI')
    parser.add_argument('--complete-chord', action='store_true', help='require every theoretical chord tone')
    parser.add_argument('--notes', nargs='+', help='custom chord tones, e.g. C E G Bb')
    parser.add_argument('--tuning', default='E A D G B E', help='quoted tuning, low to high')
    parser.add_argument('--frets', type=nonnegative, default=DEFAULT_FRETS,
                        help=f'highest fret (default: {DEFAULT_FRETS})')
    parser.add_argument('--window', type=nonnegative, default=DEFAULT_WINDOW,
                        help=f'frets displayed in each movable window (default: {DEFAULT_WINDOW})')
    parser.add_argument('--max-span', type=nonnegative, default=DEFAULT_MAX_SPAN,
                        help=f'maximum distance between fretted notes (default: {DEFAULT_MAX_SPAN})')
    parser.add_argument('--limit', type=nonnegative, default=0, help='CLI maximum voicings to print; default: 0 (all)')
    args = parser.parse_args(argv)
    if args.window < 1:
        parser.error('--window must be at least 1')
    try:
        tuning_tokens, _, _ = parse_tuning(args.tuning)
        tuning = ' '.join(tuning_tokens)
        root = clean_note(args.root)
        notes = (list(dict.fromkeys(clean_note(note) for note in args.notes))
                 if args.notes else chord_notes(root, args.quality))
    except ValueError as error:
        parser.error(str(error))

    if not args.cli:
        try:
            from tui import NeckromancerApp
        except ModuleNotFoundError as error:
            if error.name not in {'textual', 'rich'}:
                raise
            parser.exit(1, 'Install the TUI dependencies with: python3 -m pip install -r requirements.txt\n')
        from voicings import Settings
        settings = Settings(tuning=tuple(tuning.split()), root=root, quality=args.quality,
                            frets=args.frets, max_span=args.max_span,
                            custom_notes=tuple(notes) if args.notes else (),
                            root_bass=not args.inversions, style=args.voicings,
                            complete=args.complete_chord, window=args.window)
        NeckromancerApp(settings).run()
        return

    mapper = Mapper(tuning=tuning, fret_amount=args.frets)
    name = 'Custom chord' if args.notes else f'{root} {args.quality}'
    print(f'{name}: {" ".join(notes)}')
    print(f'Tuning (low to high): {tuning}; frets: 0–{args.frets}')
    print(f'Movable window: {args.window} frets; maximum stretch: {min(args.max_span, args.window - 1)}')
    print('Numbers: low to high; diagram: high to low; ● = fretted, o = open, x = muted.')
    allowed, required = (tuple(notes), tuple(notes)) if args.notes else voicing_tones(root, args.quality, args.complete_chord)
    tab = TabMaker(mapper.fretboard, allowed, tab_size=args.window, string_labels=mapper.tuning_labels)
    voicings = tab.iter_voicings(min(args.max_span, args.window - 1), required_notes=required)
    shown = 0
    for shown, voicing in enumerate(islice(voicings, args.limit or None), 1):
        print(f'\n{shown}.')
        print(tab.graphic_tab(voicing))
        print(tab.number_string(voicing))
    if not shown:
        print('\nNo voicings contain every chord tone in this fret range.')
    elif args.limit and next(voicings, None) is not None:
        print(f'\nShowing {shown} voicings; use --limit 0 to print all.')
    else:
        print(f'\nTotal: {shown} voicings.')


if __name__ == '__main__':
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
