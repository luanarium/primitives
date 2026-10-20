# `napster/providers/rendezvous.py` -- where a downloader goes

**Role.** Turning a 203 into a 204: the address, port, checksum and link speed
the client should dial. Plus the two-line endianness fix everything depends
on.

**In the primitive.** `Backend.resolve()` returns the same four values, §7;
`ip_to_wire`/`wire_to_ip` are §5.

## `ip_to_wire`, and why it is here

**The protocol's `<ip>` is a little-endian uint32 of the dotted quad.**
127.0.0.1 is **16777343**, not 2130706433. Getting it backwards sends the
client to an address that exists and is not yours -- which presents as a
transfer that fails on connect, with nothing wrong in the log.

## The two providers

**`DirectRendezvous`** hands over the peer's real address, as the protocol
intends. Two findings:

- **The port is read live, not from login.** 703 takes effect immediately on
  the existing connection with no reconnect, and 204 must advertise the
  current value.
- **A peer that is not online is a 206 get-error**, not silence.

**`SandboxRendezvous`** is the sandbox case: **a fabricated user has no
socket**, so the 204 for one of their files cannot carry their address because
there is nobody there. It carries *ours*, and the peer server answers the
`GET` from the real file behind the fiction. The client cannot tell.

And the part that keeps it honest: **anything the library cannot serve falls
through to the wrapped provider**, so a transfer between two real clients is
still brokered the way the protocol intends and never passes through here.

## Findings encoded here

- **The client tries 203 first and only falls back to 500** after reading
  `<port>` 0 out of the ack. It does not decide from the search result's
  address, so this round trip cannot be short-circuited for a firewalled peer.
- **`proxied` is recorded on the result** even though the client cannot see
  it, because the *operator* can: a proxied transfer costs the sandbox
  bandwidth and a direct one does not.
- **`bind()` forwards to the fallback**, so wrapping a provider does not
  disconnect it from the registry.

## Lifting it
Lift `ip_to_wire`/`wire_to_ip` verbatim. Lift the wrap-rather-than-replace
shape if the tool will ever have both fabricated and real peers at once --
which it will, the moment two instances find each other.
