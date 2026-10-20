# Supporting the Napster client: an integration brief

Everything a networking tool needs in order to be the whole world of an
original Napster 2.0 BETA 9 client. Written for a project that is not this
one: nothing here assumes nim's package layout, its CLI or its directory
conventions.

Target: **Napster 2.0 BETA 9 (build `02b09`), `napster.exe` 1,548,288 bytes,
dated 10 January 2001**, SHA-256
`70675a5d444f18ee0bad46424159bdfb38ec85719b0b14f9c7ac52dfffc3bcec`. Every
behaviour marked OBSERVED was read off a capture of that binary. Where the
2000-era specification `napster.txt` disagrees with a capture, the capture
wins and the disagreement is called out, because the spec is wrong in places
that matter and wrong in both directions.

The companion documents:

| | |
|---|---|
| `primitive/napster_primitive.py` | the whole protocol substrate in one stdlib-only file, with every finding below encoded as code or comment |
| `primitive/smoke_test.py` | thirteen conformance checks; pass them and a real client works |
| `pages/` | the pages that populate the client's own tabs, and how they get there |
| `modules/` | one micro brief per module of the source project |

---

## 1. The shape of the problem

A Napster client is not one client. It is **four independent surfaces**, and
three of them are not the protocol:

| Surface | Carried by | Reached how |
|---|---|---|
| **Protocol** -- login, search, chat, rendezvous | TCP, `<len><type><data>` frames, ports 8875 then 8888 | the client's **own SOCKS proxy setting** |
| **Peer transfers** -- the actual bytes | TCP, an ad-hoc ASCII handshake, the peer's data port | direct, or the same SOCKS proxy if `ProxyTransfers` is set |
| **Web** -- the Home, Discover and Help tabs | plain HTTP on port **80** | the embedded Windows WebBrowser control, honouring **WinINet's** proxy or name resolution. **It ignores the SOCKS setting entirely.** |
| **Desktop** -- a clicked link | `ShellExecute` on a URL | the OS URL handler. Not a socket at all, and the one that escapes a network sandbox. |

Support all four or the client half-works in ways that look like bugs
somewhere else. Serve only the protocol and the Home tab is a blank frame.
Seal only the network and a click on the banner opens a browser on the host.

Two measurements make redirection possible without touching DNS, and both
were open questions until a live client settled them:

- **The client's own SOCKS setting carries the control connection**, not
  merely transfers, despite the UI around it being transfer-centric and the
  registry value being named `ProxyTransfers`.
- **WinINet's proxy captures the embedded webview**, in absolute-form requests
  (`GET http://www.napster.com:80/client/home.html?02b09 HTTP/1.1`).

And one consequence of the first that does more work than it looks:

> The client resolves its own hardcoded `server.napster.com` and then asked
> the proxy to connect to `127.12.34.56:8875` -- an address that appears
> nowhere in the binary and resolves to nothing. **The port was exact.** So a
> proxy in front of this client should **route by destination port and ignore
> the destination address**, and the client then needs no working name
> resolution at all: no hosts file, no resolver, no namespace, no root.

| Asked for | Send it to |
|---|---|
| port 8875 | the metaserver -- **first contact** |
| port 8888, 7777 | the protocol server |
| port 80 | the web surface |
| anything else | a real connection: it is a peer transfer, and that address is another peer's -- the one address the client did not invent |

That last row carries a policy. A proxy that will connect anywhere on the
client's behalf is an egress path. Restrict it to loopback and private ranges
by default; `any` and `none` are the other two honest settings.

---

## 2. The protocol, and the nine things the spec gets wrong

### Framing

```
<length:2><type:2><data:length>
```

Both header fields are **little-endian uint16**; `length` counts only `data`.
There is **no line terminator** -- nothing ends in CRLF, and `length` is
authoritative. `data` is plain ASCII, space separated, with double quotes
around any field that may contain spaces.

**Quotes are not escaped, and there is no escape to invent.** The spec itself
records that searching for `a "quoted" string` emits
`FILENAME CONTAINS "a "quoted" string" MAX_RESULTS 100` and that the official
server simply rejects it. So the field splitter must be **lenient by
position, not strict by grammar**: an unbalanced quote runs to end of payload
rather than raising. `shlex` is close and wrong.

Most period servers capped a command at **2048 bytes**, which is why the
batch-share message 870 exists and why it still has to be chunked.

### Ports

| Port | Role |
|---|---|
| **8875** | metaserver / redirector -- **first contact**, and a separate protocol |
| 8888, 7777 | client↔server |
| 6699 | the client's own data port, by convention |
| 6700 | where to put *your* peer listener, because the client wants 6699 |
| 80 | HTTP: the web surface, and the message-5 auto-upgrade |
| 25 | the client talks **raw SMTP** to `mail.napster.com` for feedback |

### The nine corrections

