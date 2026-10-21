# Web, chat and social over LXMF: an integration brief

Everything needed to build a web, chat and social surface on Reticulum and LXMF
without rediscovering it. Written for a project that is not the one this came
out of: nothing here assumes a package layout, a CLI or a directory convention.

Established against **`rns 1.5.7`** and **`lxmf 1.2.0`**, on Python 3.10. Where
a finding is marked OBSERVED it was read off a running pair of instances or off
the libraries themselves; where the stack's own documentation disagrees with
what was observed, the observation is stated and so is the disagreement.

The companion documents:

| | |
|---|---|
| [PRIMITIVE.md](PRIMITIVE.md) | the one portable file, what it holds, what it leaves out, and the invariants that are easy to drop |
| [DISSEMINATION.md](DISSEMINATION.md) | the designed-but-unbuilt half: digest announces, propagation nodes, private topics, and three reversed decisions |
| [modules/](modules/README.md) | one brief per part, with the findings encoded in each |
| [primitive/smoke_test.py](primitive/smoke_test.py) | 34 conformance checks; run it, do not read it |

---

## 1. The shape of the problem

**This is five problems, and the message layer answers one of them.** That is
the single most useful thing in this bundle, because the layer that looks like
the whole job is the part that is already done.

| # | Seam | What it decides | Does the stack answer it? |
|---|---|---|---|
| 1 | **The payload** | what a post, a line of chat, a comment or an index row *is*, and how it stays verifiable after being forwarded | No. It gives you hashing, signing and identities to build it from |
| 2 | **Local durability** | what is true on one instance, and what a subscriber missed | No. Entirely yours |
| 3 | **Dissemination** | how an event reaches an instance that was asleep, or that you have never heard of | **Partly, and not the part people expect.** See below |
| 4 | **Protocol adapters** | what a client actually speaks: IRC, a Mastodon API, mail, HTTP | No |
| 5 | **Content at scale** | how a gigabyte is shared on a network with a 464-byte broadcast | No, but it gives you the pieces |

Routing discovers paths and delivers encrypted packets. The message layer
delivers a message from one identity to another, with acknowledgement and
store-and-forward. **Neither knows what is in the payload**, and that is the
correct division — it is also why four of the five seams above are yours.

### The part of seam 3 that bites

**Delivery is not dissemination, and the stack only does delivery.** Sending an
event to every peer you know is N² in fanout, ignores whether the peer wants the
topic, and — the part that actually matters — reaches only the peers you know
*at that moment*. Three consequences, the third being the one that decides your
architecture:

- An instance that was asleep never gets the event, and nothing retries.
- A kind that is only correct when re-published self-heals; a chat line missed
  while offline is simply gone.
- **A↔B and B↔C, with A never having heard C, means C misses A's events
  permanently**, because nothing forwards. That is precisely the ad-hoc case a
  mesh exists for.

Store-and-forward does not fix this. **Propagation is addressed per recipient
destination, not per topic**: it is a mailbox, not a topic bus. It fixes offline
delivery and backfill and it does not fix fanout.

The answer that works is **ask, not flood** — a peer tells you what it holds and
you fetch the difference, through a gate that verifies everything. That is built
and checked (§13 of the primitive). The cheaper half, announcing a digest so a
peer can skip asking, is designed and unbuilt:
[DISSEMINATION.md](DISSEMINATION.md).

### The second framing decision

**Everything is a signed event in an append-only store, and the store is the
truth.** A feed, a chat channel, a shared index, a room's membership and a name
claim are one object with a different `kind` and a different topic. The payoff
is that the same bytes mean the same thing over any path, now or after you add
a federation boundary; the cost is that you resolve questions over a *set* of
events rather than reading current state out of a table, which is what §2 and
§6 below are about.

---

## 2. The corrections

Numbered, and each one says what it contradicts. The first five cost the most
time.

1. **`message.fields` is documented as a dict and is not always a dict.**
   OBSERVED: it arrives as `None`, as bytes, or as another type depending on the
   sender and the message type. Guard with an isinstance check before every
   read. Contradicts the field documentation.

