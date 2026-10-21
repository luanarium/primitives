# `fetch` -- a key resolved through an index, or refused

**Role.** Moving the bytes an index row describes, between instances, without
letting a remote name become a path.

**In the primitive.** The rules are lifted, as §10's `fetch_key`. The transport
is the carrier's.

## What it provides

`fetch_key`: resolve a key through the index, read via a holder, check the
bytes against what the index promised, raise `FetchRefused` otherwise.

## What it expects

An index with size and digest on every row, and a reader that produces bytes.

## Findings encoded here

- **A filename in a remote fetch is an index key resolved through the index or
  refused -- never a path.** Nothing in the path opens a file by a name a peer
  sent, so there is no traversal to defend against: a key nobody published is
  simply not a thing that can be asked for.
- **The bytes are checked against what the index promised, not against what the
  sender claims about them.** Those are two different claims and only the first
  one is verifiable.
- **The instances are the peers.** A client dials its own instance and that
  instance fetches from the far one -- so no client is ever asked to serve
  anybody, the firewalled-peer path disappears, and the address handed back to
  the client is its own instance's, which is the address it is most certain of.
- **An instance says where it answers in a signed event**, so the transfer
  target is authenticated rather than configured.
- **The transport is the core's choice, not a plugin's.** It is a seam on
  purpose: a direct connection today, a resource over a routed path later, with
  nothing above it changing.
- **One defect worth repeating, because it survived review:** an instance told
  every peer to fetch bytes from *its own* machine -- the address it published
  was the one it had locally rather than the one a peer should dial. It works
  perfectly in a single-host test.
- **A published pin key must be the collection's own key, not the file's base
  name.** Getting that wrong makes pinning work from a collection's root and
  fail from a subdirectory as "a key nobody holds", which points at the wrong
  layer entirely.

## Lifting it

Take `fetch_key` and keep both refusals. Fill the reader with your transport.
