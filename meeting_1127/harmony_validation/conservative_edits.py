"""Compare one-edit rules at a common preservation target on intact annotations.

Run after diagnostic.py with Python and NumPy. The partition is by song.
The target was chosen after seeing the original aggregate, so this comparison
is exploratory. The evaluation half plays no part in fitting the thresholds.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


DIRECTORY = Path(__file__).resolve().parent
METHODS = ("melody", "context", "combined")
PRESERVE = 0.90
TOLERANCE = 1e-9


def partition_key(row):
    return hashlib.sha256(("intact-holdout-v1/" + row["song_id"]).encode()).digest()


def scores(rows, method, threshold):
    above = [float(r[f"{method}_gain"]) > threshold for r in rows]
    intact = [float(r[f"{method}_clean_gain"]) > threshold for r in rows]
    location = np.array([float(r[f"{method}_location"]) * a for r, a in zip(rows, above)])
    exact = np.array([float(r[f"{method}_restore"]) * a for r, a in zip(rows, above)])
    return {
        "threshold": threshold,
        "changed_intact_count": sum(intact),
        "kept_intact_rate": 1 - float(np.mean(intact)),
        "proposed_on_altered_count": sum(above),
        "located_rate_all_altered": float(location.mean()),
        "restored_rate_all_altered": float(exact.mean()),
    }


def main():
    with (DIRECTORY / "per_song.csv").open(newline="") as f:
        songs = sorted(csv.DictReader(f), key=partition_key)
    calibration, evaluation = songs[:len(songs) // 2], songs[len(songs) // 2:]
    rank = min(len(calibration), math.ceil((len(calibration) + 1) * PRESERVE))
    result = {
        "target_intact_preservation": PRESERVE,
        "n_calibration": len(calibration),
        "n_evaluation": len(evaluation),
        "rank_one_based": rank,
        "methods": {},
    }
    for method in METHODS:
        gain = sorted(float(row[f"{method}_clean_gain"]) for row in calibration)
        cutoff = max(TOLERANCE, gain[rank - 1] + TOLERANCE)
        result["methods"][method] = {
            "original": scores(evaluation, method, TOLERANCE),
            "calibrated": scores(evaluation, method, cutoff),
        }
    path = DIRECTORY / "conservative_summary.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(path.read_text())


if __name__ == "__main__":
    main()
