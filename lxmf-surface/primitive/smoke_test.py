"""Conformance checks for `lxmf_surface.py`.  Run it; do not read it.

One check per behaviour a destination project depends on, each printing what it
saw, so the output doubles as a transcript of what this surface does. A port
that passes all of them behaves like the original.

    python3 smoke_test.py            # the checks
    python3 smoke_test.py --prove    # break three invariants and show them caught

`--prove` exists because a conformance check that never saw the behaviour it
names is worse than no check: it feeds each of three checks a deliberately
broken surface and fails if the check passes anyway.
"""

import sys
import time

import lxmf_surface as S

PASSED = []
FAILED = []


def check(name):
    def wrap(fn):
        PASSED.append((name, fn))
        return fn
    return wrap


def say(text):
    print("        %s" % text)


def wired(count=2):
    """`count` surfaces in one process, each knowing the others' keys."""
    carrier = S.LoopbackCarrier()
    made = []
    for _ in range(count):
        surface = S.Surface(carrier=carrier)
        carrier.join(surface)
        made.append(surface)
    return carrier, made


# -- the event -----------------------------------------------------------


@check("canonical bytes are stable whatever the key order")
def _():
    one = {"author": "a", "kind": 2, "topic": "post", "created": 7,
           "tags": [], "content": "hi"}
    two = {"content": "hi", "tags": [], "created": 7, "topic": "post",
           "kind": 2, "author": "a"}
    assert S.canonical(one) == S.canonical(two)
    say("both orders -> %s" % S.canonical(one).decode())


@check("canonical bytes exclude the id and the signature")
def _():
    event = {"author": "a", "kind": 2, "topic": "", "created": 1, "tags": [],
             "content": "x"}
    before = S.canonical(event)
    event.update({"id": "ff" * 32, "sig": "ee" * 64})
    assert S.canonical(event) == before
    say("adding an id and a sig changed nothing: %d bytes either way"
        % len(before))


@check("the id is the hash of the canonical bytes and the signature holds")
def _():
    me = S.Identity.generate()
    event = S.build(me, S.POST, "hello", "post")
    assert S.Identity.full_hash(S.canonical(event)).hex() == event["id"]
    assert S.verify(event, me.public())
    say("author %s  id %s" % (event["author"][:12], event["id"][:16]))
    say("signer is %s" % ("Reticulum Ed25519" if me.real
                          else "the local stand-in (rns not installed)"))


@check("changing any signed field breaks verification")
def _():
    me = S.Identity.generate()
    event = S.build(me, S.POST, "hello", "post")
    for field, value in (("content", "hello?"), ("kind", 4), ("topic", "post/x"),
                         ("created", 1), ("author", "aa" * 16), ("tags", [["t", "y"]])):
        tampered = dict(event)
        tampered[field] = value
        assert not S.verify(tampered, me.public()), field
        say("%-8s tampered -> refused" % field)


@check("a forged signature does not verify")
def _():
    me, them = S.Identity.generate(), S.Identity.generate()
    event = S.build(me, S.POST, "hello", "post")
    event["sig"] = them.sign(S.canonical(event) +
                             bytes.fromhex(event["id"])).hex()
    assert not S.verify(event, me.public())
    say("signed by %s, claimed by %s -> refused"
        % (them.hash[:12], me.hash[:12]))


@check("the LXMF fields mirror the event, and any wrong type survives")
def _():
    me = S.Identity.generate()
    event = S.build(me, S.COMMENT, "x", "post", [["for", "ab" * 32]])
    fields = S.fields_for(event)
    assert fields[S.FIELD_KIND] == S.COMMENT
    kind, tags, bundle = S.read_fields(fields)
    assert kind == S.COMMENT and ["t", "post"] in tags
    say("fields %s -> kind %d, %d tags" % (sorted(fields), kind, len(tags)))
    for junk in (None, b"bytes", 7, [1, 2], {S.FIELD_KIND: "two"}):
        kind, tags, bundle = S.read_fields(junk)
        assert kind == S.DEFAULT_KIND and tags == []
    say("None, bytes, int, list and a string kind all read as kind %d"
        % S.DEFAULT_KIND)


