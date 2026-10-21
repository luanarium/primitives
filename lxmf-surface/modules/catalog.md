# `catalog` -- replicating what exists without replicating what it is

**Role.** The pattern that lets large, untrusted content be shared across a
surface: the catalog travels, the bytes stay, and a gate decides what any item
may do locally.

**In the primitive.** The grant model is lifted, as §10's `Grants`. The content
reader is not; see "What is not here".

## What it provides

Three states per item per instance -- `held`, `pinned`, or `catalog` and served
by proxying to a holder -- and a local grant table that defaults to no.

## What it expects

An index ([index.md](index.md)) and a fetch path ([fetch.md](fetch.md)).

## Findings encoded here

- **Ingestion is a gate, and incoming content is untrusted.** Adding an item
  scans it, reports what it found -- digest, the hosts it claims, its layout,
  whether it contains script at all -- and asks questions whose answers **both
  default to no**, per item, set by a person, with no configuration key that
  turns them on by default.
- **A grant is local and never replicates.** A catalog row says what an item
  *is*; a grant says what it may do *here*. That asymmetry is the whole reason
  the gate holds across instances, and it is why a grant is not an event and has
  no kind.
- **An item that arrived by replication is quarantined**: no scripts, no
  emulation, neither grantable -- and still catalogued, searchable and readable,
  which is the point of replicating it. Leaving quarantine is a human act.
  **Pinning an item's bytes is not adopting it.**
- **The default presentation is your own namespace, not the original location.**
  One origin per item, stable and linkable. Emulating the real host is an
  overlay, so declining that grant costs the original URL and nothing else.
- **Scripts-off cannot be a header alone.** An era client ignores a content
  security policy entirely, so a scope serving such clients enforces it by
  **stripping at serve time**. A modern client gets the stripping *and* the
  policy, because a header is a second line rather than a first one.
- **An address is not an origin.** Items can share a serving address, which is
  free because the host header tells them apart. They must never share an
  *origin*, or one reads another's storage.
- **One provider among several.** An ordered list per endpoint, so a miss falls
  through rather than failing.
- **A reader written from a specification and never pointed at real output is
  unmeasured, and must say so.** Testing it against an independent
  implementation of the same specification proves the two agree, not that either
  is right.
- **Declare the lowest version floor you can read, and refuse the unreadable
  case by name at the point of reading.** A floor set by the newest format you
  support refuses the whole thing on an older interpreter, including for the
  content it could have read perfectly.

## What is not here

The format reader, and full-text search. Full-text means reading an index format
the stack cannot read; titles and metadata are reachable in-stack and useful at
this scale, and **a page calling itself a search engine while matching only
titles would overclaim**, so it says which it is doing. A title search over a
sorted pointer list is a binary search and a short walk rather than a scan.

## Lifting it

Take `Grants` and the three states. The gate's wording is yours; the defaults
are not negotiable.
