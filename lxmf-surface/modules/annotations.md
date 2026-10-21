# `annotations` -- notes on content, and the four states of a reference

**Role.** The operator's own data beside somebody else's content: a tag, a note,
a titled collection. Not lifted as code, but the anchor design is the part worth
carrying.

**In the primitive.** Not lifted. §9 carries the version rule these use; the
two-part anchor is described here and left to the destination project, because
what an anchor points *at* is that project's content model.

## What it provides

An anchor with a **durable** part and an **exact** part, and four resolution
states.

## What it expects

Content that can be named both durably and exactly.

## Findings encoded here

- **An anchor records two parts, and that is the whole design.** A durable part
  (where the thing lives: a host and a path) and an exact part (which bytes:
  a digest and an entry). Resolution tries exact first.
- **The four states are the point**, and a reader is owed the difference:
  `exact` resolved both ways; `carried` resolved durably after the content was
  replaced, and **is marked as carried rather than silently re-pointed**;
  `orphaned` resolved neither way and is **kept and listed** rather than
  deleted; `unresolved` means nothing loaded can answer the question. Losing
  notes to a content upgrade is the failure this exists to prevent.
- **Private by default, published deliberately.** Somebody's own notes stay
  theirs. The thing that leaves an instance is a collection, which is why it is
  the case that needed a version.
- **A received annotation is somebody else's text**: rendered as text and never
  as markup, attributed, and never merged into the operator's own.
- **Annotating grants nothing.** A quarantined item can be annotated freely,
  which is what makes an ingestion gate independent of a reading one. See
  [catalog.md](catalog.md).
- **Resolution state is derived, never stored.** Two sources of truth is the
  bug.

## Lifting it

Write the anchor as two parts from the start. Retrofitting the exact half onto
anchors that only have the durable half is the migration this design exists to
avoid.
