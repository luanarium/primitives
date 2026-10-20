# The portable primitive

`primitive/napster_primitive.py` is the whole protocol substrate in one
stdlib-only file. `primitive/smoke_test.py` is thirteen conformance checks
against it. Nothing else in this project imports either of them, and nothing
in this project was rewritten to use them: the primitive is an emitted
artifact for the next tool to vendor, and the library it was condensed from
stays as it is.

```python
from napster_primitive import Backend, serve

serve(Backend())        # a real client logs in, joins channels, finds nothing
```

```python
class Shelf(Backend):
    def search(self, *, terms, requester, max_results):
        return [Hit(filename=r"C:\mp3\track.mp3", checksum="...-3994",
                    size=4014, bitrate=192, frequency=44100, seconds=12,
                    nick="albear69", ip=ip_to_wire("127.0.0.1"), link_type=4)]
    def resolve(self, *, requester, nick, filename):
        return (ip_to_wire("127.0.0.1"), 6700, "...-3994", 4)
    def source_for(self, filename):
        return LocalFile("/srv/music/track.mp3")

serve(Shelf())          # and the client downloads it, for real
```

---

## What is in it

Twelve sections, in dependency order, each one self-contained enough to lift
on its own:

| § | Holds | Why it is in the primitive |
|---|---|---|
| 1 | framing: `Frame`, `encode`, `FrameReader` | nothing works without it, and the lossy latin-1 guard belongs here once rather than in every caller |
| 2 | field grammar: `split`, `join`, `quoted`, `Final`, `as_int` | lenient-by-position, because the protocol has no escape and the original's tolerance is preserved behaviour |
| 3 | `M` -- every message number, named, including the refusal-only ones | the single most valuable table in the project, and it is pure data |
| 4 | `Checksum`, `checksum_of`, `checksum_matches`, `id3v2_length` | the `<md5>-<bytes>` convention, and the OpenNap resume bug it avoids |
| 5 | `ip_to_wire` / `wire_to_ip` | two lines, and getting the endianness wrong sends the client somewhere real that is not you |
| 6 | `Level`, `SharedFile`, `Hit`, `Session`, `Channel`, `Registry` | the minimum state the protocol assumes, and the by-nick registry whois forces |
| 7 | `Backend` -- the seam, every method defaulted | one object instead of nine Protocols; the docstrings are the contract |
| 8 | `whois_payload`, `channel_user`, `server_stats` | the payloads no single backend method owns, with the level gate applied here so a backend cannot leak it |
| 9 | `FileSource`, `LocalFile`, the peer wire, `PeerServer` | the transfer path, including the undelimited size prefix and the throttle |
| 10 | `Metaserver` | first contact, and one line of protocol |
| 11 | `Server`, `Connection`, the handler table | dispatch, the pre-login echo, framework-owned terminators, push routing |
| 12 | `serve` / `serve_async` | the three listeners, and a backend shutdown that fires through cancellation |

Dependencies: none. Python ≥3.10 (it uses `slots=True` dataclasses and
`X | None` annotations). Stdlib only: `asyncio`, `hashlib`, `re`, `socket`,
`struct`, `dataclasses`, `enum`, `pathlib`.

---

## What was deliberately left out

The primitive is the substrate. Everything the source project has around it is
a separable concern with its own micro brief in `modules/`, and each one is
left out for a reason rather than for size:

| Left out | Why, and where it is written up |
|---|---|
| **Nine provider domains** resolved through entry points | right shape for a plugin ecosystem, overkill for one tool. The `Backend` method names are deliberately the same, so a provider lifts across mechanically. `modules/providers.md` |
| **The web / exhibit surface** | it is HTTP, not Napster, and it is a third of the project. `pages/README.md`, `modules/web.md`, `modules/docs.md` |
| **The IRC adapter and the chat bridge** | the bridge *interface* is summarised in `BRIEF.md` §8; the adapter is 900 lines of IRC client. `modules/chat-*.md` |
| **The latency model** | `BRIEF.md` §6 is the design; `serve_get(bps=…)` in the primitive is the one hook that matters for transfers. `modules/latency.md` |
| **Personas, the collection indexer, the transcoder** | they implement `Backend`, they do not extend the protocol. `modules/personas.md`, `modules/providers-collection.md`, `modules/transcode.md` |
| **The SOCKS proxy and the capture transcript** | both are generic network plumbing with Napster-specific *routing*; the routing table is `BRIEF.md` §1. `modules/socks.md`, `modules/capture.md` |
| **Registry seeding, the mode packages, the CLIs** | deployment, not protocol. `modules/clientconfig.md`, `modules/modes.md` |
| **Typed message classes** | the primitive decodes inside each handler with `split` instead. One class per *(number, direction)* is the right model for a library whose job is also to *document*; a tool that only serves does not need 25 dataclasses. `modules/messages.md` |
| **Server links / federation** | designed around rather than implemented, in both. The `origin` field on `Session` is the part that must exist from the start. |

The one thing in the primitive that is **not** in the library's protocol core
is the `bps` throttle on `serve_get`, folded in from the `Throttled` source
wrapper because a transfer at memory speed is the single most obviously wrong
thing a port gets for free.