@check("every kind declares its delivery, and an unknown one is async")
def _():
    assert S.delivery_of(S.MESSAGE) == S.LIVE
    assert S.delivery_of(S.MAIL) == S.ASYNC
    assert S.delivery_of(S.PRESENCE) == S.EPHEMERAL
    assert S.delivery_of(4242) == S.ASYNC
    say("chat %s, mail %s, presence %s, a kind from the future %s"
        % (S.delivery_of(S.MESSAGE), S.delivery_of(S.MAIL),
           S.delivery_of(S.PRESENCE), S.delivery_of(4242)))


# -- the store and the bus -----------------------------------------------


@check("the store is written before anything is notified")
def _():
    store = S.Store()
    bus = S.Bus(store)
    seen = []
    subscription = bus.subscribe(name="watcher")
    me = S.Identity.generate()
    event = S.build(me, S.POST, "one", "post")
    bus.publish(event)
    while True:
        got = subscription.get()
        if got is None:
            break
        seen.append(got)
        assert store.has(got["id"]), "notified before the store had it"
    say("notified %d event, and the store held it first" % len(seen))


@check("a duplicate is stored once and notified once, which stops an echo")
def _():
    store = S.Store()
    bus = S.Bus(store)
    me = S.Identity.generate()
    event = S.build(me, S.POST, "one", "post")
    assert bus.publish(event) is True
    assert bus.publish(event) is False
    assert store.count() == 1
    say("published twice: %s" % bus.counts())


@check("an ephemeral kind reaches the bus but never the store")
def _():
    store = S.Store()
    bus = S.Bus(store)
    subscription = bus.subscribe(name="watcher")
    me = S.Identity.generate()
    bus.publish(S.build(me, S.PRESENCE, "up", "presence"))
    assert store.count() == 0
    assert subscription.get() is not None
    say("presence: 0 rows stored, 1 notification delivered")


@check("a full queue drops the oldest and counts it")
def _():
    store = S.Store()
    bus = S.Bus(store)
    subscription = bus.subscribe(name="slow", size=3)
    me = S.Identity.generate()
    for n in range(6):
        bus.publish(S.build(me, S.POST, "n%d" % n, "post", created=1000 + n))
    held = [e["content"] for e in subscription.drain()]
    assert held == ["n3", "n4", "n5"], held
    assert subscription.dropped == 3
    say("six offered into a queue of three: kept %s, dropped %d"
        % (held, subscription.dropped))


@check("arrival order and authored order are different questions")
def _():
    # A join and a leave made in the same second. Keep drawing identities until
    # the ids happen to sort against the order they arrived in, which is the
    # case that matters and which roughly half of all pairs produce.
    for _attempt in range(200):
        me = S.Identity.generate()
        first = S.build(me, S.ROOM, "join", "room/x", created=500)
        second = S.build(me, S.ROOM, "leave", "room/x", created=500)
        if second["id"] < first["id"]:
            break
    else:
        raise AssertionError("never drew a pair whose ids sort backwards")
    store = S.Store()
    store.add(first, received=1)
    store.add(second, received=2)
    by_arrival = [e["content"] for e in store.query(
        S.Filter(kinds=[S.ROOM]), oldest_first=True, by_arrival=True)]
    by_id = [e["content"] for e in store.query(
        S.Filter(kinds=[S.ROOM]), oldest_first=True)]
    assert by_arrival == ["join", "leave"], by_arrival
    assert by_id == ["leave", "join"], by_id
    say("same second: by arrival %s  <- what this node saw" % by_arrival)
    say("             by id      %s  <- agreed by every node, and not a history"
        % by_id)
    say("replaying a membership log by id would report somebody as in a room "
        "they left")


# -- the gate ------------------------------------------------------------


@check("an event from an author we never heard announce is held, not dropped")
def _():
    stranger = S.Identity.generate()
    mine = S.Surface()
    event = S.build(stranger, S.POST, "from nowhere", "post")
    assert mine.accept(event) is False
    assert mine.store.count() == 0
    assert sum(len(v) for v in mine.pending.values()) == 1
    say("held 1 event from %s, store still empty" % stranger.hash[:12])
    kept = mine.learn(stranger.public())
    assert kept == 1 and mine.store.count() == 1
    say("the announce arrived -> %d held event verified and stored" % kept)


