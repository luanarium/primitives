# `napster/deployment.py` -- wiring

**Role.** The `Deployment` dataclass, entry-point resolution, and
`serve_async` -- which brings up the protocol server, the metaserver, an
optional SOCKS proxy and an optional peer server together.

**In the primitive.** §12 keeps `serve`/`serve_async` and the three listeners;
the nine-domain dataclass and the entry-point machinery are replaced by one
`Backend` object. See `providers.md`.

## The composition model

A **frozen dataclass with every field defaulted**, so `serve(Deployment())` is
a working empty server and a deployment replaces only what it cares about.
Nine domains: `identity`, `presence`, `chat`, `library`, `rendezvous`,
`policy`, `web`, `mail`, `federation`, plus `latency` and
`metaserver_targets`.

**No DI container, no plugin framework, no message bus** -- `typing.Protocol`,
a dataclass, `importlib.metadata` and asyncio. Providers are discovered per
domain (`napster.identity`, `napster.library`, …) so an installed provider is
selectable **by name** with no import paths, and a package that wants to set
several domains at once registers a *bundle* under `napster.backends`.
Per-domain choices override a bundle.

## Findings encoded here

- **`_bind()` hands providers the session registry.** This is what lets a
  provider *push* rather than only answer: 406 to other members, 607 to an
  uploader, 209/210 to hotlists. A provider that can only return rows for the
  request it was handed cannot drive the protocol.
- **The metaserver is on by default**, because it is first contact.
- **The peer server is conditional on the library being able to hand over
  bytes** (`source_for`), because that is the only case where it is needed.
- **`peer_ip` is the address as the *client* must reach it** -- loopback for a
  prefix on this machine, the host's address on the VM network for a guest --
  and it is pushed into the library too, so the address in the search rows and
  the address in the download ack are the same one.
- **One link budget per downloader**, keyed on the nick, rebuilt when the
  rate changes. Its rate comes from the link type the client **declared at
  login**, so the client's own Preferences decide how fast its line is.
- **The default rendezvous is wrapped, not replaced.** `SandboxRendezvous`
  goes in front of `DirectRendezvous` only when the deployment did not choose
  its own -- a deployment that chose one meant it.
- **`_shutdown()` gives each provider three seconds and logs its failures
  rather than raising.** It runs while the process is already going away, and
  a provider that cannot shut down cleanly must not stop the next one from
  trying. It fires through cancellation as well as a clean exit, because a
  chat adapter that is killed leaves a ghost sitting in a real IRC channel
  until the ircd times it out -- and the people in that channel are the ones
  who see it.

## Lifting it
Lift `serve_async`'s shape: gather the listeners, and shut the backend down in
a `finally`. Lift the nine-domain dataclass only if the tool wants a plugin
ecosystem; the method *names* are what makes a provider portable either way.
