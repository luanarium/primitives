# Web, chat and social over LXMF

The choices, methods and conventions for building a shared surface on Reticulum
and LXMF — posts, comments, reactions, chat channels, rooms, and content shared
by catalog rather than by bytes — written so another project can work from it
without this one's source in front of it.

```sh
python3 primitive/smoke_test.py            # 34 checks, standard library only
python3 primitive/smoke_test.py --prove    # break three invariants, show them caught
```

One file does the work, it has no third-party dependencies, and nothing in it
reaches the network until a carrier is constructed. `rns` and `lxmf` are
optional: with them installed the real Reticulum construction is used for
hashing and signing, and without them a clearly-labelled stand-in stands in so
every invariant is still checkable.

## The shortest version

- **This is five problems and the message layer answers one.** The payload,
  local durability, dissemination, protocol adapters and content-at-scale are
  all yours. Routing delivers packets and LXMF delivers messages; neither knows
  what is inside.
- **Delivery is not dissemination.** Sending to every peer you know reaches only
  the peers you know *at that moment*, so an instance that was asleep never gets
  the event and nothing retries. Store-and-forward does not fix it:
  **propagation is addressed per recipient, not per topic** — a mailbox, not a
  topic bus. **Ask, do not flood.**
- **A delivery destination hash and an identity hash are different values**, and
  `recall` is keyed by the first while an event's author is the second. The
  verifying key comes from the announce; keep the map yourself. Getting this
  wrong looks exactly like a signing bug.
- **A coroutine created inside a delivery callback never runs, and nothing says
  so.** It fires in the message layer's thread. This is the most expensive bug
  in the layer.
- **A send with no path fails silently.** Check, request, wait, fail cleanly.
- **`message.fields` is documented as a dict and arrives as `None` or bytes.**
  Guard every read, and let the signed payload win on any mismatch.
- **Canonicalise once, in one function.** Sorted keys, `id` and `sig` excluded.
  Two implementations means nobody's events verify, with no symptom but that.
- **Store before you notify, and return false for an id already held.** That is
  the whole anti-echo rule; nothing rebroadcasts what it received.
- **Hold an event whose author has not announced yet — do not drop it.** At
  bring-up the first events reliably arrive before the announce that would
  verify them, and dropping is permanent because nothing retries.
- **Resolve as a set, never latest-wins.** `created` is a second, so a tie is
  the normal case; breaking it by id gets agreement without correctness.
  Reactions are an OR-Set; records that are *replaced* carry a per-author
  version instead.
- **A remote filename is an index key resolved through the index or refused,
  never a path** — and the bytes are checked against what the index promised,
  not against what the sender claims.
- **A grant never replicates.** What an item may do *here* is local state, which
  is what makes an ingestion gate hold across instances.
- **A feed is a topic, so nothing creates one**, and the default feed is
  cross-talk: three clients are three windows onto one conversation.

## What is here

| | |
|---|---|
| [BRIEF.md](BRIEF.md) | the integration brief: the five seams, sixteen numbered corrections, what breaks it ranked, the out-of-band surfaces, the pacing and bounds, and the data rules |
| [PRIMITIVE.md](PRIMITIVE.md) | the one file: what each section holds, the dependency floor, what was left out with a pointer for each, and eleven invariants that are easy to drop |
| [DISSEMINATION.md](DISSEMINATION.md) | designed and not built: the digest announce, propagation nodes, private topics, dual emission of standard fields, and three decisions that were reversed |
| [primitive/](PRIMITIVE.md) | `lxmf_surface.py` and its 34 conformance checks |
| [modules/](modules/README.md) | one brief per part, grouped by concern, with the findings encoded in each |

Read `BRIEF.md` §1 first if nothing else. It is the part that would have saved
the most time.

## Read it in this order

1. **`BRIEF.md` §1** — the five seams. The layer that looks like the whole job
   is the one that is already done.
2. **`primitive/smoke_test.py`** — run it. Each check prints what it saw, so the
   output doubles as a transcript of what this surface does.
3. **`BRIEF.md` §2 and §3** — the sixteen corrections, and the eleven failures
   ranked by how often they happen. The first five of each are most of the time
   this layer will otherwise cost.
4. **`PRIMITIVE.md`** — what the one file holds, and the porting notes.
5. **`BRIEF.md` §6** — convergence, pacing and the bounds, which is what makes
   it behave right rather than merely work.
6. **`DISSEMINATION.md`** — if the destination is a networking project, read
   this third rather than sixth. It is the part not entangled with any
   implementation, and the part closest to such a project's purpose.
7. **`modules/`** — when you reach a specific piece.

## What is not here

- **A running network.** No interfaces, no propagation node, no announce at
  import.
- **The request transport for the pull half.** A session, an `identify` and a
  blocking request. The rules it has to obey are built and checked; the wiring
  is not, and `PRIMITIVE.md` says where the hole is.
- **Layer 2 between instances** — frames on sessions, fragmentation, a learning
  table. Rooms' *membership* is here; their frame transport is neither over the
  message layer nor this bundle's subject.
- **The HTTP serving half**: answering names locally, an address per name, a
  proxy in front of a renderer. A separate and larger problem.
- **An archive reader or full-text search.** The catalog pattern that lets large
  content replicate is here; the format work is not.
- **Mail, OSCAR and Mastodon adapters.** Reserved kinds and an adapter shape,
  unwritten.
- **Anything generated.** There is nothing to materialise: every artifact in
  this bundle is a file somebody wrote.

## Provenance

Everything marked OBSERVED in `BRIEF.md` was read off a running pair of
instances in separate network namespaces, or off the libraries themselves, at
`rns 1.5.7` and `lxmf 1.2.0` on Python 3.10. Where the stack's own documentation
disagrees with what was observed, the observation is stated and so is the
disagreement.

The conformance checks were run in the session that assembled this bundle: 34 of
34 with `rns` and `lxmf` installed, and 34 of 34 with neither, plus the
three-invariant `--prove` run.

**What those runs do not prove:** all 34 use the in-process loopback carrier,
so the event layer is tested and **the LXMF binding in §14 is not**. It is
adapted from code that ran for real in the project this came out of, and its
`ask` method is an unwritten stub, so it is a specification with provenance
rather than tested code. `PRIMITIVE.md` says what to do before trusting it.

Anything designed and unbuilt is in `DISSEMINATION.md` and says so there rather
than reading as finished.
