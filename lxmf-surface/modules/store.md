# `store` -- append-only, because an id is a hash of its own bytes

**Role.** Every event, on disk, never updated and never deleted.

**In the primitive.** Lifted, as §5, on SQLite from the standard library.

## What it provides

`add` (false when already held), `has`, `get`, a filtered `query` with two
orderings, and counts.

## What it expects

Events that have already passed the gate. The store does not verify.

## Findings encoded here

- **Append-only is not a storage preference.** An event's id is a hash of its
  own bytes, so editing a row in place would break its signature. A correction
  is a new event that supersedes; a deletion is a tombstone.
- **A duplicate is the normal case, not a fault.** The same event arrives
  directly and again out of store-and-forward or a pull, and returning false
  rather than raising is what makes that harmless.
- **Ephemeral kinds are never stored.** Presence would grow the store forever
  with information that is wrong by the time anybody reads it.
- **Arrival order is the store's own and is not in the event.** A row carries
  `received`, the local time it arrived, and the row order; neither is part of
  the event, its id or its signature, because arrival order differs per node and
  a timestamp is a claim.
- **`received` and `created` answer different questions, and picking the wrong
  one is a real bug.** Two events made in the same second tie on `created` and
  break the tie by id -- deliberate for a question about authorship, because
  every instance computes the same id and so agrees, and **wrong for replaying
  a log**, where a join and a leave in one second have to come back in the
  order this node saw them. See [rooms.md](rooms.md).
- **A filter's `since` is a time, not a cursor.** Between instances the
  cursor's job is done by an index announcing a version; see [index.md](index.md).

## Lifting it

Any append-only store with a primary key on the id works. Keep the `received`
column and both orderings.
