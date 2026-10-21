# The portable primitive

`primitive/lxmf_surface.py` is the whole substrate in one file: 1,822 lines,
standard library only, no package to install. `primitive/smoke_test.py` is 34
conformance checks against it, each printing what it saw.

```sh
python3 primitive/smoke_test.py            # the checks
python3 primitive/smoke_test.py --prove    # break three invariants, show them caught
```

```python
from lxmf_surface import Surface, LoopbackCarrier, post, comment, react, posts

surface = Surface()                 # an identity, a store, a bus, and the gate
post(surface, "hello", feed="lobby")
posts(surface.store)                # [<post 9b1e2c4a>]
```

```python
from lxmf_surface import Surface, LxmfCarrier

surface = Surface(carrier=LxmfCarrier(storage_path="/var/lib/app/lxmf"))
# real peers, real announces, events on real messages
```

**A port that passes the 34 checks behaves like the original**, for everything
above §14. They cover canonicalisation, tamper rejection, the gate, the pending
pen, convergence under reordering, the version rule, the index merge, the fetch
refusals, membership replay, the gossip bounds, and a peer that lies about what
it holds.

### What the checks do not cover, stated plainly

**Every one of the 34 runs on `LoopbackCarrier`, in one process. `LxmfCarrier`
is never instantiated.** So §1 to §13 are exercised and §14 is not.

§14 is adapted from code that ran in the project this was condensed from, and
its rules are the findings in [modules/carriage.md](modules/carriage.md) rather
than guesses. But as it stands in this file it has **not been executed against
a running Reticulum**, and `LxmfCarrier.ask` is an unwritten stub. Treat the
whole section as a specification with working provenance, not as tested code:
stand two instances up in separate network namespaces and exercise send,
announce, receive and the pull before trusting any of it. Everything above it
is tested and portable today.

## What is in it

Sections are in dependency order, so lifting a part rather than the whole file
means taking a prefix. Each has a brief of its own in [modules/](modules/README.md).

| Lines | § | Part | Why it earned its place |
|---|---|---|---|
| 72–119 | 1 | kinds and delivery classes | one registry; a kind is a claim about how the whole surface treats a payload, and an unknown one reads as `async` rather than being dropped |
| 120–254 | 2 | `Identity` | the two hashes that are not interchangeable, and the one place signing happens |
| 255–413 | 3 | `canonical`, `build`, `verify`, the LXMF fields | the single serialisation the signature depends on, and the defensive field read |
| 414–453 | 4 | `Filter` | one matcher, used for a local subscription and carried in a gossip request |
| 454–595 | 5 | `Store` | append-only SQLite, and the `received` column that makes arrival order answerable |
| 596–697 | 6 | `Bus` | store first, bus second; bounded queues that count their drops |
| 698–961 | 7 | `Carrier`, `LoopbackCarrier`, `Surface` | the seam, and the accept gate with the pending pen behind it |
| 962–1283 | 8 | posts, comments, reactions | the OR-Set, the tombstone rule, and the feed-is-a-topic convention |
| 1284–1333 | 9 | per-author versions | the counter for things that are replaced rather than added to |
| 1334–1446 | 10 | `Index`, `fetch_key`, `Grants` | the index replicates and the bytes do not; a key is resolved or refused |
| 1447–1509 | 11 | room membership | derived topics, one-round-trip convergence, arrival-order replay |
| 1510–1563 | 12 | chat adapters | channel-to-topic both ways, and a nick made from an identity |
| 1564–1659 | 13 | `have`, `diff`, `get`, `sync` | ask rather than flood, bounded both ways, nothing escaping the gate |
| 1660–1822 | 14 | `LxmfCarrier` | the only section that imports Reticulum, and the three threading rules |

Everything above §14 is arithmetic over JSON and SQLite. §14 is the only part
that knows a message format exists, which is what keeps the mesh door open: the
code above it talks to five verbs — publish, subscribe, send, resolve a name,
list peers — and nothing in it assumes how a peer is reached.

## The floor

- **Python 3.10 or newer.** Standard library only, six modules: `json`,
  `sqlite3`, `hashlib`, `hmac`, `os`, `time`.
- **`rns` and `lxmf` are optional and only §14 needs them.** With `rns`
  importable, hashing and signing use the real Reticulum construction. The
  checks were run both ways in the session that wrote this file: 34 of 34 under
  `rns 1.5.7` with `lxmf 1.2.0`, and 34 of 34 with neither installed.
