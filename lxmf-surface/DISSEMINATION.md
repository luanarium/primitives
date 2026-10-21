# Dissemination: the part that is designed and not built

The surface works and converges. What is left is mostly **decided rather than
done**, which is the portable half of any project that has been thought about
longer than it has been built. Nothing in this document is entangled with an
implementation, so it transfers as decisions and conventions rather than as
code.

Read §1 and §9 if nothing else. §1 is the decision everything else serves, and
§9 is the three things that were tried and reversed, which is what a fresh
implementer would otherwise re-try.

## 1. The decision: ask, do not flood

**Dissemination is digest-announce-and-pull**, over the stack's own primitives
rather than over anything invented above them.

What a naive surface does is send every event to every known peer. That is N²
in fanout, it ignores whether the peer subscribes to the topic, and — the part
that actually matters — **it reaches only the author's own peer list at the
moment of publishing**. An instance that was asleep never gets the event and
nothing retries. A↔B and B↔C, with A never having heard C, means C misses A's
events permanently, because nothing forwards. That is precisely the ad-hoc case
a mesh exists for.

Three steps, each a primitive rather than a mechanism of your own:

1. **Announce per topic.** The aspect is the topic; the announce's `app_data`
   carries the kind, the version or count, and a short digest. Announces are
   already epidemic and propagate through transport nodes, so this reaches every
   reachable instance rather than one peer list — which closes the A↔B↔C hole
   without forwarding anything.
2. **Subscribe by aspect.** Register an announce handler per topic you care
   about. A peer announcing a version you do not hold is the signal.
3. **Pull over a request handler.** Open a link and request it; the holder's
   response generator answers, as a resource when it is large.

**This respects the anti-echo rule rather than relaxing it.** Nothing
rebroadcasts what it received. An announce carries a digest of what a node
*holds* — a statement about itself, not a relayed payload — and the transfer
that follows is one the subscriber asked for. Any proposal here has to pass that
test.

| Half | State |
|---|---|
| **Pull** — have, diff, get over a request handler, syncing on discovery and on a jittered timer | **Built.** §13 of the primitive, and `tests` for the rules |
| **The digest announce** that would let a peer skip asking | Designed, unbuilt |
| **Propagation nodes** for store-and-forward | Designed, unbuilt, and §3 below |
| **Wire-level topic subscription** | Unbuilt. Kind 9 `subscription` is reserved and bound to nothing, and may never be needed — if an announce carries the signal, reserved-and-unused is a legitimate end state |

Pull closes the gap. The other two make it cheaper rather than possible, which
is the order to build them in.

## 2. The inventory, with the limit on each

This was written by going through what the stack already provides *before*
designing anything, and that sequence is the recommendation: **reach for a
primitive before building one.** The limits are the part worth keeping, because
each one is a thing somebody would otherwise assume.

### Dissemination

| Primitive | What it gives | The limit to respect |
|---|---|---|
| **Announces** | An epidemic broadcast with no addressing — everyone reachable hears it — carrying `app_data` | A packet's MDU is 464 bytes, less identity and signature. **Digests and pointers, never payloads** |
| **An announce handler's `aspect_filter`** | Called for announces on that aspect from *any* identity: network-wide topic subscription | Matched by name-and-identity hashing, so the aspect is **exact**. No prefixes, no wildcards, one handler per topic |
| **A group destination** | A destination type with a symmetric key: many holders of one key is a shared channel | It gives shared **encryption** on one hash. Whether one packet reaches many holders is the interface's business — a broadcast-capable interface delivers to all, routed transport takes one path. **A channel key, not guaranteed multicast** |

### Catch-up

| Primitive | What it gives |
|---|---|
| **Enabling propagation** | This instance becomes a store-and-forward node for peers that were offline |
| **Peer sync between propagation nodes** | Anti-entropy *between nodes*, already implemented in the stack |
| **Requesting messages from a propagation node** | Pull backfill: a client asks a node for what it missed |
| **Propagation node announces, with name, sync stratum, throttle and utilisation metadata** | Nodes advertise themselves and their capacity, so a client can choose one |
| **`try_propagation_on_fail`** | Direct when the peer is up, propagated when it is not, decided per message |
| **Stamps and tickets** | Proof-of-work and flow control for a surface open to strangers |

