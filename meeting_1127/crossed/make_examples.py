"""Rebuild the four original examples with Python 3's standard library.

Run: python make_examples.py
Output: 10 s, mono, linear PCM 16-bit, 24 kHz, 100 BPM, four bars of 4/4.
Endings share a rhythmic slot (beat 8). Targets start at beat 9.
"""
import math
import struct
import wave
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent
RATE = 24000
BEAT = 0.6
BUFFER_LENGTH = RATE * 10
ATTACK = 0.008
RELEASE = 0.055


def add_note(track, beat, length, midi, level):
    start = round(beat * BEAT * RATE)
    gate = length * BEAT
    hz = 440.0 * 2 ** ((midi - 69) / 12)
    phase_step = 2 * math.pi * hz / RATE
    for offset in range(round((gate + RELEASE) * RATE)):
        t = offset / RATE
        phase = phase_step * offset
        fundamental = math.sin(phase)
        harmonics = 0.32 * math.sin(2 * phase) + 0.12 * math.sin(3 * phase)
        pluck = fundamental + harmonics * math.exp(-2.2 * t)
        decay = 0.45 * math.exp(-4.5 * t) + 0.55 * math.exp(-0.7 * t)
        release = min(1.0, (gate + RELEASE - t) / RELEASE)
        envelope = min(1.0, t / ATTACK) * decay * release ** 2
        track[start + offset] += level * envelope * pluck


def make_backing():
    track = [0.0] * BUFFER_LENGTH
    # Bars 1–4: Fmaj7, E without a third, Am7, Fmaj7. Both C and A fit the
    # shared Am7 on the first chorus beat. Transitions preserve the same pulse.
    bars = [(41, (53, 57, 64)), (40, (52, 59, 64)),
            (45, (55, 60, 64)), (41, (53, 57, 64))]
    for index, (bass, chord) in enumerate(bars):
        first = index * 4
        add_note(track, first, 1.5, bass, 0.15)
        add_note(track, first + 2, 1.25, bass + 7, 0.11)
        for beat, loudness in [(0, 0.046), (1.5, 0.032), (2, 0.042), (3, 0.028)]:
            for key in chord:
                add_note(track, first + beat, 0.56, key, loudness)
    verse = [(0, 0.85, 65), (1, 0.36, 67), (1.5, 0.75, 69),
             (3, 0.7, 67), (4, 1.25, 64), (5.5, 0.4, 66), (6, 0.72, 64)]
    for beat, duration, key in verse:
        add_note(track, beat, duration, key, 0.30)
    return track


def write_examples():
    backing = make_backing()
    # The two targets share eight onset/duration pairs and the same intervals.
    motif = [(0, 1.32, 0), (1.5, 0.37, 2), (2, 0.73, 7), (3, 0.75, 2),
             (4, 1.22, 2), (5.5, 0.37, 0), (6, 0.68, -5), (7, 0.76, 0)]
    # Each recording uses identical gain. No limiting, per-file normalization or reverb.
    for ending_id, ending_key in [(1, 71), (2, 68)]:
        for chorus_id, first_key in [(1, 72), (2, 69)]:
            track = backing.copy()
            add_note(track, 7, 0.9, ending_key, 0.32)
            for beat, duration, offset in motif:
                add_note(track, 8 + beat, duration, first_key + offset, 0.32)
            with wave.open(str(OUTPUT / f"e{ending_id}_c{chorus_id}.wav"), "wb") as wav:
                wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
                pcm = [round(value * 32767) for value in track]
                assert max(map(abs, pcm)) < 32767
                wav.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))


if __name__ == "__main__":
    write_examples()
