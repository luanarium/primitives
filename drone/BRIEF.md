# The integration brief

Everything learned about this music that is written down nowhere else. The
thing that has to be preserved is **the sound**: what a listener hears, and the
band profile a measurement takes off it. Where this brief says "the sound",
that is what is meant, and every rule below exists because getting it wrong
made the sound worse in a way that was hard to trace.

Read section 1 even if nothing else. It is the part that would have saved the
most time.

---

## 1. The shape of the problem: four surfaces, not one

A piece of generated music that sounds wrong is almost never wrong in one
place, and the four places are independent. Taste cannot tell them apart,
which is why four rounds of listening and adjusting got steadily closer and
stayed wrong.

1. **The notes.** Which pitches, when they arrive, how long they hold, how many
   sound at once. Measurable with `analysis/roll.py`.
2. **The voice.** What one note is made of. Measurable only by playing somebody
   else's notes on it, which is what `--score` exists for.
3. **The spectrum.** How the energy sits across the octaves once everything is
   mixed. Measurable with `analysis/profile.sh`.
4. **The measurement itself.** Whether the instrument being used to answer 1 to
   3 is telling the truth. Three of the four measurement tools here had to be
   thrown away and rewritten, and two of the resulting mistakes cost a full
   round of work each.

The least obvious of these is the second, and it is the one that mattered most.
A piece can have exactly the right notes and the right spectrum and still sound
synthetic, and no amount of looking at either will say so. The move that broke
the deadlock was to **transcribe a minute of the real recording and play its own
notes on this engine**: with the notes identical and the spectrum matched within
a couple of dB, whatever was left had to be the voice, and it was, and it was an
organ. That test is in `samples/` and the method is in
`modules/transcribe.md`.

The fourth surface is the one that will bite a new person first, because every
tool here looks like it works. See corrections 7 to 10.

---

## 2. The corrections, numbered

Each of these is a place where observation disagreed with something: a claim, a
reasonable assumption, or the ear. The source of the disagreement is named.

1. **The recording has no 396 Hz in it.** Its title is "396 Hz Adrenal Fatigue
   Flush" and the whole genre it is sold under is built on that number.
   Measured with a 16384 point FFT at 600 s: standard A440 tuning, a Gm7
   moving to Dm/F, and nothing at 396 Hz at all. *Contradicts: the file's own
   title and the genre's premise.*
2. **The notes are struck, not swelled.** Median attack 0.1 s over 80 onsets,
   0.3 s at the 90th percentile. The music sounds like slow swells and is in
   fact a series of plucks under a long reverb. *Contradicts: the ear, four
   rounds running.*
3. **Chords move every 8 to 13 seconds**, six of them in a loop of about a
   minute, with the same loop recurring at 40:00. By ear they last a minute or
   more. *Contradicts: the ear.*
4. **The chords are plain triads with octave doublings**, not the stacked
   ninths and elevenths that ambient music is assumed to use. Probably most of
   why an hour of it is restful rather than tiring. *Contradicts: the ear and
   the genre's reputation.*
5. **It is not a pad.** Mean polyphony 5.7 and never below 2, built from
   discrete note events with long releases and nothing crossfaded. What sounds
   like one instrument growing is two chords ringing through each other.
   *Contradicts: the ear.*
6. **A fixed wavetable is an organ, however its harmonics roll off.** Two
   rounds went into the rolloff, from one over n to one over n squared, on the
   reasonable theory that a gentler rolloff is a warmer tone. Both were heard as
   an organ, because the fault is that the partials are phase locked, identical
   in every note and motionless within a note. *Contradicts: a reasonable
   theory about timbre, and two rounds of my own adjustment.*
7. **A peak following onset detector counts the carrier, not the notes.** It
   reported 1773 pulses a minute on a piece that has 68. RMS over 100 ms
   windows at a 25 ms hop found the real spacing of 0.88 s. *Contradicts: a
   standard technique, used naively.*
8. **Band energy from cascaded one-pole lowpasses and differenced cumulative
   energies does not measure bands.** It barely moved when real filters were
   changed by 12 dB. Replaced with ffmpeg highpasses plus `volumedetect`.
   *Contradicts: an obvious-looking construction.*
