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
| [lxmf-surface/](lxmf-surface/) | the layer that turns LXMF message delivery into posts, chat, rooms and file sharing between instances |
| [napster/](napster/) | what it takes to be the whole world of an original Napster 2.0 client: the protocol, and the three surfaces that are not the protocol |
| [handoff-bundle.md](handoff-bundle.md) | the brief all three bundles were produced from, for making another one |

## drone

**What it is for.** Generating meditative drone music by computation instead of
downloading a recording of it. An hour of this music is a large file for
something that is not a recording of anything, so it is rendered on demand
instead. What the engine does came from measuring a real seventy minute
recording note by note.

**What is built.** `primitive/drone.mjs`, 1130 lines, no dependencies, which
renders ten minutes of audio in about two minutes:

| | |
|---|---|
| the voice | six independent drifting partials per note plus a band of noise, and the envelopes that strike and hold them |
| the score | the engine composing for itself, or playing a transcription of somebody else's notes through the same voice |
| the room | the ceiling, the master slope, the ripple and the reverb |
| the measured constants | two chord progressions, what a note is made of, and what a struck bar is made of |
| the seam | `COMPOSER`, every method defaulted, so calling it with no arguments still produces the genre |
| the command line half | argument parsing, ffmpeg on a pipe and the sidecar note, all behind deferred imports |
| the analysis | the four scripts that produced the numbers: a piano roll, peak detection, band profiles and a transcriber |

**It is tested.** `node primitive/smoke_test.mjs` runs thirteen checks in eight
seconds. Three of them hash ten seconds of output against the generator this
was condensed from and are bit identical, which is the only useful form of that
claim about something judged by ear.

**What is not built.** `NEXT.md` holds it, and opens with a listening test
rather than a change: the oscillator was rebuilt for measured reasons and
nobody has judged the result by ear since. The other gap is that every number
here came off one recording, so a second reference is the first thing worth
doing.

**The finding that shaped the most of it.** Four rounds of writing this music by
ear stayed wrong. The fifth ran the reference recording through a piano roll
written for the job, and the numbers contradicted the usual description of the
genre: chords every 8 to 13 seconds rather than every minute, notes struck in a
tenth of a second rather than swelled, plain triads rather than stacked ninths,
nothing above 2 kHz. Built from those, the engine lands within 2.6 dB of the
reference at every octave. `BRIEF.md` numbers fourteen such corrections.

Node and ffmpeg for the engine, python3 and ffmpeg for the analysis. The
reference recording is not included, nor the one minute comparison pair cut
from it; `drone/samples/README.md` says how to remake it.

## lxmf-surface

**What it is for.** Running a small social network between instances over
Reticulum and LXMF: posts and comments, reactions, chat channels, rooms, and
sharing files that are too large to send in a message.

LXMF carries a message from one identity to another and reports whether it
arrived. It does not decide what goes inside the message, keep a copy of it,
deliver it to somebody who was offline when it was sent, speak any chat
client's protocol, or move a large file. This bundle is the layer that does
those five things.

**What it can do now**, with no network and nothing installed. `python3` and
the one file are the whole requirement:

| | |
|---|---|
| identity and events | make an identity, sign an event, verify one, reject a tampered one, and hold an event from an author whose announce has not arrived yet instead of dropping it |
| a feed | post into the default feed or a named one, comment on a post or on a comment, read a thread back flat in reading order |
| reactions | react, change a reaction, take it back, and get the same answer on two instances that received the events in opposite orders |
| editing | supersede a record with a per-author version, tombstone a post, and refuse a tombstone written by anyone but its author |
| chat and rooms | map a channel to a topic both ways, attribute a speaker from the identity that signed, join and leave a room, read who is in one |
| file sharing | publish an index of what this instance holds, merge every peer's index, fetch by key with the promised size and digest checked |
| catch-up | ask a peer which events it holds, diff that against your own store, and fetch the difference through the same verification gate |
| several instances | wire any number of them together in one process, take one offline, bring it back, and watch it catch up |

Every row is covered by the 34 checks. What needs a live network, and is
therefore specification rather than tested code, is sending and receiving over
real LXMF, announces, and the request call behind the pull.

**How it runs standalone.** One rule, applied twice: everything that touches a
platform is a seam with every method defaulted, and each default does something
useful rather than nothing.

- **`Carrier`** is how events leave and arrive. The real one is the last
  section of the file; `LoopbackCarrier` delivers between surfaces in the same
  process and can mark one offline, which is what makes multi-instance
  behaviour testable with no network at all.
- **`Identity`** is hashing and signing. With `rns` present it is the real
  Reticulum construction; without it, a labelled stand-in, because the standard
  library has no Ed25519 and the alternative was leaving every invariant
  uncheckable.

What is left over is pure functions on JSON and SQLite, in dependency order, so
taking a part means taking a prefix. `PRIMITIVE.md` has the section table.

**How it is shaped for LXMF.** The stack's properties decided the data design
rather than the other way round, and that is most of the methodology:

