"""Cross-song stress test of target sensitivity; never assigns a musical ground truth.

Run after diagnostic.py (writes frozen per_song.csv):
  hw2/.venv/bin/python meeting_1127/harmony_validation/cross_song.py hw2/POP909/training
Two fixed pairings in each estimated harmonic-anchor quality group, slotwise octave-free
pitch-class profiles. Output is a symbolic sensitivity measurement, not a listening test.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
from diagnostic import METHODS, TOLERANCE, contiguous, edits, label, notes_per_span, parse_spans


def digest(*parts):
    return hashlib.sha256("/".join(map(str, parts)).encode()).hexdigest()


def describe(training, row):
    folder = training / row["song_id"]
    spans = parse_spans(folder)
    history = spans[:len(spans) // 2]
    length = Counter()
    for start, end, chord in history:
        if chord is not None:
            length[chord] += end - start
    # No key annotations in this local copy: this is a transposition anchor, not key estimation.
    anchor = min(length, key=lambda c: (-length[c], c))
    counts = Counter((a[2], b[2]) for a, b in zip(history, history[1:])
                     if a[2] is not None and b[2] is not None and contiguous(a, b))
    totals = Counter()
    for (a, _), n in counts.items():
        totals[a] += n
    index = int(row["span_start_index_zero_based"])
    selected = spans[index:index + 8]
    blueprint = [c for _, _, c in selected]
    assert " ".join(map(label, blueprint)) == row["intact_sequence"]
    return dict(id=folder.name, anchor=anchor, window=blueprint, vocabulary=sorted(length),
                transitions=counts, totals=totals, profiles=notes_per_span(folder, selected),
                start_s=selected[0][0], end_s=selected[-1][1])


def align(host, donor):
    # Report the shortest signed transposition; choose -6 at a tritone.
    steps = ((host["anchor"] % 12 - donor["anchor"] % 12 + 6) % 12) - 6
    return [(coverage, np.roll(pc, steps)) for coverage, pc in donor["profiles"]], steps


def suggest(host, donor, method):
    profiles, steps = align(host, donor)
    gain, winners = edits(host["window"], profiles, host["vocabulary"],
                          host["transitions"], host["totals"], method)
    if gain <= TOLERANCE:
        return 0, "", gain, len(winners), steps
    # One reproducible tie break per host and candidate; donor name never enters scoring.
    i, c = min(winners, key=lambda pair: digest("tie-v1", host["id"], *pair))
    return i + 1, label(c), gain, len(winners), steps


def probe(host, donor1, donor2, pairing):
    assert len(set(x["id"] for x in (host, donor1, donor2))) == 3
    assert host["anchor"] // 12 == donor1["anchor"] // 12 == donor2["anchor"] // 12
    row = {"pairing": pairing, "A": host["id"], "B1": donor1["id"], "B2": donor2["id"],
           "A_anchor": label(host["anchor"]), "B1_anchor": label(donor1["anchor"]),
           "B2_anchor": label(donor2["anchor"]), "A_start_s": host["start_s"],
           "A_end_s": host["end_s"], "A_chords": " ".join(map(label, host["window"]))}
    for method in METHODS:
        for tag, d in (("B1", donor1), ("B2", donor2)):
            pos, chord, gain, ties, shift = suggest(host, d, method)
            row[tag + "_shift_semitones"] = shift
            for item, value in (("slot", pos), ("new_chord", chord), ("gain", gain), ("ties", ties)):
                row[f"{method}_{tag}_{item}"] = value
            if tag == "B1":
                # Control reuses identical notes and anchor but changes donor metadata.
                assert (pos, chord, gain, ties, shift) == suggest(host, dict(d, id="relabeled"), method)
    for field in ("slot", "new_chord", "gain", "ties"):
        assert row["context_B1_" + field] == row["context_B2_" + field]
    return row


def stats(rows, method):
    def rate(num, count):
        return {"n": num, "denominator": count, "rate": num / count if count else None}

    a = [(r[method + "_B1_slot"], r[method + "_B1_new_chord"]) for r in rows]
    b = [(r[method + "_B2_slot"], r[method + "_B2_new_chord"]) for r in rows]
    n = len(rows)
    acted = sum(x[0] > 0 for x in a + b)
    both = [(x, y) for x, y in zip(a, b) if x[0] and y[0]]
    changed = [(x, y) for x, y in zip(a, b) if x != y]
    per_decision = Counter()
    for r, x, y in zip(rows, a, b):
        for tag, result in (("B1", x), ("B2", y)):
            if result[0] and r[f"{method}_{tag}_ties"] > 1:
                per_decision["tie_among_positive_candidates"] += 1
    return {
        "recommend_edit": rate(acted, 2 * n),
        "retain_entire_A": rate(2 * n - acted, 2 * n),
        "retained_A_slots": rate(2 * n * 8 - acted, 2 * n * 8),
        "different_recommendation_including_noop": rate(len(changed), n),
        "different_slot_including_noop": rate(sum(x[0] != y[0] for x, y in zip(a, b)), n),
        "switched_between_edit_and_noop": rate(sum(bool(x[0]) != bool(y[0]) for x, y in zip(a, b)), n),
        "both_edit": len(both),
        "different_slot_given_both_edit": rate(sum(x[0] != y[0] for x, y in both), len(both)),
        "same_slot_but_different_chord": rate(sum(x[0] == y[0] and x[1] != y[1] for x, y in both), n),
        "different_new_chord_given_both_edit": rate(sum(x[1] != y[1] for x, y in both), len(both)),
        "top_tie_when_editing": rate(per_decision["tie_among_positive_candidates"], acted),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training", type=Path)
    parser.add_argument("--cohort", type=Path, default=Path(__file__).with_name("per_song.csv"))
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    with args.cohort.open() as f:
        hosts = [describe(args.training, r) for r in csv.DictReader(f)]
    groups = [[h for h in hosts if h["anchor"] // 12 == q] for q in (0, 1)]
    rows = []
    for group in groups:
        assert len(group) > 4
        group.sort(key=lambda h: digest("partner-v1", h["id"]))
        for name, u, v in (("primary", 1, 2), ("alternate", 3, 4)):
            for i, h in enumerate(group):
                rows.append(probe(h, group[(i + u) % len(group)], group[(i + v) % len(group)], name))
    header = list(rows[0])
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "cross_pairs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    summary = {
        "cohort_sha256": hashlib.sha256(args.cohort.read_bytes()).hexdigest(),
        "input": "Frozen eight-span windows of diagnostic.py. A's own uncorrupted progression; B1/B2 from different songs. No section/chorus labels, meter mapping, lyric, original register, expressive timing, or audio rendering.",
        "alignment": "Match each of eight normalized pitch-class histograms onto the corresponding A chord span. Transpose to the same anchor (duration-majority plain major/minor chord in the first half); pair only within anchor quality. Anchor is not necessarily tonal key. Context and chord palette come solely from the first half of A.",
        "pairing": "SHA256-sort song IDs within major-anchor or minor-anchor group. Two different donors for each host, each donor serves twice per schedule. Primary cyclic offsets +1/+2; robustness +3/+4. Neither chosen by scores. Slot 0 denotes no change; chord recommendations tie-broken using only host ID and candidate.",
        "interpretation": "Pairing sensitivity has no preference/accuracy labels. Retention of at least 7/8 slots is mechanical. Same melody relabeled yields identical output; context-only zero sensitivity is by construction. Donor pairs share songs and are not independent listening trials.",
        "n_hosts": len(hosts), "major_anchor": len(groups[0]), "minor_anchor": len(groups[1]), 
        "results": {}
    }
    for name in ("primary", "alternate"):
        batch = [r for r in rows if r["pairing"] == name]
        assert Counter(r["A"] for r in batch) == Counter(r["B1"] for r in batch) == Counter(r["B2"] for r in batch)
        summary["results"][name] = {m: stats(batch, m) for m in METHODS}
    (args.out / "cross_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for s, methods in summary["results"].items():
        print(s, {m: r["different_recommendation_including_noop"]["rate"] for m, r in methods.items()})


if __name__ == "__main__":
    main()