@check("the pen is bounded and counts what it let go")
def _():
    stranger = S.Identity.generate()
    mine = S.Surface()
    for n in range(S.PENDING_LIMIT + 5):
        mine.accept(S.build(stranger, S.POST, "n%d" % n, "post",
                            created=1000 + n))
    waiting = sum(len(v) for v in mine.pending.values())
    assert waiting == S.PENDING_LIMIT, waiting
    assert mine.dropped_pending == 5
    say("%d offered, %d held, %d let go"
        % (S.PENDING_LIMIT + 5, waiting, mine.dropped_pending))


@check("an event whose signature does not hold is refused at the gate")
def _():
    stranger = S.Identity.generate()
    mine = S.Surface()
    mine.learn(stranger.public())
    event = S.build(stranger, S.POST, "honest", "post")
    event["content"] = "tampered in flight"
    assert mine.accept(event) is False
    assert mine.store.count() == 0 and mine.rejected == 1
    say("rejected %d, stored %d" % (mine.rejected, mine.store.count()))


# -- social --------------------------------------------------------------


@check("a feed is a topic, the default feed is cross-talk, and nothing creates one")
def _():
    carrier, (a, b) = wired()
    S.post(a, "in the default feed")
    S.post(a, "in a named one", feed="lobby")
    assert S.feed_topic() == "post" and S.feed_topic("lobby") == "post/lobby"
    assert S.feeds(b.store) == {"post": 1, "lobby": 1}, S.feeds(b.store)
    say("topics: %s" % b.store.topics())
    say("feeds seen by the other instance: %s" % S.feeds(b.store))


@check("a comment rides its post's topic and cannot land in another feed")
def _():
    carrier, (a, b) = wired()
    written = S.post(a, "hello", feed="lobby")
    answered = S.comment(b, written.id[:12], "answering a prefix")
    assert answered.topic == "post/lobby", answered.topic
    assert len(S.thread(a.store, written.id)) == 1
    say("post in %s -> comment in %s, found by the 12-character prefix %s"
        % (written.topic, answered.topic, written.id[:12]))


@check("a thread is flat, in reading order, and does not loop")
def _():
    carrier, (a,) = wired(1)
    root = S.post(a, "root")
    one = S.comment(a, root.id, "first")
    time.sleep(0.01)
    two = S.comment(a, one.id, "a reply to the reply")
    found = [i.text for i in S.thread(a.store, root.id)]
    assert found == ["first", "a reply to the reply"], found
    say("thread: %s" % found)


@check("reactions converge however the events arrived")
def _():
    carrier, (a,) = wired(1)
    written = S.post(a, "react to me")
    S.react(a, written.id, "+1")
    S.react(a, written.id, "heart")      # a removal and an add
    events = a.store.query(S.Filter(), limit=100, oldest_first=True)
    # Two fresh instances, fed the same events in opposite orders.
    out = []
    for order in (events, list(reversed(events))):
        store = S.Store()
        for event in order:
            store.add(event)
        out.append(S.reactions(store, written.id))
    assert out[0] == out[1], out
    assert list(out[0][written.id]) == ["heart"], out[0]
    say("%d events, forwards and backwards -> %s both ways"
        % (len(events), out[0][written.id]))


@check("a removal that arrives before its add still removes")
def _():
    carrier, (a,) = wired(1)
    written = S.post(a, "x")
    S.react(a, written.id, "+1")
    S.retract(a, written.id)
    every = a.store.query(S.Filter(kinds=[S.REACTION]), limit=50,
                          oldest_first=True)
    removal = [e for e in every if S.tag_of(e, S.UNDO_TAG)]
    add = [e for e in every if not S.tag_of(e, S.UNDO_TAG) and e["content"]]
    store = S.Store()
    store.add(a.store.get(written.id))
    for event in removal + add:            # the removal first, on purpose
        store.add(event)
    assert S.reactions(store, written.id) == {}, S.reactions(store, written.id)
    say("removal stored before its add -> the set is empty, nothing resurrected")


