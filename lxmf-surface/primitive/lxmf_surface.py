"""A web, chat and social surface over LXMF: the whole substrate in one file.

What this is
------------
Reticulum routes encrypted packets and discovers paths. LXMF delivers a message
from one identity to another over it, with acknowledgement and store-and-forward.
Neither knows what is in the payload. Everything above that -- a feed, a channel,
a reaction, a page, a shared index -- is application logic, and this file is a
condensation of that logic as it was built and tested.

The shape, in one paragraph: every payload is a **signed JSON event**; events are
written to an **append-only store** before anything is notified; an in-process
**bus** carries only "something new arrived"; **topics** are `kind/name` strings
so a feed and a chat channel are the same construct; **protocol adapters** turn
a client's wire format into events and back and never talk to each other; and
dissemination is **ask, not flood** -- a peer tells you what it holds and you
fetch what you are missing, through a gate that verifies everything.

Why an event carries its own signature when LXMF already signs the message:
LXMF's signature covers a message from one sender to one recipient. An event
forwarded by a third party, replayed out of store-and-forward, or carried across
a federation boundary has to stay verifiable by its *author*, so it signs itself.
Adopting LXMF's message fields does not mean adopting its signature.

Running it
----------
Standard library only. With `rns` installed the real Reticulum construction is
used for hashing and signing; without it, a clearly-labelled local signer stands
in so every invariant below is still checkable. `smoke_test.py` runs the
conformance checks and prints what it saw.

    python3 smoke_test.py

Sections are in dependency order, so lifting a part rather than the whole file
means taking a prefix. The last section is the only one that imports Reticulum.

    1  Kinds and delivery classes
    2  Identity: hashing, signing, verifying
    3  Events: canonical bytes, build, verify
    4  Filters
    5  The append-only store
    6  The bus
    7  The surface: the accept gate and the pending pen
    8  Social: posts, comments, reactions
    9  Per-author versions, for things that are replaced
   10  Shared indexes, and fetching bytes by key
   11  Room and channel membership
   12  Chat adapters
   13  Gossip: have, diff, get
   14  The LXMF carrier
"""

import hashlib
import hmac
import json
import os
import sqlite3
import time

__all__ = [
    "KINDS", "ASYNC", "LIVE", "EPHEMERAL", "delivery_of", "kind_name",
    "Identity", "canonical", "build", "verify", "topic_of", "dumps", "loads",
    "fields_for", "read_fields", "Filter", "Store", "Bus", "Surface",
    "Carrier", "LoopbackCarrier", "LxmfCarrier",
    "post", "comment", "react", "retract", "posts", "comments", "thread",
    "reactions", "feeds", "feed_topic", "latest_versioned", "next_version",
    "Index", "fetch_key", "members", "channel_topic", "channel_of",
    "nick_for", "have", "diff", "get",
]


# -- 1. Kinds and delivery classes ---------------------------------------
#
# Delivery follows the kind of event, not the caller's preference. This is the
# one registry; an adapter or plugin may not add to it, because a kind is a
# claim about how the whole surface treats a payload.

ASYNC = "async"          # handed to LXMF's delivery, store-and-forward, propagation
LIVE = "live"            # to the recipient's app logic, held there until its client is up
EPHEMERAL = "ephemeral"  # worth nothing once missed, so never stored and never retried

KINDS = {
    1: ("message", LIVE),
    2: ("post", ASYNC),
    3: ("mail", ASYNC),
    4: ("comment", ASYNC),
    5: ("name claim", ASYNC),
    6: ("transfer", ASYNC),
    7: ("share index", ASYNC),
    8: ("site manifest", ASYNC),
    9: ("subscription", ASYNC),     # reserved, bound to nothing; see DISSEMINATION.md
    10: ("presence", EPHEMERAL),
    11: ("annotation", ASYNC),
    12: ("collection", ASYNC),
    13: ("room", LIVE),
    15: ("reaction", ASYNC),
    200: ("app update", EPHEMERAL),
}
DEFAULT_KIND = 1

MESSAGE, POST, MAIL, COMMENT, NAME_CLAIM = 1, 2, 3, 4, 5
TRANSFER, SHARE_INDEX, SITE_MANIFEST = 6, 7, 8
PRESENCE, ANNOTATION, COLLECTION, ROOM, REACTION = 10, 11, 12, 13, 15


def kind_name(kind):
    return KINDS.get(kind, ("unknown", ASYNC))[0]


def delivery_of(kind):
    """An unknown kind reads as `async` rather than being dropped.

    A newer peer publishing a kind this build has never heard of should have its
    event stored and passed on, not discarded: the signature still holds and a
    later build will know what it is.
    """
    return KINDS.get(kind, ("unknown", ASYNC))[1]


# -- 2. Identity: hashing, signing, verifying ----------------------------
#
# Two hashes exist and they are NOT interchangeable. A peer's **delivery
# destination hash** is where a message is sent. Its **identity hash** is what an
# event's `author` holds and what a signature is checked against. Reticulum's
# `Identity.recall` is keyed by the *destination* hash, so the public key an
# author needs comes from the announce that carried the identity and never from
# a recall on the author field. Conflating the two produces messages that arrive
# and cannot be verified, which reads as a signing bug and is not one.

class Identity:
    """An author's keypair, and the hash other instances know it by.

    With `rns` importable this wraps a real `RNS.Identity`: Ed25519 for signing,
    SHA-256 for `full_hash`, and an identity hash that is the first 16 bytes of
    the hash of the public key -- 32 hex characters, permanent, and the same
    every time the same keypair is loaded.

    Without `rns` it falls back to a local signer. **That fallback is not a
    security construction**: it is HMAC-SHA256 under a secret both sides hold,
    present only so the invariants in this file -- canonicalisation, tamper
    rejection, convergence, the pending pen, the gossip diff -- can be checked
    in a process with no Reticulum stack. Never ship it as the signer between
    machines; §14 is where the real one comes from.
    """

    def __init__(self, rns_identity=None, secret=None):
        self._rns = rns_identity
        self._secret = secret
        if self._rns is None and self._secret is None:
            self._rns = _new_rns_identity()
            if self._rns is None:
                self._secret = os.urandom(32)

    # -- how it is made and kept -----------------------------------------

    @classmethod
    def generate(cls):
        return cls()

    @classmethod
    def from_file(cls, path):
        """Load, or make and persist.

        An identity that is regenerated at every start changes its destination
        hash every time: peers cannot find it and stored path tables go stale.
        Persisting it is not an optimisation.
        """
        rns = _rns()
        if rns is not None:
            if os.path.exists(path):
                return cls(rns.Identity.from_file(path))
            identity = cls()
            identity._rns.to_file(path)
            return identity
        if os.path.exists(path):
            with open(path, "rb") as handle:
                return cls(secret=handle.read())
        identity = cls()
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(identity._secret)
        return identity

    @property
    def real(self):
        """True when this is a Reticulum identity rather than the stand-in."""
        return self._rns is not None

    @property
    def hash(self):
        """The identity hash, 32 hex characters.  An event's `author`."""
        rns = _rns()
        if self._rns is not None:
            return rns.hexrep(self._rns.hash, False)
        return hashlib.sha256(b"id" + self._secret).hexdigest()[:32]

    # -- what an event rests on ------------------------------------------

    @staticmethod
    def full_hash(data):
        rns = _rns()
        if rns is not None:
            return rns.Identity.full_hash(data)
        return hashlib.sha256(data).digest()

    def sign(self, data):
        if self._rns is not None:
            return self._rns.sign(data)
        return hmac.new(self._secret, data, hashlib.sha256).digest()

    def validate(self, signature, data):
        if self._rns is not None:
            try:
                return bool(self._rns.validate(signature, data))
            except Exception:                                     # noqa: BLE001
                return False
        expected = hmac.new(self._secret, data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)

    def public(self):
        """What a peer learns from an announce: enough to verify, not to sign.

        Reticulum hands the identity itself over in an announce, so this is that
        object. The stand-in cannot separate the halves, which is one more
        reason it is for tests only.
        """
        return self

    def __repr__(self):
        return "<Identity %s%s>" % (self.hash[:12], "" if self.real else " local")


