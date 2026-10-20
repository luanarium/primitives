# The mix

`primitive/drone.mjs`, `render` at line 310, `knee` at 753, `buildTide` at 733,
`DRIVE` at 53

**Role.** The sample loop. Every layer, the routing between them, the slow swell
over the whole piece, and the ceiling.

**In the primitive.** Lifted verbatim, with the module's configuration replaced
by a context argument and the ffmpeg pipe replaced by a `write` callback. Proved
identical to the original sample for sample; see `PRIMITIVE.md`.

## What it gives the sound

All of it. This is the only place that knows what the piece sounds like rather
than what one layer sounds like.

## What it needs

A context from `settings()` and a sink. It allocates one block of a second and
reuses it, so a sink that keeps a block must copy it. It also reports whole
percentages through a callback rather than printing, so the engine can run
somewhere with no console.

## Findings encoded here

- **A tanh across the whole mix bends four samples in a hundred, and those four
  carry harmonics nobody wrote.** `knee` is exactly linear below 0.72 and only
  rounds what is above it. This replaced a global tanh and the difference was
  audible as a general grubbiness rather than as distortion, which is why it
  took a while to find.
- **`DRIVE` is a calibration, not a taste.** It moved 2.2 to 1.07 when the
  oscillators were rebuilt, together with the score gain 0.14 to 0.27, so that
  both the piece and the resynthesis land at the reference's loudness. Any
  change to the voice invalidates it: re-measure with
  `analysis/profile.sh`, which prints the mean level first.
- **A long render needs a fade at both ends proportional to its length**,
  `min(20, seconds / 8)`, and the tail is 1.4 times the head because a piece
  that stops sounds like a mistake while one that starts abruptly sounds
  deliberate.
- **Three dB of swell either way over the whole piece is the difference between
  a recording and a test tone.** Four sines of unrelated periods between 0.004
  and 0.024 Hz, normalised. It is not much to look at written down.
- **The shared noise has to be advanced once per sample before the note loop**,
  not per note, or every note's breath is correlated and the air becomes hiss.
- **Backpressure cannot be ignored on a seventy minute render.** The loop awaits
  the sink when it says to wait, which is what keeps memory flat; without it,
  Node buffers the whole piece.

## Lifting it

The routing is the part to copy carefully. Everything but the sub and the
mallets goes through the master slope; the mallets have their own slope three
octaves up; the sub goes through neither. The reverb send carries the pad, the
mallets, the delay and a little noise, but never the sub. Getting that wrong
produces audio that measures almost right and sounds like mud.