| Property of the stack | What it forced |
|---|---|
| A signature covers one message to one recipient | Every event signs itself, so it stays verifiable once forwarded, replayed out of store-and-forward, or carried across a federation boundary |
| A mesh has no consensus and no privileged node, so no total order exists | Resolution asks a question about a set, never about which event came last. Reactions are additions and cancellations; edited records carry a counter written by their author |
| An announce is the only thing that hands over an author's verifying key | A key map fed by announces, and a bounded pen holding events that arrive before the announce that would verify them |
| Delivery is addressed per recipient, not per topic | Catch-up is asking rather than sending: a peer says what it holds and you fetch the difference. This is the finding that shaped the most of the design |
| An announce carries 464 bytes | Digests and pointers in an announce, never payloads. The same arithmetic is why an index travels between instances and the files stay where they are |
| Message fields arrive as a dict, or as None, or as bytes | The fields are a routing hint, so a dispatcher need not parse the JSON, and the signed JSON wins on any disagreement |
| A mesh stays possible only if an address means the same thing on every path | Topics are `kind/name` strings rather than network-local addresses, and nothing assumes a peer shares a network with you |

**It is tested.** 34 checks pass against the real `rns 1.5.7` and `lxmf 1.2.0`,
and pass again with neither installed. `--prove` breaks three of the invariants
on purpose and fails if the checks do not catch them. All 34 use the loopback
carrier, so the LXMF binding itself is unexercised, which `PRIMITIVE.md` states
along with what to do before trusting it.

**What is not built.** Announcing a digest so a peer can skip asking, running as
a store-and-forward node, encrypted private topics, and emitting LXMF's own
standard fields so that other clients can read the posts. `DISSEMINATION.md`
holds all four, written down rather than half-built, with three decisions that
were made and then reversed.

Python 3.10, standard library only. `rns` and `lxmf` are optional and only the
last section of the file needs them.

## napster

**What it is for.** Being the whole world of an original Napster 2.0 BETA 9
client (build `02b09`, dated 10 January 2001), so the client works again with
nothing configured inside it. The client is not distributed or linked here; the
bundle carries the digests that identify a copy and names the open-source
clients that speak the same protocol.

**What is built.** `primitive/napster_primitive.py`, 1943 lines, standard
library only, in twelve sections, grouped here:

| | |
|---|---|
| the wire | framing, and a field grammar that is lenient by position because the protocol has no escape character |
| the messages | every message number, named, including the ones that exist only to refuse |
| the checksum | the `<md5>-<bytes>` convention, stored verbatim, and the resume that breaks silently if it is parsed |
| the state | the minimum the protocol assumes: levels, shared files, hits, sessions, channels, and a registry keyed by nick |
| the seam | `Backend`, every method defaulted. Implement search, resolve and source_for and a real client logs in, searches and downloads |
| the transfer | the peer wire and the file server, including the undelimited size prefix and the throttle |
| first contact | the metaserver, which is one line of protocol on a port nobody expects |
| the server | dispatch, the pre-login echo, list terminators owned by the framework, and push routing |
| the listeners | three of them, and a backend shutdown that fires through cancellation |

**It is tested.** `primitive/smoke_test.py` is thirteen conformance checks, each
printing what it saw, so the output doubles as a transcript of what a first
session looks like on the wire.

**What else is here.** `pages/` holds the pages that populate the client's three
browser tabs, written for the project, plus manifests describing archived ones.
`modules/` is one brief per module of the source project, each saying whether
the primitive lifted it and what to carry across if not.

**What is not built.** `NETWORK.md`: peer discovery as a provider,
instance-to-instance transfers, and a layer 2 segment across several hosts.
Designed and not built, so it transfers as decisions and conventions rather
than as code.

**The finding that shaped the most of it.** A Napster client is not one client.
Three of its four surfaces are not the protocol: an embedded browser that
ignores the client's own proxy setting, a raw SMTP path, and a registry seed. A
server that answers the protocol alone leaves three of the four unserved.
`BRIEF.md` documents all four, the nine places the 2000-era specification is
wrong, and the five things that hang the client ranked by how often they will.
Behaviour marked OBSERVED was read off a decoded capture of the wire against a
live client; where the specification disagrees with a capture, the capture wins
and the disagreement is stated.

Python 3, standard library only.

## The primitive pattern

Each bundle's working part is one file that does the whole job with almost
nothing underneath it. That is the point of them, and the method is the same
every time.

| | drone | napster | lxmf-surface |
|---|---|---|---|
| the file | `drone.mjs`, 1130 lines | `napster_primitive.py`, 1943 lines | `lxmf_surface.py`, 1822 lines |
| third party dependencies | none | none | none |
| platform calls | 7 Node builtins, none above line 989 | 12 standard library modules | 6 standard library modules |
| the seam | `COMPOSER` | `Backend` | `Carrier` |
| the proof | 13 checks, 374 lines | 13 checks, 184 lines | 34 checks, 646 lines |

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
   wire, so the test output doubles as a transcript of a first session, and
   lxmf-surface's thirty-four do the same. That one also has a `--prove` mode,
   which breaks three invariants on purpose and fails if the checks do not
   notice, because a check that never saw the behaviour it names is worse than
   no check.

All three are laid out to be read from the top. `napster_primitive.py` and
`lxmf_surface.py` are sections in dependency order, each self-contained enough
to lift on its own, so taking a part means taking a prefix; `drone.mjs` runs
caller first, with the platform half last.

## The shape they share

All three bundles were produced from [handoff-bundle.md](handoff-bundle.md),
which is a brief for Claude Code rather than content. Filling in four lines and
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