9. **`highpass=f=1000:p=4` is not valid in ffmpeg 4.4.** Three cascaded
   `highpass=f=N:poles=2` is the way to get a steep slope there. *Contradicts:
   the filter's documented parameters, which include `p` in later versions.*
10. **Absolute band levels cannot be compared between two files.** A tone sweep
    rendered at 30 seconds was 6 dB quieter overall than its 60 second
    reference, which moved every band reading by 6 dB and produced exactly the
    wrong conclusion: that the mix was too dark, when it was too bright. Every
    profile here is normalised against its own file's overall level for that
    reason. *Contradicts: my own earlier measurements, twice.*
11. **The sub was 7 dB short, not heavy.** A mix short of bass does not sound
    bass light, it sounds thin and bright, so the ear sent me to the treble
    twice before the profile said otherwise. *Contradicts: the ear.*
12. **A semitone's bin sum is not a level.** Playing a transcription back with
    its own dB values gave 8 dB more bass relative to the total than the
    recording had; everything above C3 needs a 6 dB lift. *Contradicts: the
    obvious reading of the transcriber's own output.*
13. **Below C3 the transcriber reports second harmonics.** The analysis window
    bottoms out at A1 while this music's root sits a fifth below that, so a
    reported bass note is really its own octave: measured at 600 s, 48.8 Hz at
    -5.8 dB with its octave at 98.0 Hz and -9.3. The fundamental is put back an
    octave down at playback. *Contradicts: the transcriber's output, taken at
    face value.*
14. **The per note attacks in a transcription are not measurable.** The window
    is 0.37 s and the real attacks are a tenth of that, so the median of the
    whole piece is used for every note instead. Using the per note values made
    everything swell, which is correction 2 reintroduced by the back door.
    *Contradicts: the transcriber's own columns.*

---

## 3. What breaks the sound, ranked by how often it will

1. **A fixed or shared waveform.** Symptom: a listener says organ, harmonium or
   church. Cause: partials locked to the fundamental's phase, identical in
   every note, motionless within a note. Fix: six independent oscillators a
   note, each detuned, drifting, panned and enveloped on its own
   (`modules/voice.md`).
2. **Too much above 2 kHz.** Symptom: it sounds like a synthesiser rather than
   a record, often described as thin or digital. Cause: no master slope, or one
   set by ear. Fix: 24 dB an octave from 1800 Hz on everything but the sub and
   the mallets, then check with `analysis/profile.sh`.
3. **A sub set by ear.** Symptom: thin and bright, which sends you to the wrong
   end of the spectrum. Fix: the profile, not the ear. The multiplier is 0.7.
4. **Chords that press rather than roll.** Symptom: it sounds mechanical, like
   a MIDI file. Cause: all of a chord's notes starting together. Fix: roll them
   over 1.4 s, bottom to top, 30% of the time reversed.
5. **Even holds.** Symptom: the texture empties out at every chord change.
   Cause: every note of a chord releasing together. Fix: two voices a chord
   ring through the following changes (75% of top notes, 30% of the rest).
6. **A global tanh.** Symptom: a general grubbiness that does not sound like
   distortion. Cause: four samples in a hundred bent. Fix: a knee that is
   linear below 0.72.
7. **A resonant filter anywhere.** Symptom: a wah across the chord. Fix: q 1.4
   and no cutoff emphasis, ever.
8. **Correlated noise.** Symptom: the air becomes a hiss sitting on top of the
   music instead of breath inside it. Cause: advancing the noise per note
   instead of once a sample. Fix: one `hiss` line above the note loop.
9. **A note cut off mid release.** Symptom: a click at a chord change. Cause:
   `life` shorter than `rise + sustain + release`.
10. **Stale bytes.** Symptom: a change that does nothing, or a listener
    comparing two files that are not the two they think. Cause: rendering over
    the same filename, which an open player will happily keep serving. Fix: the
    `rendered:` stamp in the sidecar, the mp3 tags and the console line, and
    reopening the file.

---

## 4. Out-of-band surfaces

Everything this reaches for that is not in the bundle.