**The limit to state plainly: propagation is addressed per *recipient
destination*, not per topic.** It is a mailbox, not a topic bus. It fixes
offline delivery and backfill; it does not fix fanout.

### Hosting and transfer

| Primitive | What it gives | The limit |
|---|---|---|
| **A destination's request handler** — path, response generator, allow mode, allowed list, auto-compress | Path-routed request and response over a link, with per-identity access control over identity hashes, and automatic compression. **This is a hosting primitive**: it is how pages and files are served in this ecosystem | A maximum request size bounds it; the response generator is handed the path, the data, a request id, a link id, the remote identity and a timestamp |
| **A link's `request`** | The client half, with progress and failure callbacks | |
| **A resource** — data, link, metadata, auto-compress, segment index, request id, is-response | Bulk transfer over a link as a response to a request | Anything above 1,048,575 bytes is segmented |
| **Links, channels, buffers, raw channel readers and writers** | Encrypted sessions, and reliable sequenced messaging over one | A link's MDU is 431 |

## 3. Propagation nodes, and being one

Offline peers are the message layer's problem and it already solves them:
configure a propagation node, set `try_propagation_on_fail` on `async` kinds,
and **consider running one**. An instance that enables propagation gains the
stack's inter-node sync for free and becomes the thing that heals a partition
while everyone else is asleep. The metadata fields for sync stratum and
utilisation pressure say the stack expects a *hierarchy* of nodes with differing
capacity, so this is a role an instance takes rather than a new component.

**A propagation node is not a sequencer**, which is the obvious hope and is
worth recording as checked. It stores messages content-addressed by their own
hash, and its `received` is its own clock. It assigns no order anybody else can
use, and depending on one would make an optional component load-bearing for
correctness.

## 4. Private topics: the open question

Every topic is readable by everyone holding the access code. A private feed
needs a group key, and the two candidate shapes are not equivalent:

- **Aspects** are exact-match and need a handler each. Cheap, public, and the
  natural fit for an open topic.
- **A group destination's symmetric key** is a shared secret with a
  distribution problem, and distributing it is the part the stack does not do
  for you.

The encryption primitive is already there — an identity encrypts to another
identity and decrypts with its own, which is the mechanism for handing a group
key to one member. **What is undecided is whether topics are aspects, group
destinations, or both**, and the answer probably differs for an open topic and a
private one. Decide it per topic class rather than globally.

## 5. Dual emission: interoperability versus a second representation

The message layer already has registered fields for most of a social surface:

| Field | Key | What it would carry |
|---|---|---|
| Reaction, with reaction-to and reaction-content | 64 | a reaction |
| Comment, with comment-for | 65 | a comment |
| Thread, reply-to, reply-quote | 8, 48, 49 | threading a conversation |
| File attachments, image, audio | 5, 6, 7 | file sharing with no envelope of your own |
| Renderer, with markdown, micron, bbcode and plain | 15 | how a post is meant to be rendered, instead of guessing |
| Continuation, with continuation-of | 66 | a post too long for one message |
| Group | 11 | a channel, as the message layer already understands one |

**What this buys is interoperability rather than convenience.** A reaction
emitted in the standard field is a reaction in the ecosystem's other clients,
not only in yours, and a decentralisation claim gets stronger the less of the
envelope is your own.

**What is undecided is whether an event also emits the standard field.** Dual
emission buys that interoperability and costs a second representation that can
disagree with the first. One answer should serve posts, comments and reactions
together.

Two things already settled, and they constrain the answer:

- **Every relation the message layer defines names its target by full hash** —
  reaction-to, comment-for, continuation-of. The `for` tag in §8 of the
  primitive matches that shape deliberately, so emitting the standard field
  later is nearly free.
- **The message layer defines no retraction.** Its own note says handling of
  reaction content is left to the client, so the half that actually bites is
  yours to define. The `undo` tag is that definition, and nothing standard
  covers it.

## 6. First contact is out of band, and the carrier already exists

