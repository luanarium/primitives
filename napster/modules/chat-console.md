# `napster/chat/console.py` -- the console channel

**Role.** Every chat operation the client has no command for. A pure module: a
command returns reply lines and calls a small set of methods on the adapter.

**In the primitive.** Not lifted.

## Why the console is a *channel*

Because it is the only surface left. The client answers an unrecognised slash
command itself (`Unknown Command '%s'!`), so a custom `/connect` is
unavailable. Two things reach the server verbatim:

- `/join <channel>` -- a 400 carrying free text;
- **anything typed that is not a command at all** -- a 402 public message.

So: join `#irc`, and **every line typed there is a command rather than chat**.
That is a convention from the era the client is from -- a server window you
talk to. Nothing is bridged out of it, and the lines are echoed back by the
sandbox exactly as in any channel, so the window reads as a session
transcript.

## Findings encoded here

- **The same commands work in a private message**, and **that is where a
  password belongs**: the console is a channel, so in a deployment with more
  than one user the line you type is echoed to everyone in it exactly as any
  other public message would be. `help identify` says so rather than leaving
  it to be discovered.
- **`!` and `.` prefixes are stripped if present.** The client eats `/foo`,
  but `!foo` and `.foo` arrive intact and are what a person used to bots will
  try first.
- **The module is pure.** Nothing formats a wire message, nothing opens a
  socket, and the whole surface is testable with a fake adapter -- the same
  rule the providers follow. The adapter contract is nine methods, listed in
  the class docstring, and that list *is* the seam the tests exercise.
- **`words` per command** decides how many tokens stay tokens before the rest
  becomes one free-text tail, so `msg libera #chan hello there` works.
- **An unknown command says so** rather than silently passing the line
  through as chat, and an aliased command is listed once in `help`.
- **A command missing its arguments prints its usage**, which in a window with
  no scrollback is the only documentation there is.

## Lifting it
Lift the idea and the purity rule. A console channel is the right answer for
any client that parses its own commands, and keeping it a pure
line-in/lines-out function is what makes it testable without a client, an
ircd, or a socket.
