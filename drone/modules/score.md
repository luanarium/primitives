# The score

`primitive/drone.mjs`, `MOODS` at line 65, `buildScore` at 551, `normaliseScore`
at 268, `playScore` at 509

**Role.** The composition. Every note of every chord of the whole piece, with
its onset, its hold and its release, written out before a sample is rendered.

**In the primitive.** Lifted verbatim, and lifted into the one documented seam:
`COMPOSER.buildScore` is the method to override when this engine is wanted
under somebody else's music.

## What it gives the sound

The thing a listener calls music rather than tone. It is also where the
transcription of a real recording is encoded, so this module is the project's
findings about the genre expressed as code.

## What it needs

A validated context (`settings()`) for length, key, mood and the four shape
numbers, plus the seeded random. It returns `{ notes, roots }` and nothing
reads it again, so a replacement only has to produce that shape.

## Findings encoded here

- **Chords move every 8 to 13 seconds, not every minute.** Transcribed: six
  chords in a loop of about a minute, and the same loop recurs at 40:00. Four
  rounds of guessing had them far slower.
- **Notes are struck, not swelled.** Median attack 0.1 s over 80 onsets, 0.3 s
  at the 90th percentile. This is the opposite of what the genre sounds like it
  is doing and the correction that mattered most to the composition.
- **A chord is rolled, not pressed.** Its notes arrive one after another over
  one to two seconds, usually bottom to top, and 30% of the time the other way.
  Pressed chords are what made earlier versions sound like a machine.
- **Holds are wildly uneven and that is what fills the texture.** Median 1.1 s,
  6.9 s at the 75th percentile, one voice ringing 25 s across three changes.
  Measured polyphony is 5.7 on average and never below 2, which is only
  reachable with six note chords if the last chord is still sounding under this
  one. Hence `rings`: 75% of top notes and 30% of the rest hold through the
  following changes.
- **The voicings are plain triads with octave doublings, not stacked ninths.**
  Probably most of why an hour of this is restful rather than tiring.
- **Nothing is crossfaded.** Two chords ring through each other because the
  releases are long, which makes a change sound like an arrival rather than a
  dissolve.
- **The top of a chord has to carry less or it becomes the tune**: gain 0.046
  against 0.065 for the rest.
- **A transcription needs two corrections before it can be played back.**
  Anything under C3 gets its fundamental restored an octave down, because the
  analyser's range stops at A1 while the music's root sits a fifth below that,
  so what it reports as a bass note is really that note's second harmonic
  (measured at 600 s: 48.8 Hz at -5.8 dB with its octave at 98.0 Hz and -9.3).
  And everything above C3 is lifted 6 dB, because a semitone's bin sum is not a
  level: without the lift the playback carried 8 dB more bass relative to its
  own total than the recording did.
- **The attack is not taken from the transcription at all.** The analysis window
  is 0.37 s and the real attacks are a tenth of that, so the measured median of
  the whole piece is used instead. Taking the per note value would have made
  every note swell.

## Lifting it

`buildScore(ctx, random)` returns notes in the shape documented above
`COMPOSER`. The two places a reimplementation usually goes wrong: a note's
`life` must be `rise + sustain + release` or notes get cut off mid release, and
`roots` are separate from `notes` because the sub is mono, pulsed and mixed at a
fixed level rather than being one more voice.

`playScore` is a measurement path rather than a composition: what it produces is
somebody else's piece. Keep it. It is the only tool here that can tell the
notes' fault from the engine's.