1. **The pre-login echo (13) is mandatory -- for message 4, and only message
   4.** Send the client message 4's answer as a type-13 echo and it proceeds;
   send nothing and it **hangs at "Checking Version…" forever**. But echo the
   920 opener and it refuses the login outright with
   `Login failed (Unexpected command: 13 [920: 1])`. The spec's "the server
   echoes any commands it receives before login" is wrong in both directions.
   OpenNap 0.44 never sends the echo at all, which is why it cannot log this
   client in unaided.

2. **Message 15 is undocumented.** `napster.txt` jumps 14 → 100. The client
   sends 15 right after login as quoted key/value pairs:
   `"ZIP" "" "CTY" "United States" "SEX" "" "AGE" "" "GEN" "" "EDU" ""` -- the
   same demographic data the spec attributes to 14, in a different encoding.
   Refusing it with a 404 is safe; the client carries on. Accepting and
   discarding is more faithful.

3. **The checksum is `<md5>-<bytes-hashed>`, not a bare MD5.** The spec
   describes an MD5 over roughly the first 299,008 bytes after skipping an
   ID3v2 tag. BETA 9.4 sends e.g. `5fa48ee73a3eba1f3f7b31249ce6e830-1087737`,
   and on a 1,087,849-byte file the suffix is the whole file minus 112 bytes:
   an ID3 tag skipped, then **the remainder** hashed. Two independent installs
   produced a byte-identical value for the same file, so it is deterministic
   and usable for resume matching. **Store it verbatim.** OpenNap 0.44 cannot
   parse the hyphenated form, writes a zero hash, and silently kills resume --
   the one bug most worth not reproducing.

4. **`<ip>` is a little-endian uint32** of the dotted quad. 127.0.0.1 is
   **16777343**, not 2130706433. Getting it backwards sends the client to an
   address that exists and is not yours.

5. **The peer size prefix is undelimited and does not terminate on 0xFF.**
   The spec says the byte after the size digits is "usually 0xFF", the MPEG
   frame sync. A live capture terminated on `I` (0x49), the first letter of an
   `ID3` tag, on an entirely ordinary MP3. **Scan for the first non-digit** --
   and hand that byte back to the caller, because it is already byte 0 of the
   file and dropping it silently corrupts every transfer.

6. **The client tries 203 first and only falls back to 500** after reading
   `<port>` 0 out of the 204 ack. It does **not** decide from the search
   result's address, so the 203/204 round trip cannot be short-circuited for
   a firewalled peer.

7. **Supply the `<speed>` field in 607.** OpenNap omits it, and the client
   then issues a 600 link-speed request for that nick and waits for the 601
   before it will send 608. Supplying it saves a round trip in the one path
   where the user is already watching a progress bar.

8. **Transfer counters (218–221) are advisory.** In the push path the
   *downloader* also emits a 220/221 pair it has no business sending -- it
   appears to count any inbound connection on its own data port as an upload.
   Never let them go negative and never treat them as truth.

9. **748 is never sent.** The spec's "someone else tried to log in as you" is
   a notification; period servers **evict** instead, sending the incumbent
   `404 You were killed by server <alias>: Someone else is logging in as you,
   disconnecting.` and dropping it.

Two more that are about shape rather than a single number:

- **Direction tags in the spec are not a complete picture.** Several numbers
  are used both ways with *different field layouts* -- 205, 320, 326, 613, 617,
  821, 822, 824, 827, 830. Model one type per *(number, direction)*, never one
  struct with optional fields.
- **The client replays its whole library on every login.** Treat a connect's
  worth of 100/870 messages as a **replace**, not an append.

### Things that hang the client, ranked

1. **No type-13 echo for message 4.** Hangs at "Checking Version…" forever.
2. **A missing list terminator.** 202, 213, 217, 409, 830, 617, 827 and the
   320/326 counts. The client waits rather than failing, so it looks like a
   slow network and never recovers. This is the single most common way to
   break it, which is why the terminator must be owned by the framework and
   emitted in a `finally` -- a backend that raises half way through a result
   set must not be *able* to cause it.
3. **An un-encodable character in a filename.** One emoji in a search result
   raised `UnicodeEncodeError` out of the handler that owed the client a 202.
   Encode latin-1 **lossy**, once, at the framing layer: a period client saw
   whatever its sharer's codepage produced, so `?` is the faithful answer.
4. **A bare filename where a quoted one belongs.** A 204 whose filename
   arrived unquoted was answered with *"User %s is not properly configured.
   Try again in a few minutes."* and a `Transfer Error!`. Quote filenames
   **always**, needed or not; quoting "only what needs it" is right for a nick
   and wrong for a filename.
5. **Listening only on 8888.** The client's first control connection goes to
   **8875**. A server without a metaserver never sees it.

### The whole interaction surface

`napster_primitive.py` section 3 carries the full number space as a named
enum, including the refusal-only numbers and the documented gaps. The
annotated tables -- what each message gives the client and what breaks if the
server stays silent -- are `nim/BRIEF.md` §4.1–4.11, which is the reference
document for this and is not reproduced here. The headlines:

- **604 whois has a level-gated tail** (`<total_dl> <total_ul> <ip>
  <connect_port> <data_port> <email>`) for moderator and above only. The
  client displays every field of it in a "Finger Information" panel, so
  emitting it to a plain user leaks data that is then shown. Gate it in the
  composer, not in the backend.
- **404 is not only errors.** It is the server's general per-client text
  channel; period servers sent operator grants through it, and the client
  renders the lot in red. The strings are what the user saw -- preserve them
  verbatim: `User nosuchuser is not currently online.`,
  `Channel #nosuchchannel does not exist!`, `permission denied`,
  `ping failed, blah is not online`.
- **Unknown numbers are part of the preserved surface.** 11/12 answer
  "parameters are unparsable", 310 returns `0`, 602 answers `*gulp* Drink milk,
  it does a body good!`, and 650/651/770/771/805/811/831 all answer permission
  denied. "Unknown" is documented behaviour, not a hole.
- **Messages 900/901 are a server-directed port scanner and reflector.**
  Implement them for preservation; gate them behind an explicit, separately
  named opt-in, default off.
- **Message 5 is remote code execution by design.** The server names a host
  and a file; the client fetches it over HTTP on port 80 with no confirmation,
  saves it as `upgrade.exe` and runs `upgrade.exe UPGRADE "<current.exe>"`.
  The spec's own words: *"also known as gaping security hole."* Record the
  message in the API so the interaction is documented; **refuse to send it by
  default**, and do not ship an HTTP upgrade server.

---

## 3. What the server does not provide

The protocol socket is not the client's only reach. Every one of these is a
surface a supporting tool has to answer for, and the reason the brief exists.

### Web pages, at their exact URLs

**31 distinct URLs are compiled into the binary** and the entire help surface
was remote. What the client *actually requests at runtime* is narrower, and
was captured with a server bound to port 80 inside the sandbox:

```
GET host=www.napster.com path=/client/home.html?02b09
GET host=www.napster.com path=/client/discover.html
GET host=www.napster.com path=/client/help/
```

- **Home carries the build in its query string.** `?02b09` is assembled at
  runtime from the build number and is **not among the binary's strings**, so
  static analysis alone would have missed it. A different build asks for a
  different URL. Period napster.com could therefore serve build-specific home
  pages.
- The other two match strings recovered from the binary.
- Requests carry the host's IE user agent. **Nothing serving these should
  branch on the UA.**

The full compiled-in tree, for a Help menu that does not open dead links:

| Area | URL |
|---|---|
| Manual | `/client/help/manual/index.html` plus per-topic `install`, `configuration`, `search`, `transfer`, `myfiles`, `hotlist`, `chat_im`, `discover`, `extra` |
| FAQ | `/client/help/faq/index.html` with anchors `#gettingstarted` `#installation` `#configuration` `#connecting` `#search` `#transfer` `#myfiles` `#chat` `#company` |
| Getting started | `/client/help/gettingstarted/index.html` |
| Support | `/client/help/support/index.html` |
| Discover | `/client/discover.html` |
| Top 10 | `napster.com/help/faq/top10.html` |
| Winsock | `/help/win/faq/winsock.html` |
| Download / shop | `/download.html`, `http://shop.napster.com` |
| Generic | `http://%s` -- a format string: the client opens arbitrary hosts |

`pages/README.md` in this bundle is the full account of how those three tabs
were made to land on pages written now.

### Hardcoded hosts

Server selection was never purely external. These names are in the binary:

| Host | Role |
|---|---|
| `server.napster.com` | the primary the client dials |
| `server2.napster.com` | secondary |
| `upgrade.napster.com` | the HTTP host behind message 5 |
| `download.napster.com` | client distribution |
| `www.napster.com` | help, manual, FAQ |
| `shop.napster.com` | the "Shop for music at CDNOW" button |
| `mail.napster.com` | **and its hardcoded IP, 216.186.140.14** |

There is **no registry value for the server address**. The settings block in
the binary holds UI geometry, search defaults, behaviour flags, transfer
limits, paths, the account and the proxy -- and no server. The proxy is the
only in-client lever, which is why §1 leans on it entirely.

### The client speaks SMTP itself

User feedback does not go through the Napster server. The client talks **raw
SMTP** to `mail.napster.com` -- `HELO` / `mail from:` / `rcpt to:` / `data` /
`quit`, subject `napster %s feedback.`, sender `anon@napster.com`, response
written to `c:\mailresponse.txt`. **The IP is hardcoded alongside the name**,
so a DNS-only seal does not contain this path. Any sealed world must deny
egress at the network layer, not at the resolver. This is the concrete case
that proves the point.

It is also worth mapping rather than merely blocking: terminate the SMTP
session and expose it, and feedback can be routed to a mailbox, a chat
channel, a webhook or a 627 operator message instead of vanishing.

### The `napster:` URL scheme

