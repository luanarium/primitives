# `napster/chat/irc.py` -- the worked example

**Role.** The client's chat tab as a real, configurable IRC client. The
reference implementation of a chat target, and the model for Matrix, XMPP or
anything else.

**In the primitive.** Not lifted -- 915 lines of IRC. `BRIEF.md` §8 carries
every decision in it that generalises.

## It needs no cooperation from the far side

The webchat-gateway pattern: it works against any server, from `miniircd` on
loopback to EFnet, with no bot, no service and no server-side configuration.

## Connections -- the part that generalises

**One connection per (network, logged-in Napster user), opened on demand.**
Nothing dials until someone joins a channel that resolves to a network, and a
network nobody is in has no socket. A user's own connection carries **their
own nick**, so people on IRC see a real participant rather than
`<bridge> nick:`.

**Inbound traffic for a channel is delivered by exactly one connection** -- the
*reader*: the lowest-sorting local member joined to that channel on that
network. It is **computed rather than stored**, so it heals itself when
someone parts, and it is what stops a line being delivered once per logged-in
Napster user. Private messages and notices need no election: they belong to
the connection that received them.

This replaced an earlier always-on observer connection. **On a public network
an idle extra bot sitting in #win32 to listen on everyone's behalf is both
rude and unnecessary** -- the people who are there are already connected.

## The mapping, and its two lossy points

| Napster | IRC |
|---|---|
| 400 / 401 join, part | `JOIN` / `PART` |
| 402 → 403 public | `PRIVMSG #channel` |
| 824 emote | `PRIVMSG` + CTCP `ACTION` |
| 205 private | `PRIVMSG nick` |
| 410 topic | `TOPIC` / `332` -- **IRC carries a setter, Napster does not**, so it arrives as a notice beside the topic |
| 406/407/408 roster | `JOIN` / `PART` / `353` + `366` |
| 829 kick | `KICK` |
| 404 notice | `NOTICE`, and every numeric worth reading |

The second lossy point is multi-line text, flattened rather than truncated.

## Findings encoded here

- **Nick character sets differ.** Napster permits `[]{}-@^!$`, and `@`/`!`
  collide with IRC prefix and mask syntax, so nicks are normalised **in both
  directions**. A leading digit or `-` gets an `n` prefix; 30 characters max.
- **EFnet takes about 15 seconds to register**, because its ident lookup has
  to time out first. Not a bug to chase.
- **EFnet truncates nicks to 9 characters**, so the server may hand back a
  different nick than was asked for -- and the adapter says so in a notice
  rather than letting the user wonder.
- **A network that renames us must not break the echo guard.** The adapter
  tracks its own nicks per connection so it does not deliver its own lines
  back into Napster as if they came from outside.
- **`realname` is honest** -- `nim -- Napster client preservation bridge` --
  because the people on the far side are entitled to know what they are
  talking to.
- **`stop()` is async and says goodbye.** A killed adapter leaves a ghost in a
  real channel until the ircd times it out, and the people in that channel are
  the ones who see it.

## The dependency choice

**`irctokens`**: 50 kB, no dependencies of its own, and the one job it does --
tags, source, params, trailing -- is exactly the job a hand-rolled
`partition(" :")` gets subtly wrong.

Deliberately **not `ircstates`**, whose channel and user state would be a
second authority competing with the sandbox's own; and **not `pydle`**, which
brings its own client, connection and event model to replace a 300-line
adapter. Both were considered and rejected for the same reason: the sandbox
already owns the state that matters.

## Lifting it
Lift the connection model (per-user, on demand, one elected reader) and the
mapping table. Those are protocol-independent and are the two things a Matrix
or XMPP adapter would otherwise get wrong.
