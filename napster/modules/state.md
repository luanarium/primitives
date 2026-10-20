# `napster/state.py` -- the state model and the registry

**Role.** Accounts, sessions, channels, and the **nick-addressable** session
registry.

**In the primitive.** §6, with `Account` and `World` folded away: the
primitive's `Server` holds the channel dict directly and a `Session` carries
its own email.

## What it provides
`Level`, `LinkType`, `Account`, `Session`, `Channel`, `Registry`, `World`.

## Why the registry is queryable by nick

Not private to a socket, and **whois alone forces it**: 604 reports another
session's live transfer counters, which exist only because of that session's
218–221 pairs. Without a shared registry the protocol cannot be served at all.

It is also the **router**. A provider that can only answer the request it was
handed cannot drive 406 to other members, 607 to an uploader, 209/210 to
hotlists, or 627/628 broadcasts. Everything that pushes goes through here:
`visible()`, `watching(nick)`, `in_channel()`, `at_least(level)`, `totals()`.

## Findings encoded here

- **A duplicate nick is an eviction, not a notification.** `add()` returns the
  session being evicted. Period servers send the incumbent
  `404 You were killed by server <alias>: Someone else is logging in as you,
  disconnecting.` and drop it, and **never send the 748** the spec describes.
- **The transfer counters are advisory.** In the push path the *downloader*
  also emits a 220/221 pair it has no business sending -- it appears to count
  any inbound connection on its own data port as an upload. `adjust()` clamps
  at zero, and nothing should treat them as truth.
- **`origin` exists from the start**, carrying `"client"` or the name of
  whatever adapter introduced the session. Addressing by `(nick, origin)` is
  what stops server links and chat bridges being a retrofit later.
- **`remote=True` with `send=None`** is a user who exists only on a chat
  target's far side: visible in rosters and whois, addressable by private
  message, with no socket.
- **`data_port == 0` means firewalled**, and that is the login message's own
  encoding -- every transfer to that user must be pushed.
- **`Level` names are what 604 puts on the wire** (`User`, `Moderator`,
  `Admin`, `Elite`), with `Leech` below. `Level.parse` defaults to `USER`
  rather than raising on an unknown string.
- **`totals()` is message 214**: `(users, files, gigabytes)`, pushed
  unsolicited on the stat interval and rendered in the client's status bar.
  Static numbers are the clearest tell that nothing is real.

## Lifting it
Copy `Session`, `Channel` and `Registry`. `Account`/`World` are worth keeping
only if the tool has its own account store; the primitive pushes
authentication out to one backend method instead and is no worse for it.
