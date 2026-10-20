# Writing pages that look native

A working guide to the visual and HTML conventions of napster.com, derived from the two packs in
this directory. The goal is that a page written now — an interactive museum exhibit, a curated
essay, a fabricated sub-page — sits inside the client's Home tab and reads as period, not as a
modern page wearing a costume.

Two distinct design eras are documented. **Pick one and stay in it**; they do not mix.

---

## The renderer you are writing for

The client embeds the Windows WebBrowser control (IE-era; under Wine, mshtml + gecko — see
BRIEF.md §6.13). Practical limits:

- **Layout is tables.** No flexbox, no grid, no positioning. Nest tables; that is what the originals do.
- **Styling is attributes**, with a small stylesheet in the 2001 era only. `bgcolor`, `background`,
  `<font face size color>`, `align`, `valign`, `cellpadding`, `cellspacing`, `border`.
- **Spacer GIFs do the measuring.** A 1×1 transparent GIF stretched with `width`/`height` is how
  both eras create gaps. Expect them everywhere (9 uses in 2000, 28 in 2001).
- **Images are GIF.** Animation is animated GIF. Rounded corners, curves, tabs and headings are all
  *pictures of text and shapes*, not CSS.
- **The viewport is narrow.** Content columns are fixed pixel widths around 450–550px; the client's
  pane is not a full browser window.
- Keep JS to the period idiom (image preload / swap). Anything modern will not run.

---

## Era A — March 2000: the dark, boxed layout

*Reference: the `napster-2000-03` pack. It holds no bytes; run `napster-server` and look at `http://2000.napster.com/` in the client.*

The look most people remember: a black page, a single khaki content card floating on it, grey nav
rail, and the animated wordmark top-left.

### Palette

| Role | Value |
|---|---|
| Page background | `#000000` black, plus `images/bk.gif` tile |
| Content panel | `#cccc99` khaki / olive |
| Nav rail + chrome | `#666666`, `#777777`, `#999999`, `#4f4f4f` greys |
| Body text | `#000000` |
| Links | `#000099` navy · visited `#336699` · active `#FFCC00` amber |
| Accent panel | `#99cccc` pale cyan ("MP3 Files" bar) |

### Type

One face only: `<font face="Arial, Helvetica, sans-serif">`. Sizes are `2` for body, `3` for the
lead line, `-2` for the copyright footer. Bold via `<b>`; italics rare.

### Structure

```html
<body bgcolor="#000000" background="images/bk.gif" text="#000000"
      link="#000099" vlink="#336699" alink="#FFCC00">
```

Seven tables, nested, at fixed widths: outer `546`, inner `534`, content `398`, insets `300`.
Composition, top to bottom:

1. **Animated wordmark** (`images/napster.gif`, 20 frames) top-left, over black.
2. **Tab strip** — `HOME` highlighted, `WHAT IS NAPSTER?` beside it; tabs are images, not text.
3. **"AVAILABLE MUSIC >>"** strip with a cyan `MP3 Files` field, and the `DOWNLOAD` curve graphic
   bleeding over the top-right corner with the animated arrows (`images/arrows.gif`, 11 frames).
4. **Left nav rail** on grey: WHAT IS NAPSTER? / DOWNLOAD / JOBS / COMPANY / GROUNDZERO, a gap,
   then HELP ? / TERMS OF USE. Each item is its own `images/left-*.gif`.
5. **Khaki content card** — lead sentence, a big underlined download link, then body paragraphs.
6. **Centred copyright** in `size="-2"`.

### Voice

Short, declarative, slightly evangelical. *"Napster is music at Internet speed."* ·
*"Are you an artist who wants in on the revolution?"* · *"the world's largest online music
community"*. The download call to action is the loudest element on the page.

### Rollovers

Dreamweaver-era `MM_preloadImages` / `MM_swapImage` / `MM_swapImgRestore`, with paired
`name.gif` / `name-mo.gif` images.

---

## Era B — March 2001: the corporate, legal-pressure layout

*Reference: the March 2001 snapshot at `https://web.archive.org/web/20010301220009id_/http://napster.com/`. nim no longer ships a pack for this era; what follows was recorded while one existed, and is kept because it is an authoring guide rather than an artifact.*