2. **A delivery destination hash and an identity hash are different values, and
   `Identity.recall` is keyed by the destination hash.** An event's `author` is
   an *identity* hash, so you cannot recall the key you need to verify it. The
   verifying key comes from the announce that carried the identity, and you must
   keep a map of them yourself. Contradicts the obvious reading, under which a
   hash is a hash.

3. **A send with no path in the table fails silently.** OBSERVED: the message
   appears to send and never arrives. Check for a path, request one, wait with a
   timeout, and fail the send cleanly. Contradicts the API's shape, which
   returns as if it had queued something.

4. **A coroutine created inside a delivery callback never runs, and nothing
   says so.** The callback fires in the message layer's own thread. Creating a
   coroutine there appears to work and does nothing. Cross the boundary
   explicitly — `run_coroutine_threadsafe` for a coroutine,
   `call_soon_threadsafe` for a callback. Contradicts nothing in the docs,
   which is the problem: this is the most expensive bug in the layer.

5. **`try_propagation_on_fail` has no effect unless a propagation node is
   configured.** Setting it is not the same as having store-and-forward.
   Without a node, delivery to an offline peer simply fails. Contradicts the
   flag's name.

6. **Routing must be initialised once per process, in the main thread, before
   any event loop starts.** It registers OS signal handlers Python only allows
   there; doing it in an executor or after the loop starts fails with *"signal
   only works in main thread of the main interpreter"*. Contradicts the normal
   expectation of a library that it can be constructed anywhere.

7. **An announce handler with no `aspect_filter` receives announces from every
   application on the network** — transport nodes, other tools — each arriving
   as an unexpected peer. OBSERVED. Contradicts the obvious reading of "register
   a handler for announces".

8. **Two instances on one host fight over the shared-instance socket, and the
   symptom reads as a crypto fault**: *"digest received was wrong"*, *"digest
   sent was rejected"*, *"error handling RPC call from local client"*. Pass a
   unique configuration directory per instance and disable the shared-instance
   requirement; delete a stale directory from a previous run, because the socket
   left behind causes the same errors even after the fix. OBSERVED. Separate
   network namespaces are the real answer, and they are also the shape
   production has.

9. **A propagation node is not a sequencer.** OBSERVED in its storage: messages
   are content-addressed by their own hash and its `received` is its own clock.
   It assigns no order anybody else can use. Contradicts the obvious hope, and
   depending on it would make an optional component load-bearing for
   correctness.

10. **A group destination gives shared encryption on one hash, not guaranteed
    multicast.** Whether one packet reaches many holders is the interface's
    business: a broadcast-capable interface delivers to all, routed transport
    takes one path. It is a channel *key*. Contradicts the natural reading of a
    "group" destination.

11. **An announce carries 464 bytes less identity and signature, so `app_data`
    is for digests and pointers and never for payloads.** Contradicts the
    temptation to put state in an announce.

12. **An aspect is matched exactly — no prefixes, no wildcards, one handler per
    topic** — because it is hashed with the identity. This bounds any design
    that makes a topic an aspect.

13. **The message layer defines reaction fields but defines no retraction.** Its
    own note says the handling of reaction content is left to the client, so the
    half that actually bites — taking a reaction back — is yours to define.
    Contradicts the assumption that adopting a standard field gets you the whole
    semantic.

14. **Every relation the layer defines names its target by full hash** —
    reaction-to, comment-for, continuation-of. Match that shape in your own tags
    or emitting the standard fields later becomes a migration.

15. **The auto-discovery interface needs a *settled* IPv6 link-local address,
    and a tentative one reads as present.** OBSERVED only when measured against
    a real interface: a service restart hides the race and a test suite never
    sees it. It also refuses to run at all with no link-local address, and says
    so plainly.

16. **A panic in the routing layer exits the process in a way that discards a
    block-buffered stdout.** OBSERVED: the reason gets written and thrown away,
    and the failure arrives as a bare non-zero exit. Flush or line-buffer your
    log before you need it.

---

## 3. What breaks it, ranked by how often it will

