# `gate` -- the one place the wire becomes the store

**Role.** An instance: identity, store, bus, the carrier seam, and `accept` --
the only gate between anything external and the store.

**In the primitive.** Lifted, as §7.

## What it provides

`accept`, the pending pen, the announce-fed key map, `publish`, `subscribe`,
`send`, `resolve`, `peers`.

## What it expects

A carrier that calls `accept` on what arrives, and `learn` on what an announce
hands over.

## Findings encoded here

- **One gate, two callers.** A message that arrived by itself and an event
  fetched because we asked go through the same verification. **A peer can tell
  us what it holds; whether it is true is decided here and nowhere else.**
- **An event that outruns its author's announce is held, not dropped.** A
  verifying key comes from an announce, and at bring-up the first events between
  two instances routinely arrive first. Dropping them lost real messages
  silently, because nothing retries -- found by standing two instances up and
  watching three posts in a row disappear. The event waits in a bounded pen and
  the announce drains it.
- **The pen is bounded and counts what it let go**, because a stranger could
  otherwise fill memory with events signed by nobody. Past the limit the oldest
  is let go -- the same rule the bus applies to a slow subscriber.
- **Association needs no pairing step and no accounts.** Two instances sharing a
  network name and passphrase -- the routing layer's own interface access code --
  see each other's announces and the surface is one space. Announces are signed,
  which is what replaces accounts.
- **Handle only announces on the message layer's delivery aspect.** Without that
  filter every application on the network arrives as an unexpected peer.
- **Publish locally first.** The instance that produced an event behaves exactly
  like one that received it.
- **A name belongs to the identity that announced it, first claim wins**, and a
  name claim is an event -- so resolution is a question about the store rather
  than a registry somebody keeps in sync.
- **Keep the carrier narrow and the mesh door open.** The five verbs are the
  whole interface; addresses, names and topics mean the same thing on any
  reachable path, nothing assumes a shared segment, and delivery to a peer that
  is offline or several hops away is the sender asking the layer to deliver
  rather than tracking where the peer is.

## Lifting it

Take §7 whole. If you replace the carrier, the only contract is: call `accept`
on inbound events, call `learn` with an identity when an announce arrives, and
make `send` not block the event loop.
