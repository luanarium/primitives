# `events` -- the signed JSON payload everything else moves

**Role.** One payload shape for the whole surface: a JSON object anyone can
verify without trusting whoever forwarded it. A chat line, a post, a comment, a
name claim, a share index and a room join are all this object with a different
`kind`.

**In the primitive.** Lifted, as §1 and §3.

## What it provides

The event shape, verbatim:

```json
{
  "id": "9b1e...",
  "author": "6f3a...91c2",
  "kind": 1,
  "topic": "irc/#general",
  "created": 1760115600,
  "tags": [["reply", "4c07..."]],
  "content": "hello from the guest",
  "sig": "e2d0..."
}
```

`author` is an identity hash. `id` is the full hash of the canonical bytes --
every field except `id` and `sig`. `sig` is the author's signature over those
bytes **plus the id**. One registry maps a kind to a name and a delivery class.

## What it expects

An identity that can sign and whose hash is stable, and a canonicaliser with
exactly one implementation.

## Findings encoded here

- **An event carries its own signature as well as the message layer's**,
  because the message layer's covers a message from one sender to one
  recipient. An event forwarded by a third party, replayed out of
  store-and-forward, or carried across a federation boundary has to stay
  verifiable by its *author*. Adopting the layer's *fields* is not adopting
  its signature.
- **Canonicalisation has one implementation and nothing else may serialise an
  event for signing.** Sorted keys, no incidental whitespace, UTF-8, every
  signed field present even when empty. The failure mode is the quietest
  available: messages arrive, bytes look right, and the only symptom is that
  other instances' events never verify.
- **An unknown kind reads as `async` rather than being dropped.** A newer peer
  publishing a kind this build has never heard of should still have its event
  stored and passed on; the signature holds either way and a later build will
  know what it is.
- **Delivery follows the kind, not the caller.** `async` is handed to the
  message layer's delivery and store-and-forward; `live` goes to the
  recipient's own app logic, which holds it until its client is up; `ephemeral`
  is worth nothing once missed, so it is never stored and never retried.
- **A missing kind field reads as 1.** Two numbers in the registry (1 and 200)
  were inherited from an older protocol and kept rather than renumbered, which
  is why the registry has gaps.
- **Borrowed from one widely-copied event format, and only this:** the JSON
  shape, `kind`, `tags`, and a subscription as a filter. Not its relays, key
  encoding, curve or numbered extensions.

## Lifting it

Take §1 and §3 whole. The one thing to decide for yourself is the kind numbers;
the one thing not to change is the canonicaliser.
