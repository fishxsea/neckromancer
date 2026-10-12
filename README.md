# Neckromancer

A Textual terminal app for exploring guitar chord voicings. Purple panels,
green scores, a settings sidebar, a responsive voicing grid, and a progression
strip follow the reference layout. All displayed shapes come from the chord
generator.

## Run

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python neckromancer.py
```

For the full dashboard, use a terminal around 120 columns by 48 rows or larger.
The number of columns adapts to terminal width; panels scroll when needed.

Start with a particular chord or tuning:

```sh
python neckromancer.py --root E --quality min7
python neckromancer.py --tuning 'B E A D G B E'
python neckromancer.py --root A --quality min --frets 12 --max-span 4
python neckromancer.py --frets 24 --window 5
python neckromancer.py --voicings guitar
python neckromancer.py --voicings all --inversions
```

## Explore

Enter tuning notes from lowest string to highest string. Each note creates a
string, so four-, six-, seven-, and eight-string instruments use the same
renderer and generator. Choose a preset or enter a custom tuning.
Standard guitar uses E2 A2 D3 G3 B3 E4, and the four-string bass preset uses
E1 A1 D2 G2. For a custom register or re-entrant tuning, supply octaves on every
note, for example `G4 C4 E4 A4`. Bare custom notes assume ascending open pitches.

Choose a chord root and quality, or enter custom chord tones. Custom tones take
precedence over the named chord; their first tone is treated as the root and
every custom tone is required. Custom input switches Common shapes to
Strummable shapes. Clear the field and choose Common shapes to return to the
reference shapes.
Press **Apply settings**, **Ctrl+G**, or **Enter** in a settings input to
regenerate. Sorting and display mode change immediately.

Choose a **Key** in the sidebar to restrict the chord-root and quality menus
to chords whose entire formulas use notes in that scale. **Any key** (default)
restores all choices. Key and in-key chord changes regenerate immediately;
the sidebar lists the scale notes and its basic triads. For C major these are
**C, Dm, Em, F, G, Am, Bdim**; sevenths, suspended chords, and extensions are
also available when all their notes fit. A full formula must fit even when a
guitar voicing omits an optional note. Custom tones are checked too, and an
out-of-key custom set shows an error instead of generating chords.

Minor scale choices are explicit: **Natural minor**, **Harmonic minor**, and
**Melodic minor (ascending)**. A natural minor offers Em; A harmonic minor
offers E and E7 with G#. Each choice filters against that particular scale;
it does not combine the different minor scales. These distinctions follow
[Puget Sound's discussion of chords in minor](https://musictheory.pugetsound.edu/mt21c/DiatonicChordsInMinor.html).

The **Voicing set** controls which shapes are shown:

- **Common guitar shapes**: a finite set of open and transposed
  CAGED/reference shapes. Every shape is checked against the chord tones,
  tuning, fret range, stretch, and fingering constraints. Open C major
  `x 3 2 0 1 0` appears before the barre shape `x 3 5 5 5 3`.
- **Strummable shapes**: generated shapes with a continuous block of sounding
  strings. Outer strings may be muted; holes in the middle are excluded.
- **All tone combinations** (default): also includes sparse shapes and interior mutes
  useful for fingerpicking and specialist voicings. These are not a catalog of
  conventional chord grips.

Common shapes are a reference set, not an exhaustive list of all valid guitar
voicings. If none match a particular tuning or chord, choose another voicing
set; the app does not silently describe arbitrary combinations as common grips.
For standard seven/eight-string tuning, six-string reference shapes are also
available with the extra bass strings muted. The four-string bass uses their
lower four strings, retaining only candidates that satisfy the chord formula.
Root in bass is enabled by default. Disable it for inversions, which are named
with the actual bass note, such as `C/E`.

The default highest fret is **24**, with a movable **five-fret window** and a
maximum distance of **four frets** between finger positions. The windows cover
1–5, 2–6, 3–7, and so on through 20–24. Choose **All positions** above the grid
to see shapes across the neck, or select a specific fret window. Each diagram
labels its actual fret numbers. Open strings are marked separately from the
fretted notes and are not counted in the window's finger stretch.

Change the neck length, window size, and stretch using the sidebar or
`--frets`, `--window`, and `--max-span`. The effective stretch cannot exceed
the window width minus one. The static CLI defaults are `DEFAULT_FRETS`,
`DEFAULT_WINDOW`, and `DEFAULT_MAX_SPAN` in `neckromancer.py`.

The TUI filters out shapes estimated to need more than four fingers. Allowing
barres lets one finger cover a group at the same fret, but an open, muted, or
lower fretted string interrupts that barre. Higher partial barres are limited
to two adjacent strings in the estimate. Open strings do not count toward
the stretch limit. Scores reward smaller stretches, fewer fingers, a root in
the bass, familiar reference shapes, and optionally open strings.
Scores and finger counts are estimates;
the filter does not model every aspect of hand positioning or muting.

### Chord construction and guitar omissions

Chord formulas use intervals from the chord's own root. For example, C7 is
C E G Bb, while Cmaj7 is C E G B. The original `Mapper.build_chord('C', '7th')`
API instead stacks thirds in the selected scale: in C major it produces Cmaj7.
Its ninth/eleventh/thirteenth stacks now retain all intervening thirds. Named
qualities (`7`, `maj7`, `min7`, etc.) are independent of the selected scale.
Spellings retain interval letters, including flats and double accidentals:
Cdim7 is C Eb Gb Bbb, even though Bbb sounds the same as A.

The theoretical formula and the guitar's sounding notes are separate. By
default, extended voicings may omit an unaltered fifth and intermediate
extensions, while retaining the root, defining third, seventh, and highest
extension. Altered fifths remain required. Practical C13 keeps C E Bb A;
G and D are optional and the natural 11th F is excluded. Complete-chord mode
requires the entire theoretical stack instead. These conventions follow
[Open Music Theory's voicing discussion](https://viva.pressbooks.pub/openmusictheory/chapter/jazz-voicings/)
and [Puget Sound's jazz chord guide](https://musictheory.pugetsound.edu/mt21c/JazzChordBasics.html).

An explicit 11th quality retains the third and eleventh; choose `9sus4` for a
suspended ninth voicing without the third. Cards list omitted notes.
Check **Require every chord tone**, or pass `--complete-chord`, to disallow
omissions. Custom tone sets always require every entered note.

## Diagrams

Choose **Fretboard**, **Tablature**, or **Both** above the voicing grid.

Fretboard diagrams show actual finger positions inside numbered fret spaces.
`●` means fretted, `o` means open, and `x` means muted. The double bar is the
nut. Higher-position diagrams label their actual fret numbers.

```text
      1   2   3   4   5
