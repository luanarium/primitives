"""Conformance checks for napster_primitive: run it, do not read it.

Thirteen checks, each one a behaviour the original Napster 2.0 BETA 9.4 client
depends on and each one read out of a capture rather than out of napster.txt.
If a port of this primitive passes all thirteen, a real client will log in to
it, search it, browse it and download from it.

    python3 smoke_test.py

Every check prints what it saw, so the output doubles as a transcript of what
a first session looks like on the wire.
"""
import asyncio, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import napster_primitive as np

class Shelf(np.Backend):
    def __init__(self, path):
        self.path = path
        self.file = np.SharedFile(
            filename=r"C:\My Documents\My Music\track.mp3",
            checksum=str(np.checksum_of(path)),
            size=os.path.getsize(path), bitrate=192, frequency=44100, seconds=12)
    def search(self, *, terms, requester, max_results):
        if not terms or any(t.lower() in self.file.filename.lower() for t in terms):
            return [np.Hit(self.file.filename, self.file.checksum, self.file.size,
                           self.file.bitrate, self.file.frequency, self.file.seconds,
                           nick="albear69", ip=np.ip_to_wire("127.0.0.1"), link_type=4)]
        return []
    def browse(self, nick):
        return [self.file] if nick == "albear69" else []
    def resolve(self, *, requester, nick, filename):
        if filename == self.file.filename:
            return (np.ip_to_wire("127.0.0.1"), 6700, self.file.checksum, 4)
        return None
    def source_for(self, filename):
        return np.LocalFile(self.path) if filename == self.file.filename else None
    def ping_ms(self, nick):
        return 1 if nick == "albear69" else None

async def frames(reader, n, timeout=3.0):
    out, fr = [], np.FrameReader()
    deadline = asyncio.get_event_loop().time() + timeout
    while len(out) < n and asyncio.get_event_loop().time() < deadline:
        data = await asyncio.wait_for(reader.read(4096), timeout=1.0)
        if not data: break
        out += list(fr.feed(data))
    return out

