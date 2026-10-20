# `napster/transcode.py` -- modern audio in, MP3 out

**Role.** The client understands MP3 and little else. A collection recorded
since 2001 is mostly FLAC, AAC, Opus and Vorbis, and offering one of those
produces a file the client downloads and **cannot open** -- the worst failure
mode available, because it looks like it worked.

**In the primitive.** Not lifted.

## Two design points that fall out of the protocol, not taste

- **Conversion happens at index time, not on request.** A 201 result carries
  the size and checksum of the exact bytes the peer will send, and the client
  **verifies both**. Neither is knowable for a file that has not been encoded
  yet, so a lazy transcode would have to lie about them.
- **A converted file is offered under an `.mp3` name.** Advertising
  `track.flac` and sending MP3 bytes would mislead the client and the person
  reading the list.

## Findings encoded here

- **A constant bitrate, 192k.** The 201 row has a single bitrate field, and a
  VBR file can only report an average it does not really have -- so the client
  would display a number the file does not have. Constant across a whole
  collection too, because a listing where every track claims a different
  bitrate because of how it happened to be encoded reads as noise.
- **ffmpeg is an optional *external tool*, not a Python dependency.** It is
  the mature answer by a wide margin and is already on most systems;
  hand-rolling an MP3 encoder to avoid a dependency would be absurd. Without
  it, index what can be served and **say plainly how many files were
  skipped**.
- **Write to `.part` and rename on success.** A half-written file in the cache
  would be served as if it were complete, and the client would check its
  checksum and fail. ffmpeg cannot infer a container from that extension and
  refuses with `Invalid argument`, so the format is given outright with
  `-f mp3`.
- **The cache key is path, size, mtime *and* bitrate** -- all four, or a
  re-encode at a different bitrate is served stale.
- **A native file is returned untouched.** Re-encoding an MP3 to normalise it
  throws away quality to fix nothing.
- **`-vn` and `-map_metadata 0`**: cover art is not a video stream to encode,
  and artist/title are kept because the client reads ID3. `-id3v2_version 3`
  is what a player of this age expects.
- **Originals are never touched.** The tool only ever *reads* a collection.
- **`CONVERTIBLE_SUFFIXES` is deliberately audio-only.** A video container
  that happens to hold a soundtrack is not what a music collection means.
- **A conversion is not a fabrication** -- the music is the operator's own and
  the recording is real -- but it is not the original file either, so
  `Conversion` records what it came from and the count is reported at index
  time. Nothing is presented as untouched when it is not.

## Lifting it
Lift the two design points and the `.part` rename. The ffmpeg invocation is
eight flags and three of them are findings.