The client registers itself as a Windows URL protocol handler -- `URL
Protocol`, `URL:Napster Protocol`, `DefaultIcon`, invoked as
`%TargetDir%\napster.exe -p %1`. So a `napster:` link on a web page hands off
to the running client. **The grammar of that URL is still unknown**; nothing
in the binary spells out what a link could address. It is the last significant
undocumented client surface.

### A pluggable per-format validator

`filetypes.reg` reveals that the client validates every file against a
per-type module before sharing it:

| Type | Extension | Validator | Default download / upload |
|---|---|---|---|
| MP3 Audio File | `.MP3` | `VMP3.NVM` | `C:\DOWNLOAD\MP3` / `C:\UPLOAD\MP3` |
| MP2 Audio File | `.MP2` | `VMP3.NVM` | same |
| Windows Media File | `.WMA` | `VWMA.NVM` | `C:\DOWNLOAD\WMA` / `C:\UPLOAD\WMA` |

Which explains the `WMA-FILE` checksum sentinel, means fabricated files must
satisfy a real format validator rather than a filename, and suggests the
shareable type set is extensible through the registry.

### In-protocol content that looks like a web surface

Easy to mistake for HTTP, and much cheaper to use: **MOTD (621)**, one message
per line, pushed right after login and the first thing a user reads;
**channel MOTD (425)** and **topic (410)**; **global (628)** and **operator
(627)** messages; and the **error strings (0, 404)**. If an announcement needs
to reach the user and does not need pictures, it belongs here.

### Directory services, long dead

Rapigator and Napigator fetched server lists over HTTP from third-party
directories outside the protocol. OpenNap's side was a stats reporter:
`stats_port 8889` locally, pushing to `stat.napigator.com:8890`. Those hosts
are gone; the hardcoded hosts above are what remain.

---

## 4. Pointing a client at you

Rung 1 of the ladder: **seed the settings the client was built to read**,
rather than intercepting names or patching the binary. Two surfaces, two
settings.

```
HKLM\Software\Napster\<nick>
    ProxyServer    = 127.0.0.1
    ProxyPort      = 1080
    ProxyVersion   = 5            (4 and 5 both offered by the dialog)
    ProxyTransfers = 1

HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings
    ProxyEnable  = 1   (REG_DWORD)
    ProxyServer  = "127.0.0.1:80"
```

Five things about this that cost time to find:

- **The proxy settings are per nick.** There is no global key. A seed has to
  know the account, and the user must then **sign in as that account** --
  signing in as anyone else dials `server.napster.com` and fails. Read out of
  a live prefix: `HKLM\Software\Wow6432Node\Napster\CurrentUser = preserve`,
  then the proxy values under `…\Napster\preserve`.
- **On 64-bit Windows a 32-bit app's `HKLM\Software` writes land under
  `Wow6432Node`**, so an emitted `.reg` should carry both paths. Inside Wine
  the redirection is handled and one path is enough; writing both costs
  nothing and makes the file portable between a prefix and a VM.
- **`ProxyUser` and `ProxyPass` should not be written.** A live prefix has
  `ProxyUser = 1` and `ProxyPass = Internal`, which do not read as
  credentials and whose meaning is unknown. A seed that guesses at them is
  inventing preservation data.
- **Absolute-form requests must be normalised.** With WinINet proxied the
  webview sends `GET http://host/path HTTP/1.1`; dispatch on the URL's host
  in preference to the `Host` header, which is also the more trustworthy of
  the two in proxy mode. Skip the normalisation and a page handler is handed
  `http:` as a path component and looks for a file by that name.
- **Proxying the webview is better than a hosts file for discovery**, because
  a request for a host you do not resolve still *arrives* rather than
  vanishing into a DNS failure. That is how the CDNOW target was found, after
  the binary turned out to contain no URL for it at all.

Where the client writes its downloads is `SavePath`, default
`C:\Program Files (x86)\Napster\My Files`, and whether that folder is also
shared is a value *name* under `…\Napster\<nick>\Shared` with the path as the
name and a flag as the data. It matters: **the client scans its shared
folders and nothing else**, so a download lands somewhere it will never look
again -- refreshing the library does not pick it up, however many times it is
pressed. Observed as 11 share messages at login, 11 removals after a rescan,
and never a share for either downloaded file. Sharing the download folder is
also what the real thing did; that is how the network grew.

**Keep the collection you offer and the folder the client downloads into
separate.** A folder that is both offers the user their own downloads back as
somebody else's files.

---

## 5. Sealing it, and the hole that is not a socket

Three rungs, in increasing strength and decreasing convenience:

| Rung | What it does | What it does not claim |
|---|---|---|
| **Settings only** | Redirects every surface the client is known to use, through its own registry values. No root, no namespace, nothing system-wide. | That the client *cannot* reach the network. Something in it could still try a path nobody has measured. |
| **A VM with a host-only adapter** | The guest's only route anywhere is your machine. The guest's own network does the job a namespace was doing, with none of the plumbing. | Nothing. This is the cheapest strong seal. |
| **A user namespace with no route out** | `unshare -Urnm`, loopback only, a bind-mounted hosts file, egress denied and **asserted on every run by trying**. | -- |