_RNS = [None, False]


def _rns():
    """Reticulum, if it is installed.  Imported once, lazily, never required."""
    if not _RNS[1]:
        _RNS[1] = True
        try:
            import RNS                                            # noqa: PLC0415
            _RNS[0] = RNS
        except Exception:                                         # noqa: BLE001
            _RNS[0] = None
    return _RNS[0]


def _new_rns_identity():
    rns = _rns()
    return rns.Identity() if rns is not None else None


# -- 3. Events: canonical bytes, build, verify ---------------------------

TOPIC_TAG = "t"

# The fields the signature covers, in the order they are serialised. `id` and
# `sig` are excluded because they are derived from exactly this.
SIGNED = ("author", "content", "created", "kind", "tags", "topic")

# LXMF message fields, so a dispatcher can route without parsing the JSON.
# These sit above LXMF's own registered range of 1-255, which is safer than the
# generic custom slots at 251-253 where two applications would collide.
FIELD_KIND = 0x0100
FIELD_TAGS = 0x0101
FIELD_BUNDLE = 0x0102


class EventError(Exception):
    """A malformed event, or one whose signature does not hold."""


def canonical(event):
    """The bytes the id and the signature are over.

    Sorted keys, no incidental whitespace, UTF-8, every signed field present
    even when empty. **This has exactly one implementation and nothing else may
    serialise an event for signing.** Any difference here makes a signature
    unverifiable on the other side, which is the quietest failure available:
    the message arrives, the bytes look right, and the only symptom is that
    somebody else's events never verify.
    """
    body = {key: event[key] for key in SIGNED if key in event}
    for key in SIGNED:
        body.setdefault(key, _empty(key))
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _empty(key):
    if key == "tags":
        return []
    if key in ("kind", "created"):
        return 0
    return ""


def build(identity, kind, content="", topic=None, tags=(), created=None):
    """Make a signed event.

    `id` is the full hash of the canonical bytes; `sig` is the author's
    signature over those bytes **plus the id**. That mirrors how LXMF hashes and
    signs a message, and it is the only construction used anywhere here.
    """
    tags = [list(tag) for tag in tags]
    if topic and not any(tag and tag[0] == TOPIC_TAG for tag in tags):
        tags.append([TOPIC_TAG, topic])
    event = {
        "author": identity.hash,
        "kind": int(kind),
        "topic": topic or "",
        "created": int(created if created is not None else time.time()),
        "tags": tags,
        "content": content,
    }
    body = canonical(event)
    event["id"] = Identity.full_hash(body).hex()
    event["sig"] = identity.sign(body + bytes.fromhex(event["id"])).hex()
    return event


def verify(event, verifier):
    """True when the id matches the bytes and the signature holds.

    `verifier` is the author's identity as learned from an announce. There is no
    path here that reaches the network: an event whose author is unknown is not
    verifiable *yet*, and §7 holds it rather than dropping it.
    """
    try:
        for key in ("id", "sig", "author"):
            if not isinstance(event.get(key), str) or not event[key]:
                return False
        if verifier is None:
            return False
        if getattr(verifier, "hash", None) != event["author"]:
            return False
        body = canonical(event)
        if Identity.full_hash(body).hex() != event["id"]:
            return False
        signed = body + bytes.fromhex(event["id"])
        return bool(verifier.validate(bytes.fromhex(event["sig"]), signed))
    except (ValueError, TypeError, KeyError):
        return False


def topic_of(event):
    """The topic, from the field or the tag, because both carry it."""
    if event.get("topic"):
        return event["topic"]
    for tag in event.get("tags") or []:
        if tag and tag[0] == TOPIC_TAG and len(tag) > 1:
            return tag[1]
    return ""


def tag_of(event, name):
    for tag in event.get("tags") or []:
        if tag and tag[0] == name and len(tag) > 1:
            return tag[1]
    return None


def dumps(event):
    return json.dumps(event, separators=(",", ":"), ensure_ascii=False)


def loads(text):
    try:
        event = json.loads(text)
    except (ValueError, TypeError):
        raise EventError("not JSON")
    if not isinstance(event, dict):
        raise EventError("not an object")
    return event


def fields_for(event):
    """The LXMF fields that mirror an event, for routing without parsing it."""
    return {
        FIELD_KIND: int(event.get("kind", DEFAULT_KIND)),
        FIELD_TAGS: json.dumps(event.get("tags") or [], separators=(",", ":")),
    }


def read_fields(fields):
    """Read LXMF fields defensively, and let the JSON win.

    `fields` is documented as a dict and arrives as `None`, as bytes, or as
    something else, depending on the sender and the message type -- so it is
    guarded before use. On any mismatch with the payload the **signed event is
    the truth**; these are a routing hint and nothing more.
    """
    if not isinstance(fields, dict):
        return DEFAULT_KIND, [], None
    kind = fields.get(FIELD_KIND, DEFAULT_KIND)
    if not isinstance(kind, int):
        kind = DEFAULT_KIND
    tags = []
    raw = fields.get(FIELD_TAGS)
    if isinstance(raw, (str, bytes)):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                tags = parsed
        except (ValueError, TypeError):
            tags = []
    bundle = fields.get(FIELD_BUNDLE)
    return kind, tags, bundle if isinstance(bundle, str) else None


# -- 4. Filters ----------------------------------------------------------

class Filter:
    """A subscription: kinds, topics, authors, `since`, ids.

    Every field is optional and an absent one matches everything, so an empty
    filter is "all of it" rather than "none of it". The same object is used for
    a local subscription and carried between instances in a gossip request.
    """

    def __init__(self, kinds=None, topics=None, authors=None, since=None,
                 ids=None):
        self.kinds = set(kinds) if kinds else None
        self.topics = set(topics) if topics else None
        self.authors = set(authors) if authors else None
        self.since = since
        self.ids = set(ids) if ids else None

    def matches(self, event):
        if self.kinds is not None and event.get("kind") not in self.kinds:
            return False
        if self.topics is not None and topic_of(event) not in self.topics:
            return False
        if self.authors is not None and event.get("author") not in self.authors:
            return False
        if self.since is not None and int(event.get("created", 0)) < self.since:
            return False
        if self.ids is not None and event.get("id") not in self.ids:
            return False
        return True

    def as_dict(self):
        return {"kinds": sorted(self.kinds) if self.kinds else None,
                "topics": sorted(self.topics) if self.topics else None,
                "since": self.since}

    def __repr__(self):
        return "<Filter kinds=%s topics=%s>" % (self.kinds, self.topics)


# -- 5. The append-only store --------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       TEXT PRIMARY KEY,
    author   TEXT NOT NULL,
    kind     INTEGER NOT NULL,
    topic    TEXT NOT NULL DEFAULT '',
    created  INTEGER NOT NULL,
    tags     TEXT NOT NULL DEFAULT '[]',
    content  TEXT NOT NULL DEFAULT '',
    sig      TEXT NOT NULL,
    received INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS events_topic   ON events (topic, created);
