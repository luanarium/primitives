# `napster/communities.py` -- the operator's links, and a UCI-style CLI

**Role.** One YAML file, three sections, two front ends. What fills the
landing page's rails, and what IRC networks the chat tab can reach.

**In the primitive.** Not lifted.

## The three sections

| Section | Ships | Why |
|---|---|---|
| `community` | **empty** | no surviving Napster community was found, and linking something adjacent while calling it one would be exactly the fabrication this project avoids. The slot renders an invitation instead of a blank -- an empty slot should explain itself |
| `media` | **with entries** | real things elsewhere wearing the filenames they would have had: a documentary as an `.avi`, an article as a `.txt` |
| `network` | **empty** | the tool knows EFnet and Libera without being told, and an entry with one of those names *replaces* its own rather than fighting it |

## Why UCI

OpenWrt's `uci` is the model because it is the mature convention for exactly
this shape of problem -- **a small typed config tree that both a human and a
script need to edit** -- and because its staged `commit` means a half-finished
edit never reaches a running server.

Unlike `uci` there is no daemon to hold the staged tree, so an edit and its
`commit` belong in one invocation:
`nim-config add media name='Thing.avi' url='…' commit`.

## Findings encoded here

- **Reading hand-edited YAML needs PyYAML; writing does not.** The schema is
  flat and known, so the tool emits it itself and the file stays readable and
  commented. Parsing arbitrary hand-edited YAML is not something to hand-roll,
  and the core stays dependency-free. A missing optional dependency prints the
  one line that fixes it, not a traceback.
- **An absent key means "whatever the tool ships"**; `media: []` means none;
  a present `media:` replaces the defaults entirely. An operator is never
  stuck with someone else's taste.
- **`commit` refuses a tree that would render wrongly.** A bad URL in the rail
  is a dead link in a client that cannot explain why.
- **`forward` is how a link becomes *openable* from a sealed client**, and it
  is off by default and opt-in per link, because "the sandbox is the client's
  whole world" is the rule and reaching out is the exception the operator
  asks for. `forward: true` maps the link's own host; `forward: [a, b, c]`
  maps a set -- **which is usually what you want**, because a modern site
  serves its pages from one name and its images from several others.
- **`local_url()` rewrites only a forwarded link to http.** Anything else
  keeps its real scheme and simply will not open, which is the honest outcome.
- **`to_filename()` applies the constraint a 2001 user actually faced.**
  Windows forbids `<>:"/\|?*`, and a filename that broke the protocol's
  space-separated fields would have been useless, so `:` and `|` become dashes
  -- what people actually typed -- and everything else illegal is dropped rather
  than transliterated.
- **`where` decides rail versus listing.** The rail is about 128px wide, so a
  name there carries underscores rather than spaces or it wraps into porridge,
  and it is rendered in the rail's small sans face rather than the listing's
  monospace.
- **The conceit is disclosed once, beneath the listing**, not beside every
  row: a list that apologises four times stops reading as a listing, and
  looking like files is the point. The real host is printed in grey beside
  each filename, so nothing about where a link goes is hidden.
- **`_emit()` is generic over the dataclass**, writing `name` first and then
  only what differs from the record's own defaults -- which is what keeps a
  hand-edited file readable, and what stops a fourth section meaning a fourth
  copy of the writer.
- **`section_type()` imports the `Network` class inside the function**,
  because the chat side imports this module for `Config` and a module-level
  import would be a cycle.
- **`render_rail` escapes what an operator typed.** It is their file, but it
  reaches a page.

## Lifting it
Lift the UCI shape -- staged tree, dotted keys, explicit `commit`, refuse on
validation -- and the write-without-the-parser trick. Both are reusable well
beyond this.