Two findings that any of these has to respect:

**A namespace seals sockets, not intents.** Clicking the client's CDNOW
button called `ShellExecute` on the URL, and Wine handed it to a **host**
browser: Firefox launched on the real network, and a browser already open on
the host navigated as well. Egress was denied, the archive was unreachable
from inside, every assertion passed -- and the client still reached the
outside world by asking the desktop to do it. **Anything that can reach a URL
handler can leave.** Two settings close it:

```
HKCU\Software\Wine\WineBrowser    Browsers = ""   Mailers = ""
HKCR\http\shell\open\command      <in-prefix browser> "%1"
```

The second is the better half: point the handler at the prefix's **own**
browser, which runs inside the seal and can only reach what you serve. That
is a better outcome than disabling the button -- the original behaviour was to
open an external browser, so reproducing it faithfully *and* staying sealed
means giving the sandbox a browser of its own rather than taking the
capability away.

**One click, two windows, and the two causes.** The button produces two
browser windows. The server log settles why: **two requests arrive whichever
way the server answers**, so the client calls `ShellExecute` twice and nothing
server-side can change it. Three details fix it at the handler:

- Point `http` and `https` at a small wrapper that holds a lock for as long as
  the browser is open. **The lock must be a directory, not a file** -- the two
  calls arrive together, so "does it exist" then "create it" is a race both
  sides win; `CreateFolder` throws atomically.
- Run the wrapper under the **windowless script host**, not a shell. A batch
  file works, but a console program gets a console window, and because the
  wrapper lives as long as the browser does, that window then sits on the
  desktop beside the page for the whole visit.
- **Delete `HKCR\<scheme>\shell\open\ddeexec`.** Wine registers IE as a DDE
  server for `WWW_OpenURL`, and with that key present `ShellExecute` runs the
  command *and* sends the DDE message. The command opens the page, the DDE
  opens it again in a second window of the same process, stacked exactly on
  the first -- confirmed with `wmctrl -lx` and `xprop _NET_WM_PID`: same pid,
  same geometry. The lock never sees that one, because it never comes through
  the handler.

**And a seal is incompatible with fetching anything.** If the surface you
serve needs to go and get something -- an archived page, a live site -- then the
fetching process must live **outside** the seal and be reached from inside
over a filesystem object. Unix sockets cross a network namespace, which is the
whole trick: inside, a hosts file points every name at loopback and a relay on
port 80 carries the connection out over a Unix socket; outside, the real
server does the fetching. The client is unchanged and none the wiser.

### Prerequisites inside a Wine prefix

Not optional, and each one costs an afternoon if missed:

- **`wine-gecko`, at the version the prefix pins.** Read it out of the
  prefix's own `mshtml.dll` rather than guessing. Without it every page
  fetches and renders **blank** -- two 200s in the log and an empty viewport.
- **The MSI must be reachable from a Windows path.** With `dosdevices/z:`
  removed -- which it should be, so the client's disk scan cannot walk the host
  filesystem -- Wine cannot see the host cache and `msiexec` **exits 0 having
  installed nothing**. Copy the MSI inside the prefix first.
- **`mshtml` must be registered.** A prefix first created with
  `WINEDLLOVERRIDES="mshtml="` never writes mshtml's class and MIME
  registrations, and installing gecko afterwards does not add them. The
  symptom is a blank viewport with the gecko files plainly present; the
  diagnosis is `WINEDEBUG=+mshtml` printing
  `Could not find object for MIME L"text/html"`. `regsvr32 mshtml.dll` and
  `regsvr32 urlmon.dll` fix it.
- **The Microsoft core fonts, in `drive_c/windows/Fonts/`.** Period pages ask
  for Arial, Helvetica and Verdana; without them text falls through to a serif
  face and the layout reads wrong. Liberation is metric-compatible with Arial
  and Times but there is no free Verdana.
- **Kill `wineserver` before entering a namespace**, or the inner Wine
  attaches to the existing one over `/tmp` and its processes run in the
  *outer* network namespace.
- **Delete `dosdevices/z:`** or the client's "search my disks" walks the
  entire host filesystem through Wine's `Z: → /` mapping.

---

## 6. Making it feel like 2001

Everything runs on loopback, so the protocol completes **faster than the
client can draw it**. The dialogs flash past and the whole sign-in is over
before any of it is readable. That is the one part of the original experience
nobody had, and restoring it is cheap.

Put a pause in front of each stage the client *shows*, not around the whole
thing:

| Stage | Why it is visible |
|---|---|
| the metaserver's answer | the client's very first connection; in the era a DNS lookup sat in front of it |
| the type-13 echo | the client is showing "Checking Version…" until it arrives -- the longest and most remembered wait |
| the login ack | the server was looking you up |
| each MOTD line | so they arrive rather than appear |
| the first stats | the status bar filling in |

