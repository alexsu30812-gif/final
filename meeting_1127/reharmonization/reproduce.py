"""Render three original, matched examples. Requires only Python 3's standard library.

Run: python3 reproduce.py
The A draft, A vocabulary and the B melody below are hand-written illustrations.
Scores measure membership in triad pitch classes. They do not measure perceived quality.
"""
import itertools
import math
import struct
import wave
from array import array
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
RATE = 24000
TEMPO = 100
FRAMES_PER_BEAT = RATE * 60 // TEMPO
BAR_FRAMES = FRAMES_PER_BEAT * 4
DRAFT = ("C", "Am", "F", "G", "C", "Am", "F", "G")
# Dm7 is available from a second, invented A phrase. All other chords occur
# in the draft as well. Dm7 gets the same three scored pitch classes as a triad.
A_REFERENCE = ("Dm7", "G", "C", "Am")
VOICINGS = {
    "C": (48, 55, 60, 64),
    "Am": (45, 52, 57, 60),
    "F": (41, 53, 57, 60),
    "G": (43, 55, 59, 62),
    "Dm7": (50, 53, 57, 60),
}
TRIADS = {
    "C": {0, 4, 7}, "Am": {9, 0, 4}, "F": {5, 9, 0},
    "G": {7, 11, 2}, "Dm7": {2, 5, 9},
}
# One original melody. Each tuple holds note length in beats and MIDI pitch.
MELODY = (
    ((1, 64), (1, 67), (0.5, 69), (0.5, 67), (1, 64)),
    ((2, 74), (1, 77), (1, 69)),
    ((1.5, 69), (0.5, 67), (1, 65), (1, 72)),
    ((1, 71), (1, 74), (1, 71), (1, 67)),
    ((1, 64), (1, 67), (1.5, 72), (0.5, 71)),
    ((2, 76), (1, 72), (1, 69)),
    ((1, 69), (1, 65), (1, 60), (1, 65)),
    ((1, 74), (1, 71), (2, 67)),
)


def support(progression, palette):
    earned = 0
    total = 0
    for chord, notes in zip(progression, MELODY):
        for i, (beats, pitch) in enumerate(notes):
            weight = beats * (2 if i == 0 else 1)
            total += weight
            if pitch % 12 in palette[chord]:
                earned += weight
    return earned, total


def substitute(bar, chord):
    return DRAFT[:bar] + (chord,) + DRAFT[bar + 1:]


def rank_edits(palette):
    pool = sorted(set(DRAFT + A_REFERENCE))
    candidates = []
    for bar, chord in itertools.product(range(1, len(DRAFT) - 1), pool):
        if DRAFT[bar] != chord:
            candidate = substitute(bar, chord)
            score, _ = support(candidate, palette)
            candidates.append((score, bar, chord))
    return sorted(candidates, reverse=True)


def play_note(buffer, start, beats, midi, level):
    """Synthesize one dry pluck with its release entirely inside the given slot."""
    frames = round(beats * FRAMES_PER_BEAT)
    frequency = 440 * 2 ** ((midi - 69) / 12)
    phase_step = 2 * math.pi * frequency / RATE
    attack = round(0.008 * RATE)
    release = min(round(0.065 * RATE), frames // 3)
    for i in range(frames):
        phase = phase_step * i
        body = math.sin(phase)
        attack_colour = (0.24 * math.sin(2 * phase) + 0.095 * math.sin(3 * phase))
        time = i / RATE
        amplitude = min(1, i / attack, (frames - 1 - i) / release)
        buffer[start + i] += level * amplitude * math.exp(-0.95 * time) * (
            body + attack_colour * math.exp(-2 * time)
        )


def make_lead():
    lead = array("d", [0.0]) * (len(DRAFT) * BAR_FRAMES)
    for bar, notes in enumerate(MELODY):
        assert sum(beats for beats, _ in notes) == 4
        start = bar * BAR_FRAMES
        for beats, note in notes:
            play_note(lead, start, beats * 0.94, note, 0.27)
            start += round(beats * FRAMES_PER_BEAT)
    return lead


def render(progression, lead):
    mix = lead[:]
    for bar, chord in enumerate(progression):
        start = bar * BAR_FRAMES
        bass, *upper = VOICINGS[chord]
        play_note(mix, start, 1.8, bass, 0.15)
        play_note(mix, start + 2 * FRAMES_PER_BEAT, 1.6, bass, 0.11)
        for beat, length, level in [(0, 1.3, 0.077), (1.5, 0.44, 0.045), (2, 1.75, 0.065)]:
            for note in upper:
                play_note(mix, start + round(beat * FRAMES_PER_BEAT), length, note, level)
    assert max(map(abs, mix)) < 1
    return struct.pack(f"<{len(mix)}h", *(round(value * 32767) for value in mix))


def write_wav(name, data):
    with wave.open(str(DIRECTORY / name), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(data)


def main():
    ranked = rank_edits(TRIADS)
    high_score, best_bar, best_chord = ranked[0]
    winners = [(bar + 1, chord) for score, bar, chord in ranked if score == high_score]
    next_score = max(score for score, _, _ in ranked if score < high_score)
    runners_up = [(bar + 1, chord) for score, bar, chord in ranked if score == next_score]
    print("Single-slot candidates:", len(ranked), "top:", winners, "next:", next_score, runners_up)
    control_bar = 5  # Same original chord, same note lengths, same edit Dm7.
    assert winners == [(2, "Dm7")] and DRAFT[control_bar] == DRAFT[best_bar]
    # Check whether crediting all sounding chord tones would change the winner.
    extended = {name: {pitch % 12 for pitch in notes} for name, notes in VOICINGS.items()}
    assert rank_edits(extended)[0][1:] == ranked[0][1:]
    lead = make_lead()
    baseline_pcm = render(DRAFT, lead)
    write_wav("baseline.wav", baseline_pcm)
    print("baseline", support(DRAFT, TRIADS))
    for name, bar in [("targeted.wav", best_bar), ("position_control.wav", control_bar)]:
        progression = substitute(bar, best_chord)
        pcm = render(progression, lead)
        lo = bar * BAR_FRAMES * 2
        hi = lo + BAR_FRAMES * 2
        assert pcm[:lo] == baseline_pcm[:lo] and pcm[hi:] == baseline_pcm[hi:]
        assert pcm[lo:hi] != baseline_pcm[lo:hi]
        write_wav(name, pcm)
        print(name, "triad support:", support(progression, TRIADS), "weight / total")
    print("PCM outside the edited bars identical. Shared melody. Sample rate:", RATE)


if __name__ == "__main__":
    main()
