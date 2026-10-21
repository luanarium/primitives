# Drone

A meditative drone generator and the measurements it was built from. Parked out
of Skybox on 2026-10-20, as a time capsule: either its own project later, or an
engine to lift into something else.

```sh
node primitive/drone.mjs --minutes 10 --out .     # render ten minutes
node primitive/smoke_test.mjs                     # thirteen checks, eight seconds
```

Two files do the work, neither has a dependency, and nothing here reaches the
network. Node and ffmpeg for the engine, python3 and ffmpeg for the
measurements.

## The shortest version

An hour of this music is a large download for something that is not a recording
of anything, so it can be computed instead. Four rounds of writing it by ear got
steadily closer and stayed wrong. The fifth ran a seventy minute track of the
genre through a piano roll written for the job, and what that said about the
music was nothing like what the music sounds like it is doing: chords every 8 to
13 seconds rather than every minute, notes struck in a tenth of a second rather
than swelled, chords rolled note by note like a harp, holds wildly uneven with
one voice ringing 25 seconds across three chord changes, plain triads with
octave doublings rather than stacked ninths, and nothing above 2 kHz worth the
name.

Built from that, it renders. A ten minute piece takes 2m11 and lands within
2.6 dB of the reference recording at every octave, with the mallets off.

**One question is open, and it is a listen rather than a change.** Transcribing
a minute of the real recording and playing its own notes on this engine was what
finally separated the notes from the voice, and on 2026-10-20 the verdict was
that the original reads as an airy synth and the resynthesis as an unpleasant
church organ. The oscillator was rebuilt because of that, from a fixed wavetable
to six independent drifting partials a note, both files were re-rendered, and
nobody has listened to them since. Start there: neither file is in this
repository, so make the pair again with the two commands in
`samples/README.md`, then play them back to back.

## What is here

| | |
|---|---|
| [BRIEF.md](BRIEF.md) | everything learned about this music that is written down nowhere else: the four surfaces, fourteen numbered corrections, what breaks the sound ranked, and how to measure any of it |
| [PRIMITIVE.md](PRIMITIVE.md) | the engine as one file: what is in it, the floor it needs, what the checks check, and the invariants that are easy to drop |
| [NEXT.md](NEXT.md) | what is designed and not built, the open question, and the decisions already made so they are not re-made |
| [ORIGIN.md](ORIGIN.md) | the account of the engine's design that Skybox's README carried, kept as provenance |
| [primitive/](PRIMITIVE.md) | `drone.mjs` and its thirteen conformance checks |
| [analysis/](analysis/README.md) | the four measuring scripts, and the findings each one produced |
| [samples/](samples/README.md) | the rendered audio, the measured band profiles, the transcription, and how to make the A/B pair, which is not here |
| [modules/](modules/README.md) | one brief per part of the source, with the findings encoded in each |

Read `BRIEF.md` section 1 first if nothing else. It is the part that would have
saved the most time.

## What is not here

- **The reference recording**: 4270 seconds, 192 kbps, 97.7 MB of somebody
  else's work, held locally and not redistributed. One minute of it travels
  here instead, in `samples/`, which is the minute every listening test used. Its title claims 396 Hz and it contains none; that is
  correction 1.
- **Skybox**, which this came out of and which never called it. The generator
  was two scripts in a plugin's `tools/` directory, and a plugin for looking at
  a vault is not an instrument. The only trace left is the sidecar note the
  renderer writes, in `modules/encode.md`.
- **A verdict on the current voice.** The rebuild was measured and never judged,
  which is why `NEXT.md` opens with a listen.
- **A second opinion on the genre.** Every number here came off one recording.
  That is the project's largest weakness and the first thing worth fixing;
  `NEXT.md` section 3 says what it would take.
- Anything generated: every artifact the engine produces that the findings
  depend on is materialised as a file in `samples/`, including the 373 note
  score and the profiles table.
