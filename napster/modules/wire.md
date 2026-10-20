# `napster/wire.py` -- framing

**Role.** `<length:2><type:2><data:length>`, both header fields little-endian
uint16, `length` counting only `data`. No line terminator anywhere: nothing
ends in CRLF and `length` is authoritative.

**In the primitive.** §1, essentially verbatim. 109 lines → 70.

## What it provides
`Frame` (type + the bytes as received), `encode(type, data)`,
`FrameReader.feed()`, `iter_frames()` for replaying a capture, and
`MAX_COMMAND_LENGTH = 2048`.

## What the client expects
Nothing, directly -- but it **splits a message across packets**, and the peer
protocol in particular writes its parts as separate `send()` calls. An
implementation that assumes one read is one message loses frames at random
under load and never under test.

## Findings encoded here

- **`encode()` is latin-1 lossy, by design.** The protocol predates Unicode: a
  field is bytes, and a 2001 client received whatever its sharer's codepage
  produced, so a character with no latin-1 byte becomes `?` -- which is what
  such a client would have shown. This is not fussiness. A YouTube title
  containing `✨` and `🔥` raised `UnicodeEncodeError` out of a search, which
  killed the handler **before it could send the end-of-search message**, and
  the client sat at *Performing search…* for ever. Any provider can be handed
  text it did not choose, so the guard belongs here, once, rather than in each
  of them.
- **Decoding never raises on malformed input.** A frame whose type is unknown
  is still a frame and the caller decides. The original server's response to
  garbage is part of the preserved behaviour.
- **Every higher layer keeps a reference to the raw payload**, so a capture
  replays byte-exact and a parse failure never loses information.
- `.text` decodes latin-1, which never fails -- do not use `ascii` or `utf-8`
  on the receive side.

## Lifting it
Copy it. There is nothing project-specific in it. The only thing to resist is
"improving" the encode to raise on un-encodable text: that is finding one.
