# The pages, and how they reach the client's tabs

The client has three tabs that are web pages: **Home**, **Discover** and
**Help**. This directory holds every page this project put behind them, the
manifests that wire them, and the authoring guide for writing more that sit
natively in the client's renderer.

Nothing archived is in here. Two of the manifests describe pages held by the
Internet Archive and forwarded at request time; the bytes are never stored.

```
pages/
  README.md                     this
  DESIGN.md                     how to write a page that looks native in this renderer
  napster.com/
    index.html                  the landing page: what the client's Home tab shows
    about.html                  what is real and what is not, linked from the rail
  docs.napster.com/
    index.html                  the Discover tab, rendered to a file from the source
    help.html                   the Help tab, rendered to a file from the source
  packs/
    nim-default.pack.json       the landing page's manifest: aliases, slots, sources
    napster-2000-03.pack.json   napster.com, 1 March 2000 -- a manifest, no bytes
    napster-cdnow-2001-02.pack.json   where the client's CDNOW button lands
```

---

## 1. What the client asks for

Captured from a live client with a server bound to port 80 inside the sandbox.
This is the whole request surface; everything else in the Help *menu* is the
31-URL tree in `../BRIEF.md` §3, which the tabs themselves never touch.

```
GET host=www.napster.com path=/client/home.html?02b09
GET host=www.napster.com path=/client/discover.html
GET host=www.napster.com path=/client/help/
```

| Tab | Asks for | This project serves |
|---|---|---|
| Home | `/client/home.html?02b09` | `napster.com/index.html`, the museum's landing page |
| Discover | `/client/discover.html` | `docs.napster.com/index.html`, the documentation, generated from the source at request time |
| Help | `/client/help/` | `docs.napster.com/help.html`, where to put the client and how to run each mode |

**`?02b09` is the build number**, assembled at runtime and absent from the
binary's strings -- static analysis alone would have missed it, and a different
build asks for a different URL. Period napster.com could therefore serve
build-specific home pages. Ignore the query or honour it; do not require it.

**The client never knew these tabs could point anywhere.** What makes a 2001
tab land on a page written now is an **alias** in the pack manifest, and the
alias is a redirect. That is section 3, and it is the one thing in this
document that will cost an afternoon if skipped.

---

## 2. Three facts about the renderer

**The webview is not the client's socket layer.** It is the Windows
WebBrowser/WinINet stack, so it **ignores the SOCKS proxy** the rest of the
client uses and goes by name resolution or by WinINet's own proxy setting.
Clicking Home and Discover with a SOCKS capture proxy running produced *no
proxy traffic at all*. Consequence: the web surface has to be served where the
client can reach it by name, or WinINet has to be proxied; a SOCKS proxy
cannot intercept it.

**Port 80 is the faithful port.** A client reached *by name* asks for
`http://www.napster.com/`, and that means 80, and that needs root. A client
pointed at you through WinINet's proxy does not care what the number is,
because a proxied request names its host in the URL. So: try 80, fall back to
8080/8088/8008/8800, and **say which you took** -- then the instruction you
print matches what is running.

**It is an IE-era engine.** Tables, `<font>`, GIFs, attribute styling. No
flexbox, no grid, no positioning, no CSS custom properties. `DESIGN.md` is the
working guide -- palettes, text classes, table widths, the spacer-GIF idiom,
the rollover pattern, voice -- derived from the two site eras this project
measured, so a page written now sits inside the Home tab and reads as period
rather than as a modern page in costume.

Two practical floors found by reading the pages in the real client:

- **A font floor.** The pages are read in a small embedded window at 640px,
  where HTML `size="1"` is unreadable. Every size was stepped up one, so the
  old body size is now the smallest anything is: captions 1→2, body 2→3,
  headings 3→4. A test asserts no served page contains `size="1"` again.
- **The content column stays at the period width**, about 448–534px.
  Widening it is the fastest way to look wrong, because every period graphic
  is cut to those measures.

---

## 3. Mount per host, and make the alias a redirect

### Per host, not per path

**Archived pages use relative asset URLs.** A pack served under
`/exhibit/foo/` resolves its images in the wrong place; the same pack given
its own hostname sits at a root and works untouched. So the server dispatches
on the **`Host` header** (or, in proxy mode, on the host in the absolute-form
URL, which is the more trustworthy of the two) and every name resolves into
the sandbox.

The hostnames this project uses:

| Host | Serves |
|---|---|
| `napster.com`, `www.napster.com` | the landing page |
| `2000.napster.com` | the March 2000 site, forwarded |
| `docs.napster.com` | the documentation, generated |
| `img.napster.com` | asset host, if a pack references it |
| `shop.napster.com` | a 302, as it answered in the era |
| `napster.cdnow.com`, `gs.cdnow.com` | where that redirect lands, and every image on it |