CREATE INDEX IF NOT EXISTS events_author  ON events (author, created);
CREATE INDEX IF NOT EXISTS events_kind    ON events (kind, created);
CREATE INDEX IF NOT EXISTS events_created ON events (created);
"""


class Store:
    """Append-only, and that is not a storage preference.

    An event's id is a hash of its own bytes, so editing a row in place would
    break its signature. A correction is a new event that supersedes the old
    one and a deletion is a tombstone; nothing here updates or deletes.

    Ephemeral kinds are never stored. Presence is worth nothing once missed and
    keeping it would grow the store forever for information that is wrong by the
    time anybody reads it.
    """

    def __init__(self, path=":memory:"):
        self.path = path
        directory = os.path.dirname(path) if path != ":memory:" else ""
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    def add(self, event, received=None):
        """Store it.  False means we already held it, which is not an error.

        A duplicate is the normal case rather than a fault: the same event
        arrives directly and again out of store-and-forward or a gossip pull,
        and ignoring the second copy is exactly what makes that harmless.
        """
        if delivery_of(event.get("kind", 0)) == EPHEMERAL:
            return False
        try:
            self.db.execute(
                "INSERT INTO events (id, author, kind, topic, created, tags, "
                "content, sig, received) VALUES (?,?,?,?,?,?,?,?,?)",
                (event["id"], event["author"],
                 int(event.get("kind", DEFAULT_KIND)), topic_of(event),
                 int(event.get("created", 0)),
                 json.dumps(event.get("tags") or [], separators=(",", ":")),
                 event.get("content", ""), event["sig"],
                 int(received if received is not None else time.time())))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except KeyError as exc:
            raise EventError("event has no %s" % exc)

    def has(self, event_id):
        return self.db.execute("SELECT 1 FROM events WHERE id = ?",
                               (event_id,)).fetchone() is not None

    def get(self, event_id):
        row = self.db.execute("SELECT * FROM events WHERE id = ?",
                              (event_id,)).fetchone()
        return _row_event(row) if row else None

    def query(self, filter=None, limit=200, oldest_first=False,
              by_arrival=False):
        """Events matching a filter, newest first unless asked otherwise.

        `by_arrival` orders by when this instance stored them rather than by
        when their authors made them, and the difference is not cosmetic. Two
        events made in the same second tie on `created`, and the tiebreak is the
        id -- deliberate for a question about authorship, because every instance
        computes the same id and so agrees, and **wrong for replaying a log**,
        where a join and a leave made in one second have to come back in the
        order this node saw them.
        """
        where, params = [], []
        if filter is not None:
            for column, values in (("kind", filter.kinds),
                                   ("topic", filter.topics),
                                   ("author", filter.authors),
                                   ("id", filter.ids)):
                if values:
                    where.append("%s IN (%s)" % (column, ",".join("?" * len(values))))
                    params += sorted(values)
            if filter.since is not None:
                where.append("created >= ?")
                params.append(int(filter.since))
        sql = "SELECT * FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        columns = ("received", "rowid") if by_arrival else ("created", "id")
        direction = "ASC" if oldest_first else "DESC"
        sql += " ORDER BY %s %s, %s %s LIMIT ?" % (
            columns[0], direction, columns[1], direction)
        params.append(int(limit))
        return [_row_event(row) for row in self.db.execute(sql, params)]

    def count(self, filter=None):
        return len(self.query(filter, limit=10 ** 9))

    def topics(self):
        return [row["topic"] for row in self.db.execute(
            "SELECT topic, COUNT(*) AS n FROM events WHERE topic != '' "
            "GROUP BY topic ORDER BY n DESC, topic ASC")]

    def authors(self):
        return [row["author"] for row in self.db.execute(
            "SELECT DISTINCT author FROM events ORDER BY author")]

    def stats(self):
        row = self.db.execute(
            "SELECT COUNT(*) AS events, COUNT(DISTINCT author) AS authors, "
            "COUNT(DISTINCT topic) AS topics, MIN(created) AS oldest, "
            "MAX(created) AS newest FROM events").fetchone()
        return dict(row)


def _row_event(row):
    return {"id": row["id"], "author": row["author"], "kind": row["kind"],
            "topic": row["topic"], "created": row["created"],
            "tags": json.loads(row["tags"]), "content": row["content"],
            "sig": row["sig"]}


# -- 6. The bus ----------------------------------------------------------

DEFAULT_QUEUE = 256


class Subscription:
    """One subscriber's bounded queue.

    Bounded on purpose. A slow adapter must not grow memory without limit or
    stall the instance receiving events, so a full queue **drops its oldest
    notification and counts the drop**. A count that climbs is a real signal
    about a real adapter, which an unbounded queue would hide.
    """

    def __init__(self, bus, filter=None, name=None, size=DEFAULT_QUEUE):
        self.bus = bus
        self.filter = filter
        self.name = name or "anonymous"
        self.size = size
        self.items = []
        self.delivered = 0
        self.dropped = 0

    def offer(self, event):
        if self.filter is not None and not self.filter.matches(event):
            return False
        if len(self.items) >= self.size:
            self.items.pop(0)
            self.dropped += 1
            self.items.append(event)
            return False
        self.items.append(event)
        self.delivered += 1
        return True

    def get(self):
        """The next notification, or None.  Nothing here blocks.

        An async build wraps this in `asyncio.Queue`; the queueing rule above is
        the part that matters and it is the same either way.
        """
        return self.items.pop(0) if self.items else None

    def drain(self):
        out, self.items = self.items, []
        return out

    def close(self):
        self.bus.unsubscribe(self)

    def __repr__(self):
        return "<Subscription %s %s>" % (self.name, self.filter)


class Bus:
    """Store first, bus second.  The order is the contract.

    Every event is written to the store **before** anything is notified, so a
    subscriber woken by a notification can always read the event back. The bus
    carries nothing durable: a subscriber that was not listening missed it and
    goes to the store to catch up, which is one query and not a replay channel.
    """

    def __init__(self, store=None, log=None):
        self.store = store
        self.log = log or (lambda message: None)
        self.subscriptions = []
        self.published = 0
        self.duplicates = 0

    def subscribe(self, filter=None, name=None, size=DEFAULT_QUEUE):
        subscription = Subscription(self, filter, name, size)
        self.subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription):
        if subscription in self.subscriptions:
            self.subscriptions.remove(subscription)

    def publish(self, event):
        """Store it, then notify.  False means it was already held.

        Returning false for an id the store knows is **what stops an echo**: the
        same event arriving over two paths notifies once, and nothing here
        rebroadcasts what it received.
        """
        if self.store is not None:
            fresh = self.store.add(event)
            if not fresh and delivery_of(event.get("kind", 0)) != EPHEMERAL:
                self.duplicates += 1
                return False
        self.published += 1
        for subscription in list(self.subscriptions):
            subscription.offer(event)
        return True

    def counts(self):
        return {"published": self.published, "duplicates": self.duplicates,
                "subscriptions": len(self.subscriptions),
                "dropped": sum(s.dropped for s in self.subscriptions)}


# -- 7. The surface: the accept gate and the pending pen -----------------

PENDING_LIMIT = 256


class Carrier:
    """How events leave and arrive.  Every method is defaulted, so this runs.

    Fill `send` and call `Surface.accept` on what arrives, and the rest of this
    file does not change. §14 is the LXMF implementation; `LoopbackCarrier` below
    wires instances together in one process for tests.

    The method names are the narrow interface the whole design rests on --
    publish, subscribe, send, resolve a name, list peers -- and keeping LXMF
    behind it is deliberate: **do not shape the data around the message format**,
    and do not let any choice here rule out running as a mesh later.
    """

    def start(self, surface):
        return self

    def stop(self):
        return None

    def send(self, peer, event):
        """Deliver one event to one peer.  False when it could not be sent."""
        return False

    def announce(self):
        return None

    def peers(self):
        return []

    def ask(self, peer, path, data):
        """Make a request of one peer and wait for its answer.

        The pull half of §13. Returning None is "we could not ask", which is a
        normal outcome and not an error: the peer that was asleep is exactly the
        one no request reaches.
        """
        return None


class LoopbackCarrier(Carrier):
    """Several surfaces in one process, wired by hand.  For tests and demos.

    It also models the one thing a test of a mesh has to model: an instance can
    be *absent* for a while and catch up later, which is what §13 exists for.
    """

    def __init__(self):
        self.surfaces = {}
        self.offline = set()
        self.delivered = 0
        self.undeliverable = 0

    def join(self, surface):
        self.surfaces[surface.hash] = surface
        for other in self.surfaces.values():
            if other is surface:
                continue
            # An announce is what hands over the key an author is verified
            # against, so joining is where both directions learn it.
            surface.learn(other.identity.public())
            other.learn(surface.identity.public())
        return self

    def send(self, peer, event):
        target = self.surfaces.get(peer)
        if target is None or peer in self.offline:
            self.undeliverable += 1
            return False
        self.delivered += 1
        target.accept(event)
        return True

    def peers(self):
        return [h for h in self.surfaces if h not in self.offline]

    def ask(self, peer, path, data):
        """The responder, in process.  An offline peer answers nothing.

        The caller is identified, because in this carrier the link is the call;
        over Reticulum it is a link that has run `identify`, and §13 says why an
        identified caller is learned rather than checked against a list.
        """
        target = self.surfaces.get(peer)
        if target is None or peer in self.offline:
            return None
        return answer(target.store, path, data,
                      remote_identity=target.identity.public())


class Surface:
    """One instance: an identity, a store, a bus, and the gate between them.

    Association needs no pairing step. Two instances that share a network name
    and a passphrase -- Reticulum's own interface access code -- see each other's
    announces and the surface is one space. There are no accounts, because
    announces are signed.
    """

    def __init__(self, identity=None, store=None, carrier=None, log=None):
        self.identity = identity or Identity.generate()
        self.store = store if store is not None else Store()
        self.bus = Bus(self.store, log)
        self.carrier = (carrier or Carrier())
        self.log = log or (lambda message: None)
        # author identity hash -> the identity an announce handed over. Keyed by
        # IDENTITY hash, which is why this map exists at all: a recall is keyed
        # by destination hash and cannot answer this question.
        self.identities = {self.identity.hash: self.identity.public()}
        self.pending = {}
        self.names = {}
        self.sent = self.received = self.rejected = 0
        self.dropped_pending = 0
        self.carrier.start(self)

    @property
    def hash(self):
        return self.identity.hash

    # -- the narrow interface --------------------------------------------

    def build(self, kind, content="", topic=None, tags=()):
        return build(self.identity, kind, content, topic, tags)

    def publish(self, event, to=None):
        """Local first, then out.

        The instance that produced an event behaves exactly like one that
        received it: into our own store and bus before it is sent anywhere.
        """
        self.bus.publish(event)
        targets = [to] if to else list(self.carrier.peers())
        for target in targets:
            if target == self.hash:
                continue
            if self.carrier.send(target, event):
                self.sent += 1
        return len(targets)

    def subscribe(self, filter=None, name=None):
        return self.bus.subscribe(filter, name)

    def send(self, peer, event):
        return self.carrier.send(peer, event)

    def resolve(self, name):
        """A name belongs to the identity that announced it; first claim wins.

        A name claim is an event, so this is a question about the store rather
        than about a registry somebody has to keep in sync.
        """
        for event in self.store.query(Filter(kinds=[NAME_CLAIM]),
                                      limit=10 ** 6, oldest_first=True):
            if (event.get("content") or "").strip().lower() == name.strip().lower():
                return event["author"]
        return None

    def claim(self, name):
        event = self.build(NAME_CLAIM, content=name, topic="name/%s" % name)
        self.publish(event)
        return event

    def peers(self):
        return [h for h in self.carrier.peers() if h != self.hash]

    # -- learning who is out there ---------------------------------------

    def learn(self, verifier):
        """Keep what an announce handed over, and release anything waiting.

        Handle only announces on LXMF's own delivery aspect. Without that filter
        every Reticulum application on the network -- transport nodes, other
        tools -- arrives here as a peer.
        """
        if verifier is None:
            return 0
        author = getattr(verifier, "hash", None)
        if not author:
            return 0
        self.identities[author] = verifier
        return self._release(author)

    def public_key(self, author):
        return self.identities.get(author)

    # -- the one gate ----------------------------------------------------

    def accept(self, event):
        """Verify, then store, then notify.  The only gate between wire and store.

        It has two callers -- a message that arrived by itself, and an event we
        asked a peer for -- and that is the point. **A peer can tell us what it
        holds; whether it is true is decided here and nowhere else.**
        """
        author = event.get("author")
        key = self.public_key(author)
        if key is None:
            return self._hold(event, author)
        if not verify(event, key):
            self.rejected += 1
            self.log("dropped an event whose signature does not hold (author %s)"
                     % (author or "?")[:16])
            return False
        self.received += 1
        return self.bus.publish(event)

    def _hold(self, event, author):
        """An event that outran its author's announce is held, not dropped.

        A verifier's key comes from an announce, and at bring-up the first events
        between two instances routinely arrive before it. Dropping them lost real
        messages silently, because nothing retries -- found by standing two
        instances up and watching three posts in a row disappear. So the event
        waits in a bounded pen and the announce drains it.

        Bounded, because a stranger could otherwise fill memory with events
        signed by nobody: past `PENDING_LIMIT` the oldest is let go, which is the
        same rule the bus applies to a slow subscriber.
        """
        if not author:
            self.rejected += 1
            return False
        waiting = self.pending.setdefault(author, [])
        if not any(e.get("id") == event.get("id") for e in waiting):
            waiting.append(event)
        while sum(len(v) for v in self.pending.values()) > PENDING_LIMIT:
            oldest = next(iter(self.pending))
            self.pending[oldest].pop(0)
            self.dropped_pending += 1
            if not self.pending[oldest]:
                del self.pending[oldest]
        self.log("holding an event from %s until its announce arrives"
                 % author[:16])
        return False

    def _release(self, author):
        waiting = self.pending.pop(author, [])
        key = self.public_key(author)
        kept = 0
        for event in waiting:
            if not verify(event, key):
                self.rejected += 1
                continue
            self.received += 1
            if self.bus.publish(event):
                kept += 1
        if kept:
            self.log("%d held event%s from %s verified once its announce arrived"
                     % (kept, "" if kept == 1 else "s", author[:16]))
        return kept

    def status(self):
        stats = self.store.stats()
        return {"hash": self.hash, "peers": len(self.peers()),
                "events": stats["events"], "authors": stats["authors"],
                "topics": stats["topics"], "sent": self.sent,
                "received": self.received, "rejected": self.rejected,
                "pending": sum(len(v) for v in self.pending.values())}


# -- 8. Social: posts, comments, reactions -------------------------------
#
# The core's, not a plugin's. These are kinds, and a kind is a claim about how
# the whole surface treats a payload -- so a plugin reads them and, where it has
# declared it may, publishes through the core's own calls. An instance has one
# identity, so anything a plugin publishes is published as the operator: the
# core stamps `via` with the plugin's name rather than taking it from the
# content, which is what stops one claiming to be another or to be nobody.

DEFAULT_FEED = "post"
FOR_TAG = "for"      # the event this answers or reacts to
UNDO_TAG = "undo"    # the *add* a reaction removal cancels
VIA_TAG = "via"      # the plugin that made this, stamped by the core
TITLE_TAG = "title"
DELETED_TAG = "del"  # a tombstone
VERSION_TAG = "v"    # a per-author version, for §9


def feed_topic(feed=None):
    """The topic a feed's name means.

    The default feed is the bare `post`, so an instance that never names a feed
    still shares one with everybody else. **Cross-talk is the default rather
    than a thing to switch on**: a Mastodon adapter, an IRC adapter and a web
    view are three windows onto one feed, not three feeds.
    """
    feed = (feed or "").strip().strip("/").lower()
    if not feed or feed == DEFAULT_FEED:
        return DEFAULT_FEED
    return "%s/%s" % (DEFAULT_FEED, feed)


def feed_of(topic):
    topic = (topic or "").strip()
    if topic == DEFAULT_FEED or not topic:
        return DEFAULT_FEED
    if topic.startswith(DEFAULT_FEED + "/"):
        return topic[len(DEFAULT_FEED) + 1:]
    return topic


class Item:
    """One post, comment or reaction, read back out of an event."""

    def __init__(self, event):
        self.event = event
        self.kind = event.get("kind")
        self.text = event.get("content") or ""
        self.title = tag_of(event, TITLE_TAG) or ""
        self.answers = tag_of(event, FOR_TAG)
        self.undoes = tag_of(event, UNDO_TAG)
        self.via = tag_of(event, VIA_TAG)
        self.author = event.get("author")
        self.created = int(event.get("created") or 0)
        self.topic = event.get("topic") or DEFAULT_FEED
        self.deleted = bool(tag_of(event, DELETED_TAG))

    @property
    def id(self):
        return self.event.get("id")

    @property
    def feed(self):
        return feed_of(self.topic)

    @property
    def what(self):
        return {POST: "post", COMMENT: "comment",
                REACTION: "reaction"}.get(self.kind, "kind %s" % self.kind)

    def __repr__(self):
        return "<%s %s>" % (self.what, (self.id or "")[:8])


def _publish(surface, kind, content, topic, tags, via=None):
    tags = list(tags)
    if via:
        tags.append([VIA_TAG, str(via)])
    event = surface.build(kind, content, topic, tags)
    surface.publish(event)
    return Item(event)


def post(surface, text, feed=None, title=None, via=None):
    """Write a post.  The feed exists because somebody wrote in it."""
    text = (text or "").strip()
    if not text and not (title or "").strip():
        raise ValueError("a post needs something in it: text, or at least a title")
    tags = [[TITLE_TAG, str(title).strip()]] if title else []
    return _publish(surface, POST, text, feed_topic(feed), tags, via)


def comment(surface, target, text, via=None):
    """Answer a post or another comment, **on that post's own topic**.

    The topic comes from the thing being answered rather than from the caller,
    so a comment cannot land in a feed its post is not in. One subscription
    therefore carries a feed and its replies. The cost is stated rather than
    hidden: a busy feed's subscribers receive its comments too, which is right
    for a few instances and would want revisiting at a hundred.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("a comment needs something in it")
    found = _one(surface.store, target)
    if found is None:
        raise ValueError("nothing here carries the id %s, so there is nothing "
                         "to answer" % target)
    return _publish(surface, COMMENT, text, found.topic,
                    [[FOR_TAG, found.id]], via)


