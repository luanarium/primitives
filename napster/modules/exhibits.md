# `napster/exhibits/` -- the packs

**Role.** The content the client's browser loads, as **manifests** plus the
pages this project wrote. Shipped *inside* the installed package, which is
what makes an install a working museum rather than a server with nothing to
serve.

**In the primitive.** Not applicable. The pages and manifests are in
`pages/`; `pages/README.md` is the full account.

## What is in it

| Pack | Mode | What |
|---|---|---|
| `nim-default` | `local` | the museum's landing page and about page, written here |
| `napster-2000-03` | `forward` | napster.com, 1 March 2000 -- animated wordmark, *"Napster is music at Internet speed."*, *"Download Napster 2.0 Beta 5a!"* |
| `napster-cdnow-2001-02` | `forward` | where the client's "Shop for music at CDNOW" button lands |

**One historic era, deliberately.** A second snapshot would double the surface
for no gain the first does not already demonstrate.

52 kB of manifests, no archived bytes. The whole point: `uvx` the package and
it is a working museum, no checkout and nothing to download first.

## `DESIGN.md` -- the authoring guide

Both site eras recorded as a working guide so a page written now sits natively
in the client's renderer: palettes, type scales, table widths, the spacer-GIF
idiom, navigation construction, voice, the rollover pattern. **Pick one era
and stay in it** -- a slate-blue page with a khaki card is from no year that
existed.

It ends with the rule that matters most: **anything fabricated should be
discoverable as fabricated**, in `pack.json` under `reconstructed` and ideally
visible on the page. The sandbox is worth building because it is honest about
what is real; a convincing forgery of a 2001 page with no marker undermines
the entire exercise.

## Findings encoded in the manifests

- **`upstream.hosts` is the hosts the archive actually has.** The mount name
  is local naming and sending it upstream 404s every file.
- **`assets` is a record, not a shipping list.** It proves what was served
  without holding any of it, lets a warm pass prefetch, and makes a silent
  upstream change visible. A digest mismatch is logged rather than raised.
- **`reconstructed` is exact-path only**, and holds exactly one entry: the
  root `clear.gif`, generated at serve time and never stored.
- **`known_gaps` is five decorative GIFs**, left missing rather than
  approximated.
- **`aliases` must redirect**, never rewrite internally.
- **`sources` records where a written page's facts came from**, with the
  licence and the retrieval date -- and the landing page prints that
  attribution as **plain text rather than a link**, because an outside link
  does not resolve in a sealed sandbox and a dead link is worse than a
  readable URL.
- **The CDNOW chain is two mounts and a redirect**, because the binary holds
  the menu string `&Shop for music at CDNOW` in UTF-16 and **no CDNOW URL at
  all**. Driving the live client under a logging proxy showed it requests
  `shop.napster.com`, which in the era answered 302 to a co-branded CDNOW
  subdomain -- and the archive's 404 rows even preserve the affiliate tag the
  redirect carried, `from=sr-5274506`.

## Lifting it
Lift `DESIGN.md` as-is if the next tool serves period pages. Lift the manifest
schema -- it is the honest way to reference content you have no right to
redistribute.