Plus the ones that must resolve so that nothing escapes:
`server.napster.com`, `server2.napster.com`, `upgrade.napster.com`,
`download.napster.com`, `mail.napster.com`.

### The alias must be a 302

The client asks for `/client/home.html?02b09`; the page lives at `/`.
Resolving that alias **internally** serves the right bytes and breaks every
image: archived HTML uses relative asset URLs, so the browser resolves them
against `/client/` and 404s on all of them. Answering with a **302 to `/`**
makes the browser's base the page's real location.

One line of difference between a blank frame and the site. It is the single
most confusing failure in this whole surface, because the HTML arrives
correctly and nothing in the log looks wrong.

An alias may also name **another host outright**, which is how the Discover
tab ends up on documentation the client never knew about:

```json
"aliases": {
  "/client/home.html":     "/",
  "/client/discover.html": "http://docs.napster.com/",
  "/client/help/":         "http://docs.napster.com/help.html"
}
```

### A mount that owns its name must say so

`authoritative` on a mount means a miss is final. Without it, one 404 is
re-asked of **every other mapped host**: four CDN misses became fifty-two
upstream requests, aimed at servers that never had the file. Archived packs
keep the fall-through -- an asset host like `img.napster.com` genuinely lives
*inside* whichever pack referenced it -- but a live or generated host answers
for itself.

### Two requests arrive per click, whatever you do

The CDNOW button produces two browser windows. Serving the target's bytes
directly under `shop.napster.com` was tried and reverted: **two requests
arrive either way**, so the client calls `ShellExecute` twice and nothing
server-side can change it. The fix is at the URL handler, and
`../BRIEF.md` §5 has the three details that make it work (a directory lock, a
windowless script host, and deleting `ddeexec`).

`shop.napster.com` is therefore mounted as a **redirect**, which is what it
actually answered in the era -- every archived capture of it is a 302, the
earliest on 2001-02-20, five weeks after this client's build date.

---

## 4. The pages in here

### `napster.com/index.html` -- the Home tab

Written for this project, in the March 2000 era's conventions: black page,
`#CCCC99` khaki content card, `#666666` grey rail, Arial only, tables
throughout. Its text is shaped like the repository's README, because a visitor
arriving in the client and a reader arriving at the repo need the same
orientation. Below a rule it continues into a short history adapted from the
Wikipedia article "Napster" (CC BY-SA 4.0).

**The attribution is printed as plain text, not a link.** Outside links do not
resolve in a sealed sandbox, and a dead link is worse than a readable URL.

There was briefly a second mode that put the archived era on `napster.com`
directly with no museum furniture around it. It is gone: it was the same
server with less of it working, and nothing in it reached the page that
explains what any of this is.

#### Serve-time slots

The page carries HTML comment markers expanded when it is served:

| Marker | Fills |
|---|---|
| `<!--nim:media-rail-->` | the FILES block in the left rail |
| `<!--nim:communities-->` | the SOCIALS block in the left rail |
| `<!--nim:media-->` | the body's "Elsewhere" listing (unused by this layout) |

Keeping them **HTML comments** means the page stays hand-editable and renders
correctly in an ordinary browser with nothing substituted, which is what an
operator wants when they are redesigning it. An unknown marker is left alone,
and a broken config renders a visible one-line complaint rather than blanking
the page.

**Only local packs go through expansion.** An archived page is an artifact and
nothing is substituted into it.

What fills those slots is the operator's config, not this project's taste. The
rail is about 128px wide, so a name there carries underscores rather than
spaces or it wraps into porridge. Each row is a real thing elsewhere wearing
the filename it would have had here -- a documentary as an `.avi`, an article
as a `.txt` -- with the real host printed in grey beside it, and the conceit
disclosed **once beneath the block** rather than beside every row: a listing
that apologises four times stops reading as a listing, and looking like files
is the point.

The community rail **ships empty**. No surviving Napster community was found,
and linking something adjacent while calling it one would be exactly the
fabrication this project exists to avoid, so the slot renders an invitation
instead of a blank -- an empty slot should explain itself.

#### Links out of a sealed page

A sealed client reaches nothing, so an `https://` link in a rail is a label,
not a destination: correct, and dead. Making one **openable** is opt-in per
link, and the mechanism is the same one that serves archived pages pointed at
the present day instead: fetch it out here, terminate TLS out here, serve it
over plain http, and rewrite absolute URLs back to the site as http so the
browser does not try to leave.

