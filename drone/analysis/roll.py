"""A piano roll from audio, with no third-party anything.

Short-time FFT, then every bin folded onto the nearest semitone, so what comes
out is note energy against time rather than frequency against time. From that:
which notes sound, when each one arrives, how long it takes to arrive, how long
it holds, and how many sound at once.

    python3 -I roll.py FILE START SECONDS
"""
import array, cmath, math, subprocess, sys

PATH, START, LEN = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
RATE, N, HOP = 5512, 2048, 276        # 0.37 s window, 50 ms hop
LOW, HIGH = 33, 93                    # A1 to A6

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-ss", str(START), "-t", str(LEN), "-i", PATH,
     "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
    capture_output=True, check=True).stdout
samples = array.array("f")
samples.frombytes(raw)

WINDOW = [0.5 - 0.5 * math.cos(2 * math.pi * i / (N - 1)) for i in range(N)]
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


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


def name(note):
    return f"{NAMES[note % 12]}{note // 12 - 1}"


# Which bins belong to which semitone, worked out once.
bins = {}
for note in range(LOW, HIGH + 1):
    hz = 440 * 2 ** ((note - 69) / 12)
    lo = hz * 2 ** (-0.35 / 12)
    hi = hz * 2 ** (0.35 / 12)
    first, last = int(lo * N / RATE), int(hi * N / RATE) + 1
    if first < 1:
        first = 1
    if last > N // 2:
        last = N // 2
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
grid = {note: [20 * math.log10((frame.get(note, 0) or 1e-12) / top) for frame in frames]
        for note in bins}

print(f"{PATH.split('/')[-1]}")
print(f"{START:.0f}s to {START + LEN:.0f}s, {len(frames)} frames of {HOP / RATE * 1000:.0f} ms\n")

# The roll. A note is drawn where it is within 30 dB of the loudest thing here.
shades = " .:-=+*#%@"
print("                " + "".join("|" if i % 20 == 0 else " " for i in range(len(frames))))
for note in range(HIGH, LOW - 1, -1):
    row = grid.get(note)
    if row is None or max(row) < -34:
        continue
    drawn = "".join(shades[min(9, max(0, int((db + 34) / 3.6)))] for db in row)
    print(f"{name(note):>5} {440 * 2 ** ((note - 69) / 12):7.1f} {drawn}")

# How many notes are sounding at once, and which.
print("\nnotes within 18 dB of the loudest, frame by frame (every second)")
for i in range(0, len(frames), 20):
    live = sorted((db, note) for note, row in grid.items() if (db := row[i]) > -18)
    live.reverse()
    words = " ".join(f"{name(note)}" for db, note in live[:10])
    print(f"  {START + i * HOP / RATE:7.1f}s  {len(live):2d}  {words}")

# Onsets: a note rising by 8 dB inside half a second from below -26 dB.
print("\nonsets, with how long each took to arrive and how long it held")
events = []
for note, row in grid.items():
    i = 2
    while i < len(row) - 2:
        if row[i] > -26 and row[i] - min(row[max(0, i - 10):i]) > 8:
            peak = i
            while peak + 1 < len(row) and row[peak + 1] > row[peak]:
                peak += 1
            start = i
            while start > 0 and row[start - 1] < row[peak] - 20:
                start -= 1
                if peak - start > 80:
                    break
            held = peak
            while held + 1 < len(row) and row[held] > row[peak] - 12:
                held += 1
            events.append((start, note, (peak - start) * HOP / RATE, (held - start) * HOP / RATE,
                           row[peak]))
            i = held + 1
        else:
            i += 1
events.sort()
for start, note, rise, held, db in events[:40]:
    print(f"  {START + start * HOP / RATE:7.1f}s  {name(note):>4}  arrives in {rise:4.1f}s"
          f"  holds {held:5.1f}s  at {db:6.1f} dB")
print(f"\n{len(events)} onsets in {LEN:.0f}s, one every {LEN / max(1, len(events)):.1f}s")
