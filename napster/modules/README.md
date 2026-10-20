# Micro briefs, one per module

Each file: what the module provides the client, what the client expects back,
the findings encoded in it, and whether the portable primitive lifted it.
Together they are a module-by-module route from this project's source into
another tool's.

Read `../BRIEF.md` first. These go deeper than it does and assume it.

## The protocol substrate -- all of it in the primitive

| | |
|---|---|
| [`wire.md`](wire.md) | framing, and the lossy encode that stops a search hanging the client |
| [`tokens.md`](tokens.md) | the field grammar, and why a filename is always quoted |
| [`numerics.md`](numerics.md) | the number space, the terminator table, the refusal-only set |
| [`hashing.md`](hashing.md) | `<md5>-<bytes>`, and the OpenNap resume bug |
| [`state.md`](state.md) | sessions, channels, and the by-nick registry whois forces |
| [`assembly.md`](assembly.md) | the payloads no provider owns, and where the 604 level gate lives |
| [`server.md`](server.md) | the pre-login echo, framework-owned terminators, push routing |
| [`peer.md`](peer.md) | `GET`/`SEND`/`GETLIST`, and the undelimited size prefix |
| [`metaserver.md`](metaserver.md) | first contact: one line, server speaks first |
| [`sources.md`](sources.md) | where bytes come from, and why a transfer must be slow |
| [`deployment.md`](deployment.md) | composition, entry points, and shutting a provider down |
| [`messages.md`](messages.md) | typed messages -- the biggest deliberate divergence in the bundle |

## The backend seam

| | |
|---|---|
| [`providers.md`](providers.md) | the nine capability domains, and the two rules that make them swappable |
| [`providers-identity.md`](providers-identity.md) | accounts, and the real nick grammar |
| [`providers-presence.md`](providers-presence.md) | twenty lines, one constraint |
| [`providers-policy.md`](providers-policy.md) | MOTD, caps, and the level table |
| [`providers-rendezvous.md`](providers-rendezvous.md) | 203 → 204, and the little-endian address |
| [`providers-library.md`](providers-library.md) | search, browse, resume, and period tokenisation |
| [`providers-collection.md`](providers-collection.md) | a real directory as a fabricated network |
| [`experiments-youtube.md`](experiments-youtube.md) | what a remote-backed library provider has to do |

## Chat

| | |
|---|---|
| [`chat.md`](chat.md) | the seam, and why authority stays with the server |
| [`chat-bridge.md`](chat-bridge.md) | the inbound half: remote members, forced joins, lossy points |
| [`chat-networks.md`](chat-networks.md) | the address grammar, because `/join` is the only way in |
| [`chat-greeting.md`](chat-greeting.md) | the only user interface the chat side has |
| [`chat-console.md`](chat-console.md) | a channel you type commands into |
| [`chat-irc.md`](chat-irc.md) | the worked example, and its connection model |

## The surfaces the protocol does not carry

| | |
|---|---|
| [`web.md`](web.md) | per-host mounts, redirect aliases, archive forwarding |
| [`docs.md`](docs.md) | two of the client's three tabs, rendered from source |
| [`exhibits.md`](exhibits.md) | the packs, and manifests instead of copies |
| [`communities.md`](communities.md) | the operator's links, and a UCI-style CLI |
| [`personas.md`](personas.md) | invented users, and the seventeen that are not |
| [`latency.md`](latency.md) | the pacing, and the two throughput tables |
| [`transcode.md`](transcode.md) | formats the client cannot play |

## Deployment and diagnostics

| | |
|---|---|
| [`socks.md`](socks.md) | the proxy that routes by port and ignores the address |
| [`capture.md`](capture.md) | the decoded transcript every finding came out of |
| [`clientconfig.md`](clientconfig.md) | the registry seed, and the desktop seal |
| [`modes.md`](modes.md) | how a client is attached, and what confines it |
| [`cli.md`](cli.md) | three entry points, and four habits worth keeping |
| [`harness.md`](harness.md) | how the observations were produced |
| [`vmlan.md`](vmlan.md) | the networking half, already separate -- and see [`../NETWORK.md`](../NETWORK.md) for the design in full |
