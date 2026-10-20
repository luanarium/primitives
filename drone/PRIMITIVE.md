# The primitive

`primitive/drone.mjs`, 1130 lines, one file, no dependencies. It renders the
music, and it is also the thing to lift if this engine is ever wanted under
somebody else's composition.

```sh
node primitive/drone.mjs --minutes 10 --out .      # as a command
node primitive/smoke_test.mjs                      # thirteen checks, 8 seconds
```

```js
import { render, settings } from "./primitive/drone.mjs";
await render(settings({ minutes: 10, key: "c#", mood: "calm" }), (block) => sink(block));
await render(settings({ composer: { buildScore: mine } }), sink);   // your notes, this voice
```

## It is the original, proved rather than described

This is a condensation in one sense only: the generator Skybox carried read its
configuration from `process.argv` at the top level of the module, so nothing
could import it. The configuration moved into a context object that every
function takes, the ffmpeg pipe became a `write` callback, and every Node call
moved behind a dynamic import at the bottom of the file. The arithmetic was not
touched.

That claim is checked rather than asserted. The original was patched to dump raw
samples instead of spawning an encoder, and ten seconds of three different
configurations were hashed:

| Configuration | sha256 of the samples |
|---|---|
| stereo, the defaults, seed 7 | `ef5229c45cf30428…` |
| mono, no mallets, seed 7 | `43f6c6ead810cd5c…` |
| the 373 note transcribed score | `635e24cf9f4c8ca6…` |

All three are **bit identical** between the original and this file, and all
three are the first checks `smoke_test.mjs` runs. **A port that passes the
thirteen checks produces the same audio**, which is the only form of this claim
worth making about something judged by ear.

## What is in it

| Lines | Part | Why it earned its place |
|---|---|---|
| 1 to 50 | the header | the findings about the genre, where somebody will read them before touching anything |
| 52 to 133 | `RATE`, `DRIVE`, `MOODS`, `PARTIALS`, `BAR`, `NOTES` | the measured constants: two progressions, what a note is made of, what a struck bar is made of |
| 144 to 177 | `DEFAULTS` | the transcription as the empty case, so calling this with no arguments is still the genre |
| 179 | `COMPOSER` | the one seam, every method defaulted, so the empty case runs |
| 186 to 266 | `settings()` | validation, so a module caller gets the refusals a typed flag does |
| 268 to 308 | `normaliseScore()`, `renderToArray()` | a transcribed score in, and the whole piece in memory for tests |
| 310 to 507 | `render()` | the sample loop and the routing: the only part that knows what the piece sounds like |
| 509 to 620 | `playScore()`, `buildScore()` | somebody else's notes, and this engine's own |
| 622 to 684 | `voiceOf()`, `airOf()`, the envelopes | what a note is: six oscillators and a breath, none locked to another |
| 686 to 751 | `buildPings()`, `buildTide()` | the mallets and the slow swell |
| 753 to 872 | `knee()`, `filter()`, `slope()`, `pingpong()`, `reverb()` | the ceiling, the master slope, the ripple and the room |
| 874 to 953 | `midi()`, `hertz()`, `sineTable()`, `lookup()`, `mulberry()`, `sidecarNote()` | notes to frequencies, the table every oscillator reads, the seeded random, the note beside the file |
| 955 to 1130 | the command line half | argument parsing, ffmpeg on a pipe, the sidecar, all of it behind dynamic imports |

Each of those rows has a brief of its own in [modules/](modules/README.md),
and the briefs are where the findings are.

## The floor

- **Node 18 or later** for the synthesis half, which uses only `Math`, typed
  arrays, `Int16Array` and top level `await`. Tested on Node 24.21.0.
- **ffmpeg with libmp3lame** for the command line half, which is the only thing
  in the file that touches the outside world. ffmpeg 4.4.2 here.
- **Nothing else.** No package.json, no install step, no network.

The synthesis half has no static imports at all, which is deliberate and is the
one structural thing this condensation added: a single
`import { spawn } from "node:child_process"` at the top of the original is what
would stop the engine loading in a browser or an AudioWorklet. The checks do not
prove it runs in a browser, since there is no browser here to run them in; they
prove the file has no static dependency that would stop it.

