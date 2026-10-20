# The encode and the note beside it

`primitive/drone.mjs`, `sidecarNote` at line 919 and the command line half from
line 955

**Role.** Samples to an mp3 on disk, plus the markdown note that travels beside
it.

**In the primitive.** Lifted, and everything in it moved behind dynamic imports
so that the synthesis half of the file has no static Node dependency and loads
in a browser.

## What it gives the sound

A file somebody can play, at a size they can carry. Ten minutes at the defaults
is 4.8 MB.

## What it needs

ffmpeg on the path with libmp3lame. Nothing else.

## Findings encoded here

- **ffmpeg is handed finished audio and asked only to compress.** No filters, no
  resampling, no normalisation. Every sample is computed in Node, which is why
  a seventy minute render never holds more than a second of audio in memory.
- **64 kbps is plenty for a pad** and is what keeps a ten minute piece under
  5 MB. The A/B files in `samples/` are 192 kbps on purpose: at 64 the encoder
  is making decisions about the top octave and that is the octave the listening
  test is about.
- **The engine hands out an `Int16Array` in host byte order and the CLI packs it
  little endian.** `-f s16le` is a promise about bytes, and a zero-copy view of
  the engine's block would only keep that promise on a little endian machine.
  The pack also copies, which the reused block requires because a stream keeps a
  reference to whatever it is handed.
- **A render must say when it was rendered.** The same filename was overwritten
  five times during this work and a listener could not tell which version was
  playing; an open Obsidian card will also serve the old bytes after a
  re-render. So the time goes into the sidecar's frontmatter, the mp3's
  `comment` and `date` tags, and the line the console finishes on. This was a
  real reported confusion, not a precaution.
- **The sidecar carries the hash of the file**, so a vault that imports it later
  recognises it by content rather than by name, and carries the settings and the
  chord names so the note itself says what to run to hear it again longer or in
  another key.

## Lifting it

The sidecar's shape is Skybox's convention: `<name>.mp3.md`, frontmatter with
`tags` and `hash`, prose below. Anywhere else, keep `hash` and the command line
and drop the rest.
