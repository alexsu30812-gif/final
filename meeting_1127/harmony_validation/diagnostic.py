"""Probe chord-edit selection on aligned POP909 training MIDI and chord annotations.

From the course workspace:
    hw2/.venv/bin/python meeting_1127/harmony_validation/diagnostic.py hw2/POP909/training
Requirements: numpy and pretty-midi (versions recorded in the output).
The data are read-only. No externally pretrained model or human preference is used.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pretty_midi

SEED = 11272026
CONTEXT_WEIGHT = 0.2
MIN_COVERAGE = 0.25
TOLERANCE = 1e-9
METHODS = ("melody", "context", "combined")
ROOTS = dict(C=0, D=2, E=4, F=5, G=7, A=9, B=11)


def triad(label):
    # Only exact root-position :maj and :min, without extension or slash.
    # Store enharmonically equivalent roots with the same ID.
    match = re.fullmatch(r"([A-G])([#b]?):(maj|min)", label)
    if not match:
        return None
    root, accidental, quality = match.groups()
    pc = (ROOTS[root] + {"#": 1, "b": -1, "": 0}[accidental]) % 12
    return pc + (12 if quality == "min" else 0)


def label(chord):
    names = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
    return names[chord % 12] + (":maj" if chord < 12 else ":min")


def pcs(chord):
    root = chord % 12
    return [root, (root + (4 if chord < 12 else 3)) % 12, (root + 7) % 12]


def parse_spans(folder):
    spans = []
    for line in (folder / "chord_midi.txt").read_text().splitlines():
        start, end, name = line.split()
        start, end = float(start), float(end)
        if end <= start:
            raise ValueError("nonpositive_chord_span")
        spans.append((start, end, triad(name)))
    return spans


def notes_per_span(folder, spans):
    song = pretty_midi.PrettyMIDI(str(folder / (folder.name + ".mid")))
    tracks = [t for t in song.instruments if t.name.strip().upper() == "MELODY"]
    if len(tracks) != 1 or not tracks[0].notes:
        raise ValueError("absent_or_ambiguous_melody")
    notes = tracks[0].notes
    onset = np.array([n.start for n in notes])
    end = np.array([n.end for n in notes])
    keys = np.array([n.pitch % 12 for n in notes])
    profiles = []
    for begin, stop, _ in spans:
        overlap = np.maximum(0.0, np.minimum(end, stop) - np.maximum(onset, begin))
        support = np.bincount(keys, weights=overlap, minlength=12)
        # Summed overlap is note-time; simultaneous MELODY notes can add.
        coverage = support.sum() / (stop - begin)
        profiles.append((coverage, support / max(support.sum(), 1e-12)))
    return profiles


def contiguous(x, y):
    return abs(x[1] - y[0]) <= 0.002


def select_window(spans, profiles, vocabulary, first, rng):
    eligible = []
    for start in range(first, len(spans) - 7):
        group = spans[start:start + 8]
        seq = [row[2] for row in group]
        if any(c not in vocabulary for c in seq):
            continue
        if any(a == b for a, b in zip(seq, seq[1:])):
            continue
        if any(not contiguous(a, b) for a, b in zip(group, group[1:])):
            continue
        if any(p[0] < MIN_COVERAGE for p in profiles[start + 1:start + 7]):
            continue
        eligible.append(start)
    return rng.choice(eligible) if eligible else None


def edits(sequence, profiles, vocabulary, transitions, totals, method):
    melody = [{c: float(p[1][pcs(c)].sum()) for c in vocabulary} for p in profiles]

    def log_prob(a, b):
        return math.log((1 + transitions[a, b]) / (len(vocabulary) + totals[a]))

    alternatives = []
    for j in range(1, 7):
        left, old, right = sequence[j - 1:j + 2]
        for c in vocabulary:
            if c in (left, old, right):
                continue
            m = melody[j][c] - melody[j][old]
            h = (log_prob(left, c) + log_prob(c, right)
                 - log_prob(left, old) - log_prob(old, right))
            gain = {"melody": m, "context": h, "combined": m + CONTEXT_WEIGHT * h}[method]
            alternatives.append((gain, j, c))
    best = max(g for g, _, _ in alternatives)
    tied = [(j, c) for g, j, c in alternatives if abs(best - g) < TOLERANCE]
    return best, tied


def run_song(folder):
    spans = parse_spans(folder)
    profiles = notes_per_span(folder, spans)
    split = len(spans) // 2
    history = spans[:split]
    vocab = sorted({c for _, _, c in history if c is not None})
    if len(vocab) < 4:
        return None, "fewer_than_four_history_chords"
    transitions = Counter((a[2], b[2]) for a, b in zip(history, history[1:])
                          if a[2] is not None and b[2] is not None and contiguous(a, b))
    totals = Counter()
    for (a, _), count in transitions.items():
        totals[a] += count
    rng = random.Random(f"{SEED}/{folder.name}")
    start = select_window(spans, profiles, vocab, split + 8, rng)
    if start is None:
        return None, "no_eligible_eight_span_window"
    window = tuple(c for _, _, c in spans[start:start + 8])
    j = rng.randrange(1, 7)
    bad = rng.choice([c for c in vocab if c not in window[j - 1:j + 2]])
    changed = list(window)
    changed[j] = bad
    prior_eight = [tuple(c for _, _, c in history[t:t + 8]) for t in range(len(history) - 7)]
    row = dict(song_id=folder.name, span_start_index_zero_based=start,
               start_s=spans[start][0], end_s=spans[start + 7][1], changed_slot_1_to_8=j + 1,
               original=label(window[j]), replacement=label(bad),
               intact_sequence=" ".join(map(label, window)),
               earlier_same_label_octet=int(window in prior_eight))
    for method in METHODS:
        best, winners = edits(changed, profiles[start:start + 8], vocab, transitions, totals, method)
        clean_gain, clean_winners = edits(window, profiles[start:start + 8], vocab, transitions, totals, method)
        row[method + "_gain"] = best
        row[method + "_top_ties"] = len(winners)
        row[method + "_clean_gain"] = clean_gain
        row[method + "_clean_top_ties"] = len(clean_winners)
        row[method + "_edit_clean"] = int(clean_gain > TOLERANCE)
        row[method + "_abstain_corrupt"] = int(best <= TOLERANCE)
        # Equal probability for tied position/chord pairs. Include abstentions as failures.
        locate = sum(place == j for place, _ in winners) / len(winners)
        restore = sum((place, c) == (j, window[j]) for place, c in winners) / len(winners)
        row[method + "_forced_location"] = locate
        row[method + "_location"] = locate if best > TOLERANCE else 0.0
        row[method + "_restore"] = restore if best > TOLERANCE else 0.0
    return row, None


def mean(rows, key):
    return float(np.mean([r[key] for r in rows]))


def summarize(rows):
    metrics = ("forced_location", "location", "restore", "edit_clean", "abstain_corrupt")
    rates = {method: {m: mean(rows, method + "_" + m) for m in metrics} for method in METHODS}
    rng = np.random.default_rng(SEED)
    matches = rng.integers(0, len(rows), size=(5000, len(rows)))
    delta = {}
    for metric in metrics:
        d = np.array([r["combined_" + metric] - r["melody_" + metric] for r in rows])
        delta[metric] = {"estimate": float(d.mean()),
                         "percentile_95_ci_by_song": np.quantile(d[matches].mean(axis=1), [.025, .975]).tolist()}
    return {"n": len(rows), "rates": rates, "combined_minus_melody": delta}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    rows, excluded = [], Counter()
    folders = sorted(p for p in args.training.iterdir() if p.is_dir() and p.name.isdigit())
    if not folders:
        raise ValueError("No numeric POP909 training folders found")
    hasher = hashlib.sha256()
    for folder in folders:
        for name in (folder.name + ".mid", "chord_midi.txt"):
            hasher.update(folder.name.encode() + b"/" + name.encode() + b":")
            hasher.update(hashlib.sha256((folder / name).read_bytes()).digest())
        row, reason = run_song(folder)
        if reason:
            excluded[reason] += 1
        else:
            rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "per_song.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(song_folders=len(folders), exclusions=dict(excluded),
                   input_fingerprint_sha256=hasher.hexdigest(),
                   seed=SEED, context_weight=CONTEXT_WEIGHT, min_melody_note_time_fraction=MIN_COVERAGE,
                   numpy=np.__version__, pretty_midi=pretty_midi.__version__,
                   methods="MELODY note-duration fractions per annotated span; no downbeat multiplier. Add-one-smoothed bigram log probability from each song's first half. Combined = melody + 0.2 * log transition.",
                   protocol="One window per song in second half, eight annotation rows gap after first half. Only contiguous eight root-position major/minor chords in known within-song vocabulary, all adjacent labels different. Interior six have enough note-time; no section labels. Uniform interior slot and uniform feasible replacement from history excluding original and either adjacent chord. Same candidate restrictions for repair. Near-equal gains averaged over tied edit pairs; optional edit only if best gain exceeds 1e-9. Forced-position random-slot reference 1/6. Clean edits flag changes to original dataset annotations, not inherently bad music.",
                   all=summarize(rows),
                   damaged_location_counts=dict(sorted(Counter(r["changed_slot_1_to_8"] for r in rows).items())),
                   by_exact_octet_in_history={})
    for k in (0, 1):
        group = [r for r in rows if r["earlier_same_label_octet"] == k]
        if group:
            summary["by_exact_octet_in_history"][str(k)] = summarize(group)
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("song_folders", "exclusions", "all")}, indent=2))


if __name__ == "__main__":
    main()