def react(surface, target, content, via=None):
    """React.  Reacting again replaces; reacting with nothing takes it back.

    **An OR-Set, so nothing here consults a clock or depends on arrival order.**
    An add is an event and its own id is the add's unique tag; a removal names
    the add it cancels; the set is every add that no removal *from the same
    author* names. That is a question about a set, so two instances holding the
    same events agree however they arrived, and a removal that arrives before
    its add still works -- nothing resurrects, because resolution asks the whole
    set rather than replaying it.

    Why it is not latest-wins: `created` is a second, and reacting then changing
    your mind happens well inside one, so a tie is the normal case rather than
    the rare one. Breaking it by id makes every instance agree on an answer as
    likely to be the *first* reaction as the last -- agreement without
    correctness. There is no total order to be had from the stack, and that is
    structural: a datagram mesh with no consensus and no privileged node. A
    propagation node is not a sequencer; it is content-addressed and its
    `received` is its own clock.

    Replacing is a removal and an add, done by the verb rather than asked of the
    caller. The data type stays honest and the convenience lives here: if some
    other client ever leaves two adds standing, both are shown, because that is
    what the set says.
    """
    found = _one(surface.store, target)
    if found is None:
        raise ValueError("nothing here carries the id %s, so there is nothing "
                         "to react to" % target)
    content = (content or "").strip()
    last = None
    for add in _adds(surface.store, found.id, author=surface.hash):
        last = _publish(surface, REACTION, "", found.topic,
                        [[FOR_TAG, found.id], [UNDO_TAG, add.id]], via)
    if not content:
        return last if last is not None else _publish(
            surface, REACTION, "", found.topic, [[FOR_TAG, found.id]], via)
    return _publish(surface, REACTION, content, found.topic,
                    [[FOR_TAG, found.id]], via)