Lighter, denser, visibly a company under siege. A slate-blue page, white content column, a real
stylesheet, and campaign furniture (Call Congress!, Action Network, Legal Update).

### Palette

| Role | Value |
|---|---|
| Page background | `#7C869C` slate blue |
| Section headers / bars | `#525D76` darker slate |
| Content panel | `#ffffff` white |
| Panel insets | `#e6e6e6`, `#d3d9e7` |
| Rules / muted | `#999999` |
| Links | `#660A0A` dark red (all states — link, visited, active, hover) |
| "naplink" accent | `#17630B` green, bold |
| "whitelink" | `#ffffff` for use on dark bars |

### Type — use the stylesheet

`napstyle_pc.css` is the authority. Everything is `Arial, Helvetica, Sans-Serif, Times` at
percentage sizes:

| Class | Size | Use |
|---|---|---|
| `.uberhead` | 180% | page title |
| `.head` | 130% | section heading ("Speak Out!", "Featured Music") |
| `.subhead` | 120% | sub-heading |
| `.bodytext` | 90% | body copy |
| `.smbodytext` | 70% | captions, secondary |
| `.xsmbodytext` | 60% | fine print |
| `.tabon` / `.taboff` | 11pt | selected / unselected tab |

Link classes: `A.naplink` (green, bold) for in-network calls to action; `A.whitelink` for links on
dark bars. Plain `<a>` is dark red.

### Structure

```html
<body bgcolor="#7C869C" link="#660A0A" vlink="#660A0A"
      leftmargin="0" topmargin="0" marginwidth="0" marginheight="0">
```

Seventeen tables; the content column is `448`px inside a `470`px frame, with `610` and `120` used
for the outer shell and the nav rail. Composition:

1. **Wordmark top-left** on a faint watermark background.
2. **Rotating artist/celebrity quote** across the top, with `<< more >>`.
3. **Left nav as text** (not images): Home / Download / Speak Out / Discover / Press Room / Help,
   a rule, then smaller Service Status / Company / Policies.
4. **Newsletter capture** — "Your Email" field and a `Subscribe` button.
5. **Call Congress!** graphic as the rail's closing note.
6. **Main column**: intro paragraph, a boxed Download panel with "Update available!", then
   `.head` sections — **Speak Out!** (campaign text, zip-code form, Find button) and
   **Featured Music** (per-artist panel with a `#525D76` title bar, thumbnail, blurb).

### Voice

Institutional and defensive, mixed with promotion. *"Napster is under fire. The recording industry
is taking steps to shut down the Napster community."* · *"Join the Napster Action Network and get
active!"* — alongside ordinary marketing copy for featured bands. The contrast is the period.

### Randomised content

`getRandom()` picks the artist image and the quote per load. If you reproduce it, keep the rotation
small and the assets local.

---

## Rules for new content

1. **Declare the era in the pack manifest** and follow one palette. A slate-blue page with a khaki
   card is from no year that existed.
2. **Build new graphics as GIFs** at the same scale as the originals — nav items ~110×16, section
   bars the width of the content column, artist thumbnails ~120×100.
3. **Keep the content column at the period width** (≈448–534px). Widening it is the fastest way to
   look wrong, because every graphic is cut to those measures.
4. **Use the 2001 stylesheet classes** rather than inventing new ones, if writing in era B. They
   already cover six text levels.
5. **Spacer GIFs, not margins.** `clear.gif` stretched to size.
6. **Label fabrication.** Anything written now that is not an archived artifact should be
   discoverable as such — in `pack.json` under `reconstructed`, and ideally visible on the page
   itself. The sandbox is worth building because it is honest about what is real; a convincing
   forgery of a 2001 page with no marker undermines the entire exercise.

## Fonts

Pages ask for Arial/Helvetica/Verdana. These must exist in the Wine prefix or text falls through
to a serif face and the layout reads wrong (see BRIEF.md §6.14). The core fonts are installed into
`drive_c/windows/Fonts/`; `harness/README.md` has the procedure.