Measured against a real client: a sign-in takes **6.2s**, or 8.9s when the
version check fires. **Jitter matters more than the values** -- a fixed delay
reads as a progress bar; varying each wait by up to 30% is what makes it feel
like a network rather than a timer. The numbers themselves are what 56k felt
like, not a measurement; nothing was recorded at the time.

Three more that are about the protocol rather than taste:

- **Search results arrived in uneven groups.** The server answered from more
  than one place and each answer carried whatever it had. With a handful of
  files that is invisible, so the unevenness should **grow with the count**: a
  five-file answer comes in one or two steady groups, a ninety-file answer
  comes in lumps. The sizes must still sum to the count -- never drop a row to
  make the arithmetic work.
- **A transfer runs at the slower of the two ends.** The uploader's *upstream*
  and your *downstream*, which is why the link column in a search result was
  the column people read, and why the same file took wildly different times
  from different people. Upstream is the number that mattered and the one
  nobody quoted: a 56k modem served at about 4 KB/s, a 2001 cable line at
  perhaps 24 KB/s against 150 KB/s down, a T1 at 180 KB/s symmetric -- which is
  why campus users were worth queueing for.
- **Your end of the wire is shared by every transfer at once.** A 56k line
  carries 4.5 KB/s whether one file is arriving or four. Give each transfer
  the whole line and three concurrent downloads deliver three times the link
  rate and all run at the same speed whoever they came from, which is the
  opposite of what a slow line does to you. Share it **max-min fair**: equal
  shares, except that a peer who cannot use its share does not get it and what
  it cannot use goes to whoever can. Recompute per chunk, so starting another
  download slows the others and finishing one speeds them up -- that is the
  thing people watched the progress bars for.
- **Size the chunk from the rate**, about four a second. A 64 kB chunk at
  modem speed is a fourteen-second silence followed by a burst.
- **A peer's ping sits in front of their first byte.** A 540 ms modem user did
  not answer instantly and then crawl; they did both.

At the modem rate a four-megabyte MP3 takes about fifteen minutes, which is
what it took. Offer a `broadband` profile at about a minute and a `none` that
removes all of it -- tests and captures want `none`, because a test that waits
for the era is just a slow test.

---

## 7. Presenting something as a network

The motivating use case: a personal collection, offered to the client as if
it came off a network, attributed to people who do not exist. The files are
real and the bytes transfer for real; everything around them is staged.

Nine findings, each of which is a wrong-looking result if ignored:

1. **A fabricated owner has no socket.** The 204 for one of their files
   cannot carry their address, because nobody is there and the download fails
   at the TCP level with **no protocol-visible error**. It must carry *yours*,
   and you answer the peer `GET` from the real file behind the fiction. The
   client cannot tell: both cases ride the same two messages.
2. **Not port 6699.** The client wants that one for its own uploads and drops
   into firewall mode if it cannot bind it. 6700.
3. **A user never sees their own files in their own results.** A real server
   excludes them, so a sandbox that attributes fabricated results to the
   logged-in user shows them *nothing*.
4. **Attribute at index time, not at search time.** A file gets an owner once,
   when it is discovered, and keeps it -- so the same track is always offered
   by the same person, browsing their library shows a coherent set, and a
   second search agrees with the first. Deciding per result produces a network
   where nobody owns anything twice, which reads as wrong immediately.
5. **Cluster owners by directory.** A real user's shared folder is a
   collection, not a sample. One tunable for how often the cluster breaks.