- **The versions the findings were established against** are `rns 1.5.7` and
  `lxmf 1.2.0`.

### The stand-in signer is not a security construction

Without `rns`, `Identity` falls back to HMAC-SHA256 under a secret both sides
hold. It exists so the invariants above are checkable in a process with no
Reticulum stack, and for nothing else — it has no public half, so it cannot
model the one property the real construction is for. **Never ship it as the
signer between machines.** The docstring says so at the class, which is where
somebody would otherwise get it wrong.

## What was left out, and where each omission is written up

| Left out | Why | Where it is |
|---|---|---|
| The gossip request half over a real link | It is a link, an `identify`, and a `request` with a response callback, and it blocks. The rules it must obey are §13 and are checkable without it | `LxmfCarrier.ask`, and [modules/gossip.md](modules/gossip.md) |
| The digest announce, and propagation nodes | Designed, not built. Pull closes the gap; both of these make it cheaper | [DISSEMINATION.md](DISSEMINATION.md) §1, §3 |
| Layer 2 between instances — Ethernet frames on links, fragmentation, a learning table | Not over LXMF and not in this bundle's subject. A room's *membership* is here; its frame transport is not | [modules/rooms.md](modules/rooms.md), "What is not here" |
| The HTTP serving half — a proxy, a DNS responder, name answering for clients that cannot be configured | A separate problem from the surface, and a large one | [modules/webapp.md](modules/webapp.md) |
| An archive reader, and full-text search | Format work, not surface work. The catalog pattern that makes archives replicate is §10 | [modules/catalog.md](modules/catalog.md) |
| Mail, and an OSCAR or Mastodon adapter | Intended and unwritten. The kinds are reserved and the adapter shape is §12 | [modules/chat-irc.md](modules/chat-irc.md), "Lifting it" |
| Encrypted private topics | The primitive is there — an identity encrypts to another identity — and distributing the keys is the unanswered half | [DISSEMINATION.md](DISSEMINATION.md) §4 |

## Porting notes: the invariants that are easy to drop

Ranked by how quietly each one fails.

1. **`canonical` has exactly one implementation.** Sorted keys, no incidental
   whitespace, UTF-8, every signed field present even when empty, and `id` and
   `sig` excluded. Serialise an event for signing anywhere else and signatures
   stop verifying between your build and everyone else's, with no symptom but
   "their events never verify".
2. **`sig` covers the canonical bytes *plus the id*,** not the bytes alone.
3. **An author's verifying key comes from an announce, never from a recall.**
   An identity hash and a delivery destination hash are different values;
   recall is keyed by the second. Keep the map §7 keeps. Conflating them gives
   messages that arrive and cannot be verified, which reads as a signing bug.
4. **Store before you notify.** A subscriber woken by a notification must be
   able to read the event back.
5. **Return false for an id already held, and do not notify again.** That is
   the whole of the anti-echo rule, and nothing may rebroadcast what it
   received.
6. **Hold an event whose author is unknown; do not drop it.** Bounded, oldest
   let go. Dropping is permanent, because nothing retries.
7. **Resolve reactions as a set, never as latest-wins.** No clock, no arrival
   order. `--prove` shows latest-wins diverging across two arrival orders.
8. **Use `received` for a log and `created` for display.** Replaying membership
   by authored order reports somebody as in a room they left.
9. **Check `isinstance(fields, dict)` before reading LXMF fields,** and let the
   signed JSON win on any mismatch.
10. **Never let a remote filename become a path.** It is an index key resolved
    through the index or refused, and the bytes are checked against what the
    index promised rather than what the sender claims.
11. **A grant never replicates.** It is local state, not an event, and that is
    what makes an ingestion gate hold across instances.

## Thread rules, for an async build

The three in §14 are the ones that cost real time, and the first two fail
silently:

- Initialise Reticulum **once per process, in the main thread, before any event
  loop**. It registers OS signal handlers Python only allows there.
- A delivery callback fires in an LXMF thread. Cross back with
  `run_coroutine_threadsafe` for a coroutine or `call_soon_threadsafe` for a
  callback. **A coroutine created in that thread is never awaited**: the
  callback runs, appears to work, and nothing happens.
- Path discovery blocks. A send goes through an executor and never on the loop.

One more that is not about threads: two instances cannot both run
`AutoInterface` on one host — they fight over the discovery port and one dies.
Separate network namespaces are how same-machine testing works, which is also
the shape production has.
