# The transcriber

`analysis/transcribe.py`, 115 lines

**Role.** Note events out of audio as a score an engine can play: onset, midi
number, peak dB and how long the note holds, one a line, tab separated.

**In the primitive.** Not lifted. It is a measuring instrument rather than part
of the sound, and it stays Python because the FFT reads better there.

## What it gives the sound

The only thing that can separate the notes from the voice. Feed its output to
`drone.mjs --score` and whatever is left over is the engine's fault, because
the notes are no longer in question. That test is what found the organ.

## What it needs

ffmpeg to decode, and nothing else: no numpy, no librosa, no pip. The FFT is
written out in the file because this machine has none of them.

## Findings encoded here

- **Fold every bin onto its nearest semitone.** What comes out is note energy
  against time rather than frequency against time, which is the form a
  composition can be read from. Each semitone takes the bins within 0.35 of a
  semitone either side.
- **An onset is a rise, not a level.** Above the floor and at least 5 dB up on
  the quietest of the last eight frames, then walk forward to the peak.
- **A note has let go when it is 15 dB under its own peak**, not when it hits
  the noise floor, which is what makes holds measurable in a piece where
  everything overlaps.
- **Anything shorter than 0.15 s is not a note here**, it is the analysis
  twitching.
- **5512 Hz is the right rate to decode at.** The music has nothing above
  2 kHz, and at a quarter of 44100 the FFT is sixteen times cheaper.
- **Two honest limits, both from the 0.37 s window.** Onsets are placed to about
  a tenth of a second, so no attack shorter than that can be measured here, and
  the attack has to come from the median of the whole piece instead. And a
  note's own harmonics land on real semitones, so a loud low note can post a
  quieter octave or twelfth above itself. In this genre those are usually notes
  that are played anyway, which makes the doubling tolerable rather than fatal.
- **Below C3 the reported note is a second harmonic**, because the music's root
  sits under the lowest semitone the window can resolve. The correction is in
  `playScore`, not here, so that the transcription stays a measurement.

## Lifting it

It prints the score to stdout and its own notes to stderr, so `> score.tsv`
captures exactly the file `--score` wants. Run it under `python3 -I`: it gets
pointed at directories full of downloaded audio, and `-I` stops the interpreter
importing out of the working directory.

The conformance check named "the transcriber reads back a note this engine
played" in `primitive/smoke_test.mjs` is the round trip: a note at A4 out of the
engine, through ffmpeg, back through this, and it has to come out as midi 69.
