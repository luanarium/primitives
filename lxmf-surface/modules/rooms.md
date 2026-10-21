# `rooms` -- membership that converges in one round trip

**Role.** A named space several instances are in, where nothing about it is
allocated.

**In the primitive.** Membership is lifted, as §11. The frame transport is not;
see "What is not here".

## What it provides

`room_topic`, `join_event`, `greeting_for`, `members`.

## What it expects

A surface to publish on, and a store to replay from.

## Findings encoded here

- **Everything about a room is derived from its name, which is what makes
  create and join the same act.** Two people who both join `lunch` are in the
  same room, neither is the one who made it, and neither has to be running when
  the other joins. Nothing is allocated and there is no second source of truth.
- **Membership rides the surface, not a session**, because it has to reach an
  instance *before* any session to that instance exists.
- **One round trip, and a greeting never answers a greeting.** An arriving
  instance says `join`; every instance already in replies `here` exactly once; a
  departing one says `leave`. Greeting a greeting is how that becomes a storm.
- **The log is replayed in arrival order, not by the authors' timestamps.** A
  join and a leave made in the same second would otherwise come back in id
  order -- an order with nothing to do with which happened -- and would report
  somebody as in a room they left. This is the clearest case for why the store
  keeps `received`.
- **It is a log and says so.** An instance that left without saying so is still
  in it; a serving process knows who is actually answering, and a process that
  only has the events does not.
- **Reaching a room is not membership.** Anything that can reach the room's
  destination can open a session to it; the signed membership event is what
  counts, and a frame from a non-member is dropped.

## What is not here

The frame transport: Ethernet frames carried between instances over sessions,
the fragment header, reassembly, and the learned address table. It is not over
the message layer -- frames go as unreliable session packets, because a frame
that needs a retry has already missed the moment it was for -- and it is layer 2
rather than this bundle's subject. Four facts from it that transfer anyway:
a fragment header naming the room means one session carries every room two
instances share; a missing fragment drops its whole frame and nothing is
retried, which is what a switch dropping a frame does; unicast is switched by
learning from source addresses rather than flooded; and what was learned behind
a member goes when that member does.

## Lifting it

Take §11. If you add a frame path, keep membership on the surface -- it is the
only thing that works before a session exists.