Two translations, both **deletions rather than inventions**. Nothing is
modernised: a site that needs flexbox or CSS custom properties lays out badly,
and that is the honest result rather than something to paper over.

**Map the asset hosts, not just the page host.** A modern site serves its
pages from one name and its images from several others. Mapping only the first
gives a correct layout with *no pictures at all*, which reads as an engine
failure and is not one. Tested against SpaceHey, which names fourteen hosts:
with the full set mapped, images load -- wordmark, panel logo, album art, the
PayPal button with its card icons.

### `napster.com/about.html`

Four headings: what this is, what is real, what is not, why it matters. It
exists so that the fabrication rule has somewhere to be stated to the person
actually looking at the thing, rather than only in a repository.

### `docs.napster.com/index.html` -- the Discover tab

**Rendered from the source at request time**, not stored. The copy in here is
a render taken for this bundle, so it can be read without running anything;
the live page is generated when the client asks for it.

Six sections: Quick start, Usage, The client, The pages, Chat adapters,
Search and users. Quick start is first because this is what the Discover tab
loads and the first question anyone has is how to run the thing.

Three decisions worth lifting:

- **Code examples are pulled out of the running source by dotted path**, with
  `inspect.getsource`. Nothing is copied into the documentation module, so an
  example cannot drift from the code it describes. A failed extraction prints
  the reason in place of the example rather than rendering an empty block, and
  a test asserts no failure reaches the page.
- `getsource` handles code objects only, and two of the things most worth
  showing are **data** -- an observed-nick list and a table of name shapes. Those
  are located in the file with `ast` instead, **together with the comment block
  above them**, which on a constant is the explanation.
- **Docstrings are stripped from the excerpts.** On a page that already
  explains the thing in prose, repeating the docstring doubles the length and
  halves the point.

An earlier version rendered every module docstring in the package, twenty-one
chapters of it. That was a lot of text that never got round to saying what the
thing does, so it was replaced.

### `docs.napster.com/help.html` -- the Help tab

**Deliberately two things only**: where to put the client, and how to run each
mode. The Help tab is where someone goes when they are stuck, so it holds the
two things they are stuck on and nothing else; a test asserts the
documentation page's other sections have not leaked into it.

It also carries the one instruction an operator needs when something has gone
wrong -- run it again with a capture flag, and read the file before sending it
on -- because a published mode has no harness behind it.

Both pages are generated from the **same table** that lists the installable
modes, so the instructions cannot name a mode that does not exist. A test ties
that table to the mode packages on disk by **equality**, because a row with no
package behind it is as wrong as a package with no row. The table is the
*published* modes, which is why the project's own verification rig is a
paragraph in the Help tab rather than a fourth row offering a command nobody
can install.

---

## 5. Exhibits as manifests: links, not copies

Two of the manifests in `packs/` hold no bytes. An exhibit is a **record of
what a page was and where it came from**; the bytes are forwarded from the
Internet Archive at request time and cached outside the project. The client is
unaffected and cannot tell: it asks `napster.com` for a GIF over plain HTTP on
port 80 and receives a GIF.

That is also why the manifests are small enough to ship *inside* an installed
package, which is what makes an install a working museum rather than a server
with nothing to serve -- no checkout, no content to fetch first.

### `id_` and `im_` keep the archive out of the frame

Wayback's **`id_`** modifier (`/web/<timestamp>id_/<url>`) returns the
*original* bytes -- no toolbar, no banner, no rewritten links -- and **`im_`**
does the same for assets. A page fetched that way needs no cleaning and keeps
its original URLs, so a pack is simply a host → path → file tree that happens
to live somewhere else.

A strip-anything-the-archive-added pass runs anyway, and **only ever
deletes**. A snapshot that redirects to a neighbouring capture can still
arrive wrapped, and a Wayback banner inside the client's Home tab would be the
single most era-breaking thing on screen. A page that arrives clean leaves
unchanged, so the exhibit stays an artifact rather than quietly becoming
yours.

### Five failures to design against

1. **The mount hostname is not the archived hostname.** This project mounts
   the 2000 pack on `2000.napster.com`; the archive has never heard of that
   name. Sending it upstream 404'd every single file **while still returning
   200 to the client**, because the request then fell through to another mount
   and served the landing page -- a total failure that looks like a working
   page. Map the requested host onto one the pack declares in
   `upstream.hosts` *before any URL is built*, and key the cache on the
   archived host too, or each mount alias fetches its own copy and none of
   them matches the manifest.
