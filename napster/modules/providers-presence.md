# `napster/providers/presence.py` -- who is online

**Role.** The default presence provider: read straight off the session
registry. Twenty lines, and the shortest module in the project.

**In the primitive.** Folded away entirely: the primitive reads the registry
in `whois_payload` and has no presence seam.

## Why it exists at all

Because presence is a domain someone will want to delegate -- to a directory,
to a chat network, to a shared index across instances -- and the seam has to
exist before that is possible. The default is the degenerate case.

## The finding that constrains every replacement

**Presence is always a *merge*, never a replacement.** The 218–221 transfer
counters and the data port come from the Napster connection itself and can
only live in the sandbox's registry. So a delegated presence provider
contributes `status_of()` -- `Active` / `Inactive` / `Remote`, which is the 604
field -- and **nothing else**. A provider that tried to own presence outright
would have to invent the counters, and whois would start lying.

`on_signon` / `on_signoff` are notifications, not authority: they exist so a
provider can mirror the event somewhere, and the sandbox has already updated
its own registry before calling them.

## Lifting it
Nothing to lift. Keep the constraint.