6. **Restage the paths.** Show a plausible period Windows path under the
   owner's own drive, never the operator's real one; a result list full of
   `/home/someone/Music` breaks the illusion in the first screenshot. Keep the
   real path privately for serving, and map **only** in that direction -- a
   dict lookup on the path you advertised, never a join onto a filesystem,
   because the filename in a peer request is text the client supplies and the
   obvious attack on it is `..\`.
7. **A fabricated user has to answer a ping.** The client pings a user
   *before* it downloads from them and its advanced search can filter on the
   answer, so a fabricated user who cannot be pinged is a fabricated user
   nobody will download from. Answer for them, after as long as their line
   would have taken.
8. **Draw the link speed and the ping together.** They are one fact about one
   person: a 56k line with a T1's ping is the kind of detail that gives a
   fiction away. And put a floor under the fast end -- a 2 ms ping in a 2001
   client is not a fast user, it is a local disk.
9. **Seed the generator.** The same collection should index to the same names
   every run, or the museum reshuffles its population between restarts and a
   capture stops being reproducible.

**The client plays MP3 and little else**, and a collection recorded since 2001
is mostly FLAC, AAC, Opus and Vorbis. Offering one of those produces a file
the client downloads and cannot open -- the worst failure available, because it
looks like it worked. Convert with `ffmpeg`, and two constraints fall out of
the protocol rather than preference:

- **Convert at index time, not on request.** A 201 row carries the size and
  checksum of the exact bytes the peer will send and the client **verifies
  both**. Neither is knowable for a file that has not been encoded yet, so a
  lazy transcode would have to lie about them.
- **Offer a converted file under an `.mp3` name**, and keep "the bytes sent"
  and "what they were made from" as separate fields so nothing loses track of
  where the music actually lives.
- Use a **constant** bitrate: the 201 row has one bitrate field, and a VBR
  file can only report an average it does not really have.
- Write to a temporary name and rename on success, or a half-written file gets
  served as complete and the client fails its checksum. (ffmpeg cannot infer a
  container from a `.part` extension and refuses with `Invalid argument`, so
  give `-f mp3` explicitly.)

### On fabrication, as a rule

The reason this is worth building is that it is honest about what is real. A
convincing forgery with no marker undermines the whole exercise. So:

- Anything fabricated is **discoverable as fabricated** -- in the manifest, in
  a flag on the record, and ideally visible on the page.
- **Nothing fabricates files.** The collection is whatever it is; a search
  with no match returns nothing. Inventing results to make a demo look
  livelier is the one thing to refuse.
- Where an artifact is **missing, leave it missing** rather than approximating
  it. A gap is honest, a guess is not. The one exception worth making is
  structural rather than pictorial: a 1×1 transparent spacer GIF, generated at
  serve time, cannot misrepresent anything.
- Count invented and observed separately, because they are not the same
  claim. (nim hands out seventeen nicks read whole off the one surviving
  screenshot of the client in use before it generates anything, and never
  emits the five that screenshot truncates: a cut-off nick is a guess about
  its ending.)

---

## 8. Chat, and the one command the client passes through

The chat tab can be a real chat client, and the ceiling on that is set by the
client rather than by the protocol.

**The client is also the parser.** `Unknown Command '%s'!` is in the binary: a
slash command the client does not know is answered *in the window* and never
sent. So a custom `/connect` or `/irc` is not available at any price. Two
things do reach the server verbatim:

- **`/join <channel>`** -- a 400 carrying free text. It is the only known
  command whose argument is free text.
- **anything typed that is not a command at all** -- a 402 public message.

Which forces two conventions, and they are the whole user interface:

1. **The far-side network rides inside the channel name.**
   `/join #windows@libera`, with a catalogue so that `/join #win32` alone
   resolves to the right network. A name that resolves to no network must stay
   an ordinary **local** channel -- resolution failure means local, never a
   guess at somebody's network, or a typo silently opens a connection.
2. **The console is a channel.** Join `#irc` and every line typed there is a
   command rather than chat. That is a convention from the era the client is
   from: a server window you talk to. Nothing is bridged out of it, and the
   lines are echoed back as in any channel, so the window reads as a session
   transcript. The same commands should work in a private message, which is
   where a password belongs -- a console channel echoes what you type to
   everyone in it.

Also in the binary: `This command will only work from a channel window!`,
`/leave` and `/part` as aliases with a **required** channel argument, and
`You are not in '%s'!` beside them, so the client checks your own channel set
before it sends the 401.

### The rule that makes a chat adapter portable

**The sandbox stays authoritative for channel state.** A chat target is a
transport and an optional mirror, never the source of truth -- otherwise the
lists the client *must* receive (408/409, 618/828) depend on whether the far
side happens to have a concept of membership. An ActivityPub timeline has
none; the server synthesises it from its own state rather than degrading the
protocol.

An adapter therefore needs **two directions** and never formats a wire
message:

- **Outbound** is hooks: the Napster client joined, spoke, emoted, messaged.
- **Inbound** is a bridge object handed over at bind time, dealing in nicks,
  channels and text: `deliver_public`, `deliver_emote`, `deliver_private`,
  `remote_join`, `remote_part`, `remote_quit`, `set_topic`, `kick`, `notice`,
  `broadcast`, `ensure_channel`, `force_join`, `force_part`.

Five things that are easy to get wrong:

- **Register remote users.** A user who exists only on the far side becomes a
  session with `remote=True`, no socket, and the adapter's name as its origin
  -- visible in rosters and whois, addressable by private message. Skip it and
  those people are invisible to the client and the roster is a lie.
- **A remote join must never evict a local session.** The nick space is one
  space and the logged-in user is the one actually there; the far-side user
  stays unrepresented rather than impersonated, and says so in the log.
- **`ensure_channel` before anyone joins.** That is how the far side's rooms
  reach the client's own channel list with their topics, so a user enters by
  double-clicking rather than by typing a name they had to be told first.
- **`force_join` works even though the spec has no server-initiated join.**
  The join sequence is 405, 408 per member, 409, 410, and nothing in it refers
  to the 400 that usually precedes it. 401 part is explicitly unsolicited, so
  the client already copes with its channel set changing underneath it.
- **Two lossy points, handled rather than hidden.** Napster's 410 topic has no
  setter field, so a setter arrives as a notice beside the topic; and a
  multi-line message is **flattened into several**, because a newline would
  corrupt the frame. Flatten, never truncate.