def retract(surface, target, via=None):
    """Take back whatever reaction we have on a target."""
    return react(surface, target, "", via)


def delete(surface, target):
    """A tombstone.  The store is append-only, so nothing is removed.

    A superseded post stays readable, which is the difference between an edit
    and a loss. Only the author's own tombstone counts, enforced when reading:
    a target somebody else wrote is not theirs to retract.
    """
    found = _one(surface.store, target)
    if found is None:
        raise ValueError("nothing here carries the id %s" % target)
    return _publish(surface, found.kind, "", found.topic,
                    [[FOR_TAG, found.id], [DELETED_TAG, "1"]])


def _items(store, kinds, topics=None, limit=10 ** 5, by_arrival=False):
    if store is None:
        return []
    found = store.query(Filter(kinds=list(kinds), topics=topics), limit=limit,
                        oldest_first=True, by_arrival=by_arrival)
    return [Item(event) for event in found]


def _one(store, id):
    """One post or comment by id, or by a unique prefix of one.

    A prefix, because an id is 64 characters and every listing shows the first
    twelve: a command that printed an id it would then refuse could not be used
    from its own output. Exact wins over prefix, so a full id never becomes
    ambiguous as the store grows.
    """
    if store is None or not id:
        return None
    event = store.get(id)
    if event is None:
        event = _by_prefix(store, id)
    if event is None or event.get("kind") not in (POST, COMMENT):
        return None
    found = Item(event)
    return None if found.deleted else found


def _by_prefix(store, prefix):
    prefix = (prefix or "").strip().lower()
    if len(prefix) < 4:
        return None
    found = [i.event for i in _items(store, (POST, COMMENT))
             if (i.id or "").startswith(prefix)]
    if len(found) > 1:
        raise ValueError("%d events start with %s, so it does not say which "
                         "one. Use more of the id" % (len(found), prefix))
    return found[0] if found else None


