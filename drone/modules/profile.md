# The band profile

`analysis/profile.sh`, 12 lines of bash around ffmpeg

**Role.** How a file's energy sits across the octaves: the mean level, then
250 Hz, 500, 1 k, 2 k and 4 k, each one relative to that file's own overall
level.

**In the primitive.** Not lifted. It is the ruler, not the thing being measured.

## What it gives the sound

Every calibration in the engine. The master slope, the sub level, the upper
partial gains, `DRIVE` and the mallet slope were all set by this and not by
ear, and in each case the ear had been wrong by 5 to 24 dB.

## What it needs

ffmpeg 4.4 or later and python3 for the subtraction. One run is six ffmpeg
passes over 58 seconds, so a few seconds.

## Findings encoded here

- **Every band is printed relative to the file's own level.** This is the
  point of the script. Comparing raw band levels between two files without
  matching their loudness first is the mistake that cost two rounds: a tone
  sweep rendered at 30 seconds was 6 dB quieter overall than its 60 second
  reference, so every band moved by 6 dB and the conclusion came out backwards,
  saying the mix was too dark when it was in fact too bright.
- **Cascade three `highpass=f=N:poles=2`, do not ask for four poles.**
  `highpass=f=1000:p=4` is not valid in ffmpeg 4.4 and fails quietly enough to
  waste an afternoon.
- **Band energy built from one-pole lowpasses and differenced cumulative
  energies does not work.** It barely responded to real filter changes. That
  was the first attempt at this measurement and it had to be thrown away.
- **A 58 second window, not the whole file.** Long enough to average a drone,
  short enough that six passes are quick.

## Lifting it

Twelve lines, no state. If it is ported, keep the normalisation and keep it in
the output, so that nobody downstream can read the numbers as absolute.
