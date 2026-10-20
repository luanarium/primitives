# `napster/capture.py` -- the decoded transcript

**Role.** **Every finding in this bundle was read out of a file like this
one.** The 11-second gap between 203 and 204, the emoji that lost a 202, the
transfer that finished 13,684 bytes short, the login line that declares link
type 0. None of them were visible in a stack trace or at a log level, and all
of them were obvious in a decoded transcript.

**In the primitive.** Not lifted. It is the one piece of diagnostic
infrastructure worth building second, after the protocol works.

## What a line looks like

```
20:14:03.118 [c1] === CONNECT 127.12.34.56:8875 -> metaserver ===
20:14:03.822 [c1] S>C  metaserver   '127.0.0.1:8888\n'
20:14:04.090 [c2] === CONNECT 208.49.228.8:8888 -> protocol ===
20:14:04.091 [c2] C>S  920  pre login              1
20:14:04.092 [c2] S>C  13   echo                   920: 1
20:14:04.210 [c2] C>S  2    login                  preserve pw 0 "v2.0 BETA 9.4" 0
20:14:09.400 [c3] === CONNECT 127.0.0.1:6700 -> peer ===
20:14:09.401 [c3] C>P  PEER 41 bytes |GET.preserve "C:\...\song.mp3" 0|
```

## Findings encoded here

- **Decode the protocol frames; do not decode the file bytes.** A transfer is
  megabytes of MP3 and the interesting part is the handshake in front of it,
  so a peer connection logs its first 400 bytes and then says it is streaming.
  A capture of a long session with downloads in it stays **kilobytes, not
  megabytes**.
- **Three taps, chosen by what the connection carries.** `protocol` gets
  framed decoding; `peer`/`data` gets the handshake and nothing of the file;
  everything else is logged as text, which is what the metaserver's one line
  and an HTTP request are.
- **For HTTP, only the request side is written out in full**; the response
  gets its first line, which is the status. A page body is of no interest and
  is large.
- **Tag per connection** (`[c1]`, `[c2]`), so two sessions can be told apart
  in one file.
- **Line-buffered and appended**, so a transcript of a session that ended in a
  crash is still complete up to the crash -- which is the case it exists for.
- **Off unless asked for.** A transcript holds the nick, **the password**,
  every search term and every filename. `--capture FILE` is the whole
  interface, the tool says so before it starts recording, and the operator is
  told to read the file before sending it on.
- **The body limit is 1200 characters per line.** A 201 row is short; a browse
  response or a long MOTD is not, and a transcript has to stay readable.
- **It lives in the library rather than the harness**, because the harness is
  the one piece not being published -- and a released mode with no way to
  produce this artefact has no way to produce a problem report either.

## Lifting it
Lift it early. The alternative to a decoded transcript is guessing, and every
hour spent guessing at this protocol is an hour this project already spent.
