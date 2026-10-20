# `napster/server.py` -- the sandbox core

**Role.** Dispatch, the pre-login echo, framework-owned terminators, level
gating, result caps, and the push routing a provider needs.

**In the primitive.** §11, as `Server` + `Connection` + the `@handles` table.
This is the module the primitive is most faithful to.

## Three responsibilities belong here and nowhere else

**The pre-login echo.** The client sends message 4 and then *blocks forever*
if nothing comes back. A type-13 echo of `"<number>: <payload>"` releases it.
`_ECHO_PRE_LOGIN = frozenset({M.VERSION_CHECK})` -- **only message 4**: echo
the 920 opener and the client refuses the login with
`Login failed (Unexpected command: 13 [920: 1])`. The spec's "echo any
pre-login command" is wrong in both directions, and OpenNap 0.44 never sends
the echo at all, which is why it cannot log this client in unaided. This is
the single most important behaviour in the file. Message 7 has its own answer
(8/9/10) and a live client is content with that alone.

**Terminators.** 202, 213, 217, 409, 830, 617, 827 and the 320/326 counts are
emitted by the framework after a provider's rows, **in a `finally`**. A
provider must not be *able* to hang the client by forgetting one. The comment
in `_search` is the whole lesson: the first version built the rows above the
`try` and lost the terminator to a generator that raised half way through,
which is the same hang in a different place.

**Level gating and caps.** Declared once in the policy table, applied
centrally. A provider cannot forget.

## Findings encoded here

- **A handler that raises must not drop the client.** The original server kept
  talking: log the exception, send `404 server error handling that request`,
  carry on. (Note the ordering in the search path -- the terminator goes out
  first, *then* the 404. The client is released, and only then told.)
- **14 and 15 are accepted and discarded silently**, with no handler at all.
- **An unknown number gets `404 Unknown command code <n>`**, which is what
  OpenNap sends and what the client displays.
- **404 carries notices as well as errors.** `conn.error()` is used for
  `Server <alias> set you as operator on channel <channel>` -- rendered red
  beside real errors, because it is the server's general per-client text
  channel.
- **The pre-login read has a timeout; the post-login read does not.** The
  timeout text (`Idle timeout` via message 0) reaches the user verbatim.
- **Each login stage waits in front of itself**, so the client *draws* the
  sequence rather than arriving at the end of it: `latency.pause("login")`
  before the 3, per MOTD line, before the 214.
- **`spawn()` keeps a reference to the task**, so something that outlives the
  message that started it -- a delayed pong -- cannot be garbage collected
  mid-sleep.
- **On disconnect**: part every channel for the other members, 210 to every
  hotlist watcher, clear the shares, remove from the registry, notify
  presence. In that order.
- **500 sends both 607 and 501**, and the 607 carries `<speed>`: omitting it
  costs an extra 600/601 round trip before the uploader will send 608.
- **751 answers for a socketless user.** If `to_nick` finds nobody, ask the
  library for a `ping_for(nick)` and reply after that long; only if the
  library disclaims the nick is it `ping failed, <nick> is not online`.
- **870 prepends the synthetic directory token to each filename** and stores
  the tuple verbatim.

## Lifting it
Copy the structure: a module-level `{number: handler}` table filled by a
decorator, one `Connection` per socket owning one `Session`, and the three
responsibilities above kept out of the handlers. The handler bodies are short
enough to re-derive; the invariants are not.