async def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    mp3 = tmp / "track.mp3"
    mp3.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x0a" + b"\xff\xfb\x90\x00" + os.urandom(4000))
    backend = Shelf(mp3)
    server = np.Server(backend)
    asyncio.create_task(server.serve("127.0.0.1", 18888))
    asyncio.create_task(np.Metaserver(("127.0.0.1:18888",)).serve("127.0.0.1", 18875))
    asyncio.create_task(np.PeerServer(backend, nick="sandbox").serve("127.0.0.1", 16700))
    await asyncio.sleep(0.3)

    # 1. first contact: the metaserver speaks first and hangs up
    r, w = await asyncio.open_connection("127.0.0.1", 18875)
    line = (await r.read(100)).decode()
    assert line == "127.0.0.1:18888\n", line
    w.close()
    print("ok  metaserver speaks first:", line.strip())

    # 2. the version check must be echoed as 13, and 920 must not be
    r, w = await asyncio.open_connection("127.0.0.1", 18888)
    w.write(np.encode(np.M.PRE_LOGIN, "1"))
    w.write(np.encode(np.M.VERSION_CHECK, '"v2.0 BETA 9.4" 0'))
    got = await frames(r, 1)
    assert [f.type for f in got] == [13], [f.type for f in got]
    assert got[0].text == '4: "v2.0 BETA 9.4" 0', got[0].text
    print("ok  echo for 4 only:", got[0].text)

    # 3. login -> 3 ack, 621 motd, 214 stats
    w.write(np.encode(np.M.LOGIN, 'preserve pw 0 "v2.0 BETA 9.4" 0 4853 0'))
    got = await frames(r, 3)
    assert [f.type for f in got] == [3, 621, 214], [f.type for f in got]
    print("ok  login:", [(f.type, f.text) for f in got])

    # 4. undocumented 15 is accepted and discarded, silently
    w.write(np.encode(np.M.DEMOGRAPHICS, '"ZIP" "" "CTY" "United States"'))
    # 5. search -> 201 then the owed 202
    w.write(np.encode(np.M.SEARCH, 'FILENAME CONTAINS "track" MAX_RESULTS 4976092'))
    got = await frames(r, 2)
    assert [f.type for f in got] == [201, 202], [f.type for f in got]
    row = np.split(got[0].text)
    assert row[0] == r"C:\My Documents\My Music\track.mp3", row
    assert int(row[7]) == 16777343, row[7]
    print("ok  search row:", got[0].text)

    # 6. a backend that raises still gets its terminator out
    class Broken(np.Backend):
        def search(self, **kw): raise RuntimeError("boom")
    broken = np.Server(Broken())
    asyncio.create_task(broken.serve("127.0.0.1", 18889))
    await asyncio.sleep(0.2)
    r2, w2 = await asyncio.open_connection("127.0.0.1", 18889)
    w2.write(np.encode(np.M.VERSION_CHECK, '"v" 0')); await frames(r2, 1)
    w2.write(np.encode(np.M.LOGIN, 'x p 0 "v" 0')); await frames(r2, 3)
    w2.write(np.encode(np.M.SEARCH, 'FILENAME CONTAINS "x"'))
    got = await frames(r2, 2)
    # the terminator first, then the 404 notice: the client is released, and
    # only then told something went wrong.
    assert [f.type for f in got] == [202, 404], [f.type for f in got]
    print("ok  terminator survives a raising backend, then the 404:", got[1].text)
    w2.close()

    # 7. browse
    w.write(np.encode(np.M.BROWSE, "albear69"))
    got = await frames(r, 2)
    assert [f.type for f in got] == [212, 213], [f.type for f in got]
    print("ok  browse:", got[1].text)

    # 8. whois as a plain user gets the short form only
    w.write(np.encode(np.M.JOIN, "#Lobby"))
    got = await frames(r, 5)
    assert [f.type for f in got] == [405, 408, 409, 410, 404], [f.type for f in got]
    print("ok  join:", [f.type for f in got], "|", got[4].text)
    w.write(np.encode(np.M.WHOIS, "preserve"))
    got = await frames(r, 1)
    fields = np.split(got[0].text)
    assert got[0].type == 604 and len(fields) == 10, fields
    print("ok  whois short form:", fields)

    # 9. 203 -> 204 names our own peer endpoint, port non-zero
    w.write(np.encode(np.M.DOWNLOAD_REQUEST,
                      np.join("albear69", np.quoted(backend.file.filename))))
    got = await frames(r, 1)
    ack = np.split(got[0].text)
    assert got[0].type == 204 and int(ack[2]) == 6700, ack
    print("ok  204 ack:", got[0].text)

    # 10. a ping to a fabricated user is answered for them
    w.write(np.encode(np.M.PING_USER, "albear69"))
    got = await frames(r, 1)
    assert [f.type for f in got] == [752], [f.type for f in got]
    print("ok  pong for a socketless user")

    # 11. an unknown number is refused, not dropped
    w.write(np.encode(999, "nonsense"))
    got = await frames(r, 1)
    assert got[0].type == 404 and "999" in got[0].text, got[0].text
    print("ok  unknown number:", got[0].text)

    # 12. the peer wire: "1", GET, undelimited size, then the bytes
    pr, pw = await asyncio.open_connection("127.0.0.1", 16700)
    assert await pr.readexactly(1) == b"1"
    pw.write(b"GET"); await pw.drain()
    pw.write(np.join("preserve", backend.file.filename, 0).encode("latin1"))
    await pw.drain()
    size, first = await np.read_size_prefix(pr)
    body = first + await pr.read(size)
    while len(body) < size:
        more = await pr.read(size - len(body))
        if not more: break
        body += more
    assert size == backend.file.size, (size, backend.file.size)
    assert body == mp3.read_bytes(), (len(body), backend.file.size)
    print(f"ok  peer GET: size prefix {size}, terminated on {first!r}, bytes match")
    pw.close()

    # 13. the text guard: an emoji in a filename must not kill the handler
    class Emoji(np.Backend):
        def search(self, **kw):
            return [np.Hit("\u2728 fire \U0001f525.mp3", "x-1", 1, 1, 1, 1,
                           "nick", 0)]
    emo = np.Server(Emoji())
    asyncio.create_task(emo.serve("127.0.0.1", 18890))
    await asyncio.sleep(0.2)
    r3, w3 = await asyncio.open_connection("127.0.0.1", 18890)
    w3.write(np.encode(np.M.VERSION_CHECK, '"v" 0')); await frames(r3, 1)
    w3.write(np.encode(np.M.LOGIN, 'x p 0 "v" 0')); await frames(r3, 3)
    w3.write(np.encode(np.M.SEARCH, 'FILENAME CONTAINS "fire"'))
    got = await frames(r3, 2)
    assert [f.type for f in got] == [201, 202], [f.type for f in got]
    print("ok  un-encodable text survives:", got[0].text)
    w3.close(); w.close()

    print("\nall 13 checks passed")

asyncio.run(main())
