# What is designed and not built

The engine works and is calibrated. What is left is mostly decided rather than
done, which is the portable part of any project that has been thought about
longer than it has been built. Read this before changing anything.

## 1. The open question is a listen, not a change

> "the original registers as an airy synth, the resynthisized sounds like an
> unpleasant church organ"

That was the verdict on 2026-10-20, on the A/B pair in `samples/`, and it was
the right diagnosis: the engine used a fixed wavetable, and a fixed table of
harmonics at 1, 1/4 and 1/9 is literally an organ stop. It was replaced with
six independent drifting partials a note plus a band of noise, both A/B files
were re-rendered at 21:48 that evening, **and nobody has listened to them
since.**

So the first move when this is picked up again is to make the A/B pair again,
which is two commands in `samples/README.md`, and play them back to back.
Neither file is in this repository; what the comparison measured is. The notes are identical, the loudness is matched to 0.3 dB and the
bands agree within 2.4 dB up to 1 kHz, so anything heard is the voice.

**If the organ is gone**, the engine is good enough to go back to composition,
and item 3 below is the next thing worth doing.

**If it is still there**, two suspects remain, in this order:

1. **Every partial of a note still starts at the same instant.** They arrive at
   different rates and die at different times, but the onsets are simultaneous.
   Nothing struck or blown behaves that way: the partials of a real note arrive
   over a few milliseconds of each other. A per partial onset jitter of 2 to
   15 ms, scaled by the partial's number, is three lines in `voiceOf` and has
   never been tried.
2. **Nothing filters within a note.** The envelopes move the partials'
   amplitudes but the spectrum of a note never bends. A slow lowpass opening
   over a note's attack is the obvious thing and it was deliberately not built,
   because a resonant filter sweeping the harmonics of a chord is a wah and a
   wah is not restful. The version worth trying is non resonant, shallow, and
   per note rather than per partial.

## 2. The mallets are measurably outside the genre, and the fix is one flag

Measured on one minute of seed 7, normalised band profiles
(`samples/profiles.tsv`):

| | 2 kHz | 4 kHz |
|---|---|---|
| the reference recording | -43.2 | -65.9 |
| the piece as it renders | -38.4 | -60.6 |
| the piece with `--ping 0` | -40.8 | -65.5 |

With the mallets off, every band is within 2.4 dB of the reference. With them
on, the top octave is 5 dB hot and they are the entire cause. They are also
there because they were asked for: "almost xylophone progressions with a very
slow BPM for the zylophone pings".

That is a taste decision rather than a bug, and it has been put twice and not
answered: **turn them off, put them behind the master slope, or keep them and
accept the top octave.** The measurement is done; the choice is not made.

## 3. Everything here comes from one recording

Every number in `BRIEF.md` was measured on a single seventy minute track.
Chords every 8 to 13 seconds, attacks of 0.1 s, rolled chords, uneven holds,
plain triads, nothing above 2 kHz: all of it is one piece of music, and some of
it is certainly that artist rather than the genre.

Running `analysis/roll.py` and `analysis/profile.sh` over two or three more
tracks is a few minutes of work and is the highest value thing left in the
project. It would say which findings are the genre and which are one record,
and it is the obvious thing to do before building anything further on them.

The second thing it would give is a `--mood` worth having. The transcription
found the reference's own loop (Bb, Dm, Cm, Eb, F, Gm, which is III v iv VI VII
i in G minor) and the engine does not use it: `bright` and `calm` were written
by hand before the roll existed. A mood that plays the measured loop is a
twenty line addition that nobody has made.

## 4. The engine as a primitive somewhere else

The synthesis half of `primitive/drone.mjs` has no static imports, which was
done on purpose so it could load in a browser or an AudioWorklet. What is not
built is the wrapper, and the two things it would need:

- **The reverb's comb and allpass lengths are the standard Freeverb numbers at
  44100** and must be rescaled for another sample rate or the room changes
  size. Everything else follows `RATE`.
- **`render` pushes blocks and awaits a sink.** A worklet pulls 128 frames at a
  time, so it wants a generator rather than a callback. The loop is already
  frame by frame, so this is a restructure of twenty lines and not a rewrite.

The composition seam for this is already built and checked:
`settings({ composer: { buildScore } })`. See `PRIMITIVE.md`.

## 5. Decisions already made, so they are not re-made

- **Measure first, always.** Four rounds of ear-guided iteration got steadily
  closer and stayed wrong, and ten minutes with a piano roll overturned most of
  what the ear had assumed. If an opinion about this music and a measurement
  disagree, the measurement has won every single time so far.
- **No fixed waveform.** Settled, at the cost of two rounds. See
  `modules/voice.md`.
- **No resonant filters anywhere.** A peak sweeping across a chord's harmonics
  is a wah.
- **A knee, not a tanh, on the mix.** A global tanh bends four samples in a
  hundred and those four carry harmonics nobody wrote.
- **Discrete note events, not a pad with crossfades.** What sounds like one
  instrument growing is two chords ringing through each other, which only works
  if nothing is crossfaded.
- **ffmpeg compresses and does nothing else.** No filters, no normalisation, no
  resampling on the way out.
- **This never went into Skybox.** It was two scripts beside a plugin that
  never called them, and the plugin is a way of looking at a vault rather than
  an instrument. It was taken out on 2026-10-20 in `ce45528`.

## 6. Things tried and dropped, so they are not re-tried

- **A music player embed around a YouTube video.** Dropped on 2026-10-20: an
  embed from another origin will not say where it is, cannot be analysed, and
  in Obsidian will not take instructions. The buttons looked right and did
  nothing.
- **Caching YouTube audio locally with yt-dlp** to get around that. Raised and
  declined: it needs a binary the plugin cannot ship.
- **A wavetable at one over n, then one over n squared.** Both read as an organ.
- **An onset detector following peaks.** It counted the carrier ripple: 1773
  pulses a minute on a piece that has 68.
- **Band energy from cascaded one-pole lowpasses with differenced cumulative
  energies.** It barely responded to real filter changes.