def _tombstoned(items):
    """The ids their own author has deleted.

    Authorship is checked here rather than trusted: a peer cannot delete
    somebody else's post by publishing a tombstone for it. A set question, so
    posts and comments were already convergent before reactions became one.
    """
    by_id = {item.id: item for item in items if not item.deleted}
    out = set()
    for item in items:
        if not item.deleted or not item.answers:
            continue
        target = by_id.get(item.answers)
        if target is not None and target.author == item.author:
            out.add(item.answers)
    return out


def posts(store, feed=None, limit=10 ** 5):
    """Posts, newest first, tombstoned ones gone.

    Sorted by `created`, which means two posts made in the same second can show
    in different orders on two instances. That is cosmetic -- display order --
    where the same ambiguity in a reaction was not.
    """
    topics = [feed_topic(feed)] if feed is not None else None
    items = _items(store, (POST,), topics, limit, by_arrival=True)
    gone = _tombstoned(items)
    out = [i for i in items if not i.deleted and i.id not in gone]
    return sorted(out, key=lambda i: i.created, reverse=True)


def comments(store, target=None, limit=10 ** 5):
    """Comments, oldest first, because a conversation reads forwards."""
    items = _items(store, (COMMENT,), None, limit, by_arrival=True)
    gone = _tombstoned(items)
    out = [i for i in items if not i.deleted and i.id not in gone]
    if target is not None:
        out = [i for i in out if i.answers == target]
    return sorted(out, key=lambda i: i.created)


def thread(store, root, limit=10 ** 5):
    """Every comment under a post, including replies to replies.

    Flat and in reading order rather than nested: a thread is a chain of ids and
    no tree is stored. The walk decides *which* comments belong to the thread and
    not their order -- returning them in walk order would put every direct reply
    before any reply-to-a-reply, which is a shape rather than a conversation.
    """
    everything = comments(store, None, limit)
    by_target = {}
    for item in everything:
        by_target.setdefault(item.answers, []).append(item)
    reachable, queue = set(), [root]
    while queue:
        current = queue.pop(0)
        for item in by_target.get(current, []):
            if item.id in reachable:
                continue
            reachable.add(item.id)
            queue.append(item.id)
    return [item for item in everything if item.id in reachable]


def _reaction_events(store, target=None, limit=10 ** 5):
    found = _items(store, (REACTION,), None, limit)
    if target is not None:
        found = [i for i in found if i.answers == target]
    return [i for i in found if i.answers]


def _adds(store, target, author=None, limit=10 ** 5):
    """The reaction adds that still stand: every add no removal cancels.

    The `(author, undoes)` pairing is what makes a removal the author's own --
    an author cannot undo somebody else's reaction.
    """
    events = _reaction_events(store, target, limit)
    undone = {(i.author, i.undoes) for i in events if i.undoes}
    out = [i for i in events
           if i.text and not i.undoes and (i.author, i.id) not in undone]
    if author is not None:
        out = [i for i in out if i.author == author]
    return out


def reactions(store, target=None, limit=10 ** 5):
    """`{target: {content: [authors]}}` -- every add that still stands."""
    out = {}
    for item in _adds(store, target, limit=limit):
        out.setdefault(item.answers, {}).setdefault(item.text, []).append(
            item.author)
    for counts in out.values():
        for authors in counts.values():
            authors.sort()
    return out


def feeds(store, limit=10 ** 5):
    """Every feed anything was written into, with how many posts.

    Read from the store rather than kept in a list, because a feed is a topic
    and a topic is not a thing anybody creates.
    """
    counts = {}
    for item in posts(store, None, limit):
        counts[item.feed] = counts.get(item.feed, 0) + 1
    return counts


# -- 9. Per-author versions, for things that are replaced ----------------
#
# An OR-Set does not fit a note, because its text is a value to replace rather
# than a set to add to. Those take the other answer: a per-author counter, tag
# `v`. There is exactly one writer -- the author, about their own anchor or their
# own list -- so a counter is a total order of their writes and no clock is
# consulted, which is what amending a note twice inside one second needs.
#
# Highest version wins, and arrival breaks a tie only between two versionless
# events, which only data written before this convention can produce. A new
# write is version 1 and beats every old one, so nothing has to be migrated.
#
# The counter's exposure, stated because it is real: the next version is read
# from the store, so an instance that lost its own earlier events can repeat
# one. Writing once more recovers it, and it is better than a clock that cannot
# tell two writes apart at all.


def next_version(store, kind, author, anchor_tag, anchor):
    highest = 0
    for event in store.query(Filter(kinds=[kind], authors=[author]),
                             limit=10 ** 5):
        if tag_of(event, anchor_tag) != anchor:
            continue
        try:
            highest = max(highest, int(tag_of(event, VERSION_TAG) or 0))
        except (TypeError, ValueError):
            continue
    return highest + 1


def latest_versioned(store, kind, anchor_tag, anchor, author=None):
    """The current write per author for one anchor: highest `v` wins."""
    best = {}
    found = store.query(Filter(kinds=[kind],
                               authors=[author] if author else None),
                        limit=10 ** 5, oldest_first=True, by_arrival=True)
    for event in found:
        if tag_of(event, anchor_tag) != anchor:
            continue
        try:
            version = int(tag_of(event, VERSION_TAG) or 0)
        except (TypeError, ValueError):
            version = 0
        who = event["author"]
        if who not in best or version >= best[who][0]:
            best[who] = (version, event)
    return {who: event for who, (_, event) in best.items()}


# -- 10. Shared indexes, and fetching bytes by key -----------------------
#
# This is the web half, and the rule that makes it work at this scale: **the
# index replicates, the bytes do not**. A row is a few hundred bytes and the
# thing it describes can be gigabytes, so what reaches every instance is the
# knowledge of what exists and who holds it.
#
# An index **announces a version, never a change**, so a missed event costs a
# round trip rather than leaving two indexes that disagree permanently with
# nothing able to notice. It has exactly one writer -- the instance whose files
# it describes -- so there is no merge conflict to resolve; peers merge locally,
# which is what makes a search terminate at once with no slowest peer and no
# deadline to tune.


class Index:
    """Every instance's published rows, merged by author at the highest version."""

    def __init__(self, store):
        self.store = store

    def publish(self, surface, rows, topic="share", version=None):
        """Publish this instance's whole index.  Full state, not a delta."""
        if version is None:
            version = next_version(self.store, SHARE_INDEX, surface.hash,
                                   "scope", topic)
        event = surface.build(
            SHARE_INDEX, json.dumps(rows, separators=(",", ":")), topic,
            [["scope", topic], [VERSION_TAG, str(int(version))]])
        surface.publish(event)
        return event

    def rows(self, topic="share"):
        """The merged view: per author, the rows of their highest version."""
        out = []
        for who, event in latest_versioned(
                self.store, SHARE_INDEX, "scope", topic).items():
            try:
                parsed = json.loads(event.get("content") or "[]")
            except (TypeError, ValueError):
                continue
            if not isinstance(parsed, list):
                continue
            for row in parsed:
                if isinstance(row, dict):
                    row = dict(row)
                    row["author"] = who
                    out.append(row)
        return out

    def holders(self, key, topic="share"):
        return sorted({row["author"] for row in self.rows(topic)
                       if row.get("key") == key})


class FetchRefused(Exception):
    """A fetch that was not allowed to become a file read."""