| # | Symptom as you see it | Cause | Fix |
|---|---|---|---|
| 1 | Inbound events do nothing. The callback logs fine | A coroutine created in the message layer's thread is never awaited | Cross the thread boundary explicitly (correction 4) |
| 2 | "Their events never verify." Looks like a signing bug | The author field was recalled instead of looked up in the announce-fed map | Keep the identity-hash map (correction 2) |
| 3 | The first few messages between two instances vanish, reliably, at bring-up | Events outran the announce that would verify them, and were dropped for want of a key | Hold them in a bounded pen and drain it on the announce |
| 4 | Messages "sent" that never arrive, no error anywhere | No path in the table at send time | Check, request, wait, fail cleanly (correction 3) |
| 5 | Crypto errors on a two-instance test on one machine | Shared-instance socket contention | Unique config dir, no shared instance, clean up stale state, or use namespaces (correction 8) |
| 6 | Nobody can verify anything, between your build and another | Two canonicalisations of the event bytes | One implementation, sorted keys, `id` and `sig` excluded |
| 7 | The whole instance stalls under load | Path discovery or a send ran on the event loop | Executor for anything blocking |
| 8 | Memory climbs, or a slow consumer silently loses events | An unbounded queue, or a bounded one that drops without counting | Bound it, drop the oldest, count the drop |
| 9 | Two instances disagree about a reaction, permanently | Latest-wins resolution over same-second events | Resolve as a set (§6) |
| 10 | The surface will not come up, and a restart fixes it | A tentative link-local address read as present | Wait for it to settle (correction 15) |
| 11 | A page arrives with a 200 and renders blank or unstyled | An era client dropped every declaration using a custom property, or relative assets resolved against the wrong path | [modules/webapp.md](modules/webapp.md) |

---

## 4. The out-of-band surfaces

Everything this reaches for that the message layer does not provide. Exact
values, because they are data and paraphrasing loses them.

**From the routing layer rather than the message layer:**

- **Announces** — peer discovery and the only source of an author's verifying
  key. Filter on the delivery aspect. 464-byte budget less identity and
  signature.
- **Request handlers** — path-routed, identity-gated, auto-compressing hosting.
  This is the pull transport and the byte transport. A maximum request size
  bounds it.
- **Resources** — bulk transfer over a session, segmented above **1,048,575
  bytes**.
- **Sessions** — encrypted direct connections; MDU **431**. Channels and buffers
  add reliable sequencing over one, which is pairwise order and not a joint one.
- **Identity encryption** — an identity encrypts to another identity, which is
  the primitive for group keys. Distribution is unsolved
  ([DISSEMINATION.md](DISSEMINATION.md) §4).

**Your own, and not the protocol's:**

- **The group secret is a network name plus a passphrase**, used as the routing
  layer's interface access code on every generated interface. Only instances
  with the same pair exchange traffic. This replaces accounts and pairing.
- **A persisted identity file.** Non-negotiable: a new identity at every start
  is a new address.
- **Message field keys** `0x0100` kind, `0x0101` tags as a JSON string
  including the topic, `0x0102` an optional bundle hash. Above the registered
  range of 1–255, and deliberately not the generic custom slots at 251–253
  where two applications would collide.
- **A derived request destination**: your own identity under a known aspect, so
  a peer who heard your announce can compute where to ask and you advertise no
  second address.
- **Out-of-band first contact.** A message serialises to a URI or a QR code,
  bounded at **2,210** bytes for paper and **2,953** for a QR. Peer fields and
  an access code come to a couple of hundred bytes, so one link or one QR is the
  whole first exchange.
- **A propagation node hash**, if you want store-and-forward, and optionally
  being one yourself.
- **A stamp cost**, if the surface is open to strangers: senders pay a small
  proof of work for messages to you. Zero is none.

**Not in this bundle at all:** the HTTP side for clients that cannot be
configured — answering names locally, giving each name an address, and proxying
to a renderer. That is a separate and large problem.

---

## 5. Configuration, and what is deliberately not written

The settings that matter, as a shape rather than a format:

```
network         a name; with the passphrase, the group secret
passphrase      from a file, not from the config body
identity_file   persisted; the address derives from it
peers           optional static addresses, for where discovery does not reach
propagation     whether this instance stores and forwards for others
propagation_node    whose mailbox to use, if any
stamp_cost      proof-of-work asked of senders; 0 is none
```

**Deliberately not written down anywhere:**

