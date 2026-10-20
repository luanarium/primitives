# `napster/messages/` -- typed messages

**Role.** One frozen dataclass per *(number, direction)*, with a `decode_client`
that never raises.

**In the primitive.** **Not lifted.** The primitive decodes inside each
handler with `split()` and keeps only `SharedFile` and `Hit` as types. This is
the biggest deliberate divergence in the bundle, and the reason is below.

## Why one class per *(number, direction)*

Never one struct with optional fields. Several numbers are used both ways with
different layouts -- 205, 320, 326, 613, 617, 821, 822, 824, 827, 830 -- and
modelling that as one shape loses the distinction the wire makes. A library
whose job is also to *document* the protocol wants that distinction in the
type system.

A tool that only serves does not: it reads the fields it needs in the handler
and is done. 511 lines of dataclasses buys documentation, not behaviour, which
is why the primitive spends it on docstrings instead.

## What is worth keeping either way

- **Every message carries `raw`**, the payload exactly as received, so a
  capture replays byte-exact and a parse failure loses nothing.
- **Decoding never raises.** An unparseable payload becomes `Malformed`,
  carrying the reason and the bytes; an un-modelled number becomes `Unknown`
  and is still a first-class message. A parse bug must not kill a connection,
  so the whole decoder sits inside one `try` that converts any exception into
  `Malformed`.
- **`payload()` defaults to replaying the original bytes**, which is what
  makes a decoded message safely re-encodable.

## Findings carried in the docstrings

- **920** is the first message a *returning* login sends, and such a login
  sends **no version check at all**; a first run sends 4 and no 920. A server
  must tolerate either opening.
- **4** is `"v2.0 BETA 9.4" 0` -- quoted, with a trailing numeric, where the
  spec gives a bare version. The client blocks forever if it goes unanswered.
- **2** was observed with **two** trailing numerics, not the spec's single
  optional one: `preserve sandbox1 0 "v2.0 BETA 9.4" 0 4853 0`. `4853` is
  plausibly the build number; the final `0` is unexplained.
- **6** carries the login fields plus `<email>` plus an undocumented trailing
  numeric.
- **15** is undocumented -- the spec jumps 14 → 100 -- and carries the same
  demographic data as 14 in a different encoding.
- **870**'s `<dir>` is a **synthetic token** (`"1:\1\"`), not a real path: the
  client never discloses its filesystem layout, and that token is what other
  users see in 201/212.
- **200**'s `max_results` is a hint; the live client sent 4,976,092.
- **201**'s `<ip>` is a little-endian uint32.
- **500** is reached only *after* a 204 whose `<port>` was 0 -- the client does
  not decide from the search result.
- **640** has two variants: a reachable browsee answers 641 within ~1 ms, a
  firewalled one gets the requester's `ip port` and **skips 641 entirely**.
- **703** is emitted the instant the port changes in Preferences, on the live
  connection with no reconnect, and 204 must advertise the new value at once.

## Lifting it
Lift the *list of findings*, not the 25 classes, unless the next tool is also
meant to document the protocol. If it is, lift the whole module: the shape is
right and the docstrings are the deliverable.
