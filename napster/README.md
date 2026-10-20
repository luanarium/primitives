# Handoff bundle: supporting the Napster client

Everything needed to carry this project's behaviour into another tool, written
for a reader who does not have this project's source in front of them.

The target is **Napster 2.0 BETA 9**, build `02b09`, `napster.exe` 1,548,288
bytes, dated 10 January 2001. Nothing here distributes the client.

```
handoff/
  README.md        this: what is here and what order to read it in
  BRIEF.md         the integration brief: every insight needed to support the client
  PRIMITIVE.md     the portable primitive, and what was deliberately left out of it
  NETWORK.md       the roadmapped network layer: between instances, and vmlan
  primitive/
    napster_primitive.py   the whole protocol substrate, one stdlib-only file
    smoke_test.py          thirteen conformance checks; run it, do not read it
  pages/
    README.md              how the client's three tabs are populated, and how this project did it
    DESIGN.md              writing pages that look native in this renderer
    napster.com/           the Home tab's landing page, and the about page
    docs.napster.com/      the Discover and Help tabs, rendered to files
    packs/                 the three manifests that wire all of it
  modules/
    README.md              index
    *.md                   one micro brief per module of the source project

  handoff-bundle.md        not content: the brief that specifies this bundle's
                           own shape, for producing another one between two
                           other projects. A copy, so the bundle travels;
                           ~/.claude/briefs/handoff-bundle.md is canonical
```

## Read it in this order

1. **`BRIEF.md` §1** -- the four surfaces. If you take one thing from this
   bundle it is that a Napster client is not one client, and three of its four
   surfaces are not the protocol.
2. **`primitive/smoke_test.py`** -- run it. Thirteen checks, each printing what
   it saw, so the output is also a transcript of what a first session looks
   like on the wire.
3. **`BRIEF.md` §2** -- the nine places the 2000-era spec is wrong, and the
   five things that hang the client ranked by how often they will.
4. **`PRIMITIVE.md`** -- what the one file holds, what it leaves out, and the
   porting notes.
5. **`BRIEF.md` §3–§5** -- the surfaces the protocol does not carry: the web
   pages at their exact URLs, the hardcoded hosts, the raw SMTP path, the
   registry seed, and the seal.
6. **`pages/README.md`** -- if the tool will serve the client's tabs. The
   redirect-versus-rewrite distinction in §3 of it is the single most
   confusing failure in that whole surface.
7. **`BRIEF.md` §6–§9** -- the pacing, presenting something as a network, chat,
   and the one diagnostic worth building.
8. **`NETWORK.md`** -- if the destination is a networking tool, read this
   second rather than eighth. It is the part of the source project that is not
   a protocol-preservation idea at all: peer discovery as a provider, an
   index-push control link, instance-to-instance transfers, and a layer 2
   segment across several hosts. Designed and not built, so it transfers as
   conventions and decisions rather than as code.
9. **`modules/`** -- when you reach a specific piece. Each file says whether the
   primitive lifted it and what to carry across if not.

## The shortest version

- **First contact is port 8875, not 8888.** A server on 8888 alone never sees
  the client.
- **Answer message 4 with a type-13 echo, and echo nothing else before
  login.** Without it the client hangs at "Checking Version…" forever; echo
  the 920 opener instead and it refuses the login outright.
- **The framework owns every list terminator, in a `finally`.** A missing one
  hangs the client with no error anywhere, and a backend must not be *able* to
  cause it.
- **The client's own SOCKS setting carries the control connection**, and a
  proxy in front of it should **route by destination port and ignore the
  address** -- then the client needs no name resolution at all.
- **The embedded browser ignores that proxy.** It is WinINet, it wants port 80,
  and it is a separate redirection problem.
- **A clicked link is not a socket.** `ShellExecute` escapes a network sandbox
  entirely; point the URL handler inside the seal.
- **`<ip>` is a little-endian uint32** -- 127.0.0.1 is 16777343.
- **The checksum is `<md5>-<bytes-hashed>`; store it verbatim.** Parsing it
  off kills resume, silently.
- **The peer size prefix is undelimited and terminates on the first
  non-digit** -- observed as `I`, from `ID3`, not the 0xFF the spec predicts.
- **Quote filenames always.** A bare one in a 204 gets *"User %s is not
  properly configured"*.
- **Anything fabricated is discoverable as fabricated**, and anything missing
  is left missing. A gap is honest, a guess is not.

## What is not in here

- **The client.** Not distributed and not linked. `BRIEF.md` carries the
  digests that identify a copy, and names the open-source clients that speak
  the same protocol.
- **Archived pages or graphics.** `pages/` holds pages written for this
  project plus manifests describing archived ones. Nothing archived is
  redistributed, and no screenshots of it are kept.
- **A backend.** The seam is `Backend` in the primitive and the nine domains
  in `modules/providers.md`; what fills it is the next tool's business.
- **An implementation of the network layer.** `NETWORK.md` is a design with
  its decisions and the reasons they were reached, including the two it
  reversed. Four pieces of glue are named; none is written.

## Provenance

Every behaviour marked OBSERVED was read out of a decoded transcript of the
wire against a live client. Where the 2000-era specification `napster.txt`
disagrees with a capture, the capture wins and the disagreement is stated.
The source project's own notes -- `nim/BRIEF.md`, 4,500 lines with the
transcripts beside each finding -- remain the reference; this bundle is the
condensation, not a replacement for it.
