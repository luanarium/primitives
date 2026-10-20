"""napster_primitive -- the Napster client/server protocol in one file.

A portable condensation of the `napster-sandbox` library (nim). Everything
here is stdlib-only, asyncio, no package layout and no entry points, so it can
be vendored into another networking tool as a single module.

    from napster_primitive import Backend, serve
    serve(Backend())            # a working, empty server a real client logs in to

What this is
------------
The *substrate*: framing, field grammar, the message number space, the
checksum convention, the session registry, the dispatch core, the peer wire
and the metaserver. It is enough to log an original Napster 2.0 BETA 9 client
in, answer everything it can send with something structurally valid, serve it
search results and hand over real bytes.

What this is not
----------------
The nine-domain provider surface, the web/exhibit surface, the IRC adapter,
the latency model, the persona generator, the transcoder, the SOCKS proxy and
the capture transcript are all *deliberately absent*. They are separable
concerns with their own briefs in this bundle; the shape of the seam they plug
into is the `Backend` class below, which is one object with defaulted methods
rather than nine Protocols.

The five rules this file exists to enforce
------------------------------------------
1. **Answer message 4 with a type-13 echo, and echo nothing else pre-login.**
   Without the echo the client hangs at "Checking Version..." forever. Echo
   the 920 opener instead and it refuses the login outright.
2. **The framework owns every list terminator**, emitted in a `finally`. A
   backend must not be *able* to hang the client by raising half way through
   a result set.
3. **Decoding never raises.** An unknown number is still a message; a
   malformed payload keeps its bytes. The original server's response to
   garbage is preserved behaviour.
4. **Text is encoded latin-1 lossy.** One un-encodable character in a
   filename otherwise kills the handler that owed the client a terminator.
5. **Filenames are always quoted on the wire**, whether they need it or not.
   A bare filename in a 204 gets "User %s is not properly configured".

Every OBSERVED note is from a capture against a live Napster 2.0 BETA 9.4.
Section numbers in comments refer to nim's BRIEF.md.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import re
import socket
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, Iterable, Iterator

__all__ = ["M", "Frame", "FrameReader", "encode", "split", "join", "quoted",
           "Checksum", "checksum_of", "checksum_matches", "ip_to_wire",
           "wire_to_ip", "SharedFile", "Hit", "Level", "Session", "Registry",
           "Channel", "Backend", "Server", "LocalFile", "Metaserver",
           "PeerServer", "serve", "serve_async"]

log = logging.getLogger("napster")


# ==========================================================================
# 1. Framing -- <length:2><type:2><data>, little-endian, no terminator
# ==========================================================================

HEADER = struct.Struct("<HH")
HEADER_SIZE = HEADER.size

#: Most period servers refused a command longer than this (max_command_length).
#: It is why the batch share (870) exists and why it still has to be chunked.
MAX_COMMAND_LENGTH = 2048


@dataclass(frozen=True, slots=True)
class Frame:
    """One wire message, still undecoded. `data` is the bytes as received."""

    type: int
    data: bytes

    def encode(self) -> bytes:
        if len(self.data) > 0xFFFF:
            raise ValueError(f"message {self.type} payload exceeds 65535 bytes")
        return HEADER.pack(len(self.data), self.type) + self.data

    @property
    def text(self) -> str:
        """The protocol is plain ASCII; latin-1 never fails on decode."""
        return self.data.decode("latin1")


def encode(type_: int, data: str | bytes = b"") -> bytes:
    """Encode one message. Strings go out latin-1, **lossily**.

    The protocol predates Unicode: a field is bytes, and a period client saw
    whatever its sharer's codepage produced. A character with no latin-1 byte
    becomes `?`, which is what such a client would have shown.

    This is not fussiness. A YouTube title with an emoji in it raised
    UnicodeEncodeError out of a search, which killed the handler before it
    could send the end-of-search message, and the client sat at "Performing
    search..." for ever. A backend can be handed text it did not choose, so
    the guard belongs here, once.
    """
    if isinstance(data, str):
        data = data.encode("latin1", "replace")
    return Frame(type_, data).encode()


class FrameReader:
    """Incremental framer: feed bytes, get whole frames out.

    TCP gives no message boundaries and the client cheerfully splits a message
    across packets -- the peer protocol in particular writes its parts
    separately. Buffer until `length` is satisfied; `length` is authoritative.
    """

    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> Iterator[Frame]:
        self._buf += data
        while len(self._buf) >= HEADER_SIZE:
            length, type_ = HEADER.unpack_from(self._buf, 0)
            end = HEADER_SIZE + length
            if len(self._buf) < end:
                return
            payload = bytes(self._buf[HEADER_SIZE:end])
            del self._buf[:end]
            yield Frame(type_, payload)


# ==========================================================================
# 2. Field grammar -- space separated, quoted, and quotes are NOT escaped
# ==========================================================================

class Final(str):
    """A field already in the exact form it goes out in; never re-quoted."""


def quoted(value: object) -> Final:
    """A field the protocol **always** quotes, needed or not.

    A filename is written "<file>" everywhere the spec shows it, and period
    servers sent the quotes even with no space in the name. The client's
    parser relies on it: a 204 whose filename arrived bare was answered with
    *"User %s is not properly configured. Try again in a few minutes."* and a
    Transfer Error. Quoting only what "needs" it is right for a nick and
    wrong for a filename.
    """
    return Final(f'"{value}"')


def _needs_quotes(value: str) -> bool:
    return value == "" or " " in value or '"' in value


def split(payload: str, limit: int | None = None) -> list[str]:
    """Split a payload into fields, leniently by position.

    A quoted field keeps its interior spaces and loses its quotes. An
    unbalanced quote runs to end-of-payload rather than raising -- `shlex` is
    close but wrong, because the protocol has no escape and the original
    server's garbage-in tolerance is itself preserved behaviour. `limit` stops
    splitting and returns the remainder whole, which is the shape every
    message with a trailing free-text field wants.
    """
    fields: list[str] = []
    i, n = 0, len(payload)
    while i < n:
        while i < n and payload[i] == " ":
            i += 1
        if i >= n:
            break
        if limit is not None and len(fields) == limit:
            fields.append(payload[i:])
            return fields
        if payload[i] == '"':
            i += 1
            start = i
            while i < n and payload[i] != '"':
                i += 1
            fields.append(payload[start:i])
            i += 1                      # consume the closing quote if any
        else:
            start = i
            while i < n and payload[i] != " ":
                i += 1
            fields.append(payload[start:i])
    return fields


def join(*fields: object) -> str:
    """Build a payload, quoting only what must be quoted. None is dropped."""
    out: list[str] = []
    for f in fields:
        if f is None:
            continue
        if isinstance(f, Final):        # before the str check: it is one
            out.append(str(f))
        elif isinstance(f, str):
            out.append(f'"{f}"' if _needs_quotes(f) else f)
        else:
            out.append(str(f))
    return " ".join(out)


def as_int(fields: list[str], index: int, default: int = 0) -> int:
    """Read a numeric field defensively.

    Live clients send nonsense here: an observed search carried
    `MAX_RESULTS 4976092`. Never size an allocation from a wire integer.
    """
    try:
        return int(fields[index])
    except (IndexError, ValueError):
        return default


# ==========================================================================
# 3. The message number space
# ==========================================================================

class M(IntEnum):
    """Every message number, named. OBSERVED = seen on the wire."""

    # session / handshake
    ERROR = 0
    LOGIN = 2                      # OBSERVED
    LOGIN_ACK = 3                  # OBSERVED
    VERSION_CHECK = 4              # OBSERVED -- must be echoed with 13
    AUTO_UPGRADE = 5               # remote code execution by design; never send
    NEW_USER_LOGIN = 6             # OBSERVED
    NICK_CHECK = 7                 # OBSERVED
    NICK_NOT_REGISTERED = 8        # OBSERVED
    NICK_ALREADY_REGISTERED = 9
    NICK_INVALID = 10
    UNKNOWN_11 = 11
    UNKNOWN_12 = 12
    ECHO = 13                      # OBSERVED -- mandatory, for 4 and only 4
    LOGIN_OPTIONS = 14
    DEMOGRAPHICS = 15              # OBSERVED, undocumented in napster.txt
    # shared library
    SHARE_FILE = 100
    REMOVE_FILE = 102
    UNSHARE_ALL = 110
    SHARE_DIRECTORY = 870          # OBSERVED
    # search
    SEARCH = 200                   # OBSERVED
    SEARCH_RESULT = 201            # OBSERVED
    SEARCH_END = 202               # OBSERVED
    RESUME_REQUEST = 215
    RESUME_RESULT = 216
    RESUME_END = 217               # OBSERVED
    # transfers
    DOWNLOAD_REQUEST = 203         # OBSERVED
    DOWNLOAD_ACK = 204             # OBSERVED
    PRIVATE_MESSAGE = 205
    GET_ERROR = 206
    DOWNLOADING = 218              # OBSERVED
    DOWNLOAD_COMPLETE = 219        # OBSERVED
    UPLOADING = 220                # OBSERVED
    UPLOAD_COMPLETE = 221          # OBSERVED
    ALT_DOWNLOAD_REQUEST = 500     # OBSERVED (firewalled push)
    ALT_DOWNLOAD_ACK = 501         # OBSERVED
    UPLOAD_REQUEST = 607           # OBSERVED
    ACCEPT_UPLOAD = 608            # OBSERVED
    ACCEPT_FAILED = 609
    QUEUE_LIMIT_CLIENT = 619
    QUEUE_LIMIT_SERVER = 620
    DATA_PORT_ERROR = 626
    OPTIONAL_PORTS = 300
    CHANGE_DATA_PORT = 703         # OBSERVED
    SET_DATA_PORT = 613
    # browse
    BROWSE = 211
    BROWSE_RESULT = 212            # OBSERVED
    BROWSE_END = 213               # OBSERVED
    DIRECT_BROWSE = 640            # OBSERVED (both variants)
    DIRECT_BROWSE_ACCEPT = 641     # OBSERVED
    DIRECT_BROWSE_ERROR = 642
    # hotlist / ignore / presence
    HOTLIST_ADD = 207
    HOTLIST = 208
    USER_SIGNON = 209
    USER_SIGNOFF = 210
    HOTLIST_ACK = 301
    HOTLIST_ERROR = 302
    HOTLIST_REMOVE = 303
    IGNORE_LIST = 320
    IGNORE_ENTRY = 321
    IGNORE_ADD = 322
    IGNORE_REMOVE = 323
    NOT_IGNORED = 324
    ALREADY_IGNORED = 325
    IGNORE_CLEAR = 326
    LINKSPEED_REQUEST = 600        # OBSERVED
    LINKSPEED = 601                # OBSERVED
    WHOIS = 603                    # OBSERVED
    WHOIS_RESPONSE = 604           # OBSERVED
    WHOWAS = 605
    PING_USER = 751                # OBSERVED
    PONG = 752                     # OBSERVED
    # chat
    JOIN = 400                     # OBSERVED
    PART = 401
    PUBLIC_MESSAGE_OUT = 402       # OBSERVED
    PUBLIC_MESSAGE = 403           # OBSERVED
    ERROR_MESSAGE = 404            # OBSERVED -- also carries notices
    JOIN_ACK = 405                 # OBSERVED
    JOIN_MESSAGE = 406
    PART_MESSAGE = 407
    CHANNEL_USER = 408             # OBSERVED
    USER_LIST_END = 409            # OBSERVED
    TOPIC = 410                    # OBSERVED
    CHANNEL_BAN_LIST = 420
    CHANNEL_BAN_ENTRY = 421
    CHANNEL_BAN = 422
    CHANNEL_UNBAN = 423
    CHANNEL_BAN_CLEAR = 424
    CHANNEL_MOTD = 425
    INVITE = 430
    INVITE_ACCEPT = 431
    INVITE_DECLINE = 432
    LIST_CHANNELS = 617            # OBSERVED -- request and terminator share it
    CHANNEL_ENTRY = 618
    CLEAR_CHANNEL = 820
    SET_CHANNEL_LEVEL = 823
    EMOTE = 824                    # OBSERVED
    USER_LIST_ENTRY = 825
    CHANNEL_LIMIT = 826
    SHOW_ALL_CHANNELS = 827
    CHANNEL_LIST = 828
    KICK = 829
    LIST_USERS = 830
    GLOBAL_USER_LIST = 831
    # server info / moderation
    SERVER_STATS = 214             # OBSERVED
    MOTD = 621                     # OBSERVED
    SERVER_VERSION = 801
    CHANGE_USER_LEVEL = 606
    KILL = 610
    NUKE = 611
    BAN = 612
    UNBAN = 614
    SHOW_BANS = 615
    BAN_ENTRY = 616
    MUZZLE = 622
    UNMUZZLE = 623
    UNNUKE = 624
    CHANGE_LINKSPEED_USER = 625
    OPERATOR_MESSAGE = 627
    GLOBAL_MESSAGE = 628
    BANNED_USERS = 629
    CLOAK = 652
    CHANGE_LINKSPEED = 700
    CHANGE_PASSWORD = 701
    CHANGE_EMAIL = 702
    LOGIN_ATTEMPT = 748            # never sent in practice: servers evict
    SERVER_PING = 750
    CHANGE_PASSWORD_OTHER = 753
    RELOAD_CONFIG = 800
    SET_CONFIG = 810
    REDIRECT = 821
    CYCLE = 822
    BLOCKED_IP_LIST = 330
    BLOCK_IP = 332
    UNBLOCK_IP = 333
    # diagnostics -- a server-directed port scanner. Off by default.
    CONNECTION_TEST = 900
    LISTEN_TEST = 901
    # unknown / refusal-only: preserving the refusal IS the implementation
    UNKNOWN_310 = 310
    DISCONNECTING = 316
    UNKNOWN_602 = 602
    UNKNOWN_650 = 650
    UNKNOWN_651 = 651
    UNKNOWN_770 = 770
    UNKNOWN_771 = 771
    UNKNOWN_805 = 805
    UNKNOWN_811 = 811
    PRE_LOGIN = 920                # OBSERVED: body "1", returning logins


NAMES: dict[int, str] = {int(m): m.name.lower().replace("_", " ") for m in M}

#: Numbers answered with a refusal rather than an implementation.
REFUSAL_ONLY = frozenset({M.UNKNOWN_11, M.UNKNOWN_650, M.UNKNOWN_651,
                          M.UNKNOWN_770, M.UNKNOWN_771, M.UNKNOWN_805,
                          M.UNKNOWN_811, M.GLOBAL_USER_LIST})

#: Request -> the terminator the framework owes the client. A missing one
#: hangs the original client, which is the commonest way to break it.
TERMINATORS: dict[int, int] = {
    M.SEARCH: M.SEARCH_END,
    M.BROWSE: M.BROWSE_END,
    M.RESUME_REQUEST: M.RESUME_END,
    M.LIST_CHANNELS: M.LIST_CHANNELS,
    M.SHOW_ALL_CHANNELS: M.SHOW_ALL_CHANNELS,
    M.LIST_USERS: M.LIST_USERS,
}

#: Messages echoed back as type 13 before login. **Only message 4.**
#: napster.txt says "echo any pre-login command" and is wrong both ways:
#: 4 unanswered hangs the client forever, and echoing 920 makes it refuse the
#: login with `Login failed (Unexpected command: 13 [920: 1])`.
ECHO_PRE_LOGIN = frozenset({M.VERSION_CHECK})


def name_of(number: int) -> str:
    return NAMES.get(number, "?")


# ==========================================================================
# 4. The checksum -- <md5>-<bytes-hashed>, kept verbatim
# ==========================================================================

#: What napster.txt describes for the official Windows client.
SPEC_PREFIX_BYTES = 299_008
#: What the linux `nap` client 0.7-0.9 hashed -- incompatible, and a known
#: source of failed resumes between client families.
NAP_PREFIX_BYTES = 300_000
#: `.wma` files send this literal instead of a hash.
WMA_SENTINEL = "WMA-FILE"

_CHECKSUM_RE = re.compile(r"^(?P<md5>[0-9a-fA-F]{32})(?:-(?P<length>\d+))?$")


@dataclass(frozen=True, slots=True)
class Checksum:
    """A parsed checksum field. `raw` is always what came off the wire.

    BETA 9.4 sends `<md5>-<bytes-hashed>`, not the bare MD5 over a 299,008
    byte prefix that the spec describes. **Store it verbatim.** OpenNap 0.44
    cannot parse the hyphenated form, writes a zero hash instead, and silently
    kills resume -- the one bug most worth not reproducing.
    """

    raw: str
    md5: str | None = None
    hashed_bytes: int | None = None

    @property
    def is_wma_sentinel(self) -> bool:
        return self.raw.upper() == WMA_SENTINEL

    def __str__(self) -> str:
        return self.raw


def parse_checksum(field: str) -> Checksum:
    """Parse without ever rejecting: anything unrecognised is kept whole."""
    field = field.strip()
    if field.upper() == WMA_SENTINEL:
        return Checksum(raw=field)
    m = _CHECKSUM_RE.match(field)
    if not m:
        return Checksum(raw=field)
    length = m.group("length")
    return Checksum(raw=field, md5=m.group("md5").lower(),
                    hashed_bytes=int(length) if length is not None else None)


def id3v2_length(head: bytes) -> int:
    """Size of a leading ID3v2 tag, or 0. The client skips it before hashing."""
    if len(head) < 10 or head[:3] != b"ID3":
        return 0
    size = 0
    for b in head[6:10]:
        if b & 0x80:
            return 0                    # not syncsafe: refuse to guess
        size = (size << 7) | b
    return size + 10


def checksum_of(path: str | Path, *, prefix_bytes: int | None = None) -> Checksum:
    """Compute `<md5>-<bytes>` the way the client does.

    Skip a leading ID3v2 tag, then hash up to `prefix_bytes` -- by default the
    rest of the file, which is what BETA 9.4 was observed doing on files well
    over the spec's 299,008. Two independent installs produced a byte-identical
    value for the same file, so it is deterministic and usable for resume
    matching.
    """
    path = Path(path)
    with path.open("rb") as fh:
        offset = id3v2_length(fh.read(10))
        fh.seek(offset)
        digest = hashlib.md5()
        hashed = 0
        while True:
            want = 65536 if prefix_bytes is None else min(65536, prefix_bytes - hashed)
            if want <= 0:
                break
            chunk = fh.read(want)
            if not chunk:
                break
            digest.update(chunk)
            hashed += len(chunk)
    return Checksum(raw=f"{digest.hexdigest()}-{hashed}",
                    md5=digest.hexdigest(), hashed_bytes=hashed)


def checksum_matches(a: str, b: str) -> bool:
    """Would these two fields identify the same file? Used for 215/216."""
    pa, pb = parse_checksum(a), parse_checksum(b)
    if pa.md5 and pb.md5:
        if pa.hashed_bytes is not None and pb.hashed_bytes is not None:
            return pa.md5 == pb.md5 and pa.hashed_bytes == pb.hashed_bytes
        return pa.md5 == pb.md5
    return pa.raw == pb.raw


# ==========================================================================
# 5. Addresses -- the wire's uint32 is LITTLE endian
# ==========================================================================

def ip_to_wire(dotted: str) -> int:
    """Dotted quad -> the integer the protocol uses.

    127.0.0.1 is **16777343** on the wire, not 2130706433. Getting this
    backwards sends the client to an address that exists and is not yours.
    """
    return int.from_bytes(socket.inet_aton(dotted), "little")


def wire_to_ip(value: int) -> str:
    return socket.inet_ntoa(int(value).to_bytes(4, "little"))


# ==========================================================================
# 6. State -- the minimum a server must remember
# ==========================================================================

class Level(IntEnum):
    """User levels. The names are what 604 puts on the wire."""

    LEECH = 0
    USER = 1
    MODERATOR = 2
    ADMIN = 3
    ELITE = 4

    @property
    def wire(self) -> str:
        return self.name.capitalize()


#: link_type 0..10 as the client's Preferences list them.
LINK_TYPES = ("unknown", "14.4", "28.8", "33.6", "56.7", "isdn64", "isdn128",
              "cable", "dsl", "t1", "t3+")

#: Napster, Inc. accepted only these in a nick (case-insensitive).
NICK_RE = re.compile(r"^[A-Za-z0-9_\[\]{}\-@^!$]{1,32}$")


@dataclass(frozen=True, slots=True)
class SharedFile:
    """One file tuple, as it appears in 100 and repeats inside 870."""

    filename: str
    checksum: str          # verbatim: may be "<md5>-<n>" or "WMA-FILE"
    size: int
    bitrate: int
    frequency: int
    seconds: int


@dataclass(frozen=True, slots=True)
class Hit:
    """One search result before it becomes a 201.

    `ip` and `port` are **explicit**, never substituted from a socket: a real
    server fills them from the registry, a sandbox fills them with its own
    peer endpoint because its owners have no sockets. One type serves both.
    """

    filename: str
    checksum: str
    size: int
    bitrate: int
    frequency: int
    seconds: int
    nick: str
    ip: int
    link_type: int = 0
    weight: int | None = None


@dataclass(slots=True)
class Session:
    """One live client connection.

    The transfer counters are **advisory**. In the push path the *downloader*
    also emits a 220/221 pair it has no business sending -- it appears to
    count any inbound connection on its own data port as an upload. Never let
    them go negative and never treat them as truth.
    """

    nick: str
    ip: str = "127.0.0.1"
    data_port: int = 0              # 0 means firewalled: push only
    link_type: int = 0
    client: str = ""
    email: str = "anon@napster.com"
    level: Level = Level.USER
    connected_at: float = field(default_factory=time.monotonic)
    channels: set = field(default_factory=set)
    shared: dict = field(default_factory=dict)
    hotlist: set = field(default_factory=set)
    downloads: int = 0
    uploads: int = 0
    cloaked: bool = False
    muzzled: bool = False
    authenticated: bool = False
    #: True when this user exists only on a chat target's far side: visible in
    #: rosters and whois, addressable by private message, with no socket.
    remote: bool = False
    #: "client", or the name of whatever adapter introduced them. Addressing by
    #: (nick, origin) from the start is what stops server links and chat
    #: bridges being a retrofit later.
    origin: str = "client"
    send: Callable[..., None] | None = field(default=None, repr=False)

    @property
    def firewalled(self) -> bool:
        return self.data_port == 0

    @property
    def uptime(self) -> int:
        return int(time.monotonic() - self.connected_at)

    def adjust(self, *, downloads: int = 0, uploads: int = 0) -> None:
        self.downloads = max(0, self.downloads + downloads)
        self.uploads = max(0, self.uploads + uploads)


@dataclass(slots=True)
class Channel:
    name: str
    topic: str = ""
    level: Level = Level.USER
    limit: int = 200
    predefined: bool = False
    members: set = field(default_factory=set)
    operators: set = field(default_factory=set)


class Registry:
    """Live sessions, addressable **by nick** rather than private to a socket.

    Whois alone forces this: 604 reports another session's live transfer
    counters. It is also the router -- a backend that can only answer the
    request it was handed cannot drive 406 to other members, 607 to an
    uploader, 209/210 to hotlists or 627/628 broadcasts.
    """

    def __init__(self) -> None:
        self._by_nick: dict[str, Session] = {}

    def add(self, session: Session) -> Session | None:
        """Register. Returns a session being **evicted**, if any.

        A duplicate nick is an eviction, not a notification: period servers
        send the incumbent a 404 and drop it, and never send the 748 the spec
        describes.
        """
        existing = self._by_nick.get(session.nick)
        self._by_nick[session.nick] = session
        return existing if existing is not None and existing is not session else None

    def remove(self, session: Session) -> None:
        if self._by_nick.get(session.nick) is session:
            del self._by_nick[session.nick]

    def get(self, nick: str) -> Session | None:
        return self._by_nick.get(nick)

    def __iter__(self) -> Iterator[Session]:
        return iter(list(self._by_nick.values()))

    def __len__(self) -> int:
        return len(self._by_nick)

    def in_channel(self, channel: str) -> Iterable[Session]:
        return (s for s in self if channel in s.channels)

    def watching(self, nick: str) -> Iterable[Session]:
        """Sessions with `nick` on their hotlist -- the 209/210 fan-out."""
        return (s for s in self if nick in s.hotlist)

    def totals(self) -> tuple[int, int, int]:
        """(users, files, gigabytes) for message 214."""
        files = sum(len(s.shared) for s in self)
        size = sum(f.size for s in self for f in s.shared.values())
        return len(self._by_nick), files, size // (1024 ** 3)


# ==========================================================================
# 7. The backend seam -- one object, every method defaulted
# ==========================================================================

class Backend:
    """What a deployment fills in. Subclass and override what you have.

    `Backend()` on its own is a working, empty server: a real client logs in,
    joins channels, searches and finds nothing. Two rules hold whatever you
    override:

    * **A backend never formats a wire message.** It returns values; the
      server composes, gates by level and emits. A backend must not be *able*
      to leak the moderator-only tail of 604 to a plain user.
    * **No backend method knows a whole message.** Whois is assembled from
      what you return here plus the registry's own live counters.

    nim splits this into nine `typing.Protocol` domains (identity, presence,
    chat, library, rendezvous, policy, web, mail, federation) resolved through
    entry points. That is the right shape for a plugin ecosystem and overkill
    for one tool; the method names below are deliberately the same, so a nim
    provider is mechanically liftable into this.
    """

    # -- identity ----------------------------------------------------------
    #: Auto-register an unknown nick on first login, as period servers could.
    auto_register = True

    def nick_status(self, nick: str) -> str:
        """"free", "taken" or "invalid" -- drives messages 8/9/10."""
        return "free" if NICK_RE.match(nick) else "invalid"

    def authenticate(self, nick: str, password: str) -> str | None:
        """Return the account's email on success, None to refuse the login.

        The email is what goes into the 3 ack; a dummy is fine and is what an
        unregistered account got.
        """
        if not NICK_RE.match(nick):
            return None
        return "anon@napster.com" if self.auto_register else None

    def level_of(self, nick: str) -> Level:
        return Level.USER

    # -- policy ------------------------------------------------------------
    def motd(self) -> Iterable[str]:
        """621, one message per line, pushed right after login.

        The first thing a user sees, and the only place to put an announcement
        that needs no web surface.
        """
        return ("Welcome to the sandbox.",)

    def max_results(self) -> int:
        """Server-side cap. A live client asked for 4,976,092."""
        return 100

    def stat_interval(self) -> float:
        """214 cadence. Period default 60s; the client renders it in the status
        bar, and **static numbers are the clearest tell that nothing is real**
        -- drift them."""
        return 60.0

    def login_timeout(self) -> float:
        return 60.0

    def level_required(self, number: int) -> Level:
        """Gated centrally, so a backend cannot forget to."""
        return LEVEL_REQUIRED.get(number, Level.USER)

    # -- library -----------------------------------------------------------
    def replace_shares(self, nick: str, files: Iterable[SharedFile]) -> None:
        """**A login replays the whole library.** Replace, never append."""

    def clear_shares(self, nick: str) -> None:
        """Called on disconnect as well as on 110."""

    def search(self, *, terms: Iterable[str], requester: str,
               max_results: int) -> Iterable[Hit]:
        """Rows for `requester`.

        **Exclude the requester's own files.** A real server does, and a
        sandbox that attributes fabricated results to the logged-in user shows
        them nothing at all.
        """
        return ()

    def browse(self, nick: str) -> Iterable[SharedFile]:
        return ()

    def resume(self, checksum: str, size: int) -> Iterable[Hit]:
        """215/216: who else has this exact file. Match on `checksum_matches`."""
        return ()

    # -- rendezvous --------------------------------------------------------
    def resolve(self, *, requester: Session, nick: str,
                filename: str) -> tuple[int, int, str, int] | None:
        """Where the downloader should go: `(ip, port, checksum, link_type)`.

        `ip` is the little-endian uint32. Return None for a 206 get-error.
        Return the sandbox's **own** peer endpoint when the owner is a
        fabricated user with no socket -- the client cannot tell, and the two
        cases ride the same two messages.

        Read the port live rather than from login: 703 takes effect
        immediately and 204 must advertise the current value.
        """
        return None

    def source_for(self, filename: str) -> "FileSource | None":
        """Bytes for a file this backend listed, for the built-in peer server.

        Only needed when the "user" sharing a file is not a real client. Do a
        dict lookup on the path you advertised, never a join onto a real
        filesystem: the filename in a peer request is text the client supplies
        and the obvious attack on it is `..\\`.
        """
        return None

    def ping_ms(self, nick: str) -> int | None:
        """Round trip for a nick with no socket, or None for "not mine".

        The client pings a user **before** it downloads from them and its
        advanced search can filter on the answer, so a fabricated user who
        cannot be pinged is a fabricated user nobody will download from.
        """
        return None

    # -- chat (outbound hooks; the server stays authoritative for state) ---
    def on_join(self, session: Session, channel: str) -> None: ...
    def on_part(self, session: Session, channel: str) -> None: ...
    def on_public(self, session: Session, channel: str, text: str) -> None: ...
    def on_emote(self, session: Session, channel: str, text: str) -> None: ...

    def on_private(self, session: Session, to: str, text: str) -> bool:
        """Return True if you delivered it. Called when the recipient is not a
        local session, so a user can message someone who exists only on the
        far side of a bridge."""
        return False

    # -- lifecycle ---------------------------------------------------------
    def bind(self, registry: Registry) -> None:
        """Handed the registry so the backend can push, not only answer."""

    async def stop(self) -> None:
        """Called on the way out, including through cancellation.

        It matters for anything holding a connection to someone else's server:
        a chat adapter that is killed leaves a ghost sitting in a real channel
        until the far side times it out.
        """


#: Roughly thirty messages are level-gated. Declared once, applied centrally.
LEVEL_REQUIRED: dict[int, Level] = {
    M.CHANGE_USER_LEVEL: Level.ADMIN, M.KILL: Level.MODERATOR,
    M.NUKE: Level.ADMIN, M.BAN: Level.MODERATOR, M.UNBAN: Level.MODERATOR,
    M.SHOW_BANS: Level.MODERATOR, M.MUZZLE: Level.MODERATOR,
    M.UNMUZZLE: Level.MODERATOR, M.UNNUKE: Level.ADMIN,
    M.CHANGE_LINKSPEED_USER: Level.MODERATOR,
    M.CHANGE_PASSWORD_OTHER: Level.ADMIN, M.RELOAD_CONFIG: Level.ELITE,
    M.SET_CONFIG: Level.ELITE, M.CLEAR_CHANNEL: Level.MODERATOR,
    M.SET_CHANNEL_LEVEL: Level.MODERATOR, M.REDIRECT: Level.ADMIN,
    M.CYCLE: Level.ADMIN, M.KICK: Level.MODERATOR,
    M.OPERATOR_MESSAGE: Level.MODERATOR, M.GLOBAL_MESSAGE: Level.MODERATOR,
    M.CLOAK: Level.MODERATOR, M.SET_DATA_PORT: Level.MODERATOR,
}


# ==========================================================================
# 8. Composed payloads -- what no single backend method owns
# ==========================================================================

def whois_payload(registry: Registry, target: str, *,
                  asker_level: Level) -> str | None:
    """604, or None if the user is not online.

    The moderator-only tail is appended **here**, so a backend cannot leak it.
    The client displays every field of it in a "Finger Information" panel, so
    emitting it to a plain user leaks data that is then shown.
    """
    s = registry.get(target)
    if s is None:
        return None
    channels = " ".join(sorted(s.channels))
    head = join(s.nick, s.level.wire, s.uptime,
                f" {channels} " if channels else " ", "Active",
                len(s.shared), s.downloads, s.uploads, s.link_type, s.client)
    if asker_level < Level.MODERATOR:
        return head
    return f"{head} {join(s.uploads, s.downloads, s.ip, 0, s.data_port, s.email)}"


def channel_user(channel: str, s: Session) -> str:
    """406/408/825 share one layout: `<channel> <user> <shared> <link-type>`.
    825 is byte-identical to 408 -- a duplicate code path in the original."""
    return join(channel, s.nick, len(s.shared), s.link_type)


def server_stats(registry: Registry) -> str:
    """214: `<users> <files> <gigabytes>`."""
    users, files, gigs = registry.totals()
    return f"{users} {files} {gigs}"


# ==========================================================================
# 9. File sources, and the peer wire
# ==========================================================================

class FileSource:
    """Where a served file's bytes come from."""

    async def size(self) -> int:
        raise NotImplementedError

    def read(self, offset: int = 0) -> AsyncIterator[bytes]:
        raise NotImplementedError


