# The voice

`primitive/drone.mjs`, `PARTIALS` at line 105, `voiceOf` at 622, `airOf` at
641, `partEnvelope` at 659

**Role.** What one note is made of. Six independent oscillators and a band of
noise, built fresh for every note, each with its own tuning, its own drift, its
own place in the stereo field and its own envelope.

**In the primitive.** Lifted verbatim. It is the part of this project that took
longest to get right and the part most likely to be thrown away by somebody
reimplementing in a hurry, which is why it has the longest comment in the file
above it.

## What it gives the sound

Everything anybody describes as the character of this music: airy, moving,
alive, and nothing like an instrument with a fixed tone. One note played
through it is not a waveform repeating; it is six things slowly disagreeing.

## What it needs

A note event with `hz`, `pan`, `rise`, `sustain`, `release` and `gain`, and the
same seeded random it was built with, so a seed reproduces a piece. `voiceOf`
draws eleven random numbers a note and `airOf` draws four, so changing either
one's draw order changes every later note in the piece.

## Findings encoded here

- **A fixed wavetable is an organ, and no amount of tuning its rolloff fixes
  that.** Two rounds were spent adjusting a table of harmonics, first at one
  over n and then at one over n squared, on the reasoning that a gentler
  rolloff is a warmer tone. Both were described by a listener as an organ. A
  fixed table at 1, 1/4, 1/9 is literally an organ stop: every partial locked
  to the fundamental's phase, identical timbre in every note, and nothing
  moving between a note's start and its end. The table was the fault, not its
  shape. This is the single most expensive finding in the bundle, and the
  listening test in `samples/` is what proved it.
- **Two notes an octave apart with phase-locked harmonics fuse into one tone.**
  That fusion is what a pipe organ is for and the opposite of what this music
  wants, so every partial of every note gets its own detune of a few cents,
  drawn fresh. The detune is per partial, not per note: a note detuned as a
  whole is still an organ pipe, just a mistuned one.
- **A struck thing arrives bright and warms as it rings.** The upper partials
  come in later (`rise` multipliers 1 to 3.8) and die sooner (`fall` 1 down to
  0.46), which is movement inside a single note and the thing a fixed waveform
  can never have.
- **Nothing airy is exactly in tune with itself.** The top two partials sit at
  5.97 and 8.04 rather than 6 and 8.
- **The drift does not need to be computed every sample.** Recomputing each
  partial's pitch every 256 samples (`DRIFT_EVERY`) is inaudible at drift rates
  of 0.07 to 0.4 Hz and is what makes six oscillators and a bandpass per note
  affordable: a ten minute render takes 2m11 rather than hours.
- **The upper partials and the air were measurably too loud when first built.**
  Trimmed against band profiles: partial 4 from 0.08 to 0.05, 5.97 from 0.045
  to 0.016, 8.04 from 0.025 to 0.007, and the air from `0.5 + random * 0.5` to
  `0.3 + random * 0.3`. Ear-set partial gains were 5 dB out in the top octave.
- **A note's filter closing at twice its own fundamental throws away the second
  harmonic.** Found by the score test, not by listening.

## Lifting it

Take `PARTIALS`, `voiceOf`, `airOf` and `partEnvelope` together or not at all.
`airOf` needs a shared noise source that is advanced once per sample before the
note loop, not per note, or every note gets correlated noise and the breath
turns into a hiss. In `render` that is the `hiss` line, deliberately moved above
the note loop.

The conformance check named "no partial of a note is locked to its fundamental"
in `primitive/smoke_test.mjs` encodes this module's central finding, and carries
an organ stop as a counter-example to prove it is checking.
