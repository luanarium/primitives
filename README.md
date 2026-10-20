# primitives

Older projects and explorations, each condensed into a handoff bundle: a
directory another project can work from without the original source tree in
front of it. Not summaries. Each one carries the things the project learned
that are written down nowhere else, plus a single-file primitive that does the
work and a conformance test that proves it.

Every bundle is self-contained and nothing here depends on anything else here.

| | |
|---|---|
| [drone/](drone/) | a drone music generator, and the measurements of a real recording that it was built from |
| [napster/](napster/) | what it takes to be the whole world of an original Napster 2.0 client: the protocol, and the three surfaces that are not the protocol |
| [handoff-bundle.md](handoff-bundle.md) | the brief both bundles were produced from, for making another one |

## drone

A drone generator in one Node file with no dependencies, and the analysis that
produced it. `node primitive/drone.mjs --minutes 10 --out .` renders ten
minutes in about two minutes; `node primitive/smoke_test.mjs` runs thirteen
checks in eight seconds, three of which hash the output against the original
generator and are bit identical.

The interesting part is not the engine but what the measurements said. Four
rounds of writing this music by ear stayed wrong. The fifth ran a seventy
minute reference recording through a piano roll written for the job, and the
music turned out to be doing almost nothing it sounds like it is doing: chords
every 8 to 13 seconds rather than every minute, notes struck in a tenth of a
second rather than swelled, chords rolled note by note, holds wildly uneven,
plain triads rather than stacked ninths, and nothing above 2 kHz. Built from
those numbers it lands within 2.6 dB of the reference at every octave.

Contains the four measuring scripts, the 373 note transcription of one minute
of the reference, the measured band profiles, and one brief per part of the
source. `BRIEF.md` holds the fourteen numbered corrections to how this music
is usually described. `NEXT.md` holds what is designed and not built, and
opens with the one thing still open, which is a listening test rather than a
change.

Requires Node and ffmpeg for the engine, python3 and ffmpeg for the analysis.
Nothing here reaches the network. The reference recording is not included, and
neither is the one minute comparison pair cut from it; `drone/samples/README.md`
says how to make the pair again from a copy of the recording.

## napster

Everything needed to support an original Napster 2.0 BETA 9 client
(build `02b09`, dated 10 January 2001), written for a tool that does not have
the source project in front of it. The client is not distributed or linked
here; the bundle carries the digests that identify a copy and names the
open-source clients that speak the same protocol.

`primitive/napster_primitive.py` is the whole protocol substrate in one
stdlib-only file, with a `Backend` seam to fill: implement search, resolve and
source_for and a real client logs in, searches and downloads.
`primitive/smoke_test.py` is thirteen conformance checks, each printing what it
saw, so its output doubles as a transcript of a first session on the wire.

The main finding is that a Napster client is not one client. Three of its four
surfaces are not the protocol: an embedded WinINet browser that ignores the
client's own proxy setting, a raw SMTP path, and a registry seed. `BRIEF.md`
documents all four, the nine places the 2000-era specification is wrong, and
the five things that hang the client ranked by how often they will. Behaviour
marked OBSERVED was read off a decoded capture of the wire against a live
client; where the specification disagrees with a capture, the capture wins and
the disagreement is stated.

`pages/` holds the pages that populate the client's three browser tabs, written
for the project, plus manifests describing archived ones. `NETWORK.md` is a
roadmapped network layer — peer discovery as a provider, instance-to-instance
transfers, a layer 2 segment across hosts — which is designed and not built, so
it transfers as decisions and conventions rather than code. `modules/` is one
brief per module of the source project, each saying whether the primitive
lifted it and what to carry across if not.

Python 3, standard library only.

## The shape they share

Both bundles were produced from [handoff-bundle.md](handoff-bundle.md), which
is a brief for Claude Code rather than content. Filling in four lines and
pasting the rest produces another bundle between two other projects. The shape
is a README for reading order, a BRIEF of everything learned, a PRIMITIVE
describing the one portable file, that file and its conformance test, and one
micro brief per module of the source.

Two rules in it account for most of the usefulness: anything fabricated must be
discoverable as fabricated, and anything missing is left missing. A gap is
honest, a guess is not.

## License

MIT, see [LICENSE](LICENSE). Third party material described in these bundles is
not covered by it and is not included here.