class LocalFile(FileSource):
    def __init__(self, path: str | Path, *, chunk: int = 65536) -> None:
        self.path = Path(path)
        self.chunk = chunk

    async def size(self) -> int:
        return self.path.stat().st_size

    async def read(self, offset: int = 0) -> AsyncIterator[bytes]:
        with self.path.open("rb") as fh:
            fh.seek(offset)
            while True:
                data = fh.read(self.chunk)
                if not data:
                    return
                yield data


HANDSHAKE = b"1"


@dataclass(frozen=True, slots=True)
class PeerRequest:
    verb: str               # GET | SEND | GETLIST | SENDLIST
    nick: str = ""
    filename: str = ""
    offset: int = 0
    size: int = 0


async def read_size_prefix(reader: asyncio.StreamReader, *,
                           max_digits: int = 20) -> tuple[int, bytes]:
    """Read the **undelimited** size, returning `(size, first_data_byte)`.

    The spec says the terminating byte is "usually 0xFF", the MPEG frame sync.
    A live capture terminated on `I` (0x49), the first letter of an `ID3` tag,
    on an entirely ordinary MP3. **Scan for the first non-digit, never for
    0xFF** -- and hand the byte back, because it is already part of the file
    and dropping it silently corrupts byte 0 of every transfer.
    """
    digits = bytearray()
    b = b""
    while len(digits) < max_digits:
        b = await reader.readexactly(1)
        if not b.isdigit():
            return int(digits or b"0"), b
        digits += b
    return int(digits or b"0"), b""


