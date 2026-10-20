# `napster/chat/__init__.py` + `internal.py` -- the chat seam

**Role.** The default chat target: everything stays in the sandbox. Usable with
no external chat system anywhere, which is why it is the default.

**In the primitive.** `Backend.on_join` / `on_part` / `on_public` /
`on_emote` / `on_private`, §7. The server's own channel state is §11.

## Why the boundary is a domain interface, not an IRC bridge

So that another target -- Matrix, XMPP, a timeline, a mailing list -- is an
*adapter* rather than a rewrite. And whatever the target, **the sandbox stays
authoritative for channel state**: a target is a transport and an optional
mirror, never the source of truth.

The reason is concrete. 408/409 and 618/828 are lists the client *must*
receive, and if the far side owns membership then those lists depend on
whether the far side happens to have a concept of it. An ActivityPub timeline
has none. So where a target lacks a concept, the sandbox **synthesises** it
from its own state rather than degrading the protocol.

## `capabilities`

A frozenset declaring what the far side can actually do: `membership`,
`presence`, `topic`, `invites`, `moderation`, `per_user_identity`, `push`.
`InternalChat` declares all seven, because it *is* the sandbox. A
capability-poor target declares less and the sandbox fills the gaps.

## Findings encoded here

- **`irc.py` is deliberately not imported from the package `__init__`.** It
  needs the `[irc]` extra, and the library must stay usable with no chat
  system anywhere. Selection happens by entry-point name instead.
- **`on_private` returns False** in the internal target: nothing beyond the
  sandbox knows the nick, so the server answers `User <nick> is not currently
  online.`
- **`InternalChat` still implements `bind_chat`**, keeping the bridge, so a
  deployment can drive the sandbox's chat directly -- useful for tests and for
  a backend that wants to inject chat without writing an adapter.

## Lifting it
The whole value is the rule: **authority stays with the server**. The module
itself is 31 lines of no-ops.
