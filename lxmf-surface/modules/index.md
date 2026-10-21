# `index` -- the index replicates, the bytes do not

**Role.** How one instance tells every other what it holds, at a scale where
the things themselves cannot travel.

**In the primitive.** Lifted, as §10.

## What it provides

`Index.publish` (full state with a version), `Index.rows` (merged by author at
each author's highest version), `Index.holders`.

## What it expects

A version per author, and rows carrying the size and digest of the exact bytes
that will be sent.

## Findings encoded here

- **A row is a few hundred bytes and the thing it describes can be gigabytes**,
  so what reaches every instance is the knowledge of what exists and who holds
  it. This is the decision that makes content sharing work at this scale.
- **An index announces a version, never a change.** A missed event then costs a
  round trip, rather than leaving two indexes that disagree permanently with
  nothing able to notice.
- **Exactly one writer per index -- the instance whose files it describes -- so
  there is no merge conflict to resolve.** Peers merge locally, which is what
  makes a search terminate at once with no slowest peer and no deadline to tune.
- **Full state, not a delta.** A delta needs every prior delta; full state with
  a version needs only the newest.
- **A row carries the size and checksum of the exact bytes that will be sent**,
  and the client checks both, so a transfer is a pipe and nothing else.
- **A published row carries no name to lie with.** Any display name is composed
  by the instance showing it, from a claim the surface verified -- never taken
  from the row.
- **Scope is a decision.** An index can federate with instances running the same
  plugin, or with any instance. Per-plugin is the right default, because an
  app's index and roster are its own; a store that is genuinely the whole
  surface's is the exception that has to be chosen deliberately.

## Lifting it

Take §10's `Index`. The version rule is [versions.md](versions.md), reused on
purpose.
