# `napster/sources.py` -- where a served file's bytes come from

**Role.** A `FileSource` protocol -- `size()` and `read(offset)` -- with three
implementations. Making this an abstraction is what lets **proxied rendezvous
fall out of the same code path** instead of being a special case.

**In the primitive.** §9 carries `FileSource` and `LocalFile`; `Throttled`'s
behaviour is folded into `serve_get(bps=…)`; `RemotePeer` and `Generated` are
left out.

## The three sources

| | |
|---|---|
| `LocalFile` | a real file on disk |
| `RemotePeer` | **fetch from another peer and relay** -- the proxied rendezvous path. Works across NAT and between instances, costs bandwidth, and the client cannot tell: both ride the same two messages |
| `Generated` | synthesised bytes, for a sandbox that fabricates |

## `Throttled`, and why a transfer must be slow

A file the sandbox serves itself arrives at **memory speed**, which is the one
part of a transfer nobody in 2001 experienced: the progress bar was the event.

- **The rate is the slower of the two ends** -- the uploader's upstream and
  ours -- so the same file takes wildly different times from different people,
  which is what the link column in a search result was *for*.
- **Their ping sits in front of the first byte.** Half the round trip, because
  that is where it sat. A 540 ms modem user did not answer instantly and then
  crawl; they did both.
- **Our end is a shared budget**, one per downloader, so a 56k line carries
  4.5 KB/s whether one file is arriving or four. Recomputed **per chunk**, so
  starting another download slows this one and finishing one speeds the rest
  up -- the thing people watched the progress bars for.
- **A real transfer between two real clients is never throttled at all.** That
  is a real network and does not need help.

## Findings encoded here

- **`read()` yields rather than returning**, so a multi-megabyte file never
  sits in memory and the throttle has somewhere to sleep.
- **`_NoBudget` stands in when no shared budget was given**, so a source with
  no owner is governed by our end alone rather than by a `None` check in the
  hot loop.
- **`RemotePeer` performs the full peer handshake** -- wait for `1`, `GET`,
  read the undelimited size -- and **yields the first non-digit byte before
  anything else**, because it is byte 0 of the file.
- **`RemotePeer.size()` is only correct after `read()` has begun**, which is
  why the relay path fills it in from the upstream response rather than
  promising it up front.

## Lifting it
Copy `FileSource` and `LocalFile`. Lift `Throttled` if the tool wants the
pacing (it should -- see `latency.md`); lift `RemotePeer` if instances will ever
relay for each other.
