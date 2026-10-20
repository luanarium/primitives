# `napster/latency.py` -- deliberate slowness

**Role.** Everything runs on loopback, so the protocol completes **faster than
the client can draw it**. The dialogs flash past and the whole sequence is
over before you have read any of it. In 2001 the same exchange was a dial-up
round trip per stage, and the waiting was most of the experience.

**In the primitive.** Only `serve_get(bps=…)` -- the chunk-from-rate throttle.
The rest is `BRIEF.md` §6.

## The sign-in stages, in order

| Stage | Default | Why it is visible |
|---|---|---|
| `metaserver` | 1.6s | the client's very first connection; in the era a DNS lookup sat in front of it |
| `version_check` | 3.0s | the client is showing *"Checking Version…"* until the echo arrives -- the longest and most remembered wait |
| `login` | 2.5s | the server was looking you up |
| `motd_line` | 0.4s | so the lines arrive rather than appear |
| `stats` | 1.0s | the status bar filling in |

Measured in the client: **6.2s**, or 8.9s when the version check fires.

**Jitter matters more than the values.** A fixed delay reads as a progress
bar; real latency varied from one request to the next, and varying each wait
by up to 30% is what makes it feel like a network rather than a timer. The
numbers themselves are what 56k felt like, not a measurement -- nothing was
recorded at the time, and the point is how it *looks* rather than a claim
about the past.

## The two throughput tables, and why there are two

**Asymmetry is the whole reason.** A 56k modem took in about what it sent, but
cable and DSL did not: a 2001 cable line was perhaps 1.2 Mbps down against
192 kbps up, which is why **a cable user was a fast downloader and a mediocre
source**, and a T1 was 1.5 Mbps both ways, which is why campus users were
worth queueing for.

`LINK_UPSTREAM` is what a peer can *serve*; `LINK_DOWNSTREAM` is what this
client can *take in*. **Upstream is the number that mattered and the one
nobody quoted.**

## `LinkBudget` -- our end, shared

A 56k line carries 4.5 KB/s whether one file is arriving or four. The first
version gave each transfer the whole line, so three concurrent downloads
delivered 13.5 KB/s over a 4.5 KB/s link and **all three ran at the same speed
whoever they came from**, which is the opposite of what a slow line does to
you.

Shares are **max-min fair**, which is the mouthful for what a line actually
does: everyone gets an equal share, except that a peer who cannot use its
share does not get it, and what it cannot use goes to whoever can. So a T1
sharing a broadband line with a 56k modem keeps nearly all of it rather than
politely halving. An equal split would waste the difference and make every
concurrent download look the same speed again.

**Recomputed per chunk**, so starting another download slows the others and
finishing one speeds them up immediately -- the thing people watched the
progress bars for.

## Findings encoded here

- **`transfer_bps_for` is the slower of the two ends.** A T1 user feeding a
  modem is a modem transfer, and a modem user feeding a T1 is still a modem
  transfer. That is why the same file took wildly different times from
  different people, and why **the link column in a search result was the
  column people read**.
- **`downstream_for` reads the link type the *client declared at login*.** A
  client states its connection in the login message, out of the list in its
  own Preferences, so the authentic lever for "how fast is my line" is the
  client's own setting rather than a flag on the server. A client that says
  `Unknown` -- which this one does -- gets the profile's rate instead.
- **`chunk_for` sizes the chunk from the rate**, about four a second. A 64 kB
  chunk at modem speed is a fourteen-second silence followed by a burst, which
  is not what a slow transfer looked like.
- **`search_batches` returns uneven groups whose unevenness grows with the
  count.** Results did not arrive all at once and did not arrive evenly: the
  server answered from more than one place and each answer carried whatever it
  had. With a handful of files that is invisible, so a five-file answer comes
  in one or two steady groups and a ninety-file answer comes in lumps. **The
  sum of the rows is always the count** -- nothing is dropped to make the
  arithmetic work, and the reconciliation trims the tail rather than rescaling
  the unevenness away.
- **`ping` is a multiplier, not a replacement.** A fabricated user's round
  trip is a fact about *them* rather than a delay of the sandbox's, so
  `none` answers a ping instantly and `modem` answers it as that person's line
  would have.
- **`Latency.none()` is what tests and captures use.** A test that waits for
  the era is just a slow test.
- **A zero wait does not touch the event loop.** `pause()` returns without
  awaiting, so `none` is genuinely free.

## Lifting it
Lift the two tables, `transfer_bps_for`, `LinkBudget` and `chunk_for`. They
are the difference between a protocol exercise and the thing people remember,
and each one of them was a wrong-feeling transfer before it was written.