---

## The conformance checks

`python3 primitive/smoke_test.py`. Thirteen, each one a behaviour a real
client depends on and each one read out of a capture rather than out of
`napster.txt`. Every check prints what it saw, so the output doubles as a
transcript of what a first session looks like on the wire.

```
ok  metaserver speaks first: 127.0.0.1:18888
ok  echo for 4 only: 4: "v2.0 BETA 9.4" 0
ok  login: [(3, 'anon@napster.com'), (621, 'Welcome to the sandbox.'), (214, '1 0 0')]
ok  search row: "C:\My Documents\My Music\track.mp3" eb93…-3994 4014 192 44100 12 albear69 16777343 4
ok  terminator survives a raising backend, then the 404: server error handling that request
ok  browse: albear69 0
ok  join: [405, 408, 409, 410, 404] | Server sandbox set you as operator on channel #Lobby
ok  whois short form: ['preserve', 'User', '0', ' #Lobby ', 'Active', '0', '0', '0', '0', 'v2.0 BETA 9.4']
ok  204 ack: albear69 16777343 6700 "C:\…\track.mp3" eb93…-3994 4
ok  pong for a socketless user
ok  unknown number: Unknown command code 999
ok  peer GET: size prefix 4014, terminated on b'I', bytes match
ok  un-encodable text survives: "? fire ?.mp3" x-1 1 1 1 1 nick 0 0

all 13 checks passed
```

What each one pins:

1. **The metaserver speaks first and hangs up.** First contact is 8875.
2. **Only message 4 is echoed.** 920 arrives first and gets nothing; 4 gets a
   type-13 echo of its own payload. Echo both and the client refuses the
   login.
3. **Login is 3, then 621 per MOTD line, then 214** -- and the login line
   carries two trailing numerics the spec does not describe.
4. **A 201 row**, with the filename quoted and `16777343` as loopback: the
   little-endian address. Also that `MAX_RESULTS 4976092` is clamped rather
   than believed.
5. **The terminator outlives a raising backend.** 202 goes out first, *then*
   the 404 notice: the client is released, and only then told something went
   wrong. This is check 5 because it is the failure mode that hangs the real
   client and leaves no trace.
6. **Browse terminates**, carrying the browsee's address -- zero here, because
   a fabricated owner has no session.
7. **The join sequence in order**: 405 ack, 408 per member, 409 terminator,
   410 topic, and a 404 *notice* granting operator to the first member. 404 is
   not only errors.
8. **Whois as a plain user is the short form** -- ten fields, no
   moderator-only tail. The level gate is in the composer, where a backend
   cannot reach it.
9. **A 204 ack naming our own peer endpoint on 6700**, not 6699, with the
   filename quoted.
10. **A ping to a socketless user is answered for them**, after their line's
    round trip. The client pings before it downloads.
11. **An unknown number is refused, not dropped**:
    `Unknown command code 999`.
12. **The peer wire end to end** -- `1`, `GET`, the undelimited size, then the
    bytes, with the digits **terminated by `I`** (the first letter of `ID3`)
    rather than 0xFF, and the recovered bytes matching the file exactly. This
    is the capture finding of `BRIEF.md` §2.5 reproduced live.
13. **Un-encodable text survives.** An emoji in a filename becomes `?` and the
    search still sends its terminator, rather than raising out of the handler
    that owed the client one.

A port that passes all thirteen will log a real Napster 2.0 BETA 9 client in,
serve it search results, let it browse, and hand it bytes.

---

## Porting notes

- **Keep the terminator in a `finally`.** Not after the loop. A backend can
  raise when it is called, while its rows are being iterated, or not at all;
  the first version of this guard built the rows above the `try` and lost the
  terminator to a generator that raised half way through, which is the same
  hang in a different place.
- **Keep the lossy encode at the framing layer.** Pushing it out to callers
  means every future backend has to remember it, and the one that forgets
  hangs the client.
- **Keep `quoted()` distinct from `join()`'s automatic quoting.** They are
  different decisions: a nick is quoted only if it needs it, a filename is
  quoted always. The `Final` wrapper exists so the decision travels with the
  value instead of being re-derived at the join site.
- **Keep the registry addressable by nick, and keep `origin` on the session.**
  A backend that can only answer the request it was handed cannot drive 406 to
  other members, 607 to an uploader, 209/210 to hotlists or 627/628
  broadcasts. And addressing by `(nick, origin)` from the start is what stops
  server links and chat bridges being a retrofit later.
- **A handler that raises must not drop the client.** The original server kept
  talking; log the exception, send a 404, carry on.
- **`backend.stop()` must fire through cancellation as well as a clean exit.**
  It matters for anything holding a connection to someone else's server: a
  chat adapter that is killed leaves a ghost sitting in a real channel until
  the far side times it out, and the people in that channel are the ones who
  see it. Three seconds, failures logged rather than raised -- this runs while
  the process is already going away, and a provider that cannot shut down
  cleanly must not stop the next one from trying.
