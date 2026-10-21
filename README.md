# primitives

Older projects and explorations, each condensed into a handoff bundle: a
directory another project can work from without the original source tree in
front of it. Not summaries. Each one carries the things the project learned
that are written down nowhere else, plus a single-file primitive that does the
work and a conformance test that proves it.

Every bundle is self-contained and nothing here depends on anything else here.

| | |
|---|---|
| [drone/](drone/) | note-level analysis of recorded meditative music, and a generator built from the numbers |
| [napster/](napster/) | what it takes to be the whole world of an original Napster 2.0 client: the protocol, and the three surfaces that are not the protocol |
| [handoff-bundle.md](handoff-bundle.md) | the brief both bundles were produced from, for making another one |

## drone

Note-level analysis of recorded meditative music, and a generator built from
what it found. `node primitive/drone.mjs --minutes 10 --out .` renders ten
minutes in about two minutes from one dependency-free Node file;
`node primitive/smoke_test.mjs` runs thirteen checks in eight seconds.

Four rounds of writing this music by ear stayed wrong. The fifth ran a seventy
minute reference recording through a piano roll written for the job, and the
numbers contradicted the usual description of the genre: chords every 8 to 13
seconds rather than every minute, notes struck in a tenth of a second rather
than swelled, plain triads rather than stacked ninths, nothing above 2 kHz.
Built from those, the engine lands within 2.6 dB of the reference at every
octave. `BRIEF.md` has the fourteen corrections, `NEXT.md` what is designed
and not built.

Node and ffmpeg for the engine, python3 and ffmpeg for the four analysis
scripts. The reference recording is not included, nor the one minute
comparison pair cut from it; `drone/samples/README.md` says how to remake it.

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

## The primitive pattern

Each bundle's working part is one file that does the whole job with almost
nothing underneath it. That is the point of them, and the method is the same in
both cases.

| | drone | napster |
|---|---|---|
| the file | `drone.mjs`, 1130 lines | `napster_primitive.py`, 1943 lines |
| third party dependencies | none | none |
| platform calls | 7 Node builtins, none above line 989 | 12 standard library modules |
| the seam | `COMPOSER` | `Backend` |
| the proof | 13 checks, 374 lines | 13 checks, 184 lines |

How they get there:

1. **One file, no package manager.** Nothing to install and nothing to
   resolve, so it can be dropped into another project and read top to bottom.
2. **Everything that touches the platform goes to the bottom.** Spawning
   ffmpeg, hashing, the filesystem and the argument parsing are the last
   quarter of `drone.mjs`, behind dynamic imports. The part that makes the
   audio is arithmetic and imports nothing at all.
3. **Configuration is an argument, never module state.** The original drone
   generator read `process.argv` at the top level of its module, which is
   exactly why nothing could import it. Configuration became a context object
   that every function takes, and the output became a `write` callback instead
   of a pipe to an encoder.
4. **One seam, with every method defaulted.** `serve(Backend())` answers a
   real client with an empty library; `render(settings())` with no arguments is
   still the genre. The empty case runs, so a port works before it is filled
   in, and what to fill in is one named class.
5. **Prove the condensation instead of describing it.** Three of drone's
   thirteen checks hash ten seconds of output against the original generator
   and are bit identical, which is the only useful form of that claim about
   something judged by ear. Napster's thirteen each print what they saw on the
   wire, so the test output doubles as a transcript of a first session.

Both files are laid out to be read from the top. `napster_primitive.py` is
twelve sections in dependency order, each self-contained enough to lift on its
own; `drone.mjs` runs caller first, with the platform half last.

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
