# `chat-irc` -- a channel is a topic, and a nick is made from an identity

**Role.** The adapter pattern: a client's own wire format in, signed events out,
and back again. Worked through with IRC because any IRC client works unmodified.

**In the primitive.** The topic mapping and the attribution rule are lifted, as
§12. The protocol server is not.

## What it provides

`channel_topic`, `channel_of`, `nick_for`, `say`, `backlog`.

## What it expects

A surface. Nothing about the surface knows a protocol exists.

## Findings encoded here

- **Adapters never talk to each other.** They publish to and subscribe from the
  bus, so adding a protocol changes none of the existing ones.
- **A nick for a remote speaker is derived from the author's identity, never
  from a claim.** Authority stays with the server: a local nick cannot be
  impersonated by a peer, because the name is made from the thing that signed
  the event rather than from anything the sender asserted.
- **Chat is a `live` kind, so a held event waits at the recipient's instance.**
  An event for a channel nobody here has joined is stored and nothing more, and
  **a client that joins later reads it out of the store** -- which is what makes
  late joining work without a replay channel.
- **A client is never echoed its own line**, and an instance never fans its own
  event back to itself.
- **Answer an unknown command rather than ignoring it, and answer a ping**, or
  clients time out and the failure looks like a network problem.
- **The honest limit: two chat adapters do not cross-talk.** They publish the
  same kind, so the wire format already matches, but each owns its own topic
  prefix -- so they are two rooms until something points one at the other's
  prefix. This is a convention gap, not a protocol one.
- **An adapter declares what only it can know**: whether its names can share
  one address, its own protocol check, and where its anchors resolve. All three
  are read off the running instance rather than guessed.

## Lifting it

Take the mapping and the attribution rule. The protocol server is yours, and
the pattern generalises: the same shape covers mail, OSCAR and a Mastodon API,
which are reserved kinds here and unwritten.