- **ffmpeg**, on the path, with libmp3lame. Exact invocation for the encode:
  `-f s16le -ar 44100 -ac {1,2} -i pipe:0 -c:a libmp3lame -b:a {kbps}k`, plus
  `-metadata title/artist/comment/date`. 4.4.2 here. For decoding in the
  analysis scripts: `-ss START -t LEN -i FILE -ac 1 -ar 5512 -f f32le -`.
- **python3**, 3.10.12 here, with **no pip, no numpy, no sox and no
  fluidsynth**. That absence is why the FFT is written by hand. Always run the
  analysis scripts as `python3 -I`, because they get pointed at directories of
  downloaded audio and `-I` stops the interpreter importing out of the working
  directory.
- **Node 18 or later**, 24.21.0 here. No package.json and no install step.
- **The reference recording**, not shipped: `396 Hz Adrenal Fatigue Flush`,
  4270 s, 192 kbps, 97.7 MB, in the Skybox dev vault at
  a local vault, not redistributed. What travels instead is minute 10:00 of
  it and the transcription of that minute, in `samples/`.
- **The machine the numbers came from**: four cores, 3 GB of RAM. A ten minute
  render takes 2m11 on it. Nothing here needs more memory than a second of
  audio plus the score.
- **Obsidian's sidecar convention**, if the output is going into a vault:
  `<name>.mp3.md`, frontmatter carrying `tags` and `hash`, prose below. The
  hash is what makes a re-import open the existing card instead of making a
  second one.

---

## 5. Configuration, and what is deliberately not written

Every setting is a flag or an option, and every default is a measurement rather
than a preference:

| Flag / option | Default | Where the default comes from |
|---|---|---|
| `--minutes` | 10 | nothing; the only free number here |
| `--kbps` | 64 | enough for a pad, keeps ten minutes under 5 MB |
| `--pulse` | 68 | the reference's low end, counted over a minute |
| `--ping` | 30 | asked for by ear, and the one layer outside the profile |
| `--chord` | 10 | transcribed: chords move every 8 to 13 s |
| `--roll` | 1.4 | transcribed: a chord's notes arrive over 1 to 2 s |
| `--strike` | 0.12 | transcribed: median attack over 80 onsets |
| `--ring` | 1 | a multiplier on measured releases, not a measurement |
| `--seed` | 7 | any number; the same one gives the same piece back |
| `--key`, `--mood` | a, bright | written by hand before the piano roll existed, and the weakest part of the composition (see `NEXT.md`) |
| `--score` | none | a transcription to play instead of composing |
| `--mono`, `--raw`, `--no-sidecar` | off | mono halves the size; raw is what the checks compare |

Nothing is stored anywhere between runs. There is no config file, no cache and
no state: a piece is entirely determined by its flags and its seed, which is
what makes the seal in `PRIMITIVE.md` possible at all.

What a render does write, besides the mp3: the sidecar note beside it, carrying
the content hash, the key, the render time, the settings and the chord names,
and the mp3's own `title`, `artist`, `comment` and `date` tags. The time is in
three places on purpose; see correction 10 in section 3.

Deliberately not written: **no normalisation, no loudness target, no dither and
no fade applied by ffmpeg.** The engine lands the level itself (`DRIVE`, the
knee, the tide and the end fades) so that what reaches the encoder is finished.
Anything ffmpeg did to it would be a second, invisible mix.

---

## 6. Fidelity: what makes it right rather than merely correct

These are the numbers that do not look like they matter and do:

- **0.88 s between low end pulses, with about 17 dB of swing**, as a 0.05 s
  attack and an `exp(-(beat - 0.05) / 0.26)` decay. Not a tremolo.
- **The sub's floor is 0.13, not 0.** A pulse that reaches zero is a gate.
- **1.4 s to roll a chord, mostly bottom to top, reversed 30% of the time.**
  The reversal is the difference between a harp and a machine.
- **Holds: median 1.1 s, 6.9 s at the 75th percentile, one voice at 25 s.**
  Uneven on purpose, because the transcribed ones are.
- **The top of a chord carries 0.046 against 0.065.** Louder and it becomes a
  tune, which is the opposite of what this music is for.
- **Three dB of swell either way over the whole piece**, from four sines of
  unrelated periods between 0.004 and 0.024 Hz. This is the difference between
  a recording and a test tone and it is almost invisible written down.
