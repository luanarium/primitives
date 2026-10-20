# The low end

`primitive/drone.mjs`, the roots in `buildScore` at line 551, `holdEnvelope` at
670, and the pulse inside `render` at 310

**Role.** One note a chord, an octave or two under everything else, pulsing.

**In the primitive.** Lifted verbatim.

## What it gives the sound

The weight, and the only rhythm in the piece. It is what makes a drone feel
like it is breathing rather than sitting still.

## What it needs

`score.roots`, which carry no `hz` of their own in the mix (they are summed
mono) and no pan. The pulse rate comes from `ctx.pulses` and defaults to 68 a
minute because that is what the reference recording counts.

## Findings encoded here

- **The real thing pulses at 0.88 s with about 17 dB of swing.** The shape is a
  0.05 s attack and an `exp(-(beat - 0.05) / 0.26)` decay, which is a measured
  envelope rather than a tremolo.
- **The floor of that pulse is not zero.** `0.13 + 0.87 * push`: the sub never
  fully leaves, or the pulse becomes a gate.
- **It was 7 dB too quiet for the genre when set by ear.** The multiplier went
  from 0.3 to 0.7 after band profiles showed the piece was that far short of
  the reference's bass weight. A mix that is short of bass does not sound
  bass light, it sounds thin and bright, which is why the ear missed it.
- **A sub in a long reverb is mud rather than depth**, so the sub is the one
  layer with no send to the room, and it bypasses the master slope as well.
- **A second harmonic at 0.11 is enough to make it audible on a phone** without
  making it a tone in its own right.
- **The roots keep their own envelope with no sag**, because a sub that decays
  under a sustained chord reads as a mistake rather than as movement.

## Lifting it

Three numbers to keep: the 0.7 level, the 0.13 floor and the 0.26 decay. The
pulse is driven off absolute time (`(t * pulseHz) % 1`) rather than a counter,
so it never drifts over a seventy minute render.