## What the checks check, and why each one is there

`node primitive/smoke_test.mjs`, thirteen checks, about eight seconds. Each
prints what it saw, so the output is a transcript of how the engine behaves
rather than a row of ticks.

| Check | Why |
|---|---|
| three hashes of ten seconds of samples | the seal: a port either produces this audio or does not |
| the score fixture's own hash | so a changed fixture is not read as a broken engine |
| the same seed twice, and a different one | `--seed` is the only way to get a piece back |
| peak inside the ceiling and above -6 dBFS | the limiter has to land it loud without clipping |
| warm below 1 kHz, nothing above 2 | the measurement that says this is the genre at all |
| no partial locked to its fundamental | the organ finding, which cost the most to learn |
| an overridden `buildScore` is what plays | the integration seam, which is the point of a primitive |
| a promise returning sink gets every sample | backpressure, without which a long render eats memory |
| six settings refused by name | a refusal before a sample is cheaper than a render |
| the transcriber reads back a note the engine played | the analysis half, round trip |
| the sidecar says what to run to hear it again | the one piece of provenance that proved necessary |

Two of them carry a counter-example, because a check that never saw the
behaviour it names is worse than no check. The band profile is also run against
white noise, and the organ check against a deliberately locked voice, and both
must **fail** there; the run prints which.

And the whole seal can be broken on purpose:

```
$ node primitive/smoke_test.mjs --prove
FAIL  ten seconds of "stereo, the defaults" hashes to the parked engine's samples
        882000 samples, sha256 0d9a97783cb8d3d3…
        want ef5229c45cf30428… (DIFFERENT)
12 of 13 checks passed, with --prove breaking one on purpose
```

## Porting notes: the invariants that are easy to drop

1. **Advance the shared noise once a sample, above the note loop.** Per note it
   correlates and the breath becomes hiss.
2. **A note's `life` must be `rise + sustain + release`.** Shorter and notes are
   cut off mid release, which is audible as a click at a chord change.
3. **Detune per partial, not per note.** A note detuned as a whole is still an
   organ pipe.
4. **`slope()` is two filter instances, not one called twice.** One instance
   called twice shares state and is not the response it claims.
5. **The sub takes neither the master slope nor the reverb send.** Routing it
   like a voice measures almost right and sounds like mud.
6. **The mallets bypass the master slope and their echoes do not.**
7. **Clamp filter cutoffs to 6 kHz.** This filter form goes unstable above about
   a sixth of the sample rate.
8. **Pack little endian explicitly at the encoder.** `-f s16le` is a promise
   about bytes; the engine's `Int16Array` is in host order.
9. **Re-measure `DRIVE` after any change to the voice.** It is a calibration
   against a reference recording's loudness, not a taste.
10. **Keep the seeded random's draw order.** `voiceOf` takes eleven numbers a
    note and `airOf` four; inserting a draw anywhere changes every later note.

## What was left out of the primitive

- **Skybox itself.** The engine was two scripts in a plugin's `tools/`
  directory and nothing in the plugin ever called them. The one trace left is
  the sidecar's shape, which is that plugin's convention; see
  [modules/encode.md](modules/encode.md).
- **The pre-condensation original**, which is not duplicated here because it is
  byte for byte recoverable: commit `9f8926c` of this repository holds it as
  `drone.mjs`, and Skybox's history holds it up to `ce45528`.
- **The scratch versions.** Six intermediate engines were rendered and judged
  during the four ear-guided rounds. They are not here and should not be; what
  they taught is in [BRIEF.md](BRIEF.md) as corrections.
- **A seventy minute render.** Nothing stops `--minutes 70`; it has never been
  run past ten, and the two minutes eleven seconds a ten minute render takes
  says what to expect.
- **A browser or AudioWorklet wrapper.** The synthesis half was deliberately
  left able to load in one, and that is as far as it got. See
  [NEXT.md](NEXT.md).