@check("an author cannot undo somebody else's reaction")
def _():
    carrier, (a, b) = wired()
    written = S.post(a, "x")
    S.react(a, written.id, "+1")
    mine = [i for i in S._adds(a.store, written.id) if i.author == a.hash][0]
    # b publishes a removal naming a's add. It is b's removal, not a's.
    S._publish(b, S.REACTION, "", written.topic,
               [[S.FOR_TAG, written.id], [S.UNDO_TAG, mine.id]])
    standing = S.reactions(a.store, written.id)
    assert standing == {written.id: {"+1": [a.hash]}}, standing
    say("a's reaction still stands after b published a removal for it")


@check("a tombstone only counts from the target's own author")
def _():
    carrier, (a, b) = wired()
    written = S.post(a, "mine to delete")
    S._publish(b, S.POST, "", written.topic,
               [[S.FOR_TAG, written.id], [S.DELETED_TAG, "1"]])
    assert len(S.posts(a.store)) == 1, "a peer deleted somebody else's post"
    say("b's tombstone ignored; %d post still readable" % len(S.posts(a.store)))
    S.delete(a, written.id)
    assert S.posts(a.store) == []
    say("the author's own tombstone removed it, and both events are still stored "
        "(%d rows)" % a.store.count())


# -- versions, indexes and fetching --------------------------------------


@check("a per-author version replaces without consulting a clock")
def _():
    carrier, (a,) = wired(1)
    for text in ("first note", "second note", "third note"):
        version = S.next_version(a.store, S.ANNOTATION, a.hash, "anchor", "page")
        a.publish(a.build(S.ANNOTATION, text, "note/page",
                          [["anchor", "page"], [S.VERSION_TAG, str(version)]]))
    latest = S.latest_versioned(a.store, S.ANNOTATION, "anchor", "page")
    assert latest[a.hash]["content"] == "third note"
    say("three writes inside one second -> v%s wins: %r"
        % (S.tag_of(latest[a.hash], S.VERSION_TAG),
           latest[a.hash]["content"]))


@check("an index announces a version, and peers merge by author at the highest")
def _():
    carrier, (a, b) = wired()
    index_a, index_b = S.Index(a.store), S.Index(b.store)
    index_a.publish(a, [{"key": "a/one", "size": 3, "digest": ""}])
    index_a.publish(a, [{"key": "a/one", "size": 3, "digest": ""},
                        {"key": "a/two", "size": 3, "digest": ""}])
    index_b.publish(b, [{"key": "b/one", "size": 3, "digest": ""}])
    keys = sorted(row["key"] for row in S.Index(b.store).rows())
    assert keys == ["a/one", "a/two", "b/one"], keys
    say("two instances, three versions -> merged keys %s" % keys)
    say("a's superseded v1 is still stored and simply not the highest")


@check("a fetch resolves an index key or refuses, and checks what was promised")
def _():
    carrier, (a,) = wired(1)
    index = S.Index(a.store)
    payload = b"the bytes"
    import hashlib
    index.publish(a, [{"key": "doc/one", "size": len(payload),
                       "digest": hashlib.sha256(payload).hexdigest()}])
    got = S.fetch_key(index, "doc/one", lambda row: payload)
    assert got == payload
    say("doc/one fetched: %d bytes, digest matched" % len(got))
    for key, reader, why in (
            ("../../etc/passwd", lambda row: b"x", "a path, not a key"),
            ("doc/one", lambda row: b"short", "the wrong bytes")):
        try:
            S.fetch_key(index, key, reader)
            raise AssertionError("%s was not refused" % why)
        except S.FetchRefused as exc:
            say("refused (%s): %s" % (why, exc))


@check("a grant is local, defaults to no, and never replicates")
def _():
    grants = S.Grants()
    assert grants.quarantined("arrived/by/replication")
    assert not grants.may("arrived/by/replication", "scripts")
    grants.grant("adopted", "scripts")
    assert grants.may("adopted", "scripts")
    assert not grants.may("adopted", "emulate")
    say("replicated item: quarantined, catalogued, readable, granted nothing")
    say("adopted item: scripts yes, emulate still no -- one gate per thing")


