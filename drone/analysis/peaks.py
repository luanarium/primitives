"""Peak frequencies in a window of audio, with no third-party anything."""
import array, cmath, math, subprocess, sys

PATH, START, LEN = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
RATE, N = 44100, 16384

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-ss", str(START), "-t", str(LEN), "-i", PATH,
     "-ac", "2", "-ar", str(RATE), "-f", "f32le", "-"],
    capture_output=True, check=True).stdout
samples = array.array("f"); samples.frombytes(raw)
left = samples[0::2]; right = samples[1::2]

def fft(a):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit; bit >>= 1
        j |= bit
        if i < j: a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        step = -2j * math.pi / length
        w = cmath.exp(step)
        for i in range(0, n, length):
            wn = 1 + 0j
            for k in range(i, i + length // 2):
                u = a[k]; v = a[k + length // 2] * wn
                a[k] = u + v; a[k + length // 2] = u - v
                wn *= w
        length <<= 1
    return a

def spectrum(channel):
    frames = max(1, min(8, len(channel) // N))
    total = [0.0] * (N // 2)
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / (N - 1)) for i in range(N)]
    for f in range(frames):
        chunk = channel[f * N:(f + 1) * N]
        if len(chunk) < N: break
        a = [complex(chunk[i] * window[i], 0.0) for i in range(N)]
        fft(a)
        for k in range(N // 2):
            total[k] += abs(a[k])
    return [v / frames for v in total]

def report(name, mags):
    top = max(mags) or 1.0
    peaks = []
    for k in range(2, len(mags) - 2):
        if mags[k] > mags[k-1] and mags[k] >= mags[k+1] and mags[k] > top * 0.02:
            # Parabolic interpolation for a frequency between two bins.
            a, b, c = mags[k-1], mags[k], mags[k+1]
            shift = 0.5 * (a - c) / (a - 2*b + c) if (a - 2*b + c) else 0
            hz = (k + shift) * RATE / N
            peaks.append((20 * math.log10(b / top), hz))
    peaks.sort(reverse=True)
    print(f"-- {name}")
    for db, hz in peaks[:14]:
        print(f"   {hz:8.1f} Hz  {db:6.1f} dB")

report("left", spectrum(left))
report("right", spectrum(right))
