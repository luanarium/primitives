# The filters

`primitive/drone.mjs`, `filter` at line 764, `bandpass` at 777, `slope` at 790

**Role.** A state variable filter, two poles, taking its cutoff fresh every
sample, with a lowpass output and a band output off the same three lines of
arithmetic.

**In the primitive.** Lifted verbatim.

## What it gives the sound

The master slope at 1800 Hz, which is the single biggest difference between
this and the records it was measured against. Also the breath: the same cell
reading its band output turns the shared noise into air around a note.

## What it needs

A cutoff in Hz, clamped to 60 to 6000, and a q. `slope(cut)` is two in series
at q 1.4, which is 24 dB an octave with no resonant bump.

## Findings encoded here

- **The genre has nothing above 2 kHz worth the name and nothing at all above
  4 kHz.** Measured with cascaded highpasses on a seventy minute track: at one
  point this engine was producing 24 dB more up there than the reference. All
  of the reference's warmth is below 1500 Hz.
- **A resonant peak sweeping across the harmonics of a chord is a wah, and a
  wah is not restful.** None of these filters emphasise their own cutoff. This
  was tried and dropped.
- **The master slope sat 300 Hz too low** when set by ear, found by the score
  test rather than by listening.
- **The sine comes from the oscillators' own table**, not from `Math.sin`:
  `f = 2 * lookup(SINE, cut / (2 * RATE))`. At 44100 samples a second with a
  filter per note the `Math.sin` call was measurable.

## Lifting it

Two warnings. The cutoff clamp matters: this filter form goes unstable above
about a sixth of the sample rate, which is what the 6000 Hz ceiling is for. And
`slope` must be two instances, not one applied twice, or the two poles share
state and the response is not what it says on the label.
