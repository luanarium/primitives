# `napster/docs.py` -- the documentation the client serves itself

**Role.** Two pages, rendered at request time, mounted at
`docs.napster.com`, filling **two of the client's three tabs**.

**In the primitive.** Not lifted. The rendered output is in
`pages/docs.napster.com/`.

| Tab | Asks for | Gets |
|---|---|---|
| Discover | `/client/discover.html` | six sections: Quick start, Usage, The client, The pages, Chat adapters, Search and users |
| Help | `/client/help/` | **only** where to put the client and how to run each mode |

**The client never knew these tabs could point anywhere.** An alias in the
pack manifest redirects them, which is how a 2001 tab lands on a page written
now.

## Findings encoded here

- **Code examples are pulled out of the running source by dotted path**, with
  `inspect.getsource`. Nothing is copied into this module, so an example
  cannot drift from the code it describes. A failed extraction prints the
  reason in place of the example rather than rendering an empty block, and a
  test asserts no failure reaches the page.
- **`getsource` handles code objects only**, and two of the things most worth
  showing are *data* -- an observed-nick list and a table of name shapes. Those
  are located with `ast` instead, **together with the comment block above
  them**, which on a constant is the explanation.
- **Docstrings are stripped from the excerpts.** On a page that already
  explains the thing in prose, repeating the docstring doubles the length and
  halves the point.
- **A font floor, set by what the client's browser is.** These pages are read
  in a small embedded window at 640px, where HTML `size="1"` is unreadable.
  Every size stepped up one, so the old body size is the smallest anything is:
  captions 1→2, body 2→3, headings 3→4. A test asserts no served page contains
  `size="1"` again.
- **The Help tab earns its narrowness.** It is where someone goes when they
  are stuck, so it holds the two things they are stuck on and nothing else,
  and a test asserts the documentation page's other sections have not leaked
  into it. It also carries the one instruction an operator needs when
  something has gone wrong -- run it again with `--capture FILE`, and read the
  file before sending it on -- because a published mode has no harness behind
  it.
- **Both pages are generated from the same `MODES` table** that the mode
  packages are listed in, so the instructions cannot name a mode that does not
  exist. Another test ties that table to the `pyproject.toml` files on disk by
  **equality**, because a row with no package behind it is as wrong as a
  package with no row.
- **That table is the *published* modes**, which is why the project's own
  verification rig is a paragraph in the Help tab rather than a fourth row
  offering a command nobody can install.
- **An earlier version rendered every module docstring in the package**,
  twenty-one chapters of it. That was a lot of text that never got round to
  saying what the thing does, so it was replaced.

## Lifting it
Lift `source_of` / `_assignment` / `strip_docstring` if the next tool wants
documentation that cannot drift. Lift the font floor as a hard rule for
anything this client will render.