E o ║───┼───┼───┼───┼───┤
B   ║─●─┼───┼───┼───┼───┤
G o ║───┼───┼───┼───┼───┤
D   ║───┼─●─┼───┼───┼───┤
A   ║───┼───┼─●─┼───┼───┤
E x ║───┼───┼───┼───┼───┤
x 3 2 0 1 0
```

Standard tablature aligns the fret numbers vertically because the notes form
one simultaneous chord:

```text
E|--0--|
B|--1--|
G|--0--|
D|--2--|
A|--3--|
E|--x--|
x 3 2 0 1 0
```

Diagrams put the highest string at the top. Number strings run from lowest to
highest and separate fret numbers with spaces, including multi-digit frets.

## Progressions

Click a voicing or focus it and press Enter to add it to the progression strip.
Click a progression card to select it. Use the Remove and arrow buttons, or
Delete and Ctrl+Left/Right, to remove or reorder chords. Each saved chord
retains its own tuning, diagram, number string, and score.
Progression cards grow to fit their diagrams, including larger fret windows;
scroll the strip horizontally when the cards exceed the available space.
The voicing grid also uses fewer columns for wider fret windows.

Enter a file name in the sidebar and click Save, or press Ctrl+S. Files are
stored as JSON in `progressions/` under the working directory. Select a saved
progression and click Load, or press Ctrl+L. Saving to the same name replaces
that file; New clears the current progression without deleting saved files.

| Key | Action |
| --- | --- |
| Tab / Shift+Tab | Focus the next / previous control |
| Arrow keys on a voicing card | Navigate cards |
| Enter on a voicing card | Add to progression |
| PageDown / PageUp | Next / previous page |
| Ctrl+G | Apply settings and generate |
| Ctrl+S / Ctrl+L | Save / load progression |
| Ctrl+N | New progression |
| Delete on a progression card | Remove chord |
| Ctrl+Left / Ctrl+Right | Reorder selected chord |
| Ctrl+Q | Quit |

## Plain terminal output

The original streaming output is available with `--cli`, without Textual.
This mode enumerates all combinations within the fret and stretch limits,
including shapes with more than four fretted strings requiring separate fingers.

```sh
python3 neckromancer.py --cli --root C --quality maj --limit 10
python3 neckromancer.py --cli --notes C E G Bb --frets 12 > voicings.txt
python3 neckromancer.py --help
```

`--limit 0` prints all results, which is the CLI default. Named chords use the
same tone-omission policy as the TUI. Seven-tone thirteenth chords cannot fit
on six strings when `--complete-chord` is enabled; practical thirteenth
voicings work without requiring all seven tones.

## Tests

```sh
.venv/bin/python -m unittest -v
```

Tests cover exhaustive generation, stretch and finger filters, barre
interruptions, multi-digit tablature, progression validation, and headless
Textual interactions including keyboard/mouse input, saving/loading, tuning
changes, filtering, pagination, and terminal resizing.
They also check chord spelling, full diatonic stacks, octave-aware bass notes,
every reference shape's defining tones, practical thirteenths, and the default
common-shape filter.
