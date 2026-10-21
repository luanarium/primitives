# `versions` -- a per-author counter for things that are replaced

**Role.** Resolution for records whose content is a *value to replace* rather
than a set to add to: a note on a page, a titled list.

**In the primitive.** Lifted, as §9.

## What it provides

`next_version` and `latest_versioned`: highest `v` per author per anchor wins.

## What it expects

Exactly one writer per anchor -- the author, writing about their own anchor or
their own list.

## Findings encoded here

- **An OR-Set does not fit a note.** Its text is a value to replace, so these
  take the other answer: a per-author version, tag `v`. Picking one data type
  for both kinds of record would have been wrong twice.
- **One writer means a counter is a total order of their own writes, and no
  clock is consulted** -- which is what amending a note twice inside one second
  needs.
- **Highest version wins, and arrival breaks a tie only between two versionless
  events**, which only data written before the convention can produce. A new
  write is version 1 and beats every old one, so **nothing has to be migrated**.
- **The counter's exposure, stated because it is real:** the next version is
  read from the store, so an instance that lost its own earlier events can
  repeat one. Writing once more recovers it, and it is better than a clock that
  cannot tell two writes apart at all.
- **A published list is the live case.** A note that never leaves an instance
  has only latent divergence; the thing that is published is the one two
  instances can really hold two versions of.
- **The same name and meaning as a shared index's version**, deliberately, so a
  reader of one module can read the other.

## Lifting it

Take §9. The anchor is whatever tag names the thing being replaced.