- **Grants.** What an item may do *here* is local state, never an event and
  never replicated. That asymmetry is the whole reason an ingestion gate holds
  across instances ([modules/catalog.md](modules/catalog.md)).
- **Arrival order.** It is a column in the store, not a field in the event: it
  differs per node, and a timestamp in an event is a claim.
- **Anything derivable.** A room's addresses, resolution state, what the
  catalog thinks is held, the current value of a versioned record. **Two
  sources of truth is the bug**, and every one of these was a table before it
  was a function.
- **Which adapter or transport an event came from.** There is no such record, on
  purpose: it would be the beginning of forwarding, and nothing rebroadcasts
  what it received.

**One structural recommendation** that is about deployment rather than the
protocol: split privilege. Whatever changes the network runs as a privileged
one-shot and exits; whatever serves untrusted content runs unprivileged for as
long as it is up. The half that touches other people's bytes should be the half
with no capability to lose.

---

## 6. Fidelity: what makes it behave right rather than merely work

**Convergence.** Two instances holding the same events must agree, and the only
way to get that from a datagram mesh with no consensus and no privileged node is
to make every question a question about a *set*:

- **A reaction is an OR-Set.** An add is an event, its own id is the add's
  unique tag, a removal names the add it cancels, and the set is every add no
  removal *from the same author* names. No clock, no arrival order, and a
  removal that arrives before its add still works.
- **A tombstone is a set question too**, checked against the target's own
  author, which is why posts and comments were already convergent.
- **A replaceable record carries a per-author version**, not a timestamp. One
  writer means a counter is a total order of their own writes.
- **Arrival order is for display and for logs, never for resolution.** Two
  instances may show a pair of same-second posts in different orders. That is
  cosmetic; the same ambiguity in a reaction was not.

**Pacing and bounds**, all of which exist because the unbounded version failed:

| Thing | Value | Why |
|---|---|---|
| Announce at start | random **5–30 s** delay, then periodic | a healed partition otherwise storms |
| Sync | on discovery **and** on a jittered timer | discovery alone never fires for the peer that was asleep, which is the one that needs it |
| Sync concurrency | one thread per peer, never two for the same peer | |
| Subscriber queue | **256**, drop oldest, count the drop | a climbing count is a real signal; silence hides a broken adapter |
| Pending pen | **256**, drop oldest, count | a stranger could otherwise fill memory with events signed by nobody |
| `have` answer | **2,000** ids | so the cheap question stays cheap |
| `get` batch | **64** events | so one exchange cannot be made unboundedly expensive by asking |

**Defaults that are load-bearing:**

- **The default feed is cross-talk.** Every adapter and every view writes into
  one feed unless told otherwise, so three clients are three windows onto one
  conversation rather than three conversations. A named feed is a topic and
  exists the moment somebody writes in it; nothing creates one.
- **A comment rides its post's topic**, so one subscription carries a feed and
  its replies.
- **Delivery follows the kind.** `async` to the layer's delivery and
  store-and-forward; `live` to the recipient's app logic, held there until its
  client is up; `ephemeral` never stored and never retried.
- **Everything about a room is derived from its name**, so create and join are
  the same act and there is nothing to allocate.
- **Ids are shown as twelve characters and accepted as any unique prefix**,
  because a command that printed an id it would then refuse cannot be used from
  its own output.

---

## 7. Data rules

- **Anything fabricated must be discoverable as fabricated, and anything
  missing is left missing.** A gap is honest; a guess is not. This is the rule
  the rest of this section implements.
- **A published row carries no name to lie with.** Any display name is composed
  by the instance showing it, from a claim the surface verified — never read out
  of the row. The same applies to a chat nick: derive it from the identity that
  signed the event, so a peer cannot impersonate a local name.
- **A plugin or adapter that publishes speaks as the operator**, because an
  instance has one identity. Stamp the publisher's name onto the event **in the
  core**, never from the content, so one cannot claim to be another or to be
  nobody.
- **Somebody else's text is text.** A received annotation or post is rendered as
  text, attributed, and never merged into the operator's own data.
- **Untrusted content gates at ingestion, per item, defaulting to off, set by a
  person.** Not a configuration key with a permissive default.
- **A reader written from a specification and never pointed at real output is
  unmeasured, and has to say so.** Testing it against an independent
  implementation of the same specification proves the two agree, not that either
  is right.
