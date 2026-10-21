# `bus` -- store first, bus second

**Role.** In-process notification that something new arrived. It carries
nothing durable.

**In the primitive.** Lifted, as §6, with a list in place of an async queue;
the queueing rule is the part that matters and it is the same either way.

## What it provides

`subscribe` with a filter, bounded delivery, and a `publish` that stores before
it notifies.

## What it expects

A store. Subscribers that may be slow.

## Findings encoded here

- **The order is the contract.** Every event is written to the store *before*
  anything is notified, so a subscriber woken by a notification can always read
  the event back.
- **`publish` returning false for an id already held is the whole anti-echo
  rule.** The same event arriving over two paths notifies once, and nothing
  rebroadcasts what it received. There is deliberately no record of which
  adapter or transport an event came from.
- **A full queue drops its oldest notification and counts the drop.** A count
  that climbs is a real signal about a real adapter; an unbounded queue would
  hide it, and `save` must never block.
- **The bus carries nothing durable.** A subscriber that was not listening
  missed it and goes to the store to catch up -- one query, not a replay
  channel. A catch-up overlapping the live stream costs a duplicate the store
  has already refused.
- **No broker.** A heavier pub/sub enters only as an adapter for one specific
  real-time workload, never as the store.

## Lifting it

Use your language's bounded queue. Keep the drop-oldest-and-count rule and the
store-first ordering.