A surface associates over the path an invite sets up, so the first exchange has
to happen outside it. The message layer already has the carrier: a message
serialises under an `lxm` URI scheme or a QR code, bounded at 2,210 bytes for
paper and 2,953 for a QR, with unpacking from a file and writing to a directory
on the way back in. Paper is one of the valid delivery methods alongside
opportunistic, direct, propagated and resource.

Peer fields and an access code come to a couple of hundred bytes against that
budget, so **one link or one QR code is the whole exchange**. What remains to
decide is whether to emit one, not how it would travel.

## 7. Still open: a signed sub-second field

The message layer's own timestamp is a float; an event's `created` is an integer
truncation of it, and that truncation is a choice rather than the stack's.
Carrying microseconds as a **separate signed integer** would give the layer's
resolution without a float's canonicalisation hazard, and would make ties rare
everywhere rather than handled in each place that cares.

Nothing needs it now, because reactions are a set and replaceable records carry
a version. It is worth revisiting the next time something does — and it is a
change to the signed event shape, so it cannot be retrofitted quietly.

## 8. Facts about the stack, separated because they outlive this design

- Routing is a datagram mesh with **no consensus and no privileged node**, so
  there is no total order to be had. What it gives instead is the content hash
  that lets one event name another, which is the ingredient every convergent
  answer here uses.
- A **channel or buffer sequences reliably over one link**, which is pairwise
  order and not a joint one.
- An **identity is permanent**: a 16-byte address, 32 hex characters, derived
  from the public key. Persist the key or peers lose you.
- **Custom message fields 0x0100–0x0102** sit above the registered range of
  1–255, which is safer than the generic custom slots at 251–253 where two
  applications would collide.
- A **request handler with an allow-list** is path-routed, access-controlled,
  compressed hosting the stack already ships. Two uses beyond the obvious: the
  byte-transfer path for a shared library, and serving one instance's own pages
  to another instance rather than only to a local browser.
- **Announces carry the identity itself**, which is the only source of an
  author's verifying key. See the porting notes.

## 9. Reversed decisions, which are worth more than the designs they replaced

1. **Layer 2 was going to be the foundation; it became one mode among
   several, opt-in.** The surface never needed it: it writes the routing
   layer's own interfaces, and an instance with no segment and no tunnel runs
   fine. Building the mesh on top of a layer-2 segment would have made the
   ad-hoc case — no shared LAN — the hard case, when it is the main case.
2. **Latest-wins was replaced by an OR-Set for reactions.** `created` is a
   second and reacting then changing your mind happens well inside one, so a
   tie was the normal case. Breaking it by id makes every instance agree on an
   answer as likely to be the *first* reaction as the last: agreement without
   correctness. Two instances that received the same pair in opposite orders
   disagreed and kept disagreeing, because arrival order is fixed once stored
   and nothing revisits it.
3. **An OR-Set was then *not* used for replaceable records.** A note's text is
   a value to replace, not a set to add to, so those took a per-author counter
   instead. One writer means a counter is a total order of their own writes and
   no clock is consulted. Picking one data type for both would have been wrong
   twice.

Prior art, so the next reader does not re-derive it: an OR-Set is the standard
CRDT for add-and-remove; one widely-copied event format breaks a same-second tie
on replaceable events by keeping the lowest id, which converges on an answer as
likely to be the first write as the last; another protocol needed a DAG with
explicit parent links and a whole state-resolution algorithm; and commits in a
version control system, `References:` headers in mail, and the continuation
field above are all the same move — **write the link down**.

## 10. What the glue actually is

Named piece by piece, so the size of the remaining work is honest:

| Piece | Built? | What it is |
|---|---|---|
| The pull exchange — have, diff, get, bounded both ways | **Built**, and checked | §13 |
| The request half over a real link | No | A link, an `identify`, a `request` with a response callback. Blocking, so it runs off the loop. `LxmfCarrier.ask` is the hole |
| The digest announce and its handler | No | An announce per topic carrying version and digest; a handler per subscribed topic |
| Propagation configuration, and optionally being a node | No | Two settings and one call |
| A group-key distribution scheme | No | §4, and undecided before it is unwritten |
| Dual emission of standard fields | No | §5, and undecided before it is unwritten |

Two of the six are undecided rather than merely unwritten, and that distinction
is the useful one: writing them before deciding them is how a surface acquires
two representations that disagree.