def fetch_key(index, key, reader, topic="share"):
    """Fetch the bytes behind an index key, and check them against the promise.

    Two rules, both of which exist because breaking either one is a hole:

    **A filename is an index key resolved through the index, or refused --
    never a path.** Nothing in the path opens a file by a name a peer sent, so
    there is no traversal to defend against; a key nobody published is simply
    not a thing that can be asked for.

    **The bytes are checked against what the index promised**, not against what
    the sender claims about them. A row carries the size and digest of the exact
    bytes that will be sent, so a transfer is a pipe and nothing else.
    """
    rows = [row for row in index.rows(topic) if row.get("key") == key]
    if not rows:
        raise FetchRefused("%r is not a key anybody published" % key)
    row = rows[0]
    data = reader(row)
    if data is None:
        raise FetchRefused("no holder answered for %r" % key)
    if row.get("size") is not None and len(data) != int(row["size"]):
        raise FetchRefused("%r is %d bytes and the index promised %s"
                           % (key, len(data), row["size"]))
    if row.get("digest"):
        got = hashlib.sha256(data).hexdigest()
        if got != row["digest"]:
            raise FetchRefused("%r hashes to %s and the index promised %s"
                               % (key, got[:16], str(row["digest"])[:16]))
    return data


# Untrusted content gates at ingestion, per item, defaulting to off, set by a
# person -- and **a grant never replicates**, which is what makes the gate hold
# across instances. An item that arrived by replication is quarantined: still
# catalogued, searchable and readable, which is the point of replicating it,
# but granted nothing. Leaving quarantine is a human act. This is a local table
# on purpose; it is not an event and it has no kind.
class Grants:
    """What an item may do *here*.  Local, never published, default no."""

    def __init__(self):
        self.allowed = {}

    def grant(self, key, what):
        self.allowed.setdefault(key, set()).add(what)

    def may(self, key, what):
        return what in self.allowed.get(key, ())

    def quarantined(self, key):
        return not self.allowed.get(key)


# -- 11. Room and channel membership -------------------------------------
#
# Nothing about a room is allocated: its topic is derived from its name, which is
# what makes create and join the same act. Two people who both join `lunch` are
# in the same room, neither is the one who made it, and neither has to be running
# when the other joins.

JOIN, HERE, LEAVE = "join", "here", "leave"
ROOM_TAG = "room"


def room_topic(name):
    return "room/%s" % (name or "").strip().strip("/").lower()


def join_event(surface, name):
    """Say we are here.  Membership rides the surface, not a link.

    It has to reach an instance *before* any link to that instance exists, which
    is why it is an event and not a control message on a session.
    """
    return surface.build(ROOM, JOIN, room_topic(name), [[ROOM_TAG, name]])


def greeting_for(event, own, greeted):
    """What to say back.  A reply to a join, never to a reply.

    An arriving instance says `join`; every instance already in replies `here`
    exactly once; a departing one says `leave`. The set converges in one round
    trip with nobody reading a log -- and greeting a greeting is how that turns
    into a storm.
    """
    author = event.get("author") or ""
    verb = (event.get("content") or "").strip().lower()
    if not author or author == own or verb != JOIN or author in greeted:
        return None
    return HERE


def members(store, name, own=None):
    """Who is in a room, replayed from the store **in arrival order**.

    Arrival order rather than the authors' timestamps, because a join and a
    leave made in the same second would otherwise come back in id order -- an
    order with nothing to do with which happened -- and would report somebody as
    in a room they left.

    This is a log and says so: an instance that left without saying so is still
    in it. A serving process knows who is actually answering.
    """
    seen = {}
    for event in store.query(Filter(kinds=[ROOM], topics=[room_topic(name)]),
                             limit=10 ** 5, oldest_first=True, by_arrival=True):
        verb = (event.get("content") or "").strip().lower()
        if verb == LEAVE:
            seen.pop(event["author"], None)
        elif verb in (JOIN, HERE):
            seen[event["author"]] = int(event.get("created", 0))
    if own:
        seen.pop(own, None)
    return sorted(seen)


# -- 12. Chat adapters ---------------------------------------------------
#
# An adapter turns a client's wire format into events and back. **Adapters never
# talk to each other**: they publish to and subscribe from the bus, so adding a
# protocol changes none of the existing ones. They also do not share a topic
# prefix, which is the honest limit -- two chat adapters publish the same kind,
# so the wire format already matches, but each owns its own prefix and so they
# do not cross-talk until one is pointed at the other's topic.

CHAT_PREFIX = "irc"


def channel_topic(channel, prefix=CHAT_PREFIX):
    return "%s/%s" % (prefix, (channel or "").lower())


def channel_of(topic, prefix=CHAT_PREFIX):
    if not topic.startswith(prefix + "/"):
        return None
    return topic[len(prefix) + 1:]


def nick_for(author, name=None):
    """A nick derived from the author's identity, never from a claim.

    Authority stays with the server. A remote speaker is attributed from the
    identity that signed the event, so a local nick cannot be impersonated by a
    peer -- and a published row carries no name to lie with, because the name is
    composed by the instance showing it from a claim the surface verified.
    """
    if name:
        return "%s[%s]" % (name, (author or "")[:6])
    return "p%s" % (author or "unknown")[:8]


def say(surface, channel, text, prefix=CHAT_PREFIX):
    """A line from a local client becomes a signed `message` event.

    Chat is a `live` kind, so a held event waits at the *recipient's* instance:
    an event for a channel nobody here has joined is stored and nothing more,
    and a client that joins later reads it out of the store.
    """
    event = surface.build(MESSAGE, text, channel_topic(channel, prefix))
    surface.publish(event)
    return event


def backlog(store, channel, limit=200, prefix=CHAT_PREFIX):
    """What was said in a channel, oldest first, for a client that joined late."""
    return store.query(Filter(kinds=[MESSAGE],
                              topics=[channel_topic(channel, prefix)]),
                       limit=limit, oldest_first=True, by_arrival=True)


# -- 13. Gossip: have, diff, get -----------------------------------------
#
# `publish` sends an event to every peer the author knows **at that moment**, so
# an instance that was asleep, or that had not yet been heard of, never gets it
# and nothing retries. Flooding harder does not fix that; asking does. It also
# closes the case of two instances that have each heard a third but never each
# other, since each pulls from whoever it can reach.
#
# Over the stack's own hosting primitive rather than anything invented here: a
# path-routed request handler, identity-gated, compressing its own responses,
# with anything too large for a packet becoming a resource without this module
# asking. The destination is **derived, not announced** -- this instance's own
# identity under a known aspect -- so anyone who heard our announce can compute
# where to ask and we advertise no second address.

APP, ASPECT = "lxmfsurface", "gossip"
HAVE, GET = "have", "get"

# Bounded both ways, so one exchange cannot be made unboundedly expensive by
# asking.
MAX_HAVE = 2000
MAX_GET = 64


def have(store, ask=None):
    """Every id we hold matching a filter.  **Ids only, never content.**"""
    ask = ask if isinstance(ask, dict) else {}
    found = store.query(Filter(kinds=ask.get("kinds") or None,
                               topics=ask.get("topics") or None,
                               since=ask.get("since") or None),
                        limit=MAX_HAVE)
    return [event["id"] for event in found if event.get("id")]


def diff(store, ids):
    """Which of a peer's ids we do not hold."""
    return [id for id in ids or []
            if isinstance(id, str) and not store.has(id)]


