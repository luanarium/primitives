# The mallets

`primitive/drone.mjs`, `BAR` at line 123, `buildPings` at 686

**Role.** A struck bar walking the chord, two octaves up, thirty times a minute.

**In the primitive.** Lifted verbatim, and it is the one layer measurably
outside the genre. See `NEXT.md`: `--ping 0` is a one flag experiment that puts
the piece inside the reference profile at every octave.

## What it gives the sound

Events. A listener asked for "almost xylophone progressions with a very slow
BPM", and at thirty a minute each note has two seconds to ring out, so what is
heard is one note at a time rather than a pattern. That slowness is the point.

## What it needs

The progression, a nominal chord rate to walk, and the seeded random. It is
skipped entirely when a transcribed score is playing, since the score is
somebody else's composition and a mallet over the top of it would make the
comparison meaningless.

## Findings encoded here

- **A struck bar is not a harmonic series.** A xylophone's partials sit near
  3, 6 and 9 times the fundamental rather than 2 and 3, and the high ones die
  first. Four of them (1, 3.01, 5.67, 9.1 with decay multipliers up to 4.6) is
  enough to hear wood. Built as a harmonic stack it sounds like a bell.
- **A struck bar with its top taken off is a sine, and then it is not a
  xylophone.** This is the only layer exempt from the master slope, on a slope
  of its own at 2800 Hz, which came down from 4400 after measurement.
- **Its echoes do take the master slope**, so a ping is crisp and its answers
  come back warm. A third of each ping goes to the delay, which is what makes
  it ripple outward rather than simply stop.
- **The mallets are the whole of the generated piece's excess above 2 kHz.**
  Measured on one minute of seed 7: with them, 2 kHz sits at -38.4 and 4 kHz at
  -60.6 relative to the file's own level; with `--ping 0`, -40.8 and -65.5.
  Against the reference recording's -43.2 and -65.9, turning them off brings
  every band within 2.4 dB. The numbers are in `samples/profiles.tsv`.
- **Being a beat behind the chord change is how a real player sounds anyway**,
  so the walk is advanced at the nominal rate rather than synchronised.

## Lifting it

Self contained: give it a chord and a rate. The decay envelope is
`exp(-age * (5 / life) * decay / 1.6)` per partial, and the 3 ms linear fade in
on the attack is there to keep the start from clicking.