async def read_peer_request(reader: asyncio.StreamReader) -> PeerRequest | None:
    """Read a verb and its arguments from a connected peer."""
    head = await reader.read(8)
    if not head:
        return None
    verb = head.decode("latin1").strip()
    for known in ("GETLIST", "SENDLIST", "SEND", "GET"):
        if verb.startswith(known):
            rest = head[len(known):]
            if known == "GETLIST":
                return PeerRequest(verb="GETLIST")
            line = (rest + await reader.read(1024)).decode("latin1").strip()
            f = split(line)
            if known == "SENDLIST":
                return PeerRequest(verb="SENDLIST", nick=f[0] if f else "")
            n = as_int(f, 2)
            return PeerRequest(verb=known, nick=f[0] if f else "",
                               filename=f[1] if len(f) > 1 else "",
                               offset=n if known == "GET" else 0,
                               size=0 if known == "GET" else n)
    return PeerRequest(verb=verb)


async def serve_get(writer: asyncio.StreamWriter, source: FileSource, *,
                    offset: int = 0, bps: float = 0.0) -> int:
    """Answer a GET: size digits, then the bytes, with no delimiter between.

    `bps` throttles to a modelled line rate. Chunks are sized **from the
    rate** rather than fixed: a 64 kB chunk at modem speed is a fourteen
    second silence followed by a burst, which is not what a slow transfer
    looked like. The progress bar was the event.
    """
    size = await source.size()
    writer.write(str(size - offset).encode("ascii"))
    chunk = 65536 if bps <= 0 else max(1024, int(round(bps / 4 / 1024)) * 1024)
    sent = 0
    async for block in source.read(offset):
        for i in range(0, len(block), chunk):
            piece = block[i:i + chunk]
            writer.write(piece)
            sent += len(piece)
            await writer.drain()
            if bps > 0:
                await asyncio.sleep(len(piece) / bps)
    return sent