def get(store, ids):
    """The events behind a batch of ids, as signed JSON, **verbatim**.

    Verbatim because the signature covers the bytes: a peer that re-encoded an
    event would hand over something that no longer verifies, which is the right
    failure rather than a puzzling one.
    """
    out = []
    for id in list(ids or [])[:MAX_GET]:
        event = store.get(id) if isinstance(id, str) else None
        if event is not None:
            out.append(dumps(event))
    return out


def sync(surface, peer, ask=None, limit=MAX_HAVE):
    """Pull from one peer through a carrier.  Returns how many we kept.

    Nothing fetched escapes verification: every event goes through
    `Surface.accept`, the same gate as one that arrived by itself.

    Who may ask: an **identified caller is learned, not checked against a list**.
    The first thing a new instance does is ask, which easily beats its own
    announce, so refusing strangers would make catching up a race -- the same
    race that used to drop events at bring-up. An identified link has proved
    possession of the key, and being on this network at all took the shared
    access code. An *unidentified* link gets nothing.
    """
    answer = surface.carrier.ask(peer, HAVE, ask or {})
    if not answer:
        return 0
    missing = diff(surface.store, answer)[:limit]
    kept = 0
    for start in range(0, len(missing), MAX_GET):
        batch = missing[start:start + MAX_GET]
        for raw in surface.carrier.ask(peer, GET, batch) or []:
            try:
                event = loads(raw)
            except EventError:
                continue
            if surface.accept(event):
                kept += 1
    return kept


def answer(store, path, data, remote_identity=None):
    """The responder half.  An unidentified caller gets nothing."""
    if remote_identity is None:
        return None
    if path == HAVE:
        return have(store, data)
    if path == GET:
        return get(store, data)
    return None


# -- 14. The LXMF carrier ------------------------------------------------
#
# The only section that imports Reticulum, and the only one that knows a message
# format exists. Everything above it is arithmetic over JSON and SQLite.
#
# Three constraints come from the stack itself and shape the code rather than the
# configuration:
#
#   * **Reticulum initialises once per process, in the main thread, before any
#     event loop**, because it registers OS signal handlers Python only allows
#     there. Initialise it inside an executor or after `asyncio.run` has started
#     and it fails with "signal only works in main thread of the main
#     interpreter".
#   * **A delivery callback fires in an LXMF thread.** Everything it touches
#     crosses back with `run_coroutine_threadsafe` (for a coroutine) or
#     `call_soon_threadsafe` (for a callback). A coroutine created in that thread
#     is never awaited and fails **silently** -- the callback runs, appears to
#     work, and nothing happens.
#   * **Path discovery blocks.** A send goes through an executor and never runs
#     on the loop.
#
# Two instances cannot both run `AutoInterface` on one host: they fight over the
# discovery port and one dies. Separate network namespaces are how same-machine
# testing works, which is also the shape production has.


class LxmfCarrier(Carrier):
    """Events on LXMF messages, peers from announces.

    Deliberately narrow. LXMF is used for messages and store-and-forward;
    announces, request handlers and bulk transfer are Reticulum's own. Nothing
    above this class knows either exists.
    """

    def __init__(self, storage_path, config_path=None, display_name="surface",
                 propagation_node=None, stamp_cost=None):
        self.storage_path = storage_path
        self.config_path = config_path
        self.display_name = display_name
        self.propagation_node = propagation_node
        self.stamp_cost = stamp_cost
        self.surface = None
        self.router = None
        self.destination = None
        self.known = {}      # identity hash -> delivery destination hash
        self._rns = None

    def start(self, surface):
        import LXMF                                              # noqa: PLC0415
        rns = _rns()
        if rns is None:
            raise RuntimeError("Reticulum is not installed")
        self.surface = surface
        # Once per process, in the main thread, before any event loop.
        self._rns = rns.Reticulum(
            configdir=self.config_path,
            # Two independent instances on one machine otherwise fight over the
            # shared instance socket, which surfaces as "digest received was
            # wrong" and reads like a crypto fault.
            require_shared_instance=False)
        identity = surface.identity._rns
        self.router = LXMF.LXMRouter(identity=identity,
                                     storagepath=self.storage_path)
        self.destination = self.router.register_delivery_identity(
            identity, display_name=self.display_name,
            stamp_cost=self.stamp_cost)
        self.router.register_delivery_callback(self._on_message)
        rns.Transport.register_announce_handler(_AnnounceHandler(self))
        if self.propagation_node:
            self.router.set_outbound_propagation_node(self.propagation_node)
        self.announce()
        return self

    def announce(self):
        """Announce after a random delay at start, then periodically.

        A random 5-30 second delay is what stops every instance announcing at
        once when a partition heals.
        """
        if self.destination is not None:
            self.destination.announce(self.display_name.encode("utf-8"))

    def peers(self):
        return list(self.known)

    def send(self, peer, event):
        """Blocking: path discovery must not run on the event loop.

        `peer` is an identity hash -- an author -- and the delivery destination
        it maps to is what a message is addressed to. The two are not the same
        hash, which is why `known` exists.
        """
        import LXMF                                              # noqa: PLC0415
        rns = _rns()
        where = self.known.get(peer)
        if where is None or self.router is None:
            return False
        address = bytes.fromhex(where)
        if not rns.Transport.has_path(address):
            rns.Transport.request_path(address)
            deadline = time.time() + 20.0
            while not rns.Transport.has_path(address):
                if time.time() > deadline:
                    return False      # fail cleanly; a silent send never arrives
                time.sleep(0.1)
        recalled = rns.Identity.recall(address)
        if recalled is None:
            return False
        destination = rns.Destination(recalled, rns.Destination.OUT,
                                      rns.Destination.SINGLE, "lxmf", "delivery")
        message = LXMF.LXMessage(destination, self.destination, dumps(event),
                                 title="",
                                 desired_method=LXMF.LXMessage.DIRECT)
        # Only has an effect when a propagation node is configured; without one,
        # delivery to an offline peer simply fails.
        message.try_propagation_on_fail = bool(self.propagation_node)
        message.fields = fields_for(event)
        self.router.handle_outbound(message)
        return True

    def ask(self, peer, path, data):
        """The gossip request half, over Reticulum's own request handler.

        Left to the destination project: it is a link, an `identify`, and a
        `request` with a response callback, and it blocks, so it runs off the
        loop like a send. The rules it has to obey are in §13 and are already
        checkable without it.
        """
        return None

    def _on_message(self, message):
        """Fires in an LXMF thread.  Cross back into the loop and do nothing else."""
        try:
            event = loads(message.content_as_string())
        except EventError:
            return
        # The fields are a routing hint; the signed JSON is the truth.
        read_fields(getattr(message, "fields", None))
        self.surface.accept(event)


class _AnnounceHandler:
    """Peers appear through announces, and an announce hands over the key.

    `aspect_filter` is not optional. Without it this is called for announces
    from every Reticulum application on the network -- transport nodes, other
    tools -- and each one arrives as an unexpected peer.
    """

    aspect_filter = "lxmf.delivery"

    def __init__(self, carrier):
        self.carrier = carrier

    def received_announce(self, destination_hash, announced_identity, app_data):
        rns = _rns()
        if announced_identity is None:
            return
        author = rns.hexrep(announced_identity.hash, False)
        self.carrier.known[author] = rns.hexrep(destination_hash, False)
        # This is the only place an author's verifying key comes from: a recall
        # is keyed by destination hash and cannot answer the question.
        self.carrier.surface.learn(Identity(announced_identity))