2. **`www.` folds away.** The archive holds `napster.com` and
   `www.napster.com` as separate URLs with identical bytes; keeping them apart
   splits the cache in half, so a pack warmed under one host then re-fetches
   every asset under the other, cold, from an archive that rate limits. That
   is what made a pack reached by one hostname come up without images while
   the same pack reached by another was fine. Genuinely different hosts stay
   different: `gs.cdnow.com` is not `napster.cdnow.com`.
3. **A refused connection is not a 404.** The archive rate-limits hard and the
   two failures look alike from inside a `try`. **404/403/451 mean the archive
   does not have this and never will; anything else means it would not talk to
   you just now.** Remember only the first. Caching a rate-limit as a
   permanent absence blanked images for the rest of the session the first time
   this ran. A tight loop also returns zero-length bodies that look like
   successful fetches of an empty file, so **an empty body is a failure, not
   content**.
4. **A directory URL has two spellings and the archive stores only the one it
   crawled.** `napster.com` was captured as `/index.html`; `napster.cdnow.com`
   only as `/`. Guessing one and giving up 404s a page that is sitting right
   there. Try both.
5. **A bare directory URL has no file suffix**, so choosing the modifier by
   extension fetches a *page* with the binary modifier and the archive's
   toolbar comes back embedded in the HTML. A directory URL is a page.

Pace the fetches (2.5s) with exponential backoff, and offer a **warm** pass
that pre-fetches everything the manifest records. An exhibit served cold is
dozens of archive requests made while the client is already rendering, and the
rate limiting means images simply do not arrive. Warm once; every later run is
local. Report "not held upstream" and "deferred" **separately**, and say
plainly that deferred items are rate-limiting rather than gaps.

### What a manifest records

| Key | Holds |
|---|---|
| `mode` | `local`, `forward`, `live`, `redirect` or `generated` |
| `snapshot` | the archive timestamp |
| `upstream.template`, `upstream.modifier` | the URL shape, and `id_`/`im_` |
| `upstream.hosts` | **the hosts the archive actually has** -- the mount name is yours |
| `default_host` | what an unmatched host maps onto |
| `aliases` | the client's tab URLs. These must **redirect**, never rewrite internally |
| `assets` | every file a live client pulled while walking the page, with the sha256 and byte length it had when captured |
| `reconstructed` | **exact paths** served from something you made |
| `known_gaps` | files absent from the archive at any snapshot; served as 404 without asking |
| `slots` | the `<!--nim:name-->` markers, local packs only |
| `sources`, `reconstructed` (local) | what was written here rather than archived, and where its facts came from |

`assets` is a **record, not a shipping list**: it proves what was served
without holding any of it, lets a warm pass prefetch, and makes a silent
upstream change visible. A digest mismatch is **logged rather than raised** --
the archive may legitimately serve a neighbouring capture -- but the exhibit is
then no longer the one the manifest describes, and that is worth saying out
loud rather than discovering later in a screenshot.

`reconstructed` is **exact-path only**. There is exactly one entry: the root
`clear.gif`, a 1×1 transparent layout spacer the archive never captured,
generated at serve time and never stored. Structural rather than pictorial, so
synthesising it cannot misrepresent anything -- and it is deliberately *not*
listed under `assets`, because it is not an archive artifact. Matching it by
filename substituted the synthesised spacer for the archived
`images/clear.gif`, which *is* in the archive.

`known_gaps` is five decorative GIFs. **Left missing rather than
approximated**: a gap is honest, a guess is not.

### Forwarding dissolves "walk it to find it"

Static extraction pulled 29 assets out of the page; walking it in a live
client produced 14 more -- rollover variants referenced only from JavaScript
arrays, which surfaced as 404s the moment a real client actually navigated.
Under forwarding those are not gaps at all: an unrecorded path is simply
fetched when something asks for it. The `assets` list became a record of what
has been seen rather than a limit on what can be served.

### Forwarding needs egress, and the client must have none

Not a conflict, but it decides the deployment shape:

> **The fetching process runs outside the seal.** The client reaches it over
> loopback and a Unix socket, and still has no route anywhere.

Inside the namespace, a hosts file maps every museum name to 127.0.0.1 and a
relay on port 80 carries the connection out over a Unix socket -- the
filesystem is shared even though the network is not. Outside, the real server
serves the surface and does the fetching. The client is unchanged and none the
wiser. Assert both ends on every run:

```
egress denied
archive unreachable from inside (correct)
inside GET napster.com/ -> 7619 bytes
archive toolbar present: False
```

---

## 6. No screenshots, and no archived bytes

Verification screenshots were taken into a scratch directory and discarded.
This bundle holds no images of the archived site, of its graphics, or of the
client rendering them -- and no archived page, graphic or stylesheet. Delete
the forwarding cache and nothing is lost.