async def serve_getlist(writer: asyncio.StreamWriter, nick: str,
                        files: Iterable[SharedFile]) -> None:
    """Answer a GETLIST: `<nick>\\n`, share lines, then a bare LF.

    These lines carry the real `<md5>-<n>` checksum: this is client-to-client
    and no server is in the path to mangle it.
    """
    writer.write(f"{nick}\n".encode("latin1"))
    await writer.drain()
    for f in files:
        line = join(f.filename, f.checksum, f.size, f.bitrate, f.frequency,
                    f.seconds)
        writer.write((line + "\n").encode("latin1"))
    writer.write(b"\n")
    await writer.drain()


async def push_send(writer: asyncio.StreamWriter, reader: asyncio.StreamReader,
                    nick: str, filename: str, source: FileSource) -> int:
    """The firewalled push: wait for "1", SEND, header, read offset, send."""
    first = await reader.readexactly(1)
    if first != HANDSHAKE:
        raise ConnectionError(f"peer did not send '1' (got {first!r})")
    size = await source.size()
    writer.write(b"SEND")
    await writer.drain()
    writer.write(join(nick, filename, size).encode("latin1"))
    await writer.drain()
    raw = await reader.read(32)
    try:
        offset = int(raw.decode("latin1").strip() or 0)
    except ValueError:
        raise ConnectionError(f"peer refused: {raw!r}") from None
    sent = 0
    async for chunk in source.read(offset):
        writer.write(chunk)
        sent += len(chunk)
        await writer.drain()
    return sent