- **A measurement records only what your own code did**, and whatever was
  substituted for a real component is written down beside what was found. **A
  date also has to say what asked**: a surface exercised by a test instrument
  rather than by a real client is a different claim, and the missing client is
  the first gap in the record rather than a detail.

---

## 8. Diagnostics: the artefact that made the findings possible

**Two real instances, in separate network namespaces, with one of them made to
miss everything.** Almost every finding in §2 and §3 came from that and from
nothing else. A single-process test cannot produce them: it has no announce
race, no path table, no shared-instance contention, and no peer that was asleep.

Three variants are worth building, in this order:

1. **Two instances, one offline for a while, then catching up.** Finds the
   dissemination gap, the pen, the gate's second caller, and every bound.
2. **Replay in two orders.** Feed two fresh stores the same event set forwards
   and backwards and assert they agree. This is cheap, runs in one process, and
   is the only thing that catches a resolution rule that does not converge.
   `smoke_test.py --prove` shows latest-wins failing it.
3. **A real install at real paths, with a real client in front of it.** Finds
   what no suite reaches: the privilege split, service units, address settling,
   and the log that gets discarded on a panic. Everything that runs out of a
   temporary root stays unmeasured while reading as finished.

**Make a check fail on purpose once.** A conformance check that never saw the
behaviour it names is worse than no check — `--prove` exists because of that.

---

## 9. Integration order

1. **Read §1.** If you take one thing from this bundle, it is that the message
   layer answers one of five seams, and that delivery is not dissemination.
2. **Run `primitive/smoke_test.py`.** 34 checks, each printing what it saw, so
   the output is also a transcript of what this surface does.
3. **Read §2 corrections 1–5 and §3 rows 1–5.** They are most of the time this
   layer will otherwise cost you.
4. **Take the event shape and the canonicaliser** ([modules/events.md](modules/events.md)),
   and decide your kind numbers. Do not change the canonicaliser.
5. **Take the store, the bus and the gate** (§5–§7 of the primitive). The
   store-first ordering, the duplicate rule and the pending pen are the three
   things to keep exactly.
6. **Choose your convergence rules before writing features** (§6). Retrofitting
   a version tag or a removal tag onto a signed event shape is a migration.
7. **Wire a carrier.** [modules/carriage.md](modules/carriage.md) has the three
   threading rules; they are properties of the stack, not of this code.
8. **Add dissemination.** Pull first, because it closes the gap; the digest
   announce and propagation make it cheaper
   ([DISSEMINATION.md](DISSEMINATION.md)).
9. **Then adapters** ([modules/chat-irc.md](modules/chat-irc.md)) and content
   ([modules/index.md](modules/index.md), [modules/fetch.md](modules/fetch.md),
   [modules/catalog.md](modules/catalog.md)).

## What this bundle does not carry

- **A running network.** No interfaces are configured, no propagation node is
  named, and nothing here reaches the network at import. §14 of the primitive is
  the only part that would, and it is inert until constructed.
- **The request transport for the pull.** A session, an `identify` and a
  request, which blocks. The rules it must obey are checkable without it, which
  is why they are built and it is not
  ([modules/gossip.md](modules/gossip.md)).
- **Layer 2 between instances.** Frames on sessions, fragmentation, a learning
  table. Not over the message layer and not this bundle's subject; the four
  facts from it that transfer anyway are in
  [modules/rooms.md](modules/rooms.md).
- **The HTTP serving half** — name answering, per-name addresses, a proxy. A
  separate problem, and larger than this one.
- **An archive format reader, and full-text search.** Format work rather than
  surface work; the catalog pattern that makes large content replicate is here
  without it ([modules/catalog.md](modules/catalog.md)).
- **Mail, OSCAR and Mastodon adapters.** Reserved kinds and an adapter shape,
  unwritten ([modules/chat-irc.md](modules/chat-irc.md)).
- **A moderation policy.** There is none, and for a surface of a few associated
  instances that is the honest default rather than an omission.
- **A security review of the stand-in signer**, because it does not want one:
  it is HMAC under a shared secret, it exists so the invariants are checkable
  without a Reticulum stack, and it says so at the class.
