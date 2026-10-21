# `gossip` -- have, diff, get

**Role.** Catching up: ask a peer what it holds and fetch what you are missing.

**In the primitive.** The rules are lifted, as §13. The request transport is the
carrier's; `LxmfCarrier.ask` is the hole.

## What it provides

`have` (ids only), `diff`, `get` (verbatim JSON), `sync`, `answer`.

## What it expects

A store, a carrier that can make a request, and the gate -- nothing fetched
bypasses it.

## Findings encoded here

- **Pull rather than push, because flooding harder does not fix the problem.**
  Publishing reaches every peer the author knows *at that moment*, so an
  instance that was asleep never gets the event and nothing retries. It also
  closes the case of two instances that have each heard a third but never each
  other, since each pulls from whoever it can reach.
- **Over the stack's own hosting primitive**, which is path-routed,
  identity-gated and compresses its own responses, with anything too large for a
  packet becoming a resource without this module asking.
- **The destination is derived, not announced.** It is this instance's own
  identity under a known aspect, so anyone who heard our announce can compute
  where to ask and we advertise no second address.
- **`have` answers ids only, never content**, so the cheap question stays cheap.
- **`get` returns events verbatim**, because the signature covers the bytes: a
  peer that re-encoded one would hand over something that no longer verifies,
  which is the right failure rather than a puzzling one.
- **Nothing fetched escapes verification.** The same gate, with two callers.
  **A peer can tell us what it holds; whether it is true is decided elsewhere.**
- **An identified caller is learned, not checked against a list.** A new
  instance's first act is to ask, which easily beats its own announce, so
  refusing strangers would make catching up a race -- the same race that used to
  drop events at bring-up. An identified link has proved possession of the key,
  and being on this network at all took the shared access code. **An
  unidentified link gets nothing.**
- **Sync on discovery *and* on a timer.** Discovery alone is not enough: the
  peer that was asleep is exactly the one no discovery fires for. One thread per
  peer, never two for the same peer at once, and jitter the interval so a
  surface does not sync in lockstep.
- **Bounded both ways**, so one exchange cannot be made unboundedly expensive by
  asking.

## Lifting it

Take §13. Fill `ask` with a link, an `identify` and a request; it blocks, so run
it off the event loop. The digest-announce half is
[../DISSEMINATION.md](../DISSEMINATION.md) §1.
