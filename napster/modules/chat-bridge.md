# `napster/chat/bridge.py` -- the inbound half of an adapter

**Role.** An adapter needs two directions. Outbound is the `on_*` hooks.
**Inbound is this**, handed over once at bind time.

**In the primitive.** Not lifted. The interface is summarised in `BRIEF.md`
§8; a port that wants chat should lift this module as it stands, because every
method is a finding.

## Why it exists

So that an adapter **never formats a wire message**. It deals in nicks,
channels and text; the sandbox turns that into 403/824/205/406/407/410 and
keeps its own channel state consistent. That is the rule that lets the same
adapter code work regardless of which numbers the protocol happens to use.

## The surface

`deliver_public`, `deliver_emote`, `deliver_private`, `remote_join`,
`remote_part`, `remote_quit`, `set_topic`, `kick`, `notice`, `broadcast`,
`ensure_channel`, `force_join`, `force_part`, plus `members` /
`local_members` / `channels` / `session` / `is_local` for introspection.

## Findings encoded here

- **Remote members are the subtle part.** The sandbox is authoritative for
  membership because 408/409 must be answerable whether or not the target has
  a concept of it. So a far-side user is registered as a *remote* session:
  `remote=True`, `send=None`, `origin` set to the adapter. **Skip this and
  your users are invisible to the Napster client and the roster is a lie.**
- **A remote join must never evict a local session.** The nick space is one
  space and the local user is the one actually here; registering a remote
  session over them would take their socket out of every roster. The far-side
  user stays unrepresented rather than impersonated, and says so in the log
  rather than silently.
- **`remote_part` forgets a remote session once it holds no channels**, so the
  roster does not accumulate ghosts.
- **`ensure_channel` makes a room exist before anyone joins it.** That is how
  a target's rooms reach the client's **own channel list** (617/618, 827/828)
  with their topics, so the user enters by double-clicking rather than by
  typing a name they had to be told first.
- **`force_join` works even though the spec has no server-initiated join.**
  The join sequence is 405, 408 per member, 409, 410, and nothing in it refers
  to the 400 that usually precedes it. 401 part is *explicitly* unsolicited,
  so the client already copes with its channel set changing underneath it.
  Used by the console: a command typed in one window that has to take effect
  in another.
- **410 has no setter field.** Napster's topic cannot say who changed it, so a
  setter arrives as a **notice beside the topic** rather than being silently
  dropped. A lossy point handled rather than hidden.
- **A multi-line message is flattened into several, never truncated.** A
  newline would corrupt the frame. `_lines()` also returns `[""]` for empty
  input rather than nothing, so a deliberate blank still arrives.
- **`notice()` uses 404**, which carries notices as well as errors.
- **`kick` sends the explanation *then* the part**, because the client must
  accept an unrequested 401 at any time and the reason has to arrive first to
  be readable.

## Lifting it
Copy it whole. 264 lines, and the five bullets above are each a bug somebody
would otherwise find in a real channel with real people in it.
