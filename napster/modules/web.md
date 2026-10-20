# `napster/web.py` -- the surface the client browses

**Role.** The pages the client's embedded browser loads, mounted **per host**
on port 80. Local packs, archive forwarding, live forwarding, redirects, and
the dispatcher in front of them.

**In the primitive.** Not lifted -- it is HTTP, not Napster. `pages/README.md`
is the full account; this is the module-level index into it.

## Three things make this unlike every other domain

- **The webview does not use the client's SOCKS proxy.** It is the Windows
  WebBrowser/WinINet stack and goes direct via name resolution, or via
  WinINet's own proxy. So the surface must be served where the client can
  reach it, and a SOCKS proxy cannot intercept it.
- **The client asks for three entry points**, and Home carries the build in
  its query string -- `/client/home.html?02b09` -- assembled at runtime and
  **absent from the binary's strings**.
- **No archived page is stored.** Exhibits are *forwarded* and cached outside
  the project. The client never learns the archive exists: it asked
  `napster.com` for a GIF and got a GIF.

## The five mount kinds

| `mode` | What it is |
|---|---|
| `local` | a directory tree, with `<!--nim:name-->` slots expanded at serve time |
| `forward` | a manifest; bytes fetched from the Internet Archive on demand |
| `live` | the same machinery pointed at the present day |
| `redirect` | a hostname whose only job is a 302 |
| `generated` | rendered at request time (`docs.py`) |

## Findings encoded here

Each of these is a failure that presented as something else:

- **Per host, not per path.** Archived pages use *relative* asset URLs, so a
  pack under `/exhibit/foo/` resolves its images in the wrong place.
- **An alias must redirect, never rewrite internally.** Serving the right
  bytes at `/client/home.html` makes the browser resolve relative images under
  `/client/` and 404 every one. One line, and it is the difference between a
  blank frame and the site.
- **The mount hostname is not the archived hostname.** Sending
  `2000.napster.com` upstream 404'd every file **while still returning 200 to
  the client**, because the request fell through to another mount and served
  the landing page -- a total failure that looks like a working page.
- **`www.` folds away**, or the cache splits in half and a pack reached by one
  name re-fetches everything cold.
- **A refused connection is not a 404.** `(body, definitive)`: 404/403/451 are
  permanent, anything else is "not just now". Caching a rate-limit as an
  absence blanked images for a whole session. An **empty body is a failure,
  not content**.
- **A directory URL has two spellings** and the archive stores only the one it
  crawled. Try both.
- **A bare `/` has no suffix**, so choosing the modifier by extension fetches
  a page as an image and the archive's toolbar comes back embedded.
- **`authoritative` means a miss is final.** Without it four CDN 404s became
  **fifty-two upstream requests**, aimed at servers that never had the file.
- **Absolute-form requests must be normalised.** In proxy mode the browser
  sends `GET http://host/path`, and the host in the URL is more trustworthy
  than the `Host` header.
- **`reconstructed` is exact-path only.** Matching by filename substituted a
  synthesised spacer for the archived `images/clear.gif`, which *is* in the
  archive.
- **`strip_archive_injection` only ever deletes.** Nothing is rewritten in, so
  a page that arrives clean leaves unchanged and the exhibit stays an artifact.
- **A live host must map its asset hosts too.** Mapping only the page host
  gives a correct layout with no pictures, which reads as an engine failure
  and is not one. `live_cluster()` maps a set, and each member rewrites links
  for the whole set.
- **https → http and absolute-self-URLs → http are the only two
  translations**, both deletions. Nothing is modernised.
- **Slots are HTML comments**, so the page stays hand-editable and renders
  correctly with nothing substituted; a broken config renders a one-line
  complaint rather than blanking the page; and **only local packs go through
  expansion**, because an archived page is an artifact.
- **`hosts_line()` includes the hosts an operator asked to forward**, because
  a forwarded link that does not resolve is just a slower way of failing.

## Lifting it
If the next tool serves pages to this client at all, lift: per-host
dispatching, the 302 alias, `authoritative`, the
`(body, definitive)` distinction, and absolute-form normalisation. Those five
are each an afternoon.