For IRC specifically: open **one connection per (network, logged-in user), on
demand**, so people on the far side see a real participant rather than a
bridge nick, and nothing dials until someone joins a channel that resolves to
a network. Deliver inbound channel traffic through **exactly one** of them --
the lowest-sorting local member joined to that channel on that network,
computed rather than stored so it heals when someone parts -- or a line
arrives once per logged-in user. An always-on observer connection sitting in
someone's channel to listen on everyone's behalf is both rude and
unnecessary: the people who are there are already connected.

Nick character sets differ. Napster permits `[]{}-@^!$`, and `@`/`!` collide
with IRC prefix and mask syntax, so normalise in both directions.

---

## 9. Diagnostics: the one artefact worth building

Every finding in this brief was read out of a **decoded transcript of the
wire**, and none of them was visible in a stack trace or at a log level: the
11-second gap between 203 and 204, the emoji that lost a 202, the transfer
that finished 13,684 bytes short, the login line that declares link type 0.

The transcript is cheap if the traffic already passes through a proxy you own.
One line per protocol message in both directions, the metaserver's single
line, what the webview asked for, and the handshake in front of each transfer:

```
01:21:23.030 [c2] === CONNECT 127.12.34.56:8888 -> protocol ===
01:21:23.030 [c2] C>S  6    new user login         preserve pw 6699 "v2.0 BETA 9.4" 0 a@b.c 0
01:21:23.030 [c2] S>C  3    login ack              a@b.c
01:21:23.631 [c2] C>S  200  search                 FILENAME CONTAINS "test"
```

Four decisions that make it usable:

- **Decode the protocol frames; do not decode the file bytes.** A transfer is
  megabytes of MP3 and the interesting part is the handshake in front of it.
  Log a peer connection's first ~400 bytes and then say it is streaming. A
  capture of a long session with downloads in it is then kilobytes, not
  megabytes.
- **Tag per connection**, so two sessions can be told apart in one file.
- **Line-buffer and append**, so a transcript of a session that ended in a
  crash is still complete up to the crash -- which is the case it exists for.
- **Off unless asked for**, and say why when it is switched on: it holds the
  nick, the password, every search term and every filename of that session.
  Tell the operator to read it before sending it on.

A capture tap must never cost the client its bytes: a failed capture is a lost
line, not a lost download.

---

## 10. Integrating this, in order

1. **Vendor `primitive/napster_primitive.py`** and run
   `primitive/smoke_test.py`. Thirteen checks; they encode §2 entirely. If a
   port passes all thirteen, a real client logs in, searches, browses and
   downloads.
2. **Stand up the metaserver on 8875** before anything else, and make it
   answer with the address the client should actually dial. Until this exists
   the client never reaches the protocol port.
3. **Run a SOCKS proxy that routes by port** and point the client's per-nick
   registry values at it. Restrict its peer policy to private ranges.
4. **Serve the three web entry points on port 80**, by host rather than by
   path, and make the tab URLs **302** to wherever your content lives. See
   `pages/README.md` -- the redirect-versus-rewrite distinction there is the
   single most confusing failure in the whole surface.
5. **Decide the seal.** Settings-only is honest and convenient; a VM with a
   host-only adapter is strong and cheap; a namespace is strongest and needs
   the relay shape of §5. Whichever you pick, close the URL-handler hole, and
   remember the hardcoded SMTP IP.
6. **Fill the backend seam.** One object, every method defaulted -- §7 is what
   the implementations have to get right. Keep the two rules: a backend never
   formats a wire message, and no backend method knows a whole message.
7. **Add the pacing.** §6, and it is the difference between a protocol
   exercise and the thing people remember.
8. **Turn on the transcript** the first time something is wrong, and read §9
   before trying anything else.

### What this brief does not carry

- **The client itself.** Not distributed, not linked. The digests above identify a
  copy; `Nap`, `gnapster`/`TekNap`, `lopster` and OpenNap are open-source and
  speak the same protocol, obtainable from their own projects.
- **Archived pages or graphics.** `pages/` holds pages written for this
  project plus the *manifests* that describe archived ones. Nothing archived
  is redistributed.
- **Server links / federation.** Designed around rather than implemented:
  the message-level consequences must stay representable (`status` = `Remote`
  in whois, the 205 direction ambiguity, `LOCAL_ONLY` opting out of a search
  that would otherwise federate), which is why sessions carry an `origin`
  from the start. Addressing by `(nick, origin)` is what stops server links
  and chat bridges being a retrofit later.
- **The network layer, as code.** `NETWORK.md` carries the design: peer
  discovery as a provider, an index-push control link, instance-to-instance
  transfers, chat with nothing in the middle, and `vmlan` -- one layer 2
  segment across several hosts, which knows nothing about this protocol and is
  the piece most directly portable to a networking tool. Conventions and
  decisions, including the two it reversed. No implementation.
