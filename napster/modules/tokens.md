# `napster/tokens.py` -- the field grammar

**Role.** Space-separated positional fields, with double quotes around
anything that may contain spaces. **Quotes are not escaped and there is no
escape to invent.**

**In the primitive.** §2, verbatim apart from dropping `join_all` and
`needs_quotes` from the public surface.

## What it provides
`split(payload, limit=None)`, `join(*fields)`, `quote`, `quoted`, the `Final`
marker, and `as_int(fields, i, default)`.

## What the client expects

- **A lenient-by-position splitter, not a strict grammar.** The spec itself
  records that searching for `a "quoted" string` emits
  `FILENAME CONTAINS "a "quoted" string" MAX_RESULTS 100` and that the
  official server simply rejects it. `shlex` is close and wrong: it raises on
  an unbalanced quote where the original's tolerant garbage-in behaviour has
  to be reproduced. An unbalanced quote runs to end of payload.
- **`limit`** stops splitting and returns the remainder whole. That is the
  shape every message with a trailing free-text field wants -- a chat line, a
  reason, a topic -- and splitting the whole payload corrupts all of them.

## Findings encoded here

- **A filename is quoted always, needed or not.** `quoted()` exists for
  exactly this. A 204 whose filename arrived bare was answered with *"User %s
  is not properly configured. Try again in a few minutes."* and a `Transfer
  Error!`, because the client reads a quoted string at that position and there
  was none. Quoting only what "needs" it is right for a nick and wrong for a
  filename.
- **`Final` makes the decision travel with the value.** `join` quotes a plain
  string when it must, and `needs_quotes` says yes to anything containing a
  quote -- so a value that has had its quotes added deliberately would be
  quoted a second time. `Final` is checked *before* the `str` check, because
  it is one.
- **`quote()` does not escape an interior quote.** Inventing an escape would
  produce bytes no period client could read. A value with an embedded quote
  goes out exactly as the original would have sent it: malformed, and the
  peer's problem.
- **`as_int` never raises and never sizes anything.** A live client sent
  `MAX_RESULTS 4976092`. Never size an allocation or a loop from a wire
  integer.

## Lifting it
Copy it. 120 lines, no dependencies, and every line of it is a finding.
