# `carriage` -- events on messages, peers from announces

**Role.** The only part that knows a message format exists: how an event
travels, how a peer is found, and the three threading rules that fail silently.

**In the primitive.** Lifted, as §14.

## What it provides

`LxmfCarrier`: start, announce, peers, send, and the announce handler that feeds
the key map.

## What it expects

A surface to hand inbound events to, and to be started before any event loop.

## Findings encoded here

- **An event rides as the content of a message, with routing metadata in the
  message's fields** so a dispatcher can route without parsing the JSON. Keys
  `0x0100` kind, `0x0101` tags (including the topic), `0x0102` an optional
  bundle hash. They sit above the layer's registered range of 1–255, which is
  safer than the generic custom slots at 251–253 where two applications would
  collide.
- **The JSON wins.** The fields mirror the event; on any mismatch the signed
  event is the truth.
- **`fields` is documented as a dict and arrives as `None`, as bytes, or as
  something else.** Guard with an isinstance check before reading, every time.
- **Initialise the routing layer once per process, in the main thread, before
  any event loop**, because it registers OS signal handlers Python only allows
  there. Doing it in an executor or after the loop starts fails with "signal
  only works in main thread of the main interpreter".
- **A delivery callback fires in the layer's own thread.** Cross back with
  `run_coroutine_threadsafe` for a coroutine or `call_soon_threadsafe` for a
  callback. **A coroutine created in that thread is never awaited and fails
  silently** -- the callback runs, appears to work, and nothing happens. This is
  the single most expensive bug in this layer.
- **Path discovery blocks**, so a send goes through an executor and never on the
  loop. And a path must exist before a send: check, request, wait with a
  timeout, and **fail the send cleanly if none appears**, because sending
  without a path fails silently and the message simply never arrives.
- **An identity can only be recalled after an announce or message has been
  seen.**
- **`aspect_filter` on the announce handler is not optional.** Without it every
  application on the network -- transport nodes, other tools -- arrives as an
  unexpected peer.
- **Announce after a random 5–30 second delay at start, then periodically**, so
  a healed partition does not storm. Keep the announce's payload small: a name,
  not a state dump.
- **`try_propagation_on_fail` has an effect only when a propagation node is
  configured.** Without one, delivery to an offline peer simply fails.
- **Two instances cannot both run the auto-discovery interface on one host** --
  they fight over the discovery port and one dies. Separate network namespaces
  are how same-machine testing works, which is also the shape production has.
- **Two measured failures from running it for real**, both invisible in a test
  suite: the auto-discovery interface needs a *settled* IPv6 link-local address
  and **a tentative one reads as present**, so a restart hides the race and a
  measurement does not; and a panic in the routing layer exits the process in a
  way that **discards a block-buffered stdout**, so the reason gets written and
  thrown away and the failure arrives as a bare non-zero exit.

## Lifting it

Take §14 as the shape and rewrite the body against your stack's API. The
threading rules are the part to keep; they are properties of the stack, not of
this code.
