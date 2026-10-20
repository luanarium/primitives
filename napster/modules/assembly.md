# `napster/assembly.py` -- composing what no provider owns

**Role.** The payloads that are assembled from several providers at once, with
the level gating applied **here** so no provider can leak it.

**In the primitive.** §8, as `whois_payload`, `channel_user`, `server_stats`.
`whowas` and `channel_list_entry` were folded into their handlers.

## Why this module exists

It is the piece that makes providers genuinely swappable, and the easiest
thing to get wrong. **Whois (604) is assembled from four domains**: identity
(level, email), presence (status, channels, connected time), library (shared
count) and the registry (live transfer counters). Channel entries
(406/407/408/825) need chat for membership, library for `<files shared>` and
presence for `<link speed>`.

A provider supplies the fields it owns and returns `None` otherwise; the
sandbox substitutes the protocol's own unknowns -- `unavailable`, `0`,
`Inactive`. **Delegating identity to IRC must not break whois just because
IRC has no idea how many files anyone shares.**

## Findings encoded here

- **604's moderator-only tail is appended here.** `<total_dl> <total_ul> <ip>
  <connect_port> <data_port> <email>`, for `Level.MODERATOR` and above only.
  The client renders every field of it in a *"%s's Finger Information"* panel --
  `Number Shared:` `Ability:` `Channels:` `Connection:` `User Level:`
  `Data Port:` `Address:` `Client Version:` `User:` `Time Connected:`
  `Status:` -- so emitting it to a plain user leaks data that is then
  *displayed*. Confirmed against a live client: a `User`-level requester
  correctly sees the short form.
- **The channels field is space-padded**, `" #a #b "`, not bare. That is what
  the original sent.
- **406, 408 and 825 share one layout**: `<channel> <user> <shared>
  <link-type>`. 825 is byte-identical to 408 -- a duplicate code path in the
  original, reproduced rather than unified.
- **618 is free text to EOL** for the topic, so it is formatted rather than
  joined.
- **828 is the extended channel entry**, with the `n1` 0/1 field believed to
  mean predefined vs. user-created.

## Lifting it
Copy the functions. The rule is what matters: **a backend never formats a wire
message, and no backend method knows a whole message.** If a port lets a
provider return a formatted 604, the level gate is gone and nobody will notice
until it is in a screenshot.