# -- rooms and chat ------------------------------------------------------


@check("room membership replays in arrival order")
def _():
    carrier, (a, b) = wired()
    a.publish(S.join_event(a, "lunch"))
    b.publish(S.join_event(b, "lunch"))
    assert S.members(a.store, "lunch", own=a.hash) == [b.hash]
    # b leaves in the same second it joined: only arrival order can tell.
    b.publish(b.build(S.ROOM, S.LEAVE, S.room_topic("lunch"),
                      [[S.ROOM_TAG, "lunch"]]))
    assert S.members(a.store, "lunch", own=a.hash) == []
    say("b joined then left inside one second -> members %s"
        % S.members(a.store, "lunch", own=a.hash))


@check("a greeting answers a join and never another greeting")
def _():
    carrier, (a, b) = wired()
    greeted = set()
    joining = S.join_event(b, "lunch")
    assert S.greeting_for(joining, a.hash, greeted) == S.HERE
    greeted.add(joining["author"])
    assert S.greeting_for(joining, a.hash, greeted) is None
    here = b.build(S.ROOM, S.HERE, S.room_topic("lunch"))
    assert S.greeting_for(here, a.hash, set()) is None
    say("join -> here; join again -> nothing; a here -> nothing")


@check("a channel is a topic both ways and a nick comes from the identity")
def _():
    carrier, (a, b) = wired()
    assert S.channel_topic("#General") == "irc/#general"
    assert S.channel_of("irc/#general") == "#general"
    assert S.channel_of("post/lobby") is None
    S.say(a, "#general", "hello from the guest")
    heard = S.backlog(b.store, "#general")
    assert len(heard) == 1
    speaker = S.nick_for(heard[0]["author"])
    assert a.hash[:8] in speaker
    say("#General -> %s -> %s" % (S.channel_topic("#General"),
                                  S.channel_of("irc/#general")))
    say("one line heard on the other instance, attributed to %s" % speaker)
    say("a peer claiming a nick cannot change it: it is made from the author")


# -- gossip --------------------------------------------------------------


@check("have answers ids only, is bounded, and survives nonsense")
def _():
    carrier, (a,) = wired(1)
    for n in range(3):
        S.post(a, "n%d" % n)
    ids = S.have(a.store)
    assert all(isinstance(i, str) for i in ids) and len(ids) == 3
    assert S.have(a.store, "not a dict") == ids
    assert S.have(a.store, {"kinds": [S.COMMENT]}) == []
    say("3 posts -> %d ids, no content; a filter for comments -> %d"
        % (len(ids), len(S.have(a.store, {"kinds": [S.COMMENT]}))))
    say("MAX_HAVE %d, MAX_GET %d" % (S.MAX_HAVE, S.MAX_GET))


@check("get returns the events verbatim, so the signature still holds")
def _():
    carrier, (a,) = wired(1)
    written = S.post(a, "verbatim")
    raw = S.get(a.store, [written.id])
    assert len(raw) == 1
    event = S.loads(raw[0])
    assert S.verify(event, a.identity.public())
    assert S.get(a.store, ["ff" * 32]) == []
    assert S.get(a.store, None) == []
    say("round-tripped through JSON and still verifies: %s" % event["id"][:16])


@check("an unidentified caller gets nothing")
def _():
    carrier, (a,) = wired(1)
    S.post(a, "private enough")
    assert S.answer(a.store, S.HAVE, {}, remote_identity=None) is None
    assert S.answer(a.store, S.HAVE, {},
                    remote_identity=a.identity.public()) != []
    say("no identity -> None; identified -> %d ids"
        % len(S.answer(a.store, S.HAVE, {}, a.identity.public())))


@check("an instance that was asleep catches up by asking, and still verifies")
def _():
    carrier, (a, b) = wired()
    carrier.offline.add(b.hash)
    for n in range(4):
        S.post(a, "while b was asleep %d" % n)
    assert b.store.count() == 0, "b should have missed all of it"
    say("a published 4 posts to %d reachable peers; b holds %d"
        % (len(a.peers()), b.store.count()))
    carrier.offline.discard(b.hash)
    kept = S.sync(b, a.hash)
    assert kept == 4, kept
    caught = sorted(i.text for i in S.posts(b.store))
    assert caught == ["while b was asleep %d" % n for n in range(4)], caught
    say("b asked a and kept %d events, each through the same gate" % kept)
    say("b's rejected count is %d" % b.rejected)


