# `napster/providers/__init__.py` -- the capability domains

**Role.** One `typing.Protocol` per capability domain, each with an in-process
default. Every seam optional.

**In the primitive.** Collapsed into one `Backend` class, §7, with the **same
method names** so a provider lifts across mechanically.

## The nine domains

`identity`, `presence`, `chat`, `library`, `rendezvous`, `policy`, `web`,
`mail`, `federation`. `serve(Deployment())` is a working, empty server; a
deployment replaces only the domains it cares about.

## The two rules that make them swappable

1. **Providers never format a wire message.** They return values; the sandbox
   composes, gates by level and emits. A provider must not be *able* to leak
   the moderator-only tail of 604 to a plain user.
2. **No provider knows a whole message.** Whois is assembled from identity,
   presence, library and rendezvous. See `assembly.md`.

Break either and the gate is gone, or the domains stop being independent.

## Findings encoded in the Protocols

- **`Hit.ip` and `.port` are explicit, not substituted from the socket.** A
  real server fills them from the session registry; a sandbox fills them with
  whatever its local peer endpoint is, because its owners have no sockets. One
  type serves both.
- **`Rendezvous.proxied`** distinguishes handing over the real peer address
  (204/501 as the protocol intends) from handing over *our* endpoint and
  fetching from the real source behind it. The client cannot tell: both ride
  the same two messages.
- **`Library.search` must exclude the requester's own files.** A real server
  does, and a sandbox that attributes fabricated results to the logged-in user
  shows them **nothing**.
- **`Library.replace_shares` is a replace, never an append**, because a login
  replays the whole library.
- **`Presence` is always a merge, never a replacement.** The 218–221 counters
  and the data port come from the Napster connection itself and can only live
  in the sandbox's registry, so a delegated presence provider contributes
  status and nothing else.
- **`ChatTarget` is a transport and optional mirror, never the source of
  truth** -- otherwise the lists the client *must* receive (408/409, 618/828)
  would depend on whether the target happens to have a concept of membership.
  Its `capabilities` frozenset says what the far side can actually do, and
  where it lacks a concept the sandbox **synthesises** from its own state
  rather than degrading the protocol.
- **`ChatTarget.bind_chat` is what makes an adapter bidirectional.** Without
  it an adapter is outbound-only: it can push Napster chat into IRC but
  nothing can come back, which is half a bridge.
- **`ChatTarget.on_private` returns a bool.** True means "I delivered it";
  only if nobody claims it is it an error to the sender.
- **`Policy.level_required` is the one place level gating is declared**, so
  every deployment enforces the same thing.
- **`@runtime_checkable`** on each one, so a test can assert an adapter
  actually satisfies the shape.

## Lifting it
If the next tool wants a plugin ecosystem, lift the nine Protocols and the
entry-point groups. If it is one tool, lift the `Backend` class from the
primitive instead -- but keep the method names either way, because that is what
makes the eight provider implementations in this project portable.
