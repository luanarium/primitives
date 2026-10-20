"""Note events out of audio, as a score a synthesiser can play back.

Same machinery as roll.py: a short time FFT with every bin folded onto its
nearest semitone. This one goes further and cuts the per-note envelopes into
events, so what comes out is a list of notes rather than a picture.

    python3 -I transcribe.py FILE START SECONDS > score.tsv

One note a line, tab separated: onset in seconds from START, midi number,
peak level in dB below the loudest thing in the window, and how long the note
stays within 15 dB of its own peak.

Two honest limits. The window is 0.37 s long, so an onset is placed to about a
tenth of a second and no attack shorter than that can be measured here; the
attack is taken from the median of the whole piece instead. And a note's own
harmonics land on real semitones, so a loud low note can post a quieter octave
or twelfth above itself. In this genre those are usually notes that are played
anyway, which is why the doubling is tolerable rather than fatal.
"""
import array, cmath, math, subprocess, sys

PATH, START, LEN = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
RATE, N, HOP = 5512, 2048, 276
LOW, HIGH = 33, 93
FLOOR = -31.0          # a note below this is not being played
DROP = 15.0            # a note has let go once it is this far under its peak

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-ss", str(START), "-t", str(LEN), "-i", PATH,
     "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
    capture_output=True, check=True).stdout
samples = array.array("f")
samples.frombytes(raw)

WINDOW = [0.5 - 0.5 * math.cos(2 * math.pi * i / (N - 1)) for i in range(N)]


def fft(a):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        w = cmath.exp(-2j * math.pi / length)
        for i in range(0, n, length):
            wn = 1 + 0j
            for k in range(i, i + length // 2):
                u = a[k]
                v = a[k + length // 2] * wn
                a[k] = u + v
                a[k + length // 2] = u - v
                wn *= w
        length <<= 1
    return a


bins = {}
for note in range(LOW, HIGH + 1):
    hz = 440 * 2 ** ((note - 69) / 12)
    first = max(1, int(hz * 2 ** (-0.35 / 12) * N / RATE))
    last = min(N // 2, int(hz * 2 ** (0.35 / 12) * N / RATE) + 1)
    if first < last:
        bins[note] = (first, last)

frames = []
at = 0
while at + N <= len(samples):
    chunk = [complex(samples[at + i] * WINDOW[i], 0.0) for i in range(N)]
    spectrum = fft(chunk)
    mags = [abs(spectrum[k]) for k in range(N // 2)]
    frames.append({note: sum(mags[a:b]) for note, (a, b) in bins.items()})
    at += HOP

top = max(max(frame.values()) for frame in frames) or 1.0
step = HOP / RATE

print(f"# {PATH.split('/')[-1]}", file=sys.stderr)
print(f"# {START:.0f}s to {START + LEN:.0f}s, {len(frames)} frames of {step * 1000:.0f} ms",
      file=sys.stderr)

events = 0
for note, (_, _) in sorted(bins.items()):
    row = [20 * math.log10((frame.get(note, 0) or 1e-12) / top) for frame in frames]
    i = 1
    while i < len(row) - 1:
        if row[i] < FLOOR:
            i += 1
            continue
        # An onset: above the floor, and up on where it was a moment ago.
        back = min(row[max(0, i - 8):i]) if i else row[i]
        if row[i] - back < 5 and i > 1:
            i += 1
            continue
        peak = i
        while peak + 1 < len(row) and row[peak + 1] > row[peak]:
            peak += 1
        end = peak
        while end + 1 < len(row) and row[end + 1] > row[peak] - DROP and row[end + 1] > FLOOR:
            end += 1
        held = (end - i) * step
        if held < 0.15:
            i = peak + 1
            continue
        print(f"{i * step:.3f}\t{note}\t{row[peak]:.1f}\t{held:.2f}")
        events += 1
        i = end + 1

print(f"# {events} notes", file=sys.stderr)