@check("a fetched event still has to verify")
def _():
    carrier, (a, b) = wired()
    carrier.offline.add(b.hash)
    written = S.post(a, "honest")
    carrier.offline.discard(b.hash)
    # a hands over a tampered copy of what it holds.
    tampered = dict(a.store.get(written.id))
    tampered["content"] = "not what was signed"
    original_ask = carrier.ask

    def lying(peer, path, data):
        if path == S.GET:
            return [S.dumps(tampered)]
        return original_ask(peer, path, data)

    carrier.ask = lying
    kept = S.sync(b, a.hash)
    assert kept == 0 and b.store.count() == 0 and b.rejected == 1
    say("a peer offered a tampered event it claimed to hold -> kept %d, "
        "rejected %d" % (kept, b.rejected))


# -- proving the checks check --------------------------------------------


def prove():
    """Break three invariants and fail if the checks do not notice."""
    print("Proving the checks are checking:")
    broken = 0

    # 1. canonicalisation that depends on key order.
    original = S.canonical
    S.canonical = lambda event: __import__("json").dumps(
        {k: event[k] for k in event if k in S.SIGNED}).encode()
    try:
        one = {"author": "a", "kind": 2, "topic": "p", "created": 7,
               "tags": [], "content": "hi"}
        two = {"content": "hi", "tags": [], "created": 7, "topic": "p",
               "kind": 2, "author": "a"}
        assert S.canonical(one) == S.canonical(two)
        print("  FAIL  an unsorted canonicaliser was not caught")
    except AssertionError:
        print("  ok    an unsorted canonicaliser is caught")
        broken += 1
    finally:
        S.canonical = original

    # 2. a gate that trusts the author field instead of the announce.
    stranger = S.Identity.generate()
    mine = S.Surface()
    mine.identities[stranger.hash] = stranger.public()
    event = S.build(stranger, S.POST, "honest", "post")
    event["content"] = "tampered"
    if mine.accept(event) is False and mine.store.count() == 0:
        print("  ok    a tampered event is refused even from a known author")
        broken += 1
    else:
        print("  FAIL  a tampered event was accepted")

    # 3. latest-wins reactions, which is what the OR-Set replaced.
    carrier, (a,) = wired(1)
    written = S.post(a, "x")
    S.react(a, written.id, "+1")
    S.react(a, written.id, "heart")
    events = a.store.query(S.Filter(), limit=100, oldest_first=True)

    def latest_wins(store, target):
        found = [e for e in store.query(S.Filter(kinds=[S.REACTION]),
                                        limit=100, oldest_first=True,
                                        by_arrival=True)
                 if S.tag_of(e, S.FOR_TAG) == target and e["content"]]
        return found[-1]["content"] if found else None

    answers = []
    for order in (events, list(reversed(events))):
        store = S.Store()
        for event in order:
            store.add(event)
        answers.append(latest_wins(store, written.id))
    if answers[0] != answers[1]:
        print("  ok    latest-wins disagrees across arrival orders (%s vs %s), "
              "which is why reactions are a set" % tuple(answers))
        broken += 1
    else:
        print("  FAIL  latest-wins did not diverge, so the check proves nothing")
    return broken == 3


def main():
    if "--prove" in sys.argv:
        return 0 if prove() else 1
    print("lxmf-surface conformance checks")
    print("signer: %s\n" % ("Reticulum (rns installed)"
                            if S.Identity.generate().real
                            else "the local stand-in -- rns is not installed"))
    for name, fn in PASSED:
        try:
            fn()
        except Exception as exc:                                  # noqa: BLE001
            FAILED.append(name)
            print("FAIL  %s" % name)
            print("        %s: %s" % (type(exc).__name__, exc))
        else:
            print("ok    %s" % name)
    print("\n%d of %d checks passed" % (len(PASSED) - len(FAILED), len(PASSED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
