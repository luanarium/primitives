# `napster/socks.py` -- the proxy that routes by port

**Role.** The client's own proxy setting is the least invasive way to point it
at the sandbox, so running the proxy is part of the sandbox rather than part
of a capture harness.

**In the primitive.** Not lifted -- it is generic SOCKS. The **routing table**
is the Napster-specific part and is `BRIEF.md` §1.

## It routes by destination port and ignores the destination address

That is not a shortcut, it is the finding. The client resolves
`server.napster.com` itself and asked the proxy for **`127.12.34.56:8875`** --
an address that appears nowhere in the binary and resolves to nothing. The
port parsed as exactly 8875, so those are the bytes it sent.

**Routing by port means the client needs no working name resolution at all**,
which is what makes a hosts file, a resolver, a network namespace and root
unnecessary for pointing a client at the sandbox.

| Asked for | Goes to |
|---|---|
| 8875 | the metaserver -- first contact |
| 8888, 7777 | the protocol server |
| 80 | the web surface |
| anything else | a real connection, because it is a **peer transfer** and the address is another peer's -- the one address the client did not invent |

## The policy on that last row

A proxy that will connect anywhere on behalf of the client **is an egress
path**. `peers` decides:

- **`local`** (default) -- loopback and private ranges only. Enough for a
  prefix on this machine, a VM on a host network, and instances on a LAN,
  which are the three places a peer is ever going to be.
- **`any`** -- no restriction. For running a client against the real internet,
  which is not what this project is, but is the honest name for it.
- **`none`** -- refuse. Transfers then only work through the sandbox's own peer
  endpoint.

A hostname from a client that cannot resolve is **not** local, and is refused.

## Findings encoded here

- **SOCKS 4 and 5 both**, because the client's dialog offers both and either
  may be what a user picked. CONNECT only.
- **`ProxyTransfers` is independent of the control connection.** The capture
  that settled this had transfers explicitly set to *"Download files directly
  from source"*, so anything reaching the proxy could only be the control
  path -- and it was.
- **`kind(port)` is derived from the same ports `route()` uses**, so the
  capture's decoder choice and the log line cannot disagree with where the
  bytes actually went.
- **A capture tap must never cost the client its bytes.** The tap sees the
  bytes, never alters them, and a tap that raises is logged and swallowed: a
  capture is a diagnostic, and a failed one is a lost line, not a lost
  download.
- **Every byte the client sends passes through here**, which is why this is
  also where the transcript is taken.

## Lifting it
Lift the routing table and the peer policy. Any SOCKS implementation will do
for the rest.
