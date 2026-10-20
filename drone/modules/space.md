# The room

`primitive/drone.mjs`, `pingpong` at line 801, `reverb` at 829

**Role.** A plain Schroeder reverb, six combs into four allpasses, and a cross
fed delay for the mallets.

**In the primitive.** Lifted verbatim. Both are textbook and neither is this
project's invention; they are here because the settings are measured rather
than default.

## What it gives the sound

The sense that this is a room rather than a synthesiser, which in this genre is
most of the production. And the rippling: one struck note becomes a line of
them walking outward.

## What it needs

Nothing but samples. The delay's length is set from the pulse rate (half a
pulse), so the ripple agrees with the breathing without being locked to it.

## Findings encoded here

- **The feedback is set long on purpose**, 0.942 with 0.32 of damping. A short
  tail reads as a small room, and a small room reads as a demo.
- **The right channel's lines are offset from the left by 23 samples**, which is
  what makes the tail wide instead of a mono tail in both ears.
- **A third of the mallets' output is what goes to the delay.** More and the
  pings lose their edge, less and they stop rippling.
- **The echoes are filtered by the master slope but the dry pings are not**, so
  a ping is crisp and its answers come back warm.
- **The pad goes to the room at 0.75 and comes back at 0.6.** The sub does not
  go at all; see `sub.md`.

## Lifting it

The comb and allpass sizes are the standard Freeverb numbers at 44100 and must
be rescaled for another sample rate, or the room changes size. Nothing else
here depends on the rate except by way of `RATE`.
