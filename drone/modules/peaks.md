# The peak reader

`analysis/peaks.py`, 2.2 KB

**Role.** The loudest frequencies in a window of audio, in Hz, left and right,
loudest first. A 16384 point FFT at the full 44100.

**In the primitive.** Not lifted.

## What it gives the sound

The first look at anything. It is the cheapest question to ask of a recording
and it answered the two that reframed this whole project.

## What it needs

ffmpeg, a start and a length. Half a second to run.

## Findings encoded here

Two, and they are the reason this file is in the bundle at all:

- **The recording is in standard A440 tuning.** Not 432, not anything else, so
  an engine can use ordinary equal temperament and stop worrying about it.
- **There is no 396 Hz component in the recording at all**, despite 396 Hz
  being the first thing in its title and the whole premise of the genre it is
  sold under. What is actually there, at 600 s, is a Gm7 moving to Dm/F. The
  title is a claim and this is the measurement, and the gap between them is
  worth remembering before taking any other claim about this music at face
  value.

## Lifting it

Nothing to lift. It is forty lines and the FFT is shared with `roll.py`.
