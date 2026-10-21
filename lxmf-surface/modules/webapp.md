# `webapp` -- a view over the surface, as plain HTML

**Role.** The web half from the reader's side: pages over the surface's own
model, served to clients that may be twenty years old.

**In the primitive.** Not lifted -- a renderer is a destination project's own
business. The rules are here because each one cost something.

## What it provides

Nothing in the primitive. This brief is the finding set.

## What it expects

A store, and nothing cached.

## Findings encoded here

- **A view over the model, read fresh per request, with nothing cached**,
  because the store is the truth and a cache is a second answer to the same
  question.
- **No JavaScript and no session.** The surface is an append-only store, so a
  page is a query and a render, everything selectable is in the URL, and an
  ordinary GET is the whole protocol. This is also what makes an era client
  work.
- **Everything a peer wrote is escaped.** A received annotation is
  attacker-controlled text and text is all it is rendered as.
- **URL-encoding and escaping are two different jobs, in that order.** A value
  placed in a link is URL-encoded *and then* escaped: the first keeps a tag
  containing `&` from splitting the query, the second keeps it inside its
  attribute. Doing one is a bug that looks like working code.
- **Say `default-src 'none'` and `nosniff` anyway**, because the app writes
  every byte of its own markup and can state that rather than hope.
- **Write every colour twice, the literal first and the custom property
  second.** The era browser this was measured against implements no custom
  properties and **drops every declaration that uses one**: the first capture
  from a real guest came back entirely unstyled. The palette is still edited in
  one place and the literals are generated from it.
- **Layout is not rescued the same way.** That browser has neither grid nor
  flexbox, so the shell falls back to ordinary document flow -- sidebar above
  content, each full width -- which is readable and navigable, and is what no
  JavaScript and semantic markup were for.
- **Under a narrow viewport, scroll a wide table inside itself rather than
  hiding a column**, because a hidden column makes a row lie about its author.
- **A stale screenshot is a claim about the present.** Re-shoot in the same pass
  as the change, or do not keep them.

## Lifting it

Read the escaping and the two-colours rule before writing a template. The rest
is a reference for anybody serving the same model to the same clients.
