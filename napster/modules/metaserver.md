# `napster/metaserver.py` -- first contact

**Role.** Port 8875. **The entire protocol is one line, and the server speaks
first.**

**In the primitive.** §10, verbatim minus the latency hook.

```
client connects to :8875
server -> "127.0.0.1:8888\n"
server closes
```

The client sends **nothing**. No framing, no handshake, no request. It is
repeatable: each new connection gets a line.

## Why it matters more than its size

**A live Napster 2.0 BETA 9.4 opens its very first control connection here,
not to 8888**, and re-dials it for every subsequent connection. A sandbox
listening only on 8888 will never see the client at all -- which presents as
"the client does nothing", with no error anywhere.

The format is **not documented in `napster.txt`**. It was recovered by probing
`metaserver.exe` directly (`usage: metaserver [ -fsv ] [ -c CONFIG ] [ -l IP ]
[ -p <port> ] [ host:port … ]`, default port 8875, default target
`127.0.0.1:8888`, logging `Redirecting %s to %s`) and then confirmed by
driving the official client against an emulation of it: the client parsed the
line and immediately opened a Napster session to the address given.

It is also reachable from the protocol side: message **822 (cycle client)**
forces a client to restart login *via the metaserver*, so the client must have
working metaserver support for that message to mean anything. The string
`(REDIRECTING)` in the binary confirms a visible redirect state.

## Findings encoded here

- **Targets cycle.** `itertools.cycle`, so several addresses load-balance the
  way the original's `host:port …` argv list did.
- **A pause belongs in front of the answer.** This is the client's first
  connection of all, and in the era a DNS lookup sat in front of it.
- **Through a port-routing proxy the advertised target is cosmetic**, because
  the proxy ignores the address. For a client reaching the sandbox by address
  it has to be true.

## Lifting it
Twenty lines. The only thing to get wrong is forgetting it exists.
