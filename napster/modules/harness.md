# `nim/harness/` -- the capture apparatus

**Role.** How every observation in this bundle was produced. **Nothing here is
required to build anything** -- it is the apparatus that tells you what the
client actually does.

**In the primitive.** Not applicable. `capture.md` is the part that moved into
the library and should be built early.

## The shape

The client runs under Wine inside an **unprivileged network namespace**
(`unshare -Urnm`) with loopback only and a bind-mounted `/etc/hosts` pointing
the napster.com names at 127.0.0.1. Egress is denied and **verified from
inside**. The servers run *outside* and are bridged in.

```
                 sealed network namespace
   ┌───────────────────────────────────────────────┐
   │  napster.exe  ──SOCKS──►  napcapture.py :1080 │
   │       │                        │              │
   │       │ data port 6699         │ unix socket  │
   │       ▼                        ▼              │
   │  unixrelay.py ─────────┐   nap.sock ──────────┼──► unixrelay.py ──► opennap.exe
   └────────────────────────┼──────────────────────┘        (outside the namespace)
                            ▼
                      peer.sock  ──► leecher.py (outside)
```

**Unix sockets are filesystem objects, so they cross a network namespace.**
That is the whole trick, and it is the same shape that later carried the
exhibit server's egress: the filesystem is shared even though the network is
not.

## The files, and what each one is for

| | |
|---|---|
| `sealed5.sh` / `sealed8.sh` | runs inside `unshare`: loopback up, hosts bind-mount, **egress check**, relays, launch |
| `napcapture.py` | a SOCKS 4/5 proxy that answers 8875 itself, relays the rest, **decodes the framing live**, and injects the type-13 echo OpenNap omits |
| `unixrelay.py` / `tcp2unix.py` | bridge a unix socket to a TCP port. Used three times: server in, client data port out, web in |
| `leecher.py` | a second, scripted Napster client: logs in, searches, sends 203, then performs the peer `GET` against the real client |
| `drive.py` | drives the Wine GUI over XTEST. **The client has no scripting surface**, so the wizard is clicked through from coordinates read off a screenshot |
| `walkpack.py` | walks a page in a live client and records every asset it pulled, with digests |
| `exhibit.py` | serves port 80 inside the namespace |
| `run-museum.sh` | the whole thing, as one command |

## Findings encoded here

- **OpenNap 0.44 cannot log this client in unaided**, because it never sends
  the type-13 echo. The capture proxy injects it. That is how the echo was
  discovered to be mandatory in the first place.
- **The capture proxy answers 8875 itself**, which means the sandbox's own
  metaserver never sees first contact -- so the proxy has to reproduce the
  pause too, and the runner asks the tool for the value rather than keeping a
  second copy of the number.
- **Kill `wineserver` before entering the namespace**, or the inner Wine
  attaches to the existing one over `/tmp` and its processes run in the
  **outer** network namespace. Every assertion then passes and means nothing.
- **`opennap.exe` fails to `bind` inside a user namespace** (`Not owner`),
  hence the unix bridge.
- **Delete `dosdevices/z:`** or the client's "search my disks" walks the
  entire host filesystem through Wine's `Z: → /` mapping.
- **The run directory must be short.** A unix socket path is capped near 108
  characters and a nested scratch path silently exceeds it.
- **Wine takes 1–3 minutes to bind** a server; wait for the port rather than
  assuming.
- **A scripted second client is worth building.** Half the transfer findings --
  the push path, the spurious 220/221, the `I`-terminated size prefix -- needed
  two endpoints, and the second one has to be scriptable.

## Lifting it
Lift the unix-socket-across-a-namespace trick and the egress assertion. And
lift the principle: **the client has no scripting surface, so the only way to
learn what it does is to drive the GUI and decode the wire.** Budget for that
rather than for reading a spec.
