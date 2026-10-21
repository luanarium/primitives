# modules

One brief per part of the surface, grouped by concern. Each says what it
provides, what it expects, **the findings encoded in it**, and what to do when
lifting it. The findings section is the body of each file and the reason it
exists: one bullet per non-obvious decision, each naming the failure that caused
it.

Read in this order if you are reading them all. Within a group, the earlier file
is the one the later ones depend on.

## The payload and what it rests on

| | |
|---|---|
| [events.md](events.md) | the signed JSON object everything moves, and why it signs itself when the message layer already signs |
| [identity.md](identity.md) | the two hashes that are not interchangeable, which is the subtlest bug in this layer |

## Keeping it

| | |
|---|---|
| [store.md](store.md) | append-only, and the `received` column that makes arrival order answerable |
| [bus.md](bus.md) | store first, bus second; bounded queues that count their drops |
| [gate.md](gate.md) | the one place the wire becomes the store, and the pen that holds an event whose author has not announced yet |

## Convergence

| | |
|---|---|
| [social.md](social.md) | posts, comments and reactions, resolved as a set question rather than by a clock |
| [versions.md](versions.md) | a per-author counter, for records that are replaced rather than added to |
| [annotations.md](annotations.md) | the two-part anchor and the four states of a reference |

## Content between instances

| | |
|---|---|
| [index.md](index.md) | the index replicates and the bytes do not; a version is announced, never a change |
| [fetch.md](fetch.md) | a key resolved through the index or refused, never a path |
| [catalog.md](catalog.md) | sharing large untrusted content: the ingestion gate, and why a grant never replicates |

## Chat and presence

| | |
|---|---|
| [rooms.md](rooms.md) | membership that converges in one round trip, replayed in arrival order |
| [chat-irc.md](chat-irc.md) | the adapter pattern, and a nick made from an identity rather than a claim |

## The web side

| | |
|---|---|
| [webapp.md](webapp.md) | serving the model as plain HTML, including to clients twenty years old |

## Getting events to everyone

| | |
|---|---|
| [gossip.md](gossip.md) | have, diff, get: ask rather than flood |
| [carriage.md](carriage.md) | events on messages, peers from announces, and the three threading rules that fail silently |

The designed-but-unbuilt half of dissemination has no module, because it has no
code. It is [../DISSEMINATION.md](../DISSEMINATION.md), and it is the part
closest to a networking project's own purpose.
