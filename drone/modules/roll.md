# The piano roll

`analysis/roll.py`, the same FFT as the transcriber with a different report

**Role.** A picture of what is being played: which notes sound, when each
arrives, how long it takes to arrive, how long it holds, and how many sound at
once.

**In the primitive.** Not lifted.

## What it gives the sound

Nothing directly, and almost everything indirectly. This script is the reason
the composition is right. Four rounds of guessing at the genre by ear got
steadily closer and stayed wrong; ten minutes of this overturned most of what
the ear had assumed.

## What it needs

ffmpeg, and a start and a length. A minute takes about four seconds.

## Findings encoded here

All of the composition findings in `score.md` came out of this script, plus:

- **Mean polyphony 5.7, never below 2.** That number is what forced the two
  ringing voices per chord in `buildScore`; six note chords alone cannot reach
  it.
- **68 onsets in 20 seconds, one every 0.3 s.** The piece sounds like it is
  barely moving and is in fact dense.
- **A top voice can ring 25 seconds and bridge three chord changes.** Written
  down from one line of this report.
- **Onsets must be counted from RMS, not from a peak follower.** A peak
  following detector reported 1773 pulses a minute on a piece that has 68: it
  was counting the carrier ripple. RMS over 100 ms windows at a 25 ms hop found
  the real spacing of 0.88 s.

## Lifting it

`roll.py`, `transcribe.py` and `peaks.py` share the same hand written FFT and
the same ffmpeg decode. If any of them is ported, port the FFT once.
