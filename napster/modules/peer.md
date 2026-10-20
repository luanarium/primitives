# `napster/peer.py` -- the client-to-client wire

**Role.** `GET` / `SEND` / `GETLIST`, and a listener that answers them.
**File data never passes through the server**; it is a rendezvous broker only.

**In the primitive.** §9, with the `bps` throttle folded into `serve_get`.

## The three handshakes

Normal download -- the downloader dials the peer's data port:

```
peer  -> "1"                            one ASCII byte, on connect
dl    -> "GET"                          its own write
dl    -> <nick> "<file>" <offset>
peer  -> <size-digits><raw file bytes>  NO delimiter
```

Firewalled push -- after 500/501, the uploader dials the downloader:

```
dl    -> "1"
up    -> "SEND"
up    -> <nick> "<file>" <size>
dl    -> <offset>
up    -> <raw file bytes>
```

Direct browse -- after 640/641:

```
browsee -> "1";  browser -> "GETLIST"
browsee -> <nick>\n, then share lines LF-terminated, then a bare LF
```

A firewalled browsee pushes `SENDLIST <nick>\n` plus the same list instead,
and no 641 is exchanged at all.

## Findings encoded here

- **The size is undelimited, and does not terminate on 0xFF.** The spec says
  the byte after the digits is "usually `0xFF`", the MPEG frame sync. A live
  capture terminated on **`I` (0x49)**, the first letter of an `ID3` tag, on
  an entirely ordinary MP3. **Scan for the first non-digit, never for 0xFF.**
  This is the single most error-prone part of the protocol to reimplement.
- **Hand that byte back.** `read_size_prefix` returns `(size, first_byte)`
  because the non-digit that terminated the run is already part of the file;
  discarding it silently corrupts byte 0 of every transfer.
- **`nick` in a `GET` is the *downloader*.** The peer protocol has the asker
  name itself; the owner comes from the file. A port that reads it as the
  owner looks up the wrong share.
- **The verb and its arguments may arrive as separate writes**, so
  `read_request` reads a short head, matches the verb, and then reads more.
- **GETLIST lines carry the real `<md5>-<n>` checksum**, because this is
  client-to-client and no server is in the path to mangle it.
- **`PeerServer` exists for one case**: the "user" sharing a file is not a
  real client. A fabricated owner has no socket, so the 204 for one of their
  files names an address with nobody behind it and the download fails at the
  TCP level **with no protocol-visible error**. Disabled by default, because
  in an ordinary deployment real clients transfer to each other.
- **Not port 6699.** The client wants that one for its own uploads and drops
  into firewall mode if it cannot bind it. Use 6700.
- **`FILE NOT SHARED` and `INVALID REQUEST`** are the two refusals, sent as
  bare ASCII in place of the size.

## Lifting it
Copy it. Then run check 12 of `primitive/smoke_test.py`, which drives a real
`GET` end to end and asserts the digits terminated on `I` and the bytes match.