- **Fades of `min(20, seconds / 8)` in and 1.4 times that out.** A piece that
  stops sounds like a mistake.
- **Mallets at thirty a minute**, which gives each one two seconds to ring, so
  what is heard is one note at a time rather than a pattern. That slowness was
  the whole request.
- **A third of the mallets into the delay, cross fed, half a pulse long.** That
  is the rippling.
- **Reverb feedback 0.942, damping 0.32, right side offset 23 samples.** A
  short tail reads as a small room and a small room reads as a demo.
- **Drift recomputed every 256 samples.** Inaudible at 0.07 to 0.4 Hz and the
  reason a ten minute render is two minutes rather than hours.

---

## 7. What may be synthesised, and what may not

- **The music may be synthesised** and that is the point of the project: an
  hour of this is a large download for something that is not a recording of
  anything.
- **A render says so.** The sidecar's first line of prose is "Rendered here
  rather than downloaded", and it carries the seed and the exact command, so
  the file is never passed off as a recording and can always be reproduced.
- **The reference recording's numbers may not be synthesised, estimated or
  remembered.** Every figure in this brief came out of a script that can be run
  again on the file, and where a figure is an estimate it says so. If a number
  is needed that is not here, measure it; do not reason it out from the ones
  that are.
- **The reference recording itself is somebody else's work.** One minute of it
  travels here, for a listening test, uncompressed past its original encode.
  The full file stays where it is.
- **Nothing in the bundle reaches the network**, and nothing needs an account,
  a key or a service.

---

## 8. The one diagnostic that made all of it possible

If only one tool survived, it would be the piano roll, and the single artefact
worth producing first on any new recording is its score:

```sh
python3 -I analysis/roll.py "track.mp3" 600 60          # read it
python3 -I analysis/transcribe.py "track.mp3" 600 60 > score.tsv
node primitive/drone.mjs --minutes 1 --kbps 192 --score score.tsv --out .
```

The first command prints, for every note it finds: when it arrives, how long it
takes to arrive, how long it holds and how loud it is, then the onset count and
the polyphony. That report is where corrections 2, 3, 4, 5 and the composition
in `modules/score.md` all came from, and it takes about four seconds a minute of
audio.

The second and third turn the same analysis into the A/B test described in
section 1, which is the only way to separate the notes from the voice.

Then `analysis/profile.sh FILE 0` on both, and compare the normalised bands
rather than the absolute ones.

---

## 9. Integration order

If this is being picked up to build on, in this order:

1. **Listen to the A/B pair in `samples/`** and settle the open question in
   `NEXT.md` section 1. Everything else is cheaper afterwards.
2. **Run `node primitive/smoke_test.mjs`.** Thirteen checks, eight seconds, and
   they say whether the engine still behaves as it did when it was parked.
3. **Render something**: `node primitive/drone.mjs --minutes 10 --out .`
4. **Read `modules/voice.md` and `modules/score.md`**, in that order. They hold
   the two findings that cost the most.
5. **Only then change anything**, and measure it with `analysis/profile.sh`
   before judging it by ear. The ear has lost every disagreement so far.
6. If the engine is wanted under other music, the seam is
   `settings({ composer: { buildScore } })` and it is checked; see
   `PRIMITIVE.md`.

## What this bundle does not carry

- **The reference recording**, 97.7 MB of somebody else's work. One minute of it
  is in `samples/`, and the path to the rest is in section 4.
- **Skybox**, which this came out of and which never called it. The only trace
  left is the sidecar convention, written up in `modules/encode.md`.
- **The six intermediate engines** from the ear-guided rounds. What they taught
  is in section 2 as corrections 2, 6, 11 and 12.
- **A browser or AudioWorklet build.** The synthesis half was deliberately left
  able to load in one and that is as far as it went; the two things it would
  need are in `NEXT.md` section 4.
- **Any second opinion on the genre.** Every measurement here is one recording,
  which is the project's largest methodological weakness and the subject of
  `NEXT.md` section 3.
- **A listening verdict on the current voice.** The rebuild was measured and
  never judged, which is why `NEXT.md` opens with a listen rather than a change.
