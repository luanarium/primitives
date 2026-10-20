# `napster/providers/library.py` -- shares, search, browse, resume

**Role.** The default library provider: an in-memory share index with
period-faithful tokenisation.

**In the primitive.** `Backend.search` / `browse` / `resume` /
`replace_shares` / `clear_shares` as no-op defaults, §7. The index itself is
not lifted -- any real tool brings its own.

## Why the tokenisation is a finding

It mirrors what a period server did -- **split on non-alphanumerics, fold case,
drop stopwords** -- because that is what makes a bare-word search behave the
way the client's users remember. A substring match over whole filenames
behaves noticeably differently and feels wrong immediately.

**`STOPWORDS` comes from OpenNap's own `sample.filter`.** Searching for these
alone matched everything, which is why the original servers dropped them, and
the list is a small artifact in its own right: `napster`, `mp3`, `mp3s`,
`mp3z`, `winamp`, `scour`, `scooby`, `my`, `music`, `download`, `downloads`,
`desktop`, `documents`, `program`, `windows`, `various`, `remix`, `songs`,
single letters, and `01`/`02`/`03`.

## Findings encoded here

- **Index only the last `index_path_depth` path components** (default 2). The
  original did; indexing the whole path makes every file in
  `C:\My Documents\My Music\…` match a search for "documents".
- **Multiple `FILENAME CONTAINS` terms are ANDed** -- `set.intersection` over
  the posting lists. Artist versus title is a client-side fiction; the server
  treats every term identically.
- **A search with no terms returns nothing**, rather than everything.
- **The requester's own files are excluded**, in the loop. This is the one
  that turns a working sandbox into an empty one if missed.
- **`resume()` matches on size *and* `hashing.matches()`**, so a bare hash
  still matches a hyphenated one of the same content.
- **`_hit()` reads `ip` and `link_type` off the registry**, which is exactly
  the method `LocalCollection` overrides because its owners have no sessions.
  That override is the whole seam between a real server and a sandbox.

## Lifting it
Lift `STOPWORDS`, `tokenize()` and `index_path_depth`. They are what make a
search *feel* like the original. The dict-of-sets index is thirty lines and
will be replaced by whatever the next tool already has.
