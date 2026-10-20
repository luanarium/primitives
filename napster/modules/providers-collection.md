# `napster/providers/collection.py` -- a real directory as a fabricated network

**Role.** The use case the whole sandbox was built for. Point it at a personal
collection and the client sees search results, browsable libraries and working
transfers, attributed to people who do not exist. **The files are real and the
bytes transfer for real; everything around them is staged.**

**In the primitive.** Not lifted -- it is a `Backend` implementation, not
protocol. `BRIEF.md` §7 is its nine findings in brief.

## How the illusion holds together

- **Attribution happens at index time, not at search time.** A file is given
  an owner once, when it is discovered, and keeps it -- so the same track is
  always offered by the same person, browsing their library shows a coherent
  set, and a second search agrees with the first. Deciding per result produces
  a network where **nobody owns anything twice**, which reads as wrong
  immediately.
- **Owners cluster by directory**, because a real user's shared folder is a
  collection rather than a sample. `spread` is the chance of breaking the
  cluster: at 0 a directory maps to exactly one person, at 1 the network looks
  like noise. 0.12 by default.
- **Paths are restaged** onto a period Windows path under the owner's own
  drive -- `C:\My Documents\My Music`, `C:\WINDOWS\Desktop\mp3`, `D:\Music`,
  seven roots so a result list does not look generated from one template. The
  operator's real layout never crosses the wire.
- **The requester never sees their own files.**
- **`seed` makes the whole fiction reproducible**: the same collection yields
  the same owners, the same drive letters and the same speeds on every run, so
  a museum does not reshuffle its population between restarts and a capture
  stays reproducible.

## Findings encoded here

- **Decide what will actually be sent *before* measuring anything.** A 201
  carries the size and checksum of the exact bytes the peer will send, so they
  must be the *encoded* file's, not the original's. See `transcode.md`.
- **`Entry` keeps `real` and `source` separately** -- the bytes that go out,
  and what they were made from -- so nothing loses track of where the music
  actually lives.
- **A converted file is offered under an `.mp3` name.** Advertising
  `track.flac` and sending MP3 bytes would mislead the client *and* the person
  reading the list.
- **`source_for()` is a dict lookup on the path the client was told**, never a
  join onto the operator's filesystem: the filename in a peer request is text
  the client supplies, and the obvious attack on it is `..\`. The mapping
  deliberately only goes one way.
- **Restaged paths can collide**, and filename *is* the identity of a share on
  this wire, so collisions get a ` (n)` suffix.
- **`peer_for(filename)` returns `(link_type, ping_ms)`** for the owner, which
  is what makes a download from a 14.4 user take half an hour and the same
  file from a T1 take a minute.
- **`ping_for(nick)` returning `None` means "not one of ours"**, which is what
  lets the server fall through to the real answer, `ping failed, <nick> is not
  online`.
- **Metadata is cached** by path, mtime, size and bitrate, so a second run is
  instant and an edited source re-measures. Checksumming a large collection is
  the slow part of startup.
- **`probe()` is hand-rolled by default** -- the three fields a 201 wants are
  all in the first MPEG frame header and a CBR duration follows from the file
  size -- with `mutagen` used when it happens to be installed, because it
  handles VBR and odd tags properly. Dependency-free for the common case.
- **Nothing fabricates files.** If a search has no match the client is told
  so. Inventing results to make a demo look livelier is the one thing this
  project refuses.

## Lifting it
Lift the *rules*, not the code: index-time attribution, directory clustering,
path restaging, the one-way mapping, and the seed. They are the difference
between a result list that reads as a network and one that reads as a demo.
