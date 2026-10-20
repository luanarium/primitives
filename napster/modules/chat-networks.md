# `napster/chat/networks.py` -- the address grammar

**Role.** Data, almost entirely: networks, channel addresses, and the
catalogue of channels the sandbox offers. The *vocabulary* the behaviour
needs, which is also the vocabulary the **user types** and the operator edits.

**In the primitive.** Not lifted. `BRIEF.md` §8 carries the grammar and the
reason for it.

## Why an address grammar at all

**The client parses its own slash commands and answers an unrecognised one
itself** -- `Unknown Command '%s'!` is in `napster.exe`. So there is no
`/irc connect` to be had at any price. Of the commands it does know,
`/join <channel>` is the one whose argument is free text and reaches the
server verbatim as a 400. **So the network has to ride inside the channel
name.**

```
/join #win32              a known channel: the catalogue says EFnet
/join #windows@libera     explicit, for anything not in the catalogue
/join libera/#windows     the other way round, tolerated
```

`@` is the separator because it is legal in a Napster nick but has **no
meaning in a channel name**, and it is what everyone already reads as "over
there" (`jid@domain`, `user@host`).

## The safety rule

**A name that resolves to no network is an ordinary sandbox channel and is
never bridged.** Resolution failure means local, never a guess at somebody's
network. That default matters twice: `#Lobby` must stay local, and a typo must
not silently open a connection to someone's ircd.

`parse_address` only recognises the `network/#channel` form for networks it
*knows*, because otherwise `#a/b` reads as a network called `#a`.

## Findings encoded here

- **A network name is typed into `/join`**, so it is validated as lowercase
  letters, digits, `.`, `-`, `_` and nothing else. `validate()` says so in
  those words.
- **`services` is a fact the user has to be told rather than discover by
  losing a nick.** EFnet has no NickServ at all. It is a field on `Network`
  because the greeting and the console both read it.
- **`password_env` is preferred over `password`**, because the config file is
  plain YAML in the operator's home directory and is readable by anything that
  can read their files. `password` is still accepted -- telling someone they
  may not write a password in their own config file is not the tool's
  business -- and is written back as they gave it. `secret()` never logs and
  never echoes.
- **`sasl` is preferred over NickServ IDENTIFY where it exists**, because it
  authenticates *before* the nick is taken.
- **Port 0 means "the usual one"**: 6697 with TLS, 6667 without.
- **A channel's `note` becomes the sandbox channel's topic**, which is how it
  reaches the client's own channel list. The notes are not decoration: `#win32`
  and `#winprog` are nearly silent now, and somebody arriving from a museum
  exhibit should know that *before* they type.
- **`with_known` lets a configured network replace a built-in of the same
  name**, rather than fighting it -- the operator may well have a server of
  their own to point `efnet` at.
- **`coerce()` is shared by both front ends**, because `nim-config add network
  port=6697` and `network add` typed into the client's chat tab both arrive as
  strings.

## Lifting it
Lift `parse_address` and the safety rule. The catalogue is this project's
editorial choice and should be re-made rather than copied.
