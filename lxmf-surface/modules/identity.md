# `identity` -- two hashes that are not interchangeable

**Role.** An author's keypair, the hash peers know it by, and the signing and
hashing the event shape rests on.

**In the primitive.** Lifted, as §2, with a clearly-labelled stand-in signer so
the file runs with no dependencies.

## What it provides

A persistent identity, its 32-hex identity hash, signing, verification, and the
content hash used for event ids.

## What it expects

To be persisted. Nothing else.

## Findings encoded here

- **A peer's delivery destination hash and its identity hash are different
  values, and conflating them is the subtlest bug in this layer.** A message is
  addressed to the first. An event's `author` is the second, and so is what a
  signature is checked against. `recall` is keyed by the *destination* hash, so
  the verifying key an author needs comes from the announce that carried the
  identity and never from a recall on the author field. Get this wrong and
  messages arrive and cannot be verified, which reads as a signing bug and is
  not one.
- **An announce is the only source of an author's verifying key**, which is why
  the gate keeps a map of them. See [gate.md](gate.md).
- **Persist the key or peers lose you.** A new identity at every start means a
  new destination hash: peers cannot find you and stored path tables go stale.
- **An identity encrypts to another identity**, which is the primitive for
  group keys. Distributing them is not solved; see
  [../DISSEMINATION.md](../DISSEMINATION.md) §4.

## Lifting it

Replace the class body with your stack's identity and keep the interface:
`hash`, `sign`, `validate`, `full_hash`, `public`. The stand-in signer is for
tests only and says so at the class.
