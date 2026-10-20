# `napster/chat/greeting.py` -- what the sandbox says on arrival

**Role.** The text the chat tab shows, generated from the network catalogue
rather than typed out.

**In the primitive.** Not lifted. It is editorial, and the editorial decisions
are the point.

## Why a greeting is load-bearing

**The chat tab is the only place in the client where a user can be told
something in their own words and act on it in the same breath**, because the
one command the client passes through verbatim is `/join <channel>`. So the
greeting is not decoration: **it is the entire user interface for the chat
side**, and every line in it is either a command that works as typed or a fact
the user needs before typing one.

## The three facts that earn their lines

- **`#win32` and `#winprog` are nearly silent.** Sending a museum visitor into
  a quiet channel of working programmers with a cheerful hello is a cost borne
  by other people. Say it is quiet, and say to read first.
- **EFnet has no nick services.** Not a footnote: on a network with no
  NickServ a nick is yours only while you are using it, and someone who
  assumes otherwise loses it without being told why.
- **This is a 2001 chat window.** No scrollback worth the name, no tabs, and
  the server owns the channel list. Recommending a real client is honest, not
  a disclaimer -- and HexChat descends from XChat, which is what people
  actually used then, which is the only reason it is in a museum's mouth.

## Findings encoded here

- **No line may contain a newline** -- it would corrupt the frame -- and none
  should need wrapping in the client's channel pane, so they are kept under
  about 76 characters. A test asserts both.
- **Generated from the catalogue**, so a channel added to it is offered and a
  channel removed stops being offered. One source of truth for what the
  sandbox claims is joinable.
- **`arrival()` is not the full greeting.** The sandbox is *not* a member of a
  real IRC channel and must not behave as though it were, so entering a
  bridged channel produces a few **notices to one client** carrying only what
  is true of that room: that the people in it are real, whether it is quiet,
  and whether the network can hold a nick. The full greeting stays for a
  sandbox channel, where the sandbox is a visible member and a greeting from a
  bot is what the room is for.
- **`motd_lines()` is the pointer, not the instructions.** The MOTD is a
  different window and scrolls past at login, so it gets three lines pointing
  at the chat tab and nothing more.
- **Registration steps live here, not in the console**, so the greeting and
  `help register` cannot drift apart.

## Lifting it
Lift the *shape*: generate the text from the catalogue, keep every line under
a frame-safe length, and say the unwelcome facts out loud. The words are this
project's.