class PeerServer:
    """Listen on a data port and answer the peer protocol ourselves.

    Needed whenever the user "sharing" a file is not a real client: a
    fabricated owner has no socket, so the 204 for one of their files names an
    address with nobody behind it and the download fails on connect with no
    protocol-visible error.

    **Not port 6699.** The client wants that one for its own uploads and drops
    into firewall mode if it cannot bind it.
    """

    def __init__(self, backend: Backend, *, nick: str = "sandbox",
                 bps: float = 0.0, list_files: Callable[[], Iterable[SharedFile]] | None = None) -> None:
        self.backend = backend
        self.nick = nick
        self.bps = bps
        self.list_files = list_files or (lambda: ())

    async def handle(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        try:
            writer.write(HANDSHAKE)
            await writer.drain()
            req = await read_peer_request(reader)
            if req is None:
                return
            if req.verb == "GETLIST":
                await serve_getlist(writer, self.nick, self.list_files())
                return
            if req.verb == "GET":
                # `req.nick` is the DOWNLOADER: the peer protocol has the
                # asker name itself. The owner comes from the file.
                source = self.backend.source_for(req.filename)
                if source is None:
                    writer.write(b"FILE NOT SHARED")
                    await writer.drain()
                    return
                await serve_get(writer, source, offset=req.offset, bps=self.bps)
                return
            writer.write(b"INVALID REQUEST")
            await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    async def serve(self, host: str, port: int) -> None:
        srv = await asyncio.start_server(self.handle, host, port)
        async with srv:
            await srv.serve_forever()


# ==========================================================================
# 10. The metaserver -- FIRST CONTACT, and one line of protocol
# ==========================================================================

class Metaserver:
    """Port 8875. The server speaks first and hangs up; the client sends nothing.

        client connects to :8875
        server -> "127.0.0.1:8888\\n"
        server closes

    A live client opens its **first** control connection here, not to 8888,
    and re-dials it for every subsequent connection. A server listening only
    on 8888 never sees the client at all.
    """

    DEFAULT_PORT = 8875

    def __init__(self, targets: Iterable[str]) -> None:
        self.targets = list(targets)
        if not self.targets:
            raise ValueError("a metaserver needs at least one host:port target")
        self._next = 0

    async def handle(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        try:
            target = self.targets[self._next % len(self.targets)]
            self._next += 1
            writer.write(f"{target}\n".encode("latin1"))
            await writer.drain()
        except ConnectionError:
            pass
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    async def serve(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
        srv = await asyncio.start_server(self.handle, host, port)
        async with srv:
            await srv.serve_forever()


# ==========================================================================
# 11. The server
# ==========================================================================

Handler = Callable[["Connection", Frame], Awaitable[None]]
_HANDLERS: dict[int, Handler] = {}


def handles(number: int) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        _HANDLERS[int(number)] = fn
        return fn
    return deco


class Connection:
    """One client socket, plus the session it owns."""

    def __init__(self, server: "Server", reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter) -> None:
        self.server = server
        self.reader = reader
        self.writer = writer
        self.frames = FrameReader()
        peer = writer.get_extra_info("peername") or ("127.0.0.1", 0)
        self.session = Session(nick="", ip=peer[0])
        self.session.send = self.send
        self._closed = False

    def send(self, number: int, payload: str = "") -> None:
        if self._closed:
            return
        try:
            self.writer.write(encode(int(number), payload))
        except (ConnectionError, RuntimeError):
            self._closed = True

    def error(self, text: str) -> None:
        """404 -- **not only errors.** It is the server's general per-client
        text channel; period servers sent operator grants through it too, and
        the client renders the lot in red. The strings are what the user saw,
        so preserve them verbatim:

            User nosuchuser is not currently online.
            Channel #nosuchchannel does not exist!
            permission denied
            ping failed, blah is not online
        """
        self.send(M.ERROR_MESSAGE, text)

    def close(self) -> None:
        self._closed = True
        with contextlib.suppress(Exception):
            self.writer.close()

    @property
    def backend(self) -> Backend:
        return self.server.backend


class Server:
    """Dispatch, the pre-login echo, framework-owned terminators, push routing."""

    def __init__(self, backend: Backend | None = None, *,
                 registry: Registry | None = None,
                 alias: str = "sandbox", version: str = "napster-primitive 1") -> None:
        self.backend = backend or Backend()
        self.registry = registry or Registry()
        self.channels: dict[str, Channel] = {}
        self.alias = alias
        self.version = version
        self._tasks: set[asyncio.Task] = set()
        self.backend.bind(self.registry)

    # -- routing: a backend must be able to push, not only answer ----------
    def to_nick(self, nick: str, number: int, payload: str = "") -> bool:
        s = self.registry.get(nick)
        if s is None or s.send is None:
            return False
        s.send(number, payload)
        return True

    def to_channel(self, channel: str, number: int, payload: str = "",
                   *, skip: str | None = None) -> None:
        for s in self.registry.in_channel(channel):
            if s.nick != skip and s.send is not None:
                s.send(number, payload)

    def to_all(self, number: int, payload: str = "") -> None:
        for s in self.registry:
            if s.send is not None:
                s.send(number, payload)

    def to_level(self, level: Level, number: int, payload: str = "") -> None:
        for s in self.registry:
            if s.level >= level and s.send is not None:
                s.send(number, payload)

    def channel(self, name: str, *, create: bool = True) -> Channel | None:
        ch = self.channels.get(name)
        if ch is None and create:
            ch = self.channels[name] = Channel(name=name)
        return ch

    def spawn(self, coro) -> None:
        """Run something that outlives the message that started it, keeping a
        reference so it cannot be collected mid-sleep."""
        try:
            task = asyncio.create_task(coro)
        except RuntimeError:
            coro.close()
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # -- lifecycle ---------------------------------------------------------
    async def handle(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        conn = Connection(self, reader, writer)
        timeout = self.backend.login_timeout()
        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(4096),
                        timeout=None if conn.session.authenticated else timeout)
                except asyncio.TimeoutError:
                    conn.send(M.ERROR, "Idle timeout")
                    break
                if not data:
                    break
                for frame in conn.frames.feed(data):
                    await self._dispatch(conn, frame)
                with contextlib.suppress(Exception):
                    await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            await self._disconnect(conn)

    async def _dispatch(self, conn: Connection, frame: Frame) -> None:
        s = conn.session

        # Rule 1. The echo that stops the client hanging at "Checking
        # Version...". It is the whole answer: message 5 stays off.
        if not s.authenticated and frame.type in ECHO_PRE_LOGIN:
            conn.send(M.ECHO, f"{frame.type}: {frame.text}")
            return

        handler = _HANDLERS.get(frame.type)
        if handler is None:
            if frame.type in (M.LOGIN_OPTIONS, M.DEMOGRAPHICS):
                return                  # accept and discard: faithful, and safe
            conn.error(f"Unknown command code {frame.type}")
            return

        if s.level < self.backend.level_required(frame.type):
            conn.error("permission denied")
            return
        try:
            await handler(conn, frame)
        except Exception:
            # A bug in one handler must not drop the client. The original
            # server kept talking; so do we.
            log.exception("handler for %d (%s) failed", frame.type,
                          name_of(frame.type))
            conn.error("server error handling that request")

    async def _disconnect(self, conn: Connection) -> None:
        s = conn.session
        if s.authenticated:
            for ch in list(s.channels):
                self.to_channel(ch, M.PART_MESSAGE, channel_user(ch, s),
                                skip=s.nick)
                room = self.channels.get(ch)
                if room:
                    room.members.discard(s.nick)
            for watcher in self.registry.watching(s.nick):
                if watcher.send:
                    watcher.send(M.USER_SIGNOFF, s.nick)
            self.backend.clear_shares(s.nick)
            self.registry.remove(s)
        conn.close()

    async def _stats_loop(self) -> None:
        while True:
            await asyncio.sleep(self.backend.stat_interval())
            self.to_all(M.SERVER_STATS, server_stats(self.registry))

    async def serve(self, host: str = "0.0.0.0", port: int = 8888) -> None:
        srv = await asyncio.start_server(self.handle, host, port)
        self.spawn(self._stats_loop())
        log.info("napster primitive listening on %s:%d", host, port)
        async with srv:
            await srv.serve_forever()


# -- handlers --------------------------------------------------------------

async def _complete_login(conn: Connection, nick: str, email: str, port: int,
                          client: str, link_type: int) -> None:
    s, server = conn.session, conn.server
    s.nick, s.data_port, s.client, s.link_type = nick, port, client, link_type
    s.email = email
    s.level = conn.backend.level_of(nick)
    s.authenticated = True

    evicted = server.registry.add(s)
    if evicted is not None and evicted.send is not None:
        evicted.send(M.ERROR_MESSAGE,
                     f"You were killed by server {server.alias}: "
                     "Someone else is logging in as you, disconnecting.")
    conn.send(M.LOGIN_ACK, email)
    for line in conn.backend.motd():
        conn.send(M.MOTD, line)
    conn.send(M.SERVER_STATS, server_stats(server.registry))
    for watcher in server.registry.watching(nick):
        if watcher.send:
            watcher.send(M.USER_SIGNON, join(nick, link_type))


@handles(M.PRE_LOGIN)
async def _pre_login(conn: Connection, frame: Frame) -> None:
    """920, body `1`. The first message a *returning* login sends, and such a
    login sends no version check at all; a first run sends 4 and no 920. A
    server must tolerate either opening -- and must NOT echo this one."""


@handles(M.VERSION_CHECK)
async def _version_check(conn: Connection, frame: Frame) -> None:
    """4: `"v2.0 BETA 9.4" 0` -- quoted, with a trailing numeric, where the
    spec gives a bare version. Already answered by the echo above; reached
    only if it arrives post-login."""


@handles(M.LOGIN)
async def _login(conn: Connection, frame: Frame) -> None:
    """2: `<nick> <pass> <port> "<client>" <link-type> [<build>] [<n>]`.

    `port` 0 means **firewalled**: every transfer must be pushed (500/501).
    Observed with *two* trailing numerics, not the spec's single optional one.
    """
    f = split(frame.text)
    if len(f) < 5:
        conn.send(M.ERROR, "Invalid parameters")
        conn.close()
        return
    email = conn.backend.authenticate(f[0], f[1])
    if email is None:
        conn.send(M.ERROR, "Invalid password")
        conn.close()
        return
    await _complete_login(conn, f[0], email, as_int(f, 2), f[3], as_int(f, 4))


@handles(M.NEW_USER_LOGIN)
async def _new_user(conn: Connection, frame: Frame) -> None:
    """6: the login fields plus `<email>`, plus an undocumented trailing
    numeric."""
    f = split(frame.text)
    if len(f) < 5:
        conn.send(M.ERROR, "Invalid parameters")
        conn.close()
        return
    if conn.backend.nick_status(f[0]) == "taken":
        conn.send(M.ERROR, "Nickname already registered")
        conn.close()
        return
    email = conn.backend.authenticate(f[0], f[1]) or (f[5] if len(f) > 5 else "")
    await _complete_login(conn, f[0], email, as_int(f, 2), f[3], as_int(f, 4))


@handles(M.NICK_CHECK)
async def _nick_check(conn: Connection, frame: Frame) -> None:
    conn.send({"free": M.NICK_NOT_REGISTERED,
               "taken": M.NICK_ALREADY_REGISTERED,
               "invalid": M.NICK_INVALID}[
                   conn.backend.nick_status(frame.text.strip())])


@handles(M.SHARE_DIRECTORY)
async def _share_dir(conn: Connection, frame: Frame) -> None:
    r'''870: `"<dir>" ("<file>" <checksum> <size> <bitrate> <freq> <len>)+`.

    Two corrections from capture: `<dir>` is a **synthetic token** (`"1:\1\"`),
    not a real path -- the client never discloses its filesystem layout, and
    that token is what other users see in 201/212 -- and the checksum is
    `<md5>-<bytes>`, not a bare hash. Prepend the token and store verbatim.
    '''
    f = split(frame.text)
    if not f:
        return
    directory, files = f[0], []
    i = 1
    while i + 5 < len(f) + 1 and i + 5 <= len(f):
        try:
            files.append(SharedFile(
                filename=f"{directory}{f[i]}", checksum=f[i + 1],
                size=int(f[i + 2]), bitrate=int(f[i + 3]),
                frequency=int(f[i + 4]), seconds=int(f[i + 5])))
        except (ValueError, IndexError):
            break
        i += 6
    conn.session.shared.update({x.filename: x for x in files})
    conn.backend.replace_shares(conn.session.nick,
                                list(conn.session.shared.values()))


@handles(M.SHARE_FILE)
async def _share_file(conn: Connection, frame: Frame) -> None:
    """100: one file, one message. No ack exists; the client assumes success.
    A 5,000 file library is 5,000 of these at login."""
    f = split(frame.text)
    if len(f) < 6:
        return
    try:
        shared = SharedFile(f[0], f[1], int(f[2]), int(f[3]), int(f[4]),
                            int(f[5]))
    except ValueError:
        return
    conn.session.shared[shared.filename] = shared
    conn.backend.replace_shares(conn.session.nick,
                                list(conn.session.shared.values()))


@handles(M.UNSHARE_ALL)
async def _unshare_all(conn: Connection, frame: Frame) -> None:
    conn.session.shared.clear()
    conn.backend.clear_shares(conn.session.nick)


@handles(M.REMOVE_FILE)
async def _remove_file(conn: Connection, frame: Frame) -> None:
    conn.session.shared.pop(frame.text.strip(), None)
    conn.backend.replace_shares(conn.session.nick,
                                list(conn.session.shared.values()))


@handles(M.SEARCH)
async def _search(conn: Connection, frame: Frame) -> None:
    """200: `FILENAME CONTAINS "x" MAX_RESULTS <n> [...]`.

    Multiple CONTAINS terms are ANDed and treated identically -- artist vs.
    title is a client-side fiction. Ping-time filtering happens *in the
    client*, which will report "50 results found" while displaying 3.

    Rule 2 lives here: the 202 goes out in a `finally`, because a backend can
    raise when it is called, while its rows are being iterated, or not at all.
    A client that never receives a terminator waits for ever rather than
    failing, which is the worst failure available.
    """
    terms = tuple(re.findall(r'FILENAME CONTAINS "([^"]*)"', frame.text))
    asked = re.search(r"MAX_RESULTS (\d+)", frame.text)
    cap = conn.backend.max_results()
    limit = max(1, min(int(asked.group(1)) if asked else 100, cap))
    try:
        for h in conn.backend.search(terms=terms, requester=conn.session.nick,
                                     max_results=limit):
            conn.send(M.SEARCH_RESULT,
                      join(quoted(h.filename), h.checksum, h.size, h.bitrate,
                           h.frequency, h.seconds, h.nick, h.ip, h.link_type,
                           h.weight))
    finally:
        conn.send(M.SEARCH_END)


@handles(M.BROWSE)
async def _browse(conn: Connection, frame: Frame) -> None:
    """211 -> 212 per file, 213 terminator carrying the browsee's address.
    A nonexistent user is answered with 210, the spec's overloaded reply."""
    nick = frame.text.strip()
    target = conn.server.registry.get(nick)
    ip = ip_to_wire(target.ip) if target else 0
    if target is None and not list(conn.backend.browse(nick)):
        conn.send(M.USER_SIGNOFF, nick)
        return
    try:
        for f in conn.backend.browse(nick):
            conn.send(M.BROWSE_RESULT,
                      join(nick, quoted(f.filename), f.checksum, f.size,
                           f.bitrate, f.frequency, f.seconds))
    finally:
        conn.send(M.BROWSE_END, join(nick, ip))


@handles(M.RESUME_REQUEST)
async def _resume(conn: Connection, frame: Frame) -> None:
    f = split(frame.text)
    try:
        for h in conn.backend.resume(f[0] if f else "", as_int(f, 1)):
            conn.send(M.RESUME_RESULT,
                      join(h.nick, h.ip, 0, quoted(h.filename), h.checksum,
                           h.size, h.link_type))
    finally:
        conn.send(M.RESUME_END)


@handles(M.DOWNLOAD_REQUEST)
async def _download(conn: Connection, frame: Frame) -> None:
    """203 -> 204 `<nick> <ip> <port> "<file>" <md5> <linespeed>`.

    `port` 0 in the ack means the peer is firewalled, and **the client only
    falls back to 500 after reading that** -- it does not decide from the
    search result, so this round trip cannot be skipped.
    """
    f = split(frame.text)
    nick, filename = (f[0] if f else ""), (f[1] if len(f) > 1 else "")
    r = conn.backend.resolve(requester=conn.session, nick=nick,
                             filename=filename)
    if r is None:
        conn.send(M.GET_ERROR, join(nick, quoted(filename)))
        return
    ip, port, checksum, link = r
    conn.send(M.DOWNLOAD_ACK,
              join(nick, ip, port, quoted(filename), checksum, link))


@handles(M.ALT_DOWNLOAD_REQUEST)
async def _alt_download(conn: Connection, frame: Frame) -> None:
    """500: the uploader is firewalled, so ask it to push.

    **Supply the `<speed>` field in the 607.** Omitting it costs an extra
    600/601 round trip before the uploader will send 608.
    """
    f = split(frame.text)
    nick, filename = (f[0] if f else ""), (f[1] if len(f) > 1 else "")
    s = conn.session
    uploader = conn.server.registry.get(nick)
    if uploader is None:
        conn.send(M.GET_ERROR, join(nick, quoted(filename)))
        return
    shared = uploader.shared.get(filename)
    conn.server.to_nick(nick, M.UPLOAD_REQUEST,
                        join(s.nick, quoted(filename), s.link_type))
    conn.server.to_nick(nick, M.ALT_DOWNLOAD_ACK,
                        join(s.nick, ip_to_wire(s.ip), s.data_port,
                             quoted(filename),
                             shared.checksum if shared else "", s.link_type))


@handles(M.ACCEPT_UPLOAD)
async def _accept_upload(conn: Connection, frame: Frame) -> None:
    f = split(frame.text)
    if f:
        conn.server.to_nick(f[0], M.UPLOAD_REQUEST, frame.text)


@handles(M.DOWNLOADING)
async def _downloading(conn: Connection, frame: Frame) -> None:
    conn.session.adjust(downloads=+1)


@handles(M.DOWNLOAD_COMPLETE)
async def _download_done(conn: Connection, frame: Frame) -> None:
    conn.session.adjust(downloads=-1)


@handles(M.UPLOADING)
async def _uploading(conn: Connection, frame: Frame) -> None:
    conn.session.adjust(uploads=+1)


@handles(M.UPLOAD_COMPLETE)
async def _upload_done(conn: Connection, frame: Frame) -> None:
    conn.session.adjust(uploads=-1)


@handles(M.CHANGE_DATA_PORT)
async def _change_port(conn: Connection, frame: Frame) -> None:
    """703, emitted the instant the port changes in Preferences, on the live
    connection with no reconnect. 204 must advertise the new value at once."""
    conn.session.data_port = as_int(split(frame.text), 0)


@handles(M.DIRECT_BROWSE)
async def _direct_browse(conn: Connection, frame: Frame) -> None:
    """640. A reachable browsee answers 641 automatically within ~1 ms. A
    **firewalled** browsee gets the requester's `ip port` here and skips 641
    entirely, pushing SENDLIST straight across."""
    nick = (split(frame.text) or [""])[0]
    s = conn.session
    target = conn.server.registry.get(nick)
    if target is None:
        conn.send(M.DIRECT_BROWSE_ERROR, join(nick, "user is offline"))
        return
    if target.firewalled:
        conn.server.to_nick(nick, M.DIRECT_BROWSE,
                            join(s.nick, ip_to_wire(s.ip), s.data_port))
    else:
        conn.server.to_nick(nick, M.DIRECT_BROWSE, s.nick)


@handles(M.DIRECT_BROWSE_ACCEPT)
async def _direct_browse_accept(conn: Connection, frame: Frame) -> None:
    s = conn.session
    conn.server.to_nick(frame.text.strip(), M.DIRECT_BROWSE_ACCEPT,
                        join(s.nick, ip_to_wire(s.ip), s.data_port))


@handles(M.LINKSPEED_REQUEST)
async def _linkspeed(conn: Connection, frame: Frame) -> None:
    nick = frame.text.strip()
    target = conn.server.registry.get(nick)
    conn.send(M.LINKSPEED, join(nick, target.link_type if target else 0))


@handles(M.WHOIS)
async def _whois(conn: Connection, frame: Frame) -> None:
    nick = frame.text.strip()
    payload = whois_payload(conn.server.registry, nick,
                            asker_level=conn.session.level)
    if payload is not None:
        conn.send(M.WHOIS_RESPONSE, payload)
        return
    conn.error(f"User {nick} is not currently online.")


@handles(M.PING_USER)
async def _ping(conn: Connection, frame: Frame) -> None:
    """751. A real client answers for itself; a fabricated user has no socket,
    so answer for them after as long as their line would have taken."""
    nick = frame.text.strip()
    if conn.server.to_nick(nick, M.PING_USER, conn.session.nick):
        return
    ms = conn.backend.ping_ms(nick)
    if ms is None:
        conn.error(f"ping failed, {nick} is not online")
        return
    conn.server.spawn(_pong_after(conn, nick, ms / 1000.0))


async def _pong_after(conn: Connection, nick: str, delay: float) -> None:
    if delay > 0:
        await asyncio.sleep(delay)
    conn.send(M.PONG, nick)


@handles(M.PONG)
async def _pong(conn: Connection, frame: Frame) -> None:
    conn.server.to_nick(frame.text.strip(), M.PONG, conn.session.nick)


@handles(M.HOTLIST)
async def _hotlist(conn: Connection, frame: Frame) -> None:
    """208: the *initial* hotlist, sent at login before the share messages."""
    await _hotlist_add(conn, frame)


@handles(M.HOTLIST_ADD)
async def _hotlist_add(conn: Connection, frame: Frame) -> None:
    nick = frame.text.strip()
    conn.session.hotlist.add(nick)
    conn.send(M.HOTLIST_ACK, nick)
    target = conn.server.registry.get(nick)
    if target is not None:
        conn.send(M.USER_SIGNON, join(nick, target.link_type))


@handles(M.HOTLIST_REMOVE)
async def _hotlist_remove(conn: Connection, frame: Frame) -> None:
    conn.session.hotlist.discard(frame.text.strip())


@handles(M.JOIN)
async def _join(conn: Connection, frame: Frame) -> None:
    """400 -> 405 ack, 408 per existing member, 409 terminator, 410 topic.

    `/join <channel>` is the **only** client command whose argument is free
    text and reaches the server verbatim, which is why anything a shim wants
    to offer has to ride inside a channel name.
    """
    channel = frame.text.strip()
    s, server = conn.session, conn.server
    ch = server.channel(channel)
    first = not ch.members
    ch.members.add(s.nick)
    s.channels.add(channel)

    conn.send(M.JOIN_ACK, channel)
    for other in server.registry.in_channel(channel):
        conn.send(M.CHANNEL_USER, channel_user(channel, other))
    conn.send(M.USER_LIST_END, channel)                 # owed terminator
    conn.send(M.TOPIC,
              f"{channel} {ch.topic or f'Welcome to the {channel} channel.'}")
    server.to_channel(channel, M.JOIN_MESSAGE, channel_user(channel, s),
                      skip=s.nick)
    if first:
        ch.operators.add(s.nick)
        conn.error(f"Server {server.alias} set you as operator "
                   f"on channel {channel}")       # 404 carries notices
    conn.backend.on_join(s, channel)


@handles(M.PART)
async def _part(conn: Connection, frame: Frame) -> None:
    """401, and the server may send it **unsolicited**: the client must accept
    a part it never requested (kick, channel clear, split)."""
    channel = frame.text.strip()
    s = conn.session
    s.channels.discard(channel)
    ch = conn.server.channels.get(channel)
    if ch:
        ch.members.discard(s.nick)
    conn.send(M.PART, channel)
    conn.server.to_channel(channel, M.PART_MESSAGE, channel_user(channel, s),
                           skip=s.nick)
    conn.backend.on_part(s, channel)


@handles(M.PUBLIC_MESSAGE_OUT)
async def _public(conn: Connection, frame: Frame) -> None:
    """402 in, 403 out as `<channel> <nick> <text>`. Free text to EOL, so
    split with a limit and never on the whole payload."""
    f = split(frame.text, limit=1)
    channel, text = (f[0] if f else ""), (f[1] if len(f) > 1 else "")
    s = conn.session
    if s.muzzled:
        conn.error("You are muzzled")
        return
    conn.server.to_channel(channel, M.PUBLIC_MESSAGE, f"{channel} {s.nick} {text}")
    conn.backend.on_public(s, channel, text)


@handles(M.EMOTE)
async def _emote(conn: Connection, frame: Frame) -> None:
    '''824: client `<channel> "<text>"`; server `<channel> <user> "<text>"`.'''
    f = split(frame.text)
    channel, text = (f[0] if f else ""), (f[1] if len(f) > 1 else "")
    conn.server.to_channel(channel, M.EMOTE,
                           join(channel, conn.session.nick, text))
    conn.backend.on_emote(conn.session, channel, text)


@handles(M.PRIVATE_MESSAGE)
async def _private(conn: Connection, frame: Frame) -> None:
    """205 both ways -- the server rewrites the nick field, so direction is
    not recoverable from the message. Track it out of band."""
    f = split(frame.text, limit=1)
    if len(f) < 2:
        return
    to, body = f[0], f[1]
    target = conn.server.registry.get(to)
    if target is not None and not target.remote:
        conn.server.to_nick(to, M.PRIVATE_MESSAGE, f"{conn.session.nick} {body}")
        conn.backend.on_private(conn.session, to, body)
        return
    if not conn.backend.on_private(conn.session, to, body):
        conn.error(f"User {to} is not currently online.")


@handles(M.LIST_CHANNELS)
async def _list_channels(conn: Connection, frame: Frame) -> None:
    """617: the request and its terminator **share one number**."""
    for name, ch in conn.server.channels.items():
        conn.send(M.CHANNEL_ENTRY, f"{name} {len(ch.members)} {ch.topic}")
    conn.send(M.LIST_CHANNELS)


@handles(M.SHOW_ALL_CHANNELS)
async def _show_all_channels(conn: Connection, frame: Frame) -> None:
    for name, ch in conn.server.channels.items():
        conn.send(M.CHANNEL_LIST,
                  join(name, len(ch.members), 1 if ch.predefined else 0,
                       int(ch.level), ch.limit, ch.topic))
    conn.send(M.SHOW_ALL_CHANNELS)


@handles(M.LIST_USERS)
async def _list_users(conn: Connection, frame: Frame) -> None:
    channel = frame.text.strip()
    for s in conn.server.registry.in_channel(channel):
        conn.send(M.USER_LIST_ENTRY, channel_user(channel, s))
    conn.send(M.LIST_USERS)


@handles(M.TOPIC)
async def _topic(conn: Connection, frame: Frame) -> None:
    """410 has **no setter field**: the client can only see that it changed."""
    f = split(frame.text, limit=1)
    if len(f) < 2:
        return
    ch = conn.server.channel(f[0])
    ch.topic = f[1]
    conn.server.to_channel(f[0], M.TOPIC, f"{f[0]} {f[1]}")


@handles(M.MOTD)
async def _motd(conn: Connection, frame: Frame) -> None:
    for line in conn.backend.motd():
        conn.send(M.MOTD, line)


@handles(M.SERVER_STATS)
async def _stats(conn: Connection, frame: Frame) -> None:
    conn.send(M.SERVER_STATS, server_stats(conn.server.registry))


@handles(M.SERVER_PING)
async def _server_ping(conn: Connection, frame: Frame) -> None:
    conn.send(M.SERVER_PING)


@handles(M.SERVER_VERSION)
async def _server_version(conn: Connection, frame: Frame) -> None:
    conn.send(M.SERVER_VERSION, conn.server.version)


@handles(M.GLOBAL_MESSAGE)
async def _global(conn: Connection, frame: Frame) -> None:
    conn.server.to_all(M.GLOBAL_MESSAGE, f"{conn.session.nick} {frame.text}")


@handles(M.OPERATOR_MESSAGE)
async def _opsay(conn: Connection, frame: Frame) -> None:
    conn.server.to_level(Level.MODERATOR, M.OPERATOR_MESSAGE,
                         f"{conn.session.nick} {frame.text}")


for _n in REFUSAL_ONLY:
    @handles(_n)
    async def _refuse(conn: Connection, frame: Frame) -> None:
        """Preserving the refusal IS the implementation."""
        conn.error("permission denied")
del _n


@handles(M.UNKNOWN_310)
async def _unknown_310(conn: Connection, frame: Frame) -> None:
    conn.send(M.UNKNOWN_310, "0")       # returns 0 regardless of parameters


@handles(M.UNKNOWN_602)
async def _unknown_602(conn: Connection, frame: Frame) -> None:
    conn.error("*gulp* Drink milk, it does a body good!")


# ==========================================================================
# 12. Running it
# ==========================================================================

async def serve_async(backend: Backend | None = None, *, host: str = "0.0.0.0",
                      port: int = 8888, metaserver_port: int | None = 8875,
                      advertise: str | None = None,
                      data_port: int | None = 6700, bps: float = 0.0,
                      server: Server | None = None) -> None:
    """Run the protocol server, the metaserver, and the peer server.

    The metaserver is **on by default** because it is first contact.
    `advertise` is what it tells the client to dial; through a SOCKS proxy
    that routes by port it is cosmetic, and for a client reaching us by
    address it has to be true.

    `data_port` runs the peer server, which only matters when the user sharing
    a file is not a real client. 6700, never 6699.
    """
    backend = backend or Backend()
    srv = server or Server(backend)
    tasks = [asyncio.create_task(srv.serve(host, port))]
    if metaserver_port:
        target = advertise or f"127.0.0.1:{port}"
        if ":" not in target:
            target = f"{target}:{port}"
        tasks.append(asyncio.create_task(
            Metaserver((target,)).serve(host, metaserver_port)))
    if data_port:
        tasks.append(asyncio.create_task(
            PeerServer(backend, nick=srv.alias, bps=bps).serve(host, data_port)))
    try:
        await asyncio.gather(*tasks)
    finally:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(asyncio.shield(backend.stop()), timeout=3)


def serve(backend: Backend | None = None, **kwargs) -> None:
    """Blocking wrapper. `serve(Backend())` is a working, empty server."""
    try:
        asyncio.run(serve_async(backend, **kwargs))
    except KeyboardInterrupt:
        pass
