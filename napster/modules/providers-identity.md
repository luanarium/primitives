# `napster/providers/identity.py` -- accounts

**Role.** The default identity provider: an in-memory account store, with the
nick grammar.

**In the primitive.** `Backend.nick_status` / `authenticate` / `level_of`,
§7, with `NICK_RE` lifted whole.

## What it provides the client

- **8 / 9 / 10** out of `nick_status()` → `"free"` / `"taken"` / `"invalid"`,
  which is the registration flow probe (message 7) and the only thing the
  client needs before it sends a 6.
- **The email in the 3 login ack.** A dummy is fine and is what an
  unregistered account got.
- **The level that gates everything else**, including the 604 tail.

## Findings encoded here

- **`NICK_RE` is the real grammar**: `[A-Za-z0-9_[]{}\-@^!$]{1,32}`,
  case-insensitive. Napster, Inc. accepted only these. It matters beyond
  validation -- `@` and `!` are legal here and collide with IRC prefix and mask
  syntax, which is why a chat adapter has to normalise in both directions, and
  why `@` is available as the network separator inside a channel name.
- **`auto_register` on first login** is one of the three registration modes
  period servers had (`auto_register`, `registered_only`, open). It is the
  default because a preservation sandbox that refuses an unknown nick is a
  sandbox nobody can sign in to.
- **An empty stored password accepts anything.** That is deliberate for a
  sandbox and is the line to change first in anything else.
- **Nicks expired after 31 days** in the original (`nick_expire`), and
  moderator-and-above never expired. Not implemented; recorded because a
  long-lived deployment will eventually want it.

## Lifting it
Lift `NICK_RE` verbatim. The store itself is thirty lines and any real tool
will replace it.
