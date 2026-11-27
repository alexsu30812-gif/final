"""Write a bar-level chord plan as the chord file that MIDI-SAG's MuseControlLite step reads.

MIDI-SAG parses each line as "start end chord" (seconds, space-separated; see
MuseControlLite_inference_continuation.py, extract_chords_lab). Chord names use the
Harte-style syntax of the BTC chord parser, for example C:maj, A:min, D:min7, N.

Example (eight bars at 80 BPM, the chorus starting at 0 s):
    python chords_to_lab.py --bpm 80 C:maj A:min F:maj G:maj C:maj D:min7 F:maj G:maj \
        -o song_chord_gen.txt

Use "+" inside one item to split a bar into equal parts, e.g. "F:maj+G:maj".
Inversions keep Harte syntax, e.g. "G:maj/3".
In MIDI-SAG ground-truth mode, beats are placed from t = 0 at the MIDI's first tempo,
so --offset should normally be 0 and the vocal MIDI should start on a downbeat.
"""
import argparse
import re
import sys
from pathlib import Path

NAME = re.compile(r"^(N|X|[A-G][#b]?(:[A-Za-z0-9()#b,]+)?(/[0-9b#]+)?)$")


def spans(chords, bpm, beats_per_bar, offset):
    bar = 60.0 * beats_per_bar / bpm
    rows = []
    for i, item in enumerate(chords):
        parts = item.split("+")
        for k, part in enumerate(parts):
            if not NAME.match(part):
                raise ValueError(f"bar {i + 1}: chord name not understood: {part!r}")
            start = offset + i * bar + k * bar / len(parts)
            rows.append((start, start + bar / len(parts), part))
    merged = []
    for start, end, name in rows:
        if merged and merged[-1][2] == name:
            merged[-1] = (merged[-1][0], end, name)
        else:
            merged.append((start, end, name))
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chords", nargs="+", help="one item per bar")
    parser.add_argument("--bpm", type=float, required=True)
    parser.add_argument("--beats-per-bar", type=int, default=4)
    parser.add_argument("--offset", type=float, default=0.0, help="seconds before bar 1")
    parser.add_argument("-o", "--out", type=Path, help="output file (default: stdout)")
    args = parser.parse_args(argv)
    if args.bpm <= 0 or args.offset < 0:
        parser.error("--bpm must be positive and --offset non-negative")
    try:
        rows = spans(args.chords, args.bpm, args.beats_per_bar, args.offset)
    except ValueError as error:
        parser.error(str(error))
    if args.offset > 0:
        rows.insert(0, (0.0, args.offset, "N"))
    text = "".join(f"{s:.3f} {e:.3f} {c}\n" for s, e, c in rows)
    if args.out:
        args.out.write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
