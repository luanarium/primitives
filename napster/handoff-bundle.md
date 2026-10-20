# Brief: emit a handoff bundle

Hand this to Claude Code when work done in one project has to be carried into
another. Fill in the four lines below and paste the rest unchanged.

```
SOURCE:      <the project to condense, path>
DESTINATION: <what it is being carried into, and what that project is>
CONSUMER:    <the thing whose behaviour must be preserved: a client, a device,
              a format, an API, a downstream service>
STYLE:       <match the source project's own prose style>
```

---

## What a handoff bundle is

A directory the receiving project can work from **without the source
project's tree in front of it**. Not a summary of the source: a transfer of
the things the source learned that are written down nowhere else.

The test of a good one: someone with the bundle and no access to the source
can reproduce the behaviour 1:1, and knows which of their choices are forced
and which are free.

Emit it into a new top-level directory, `handoff/` unless told otherwise.
**Do not modify anything in the source project.** The bundle is an addition.

## The structure

```
handoff/
  README.md        index, the shortest version, and what is not here
  BRIEF.md         the integration brief: every insight needed to support CONSUMER
  PRIMITIVE.md     the condensed artifact, and what was deliberately left out
  <DESIGN>.md      the designed-but-unbuilt work, if there is any. Name it for
                   what it is (NETWORK.md, STORAGE.md, PROTOCOL-V2.md)
  primitive/
    <one file>     the substrate, dependency-free, runnable
    smoke_test.py  conformance checks: run them, do not read them
  assets/          the artifacts that populate CONSUMER -- rename for the project
    README.md      how they populate, and how the source project achieved it
    <the files>    the real bytes, including anything normally generated
  modules/
    README.md      index, grouped by concern
    <one>.md       one micro brief per module of the source
```

Rename `assets/` for what it holds: `pages/`, `templates/`, `fixtures/`,
`schemas/`, `dashboards/`. If CONSUMER is populated by artifacts of any kind,
that directory is not optional and the real files go in it.

## BRIEF.md

Ordered so that reading the first section is worth it on its own, and each
later one can be skipped by someone who does not need it. Roughly:

1. **The shape of the problem.** How many independent surfaces or seams
   CONSUMER actually has, and which of them are not the obvious one. Lead with
   this. It is usually the single most useful thing in the bundle.
2. **The corrections.** Numbered. Every place where observation disagrees with
   the documentation, the spec, the vendor's claim or the obvious reading. Say
   which is which and state the disagreement plainly.
3. **What breaks CONSUMER, ranked by how often it will.** Each entry: the
   symptom as the user sees it, the cause, the fix.
4. **The out-of-band surfaces**: everything CONSUMER reaches for that the
   obvious interface does not provide. Exact paths, ports, hostnames, keys.
5. **Configuration and deployment**: how CONSUMER is pointed at a replacement,
   what is stored where, and anything deliberately *not* written and why.
6. **Fidelity**: whatever makes the behaviour right rather than merely
   correct. Pacing, ordering, limits, the defaults that matter.
7. **Data rules**: what may be synthesised, what must not be, and how
   synthesis is disclosed.
8. **Diagnostics**: the one artefact that made the findings possible, and how
   to produce it.
9. **Integration order**, numbered, and **what the bundle does not carry**,
   with the reason for each omission.

## PRIMITIVE.md and primitive/

Condense the source's core into **one file** that runs. Dependency-free where
the language allows. State the language version it needs.

- It is a **condensation, not a summary**. Every finding from BRIEF.md that
  belongs in the core appears as code, or as a comment at the call site where
  someone would otherwise get it wrong.
- Collapse the source's plugin or provider surface into **one object with
  every method defaulted**, so the empty case runs. Keep the method names the
  source used, so its implementations lift across mechanically.
- `PRIMITIVE.md` carries: a section table saying what each part is and why it
  earned its place, the dependency and version floor, **what was left out with
  a pointer to where each omission is written up**, and porting notes for the
  invariants that are easy to drop.

**Write the conformance test, then run it.** One check per behaviour CONSUMER
depends on, each printing what it saw so the output doubles as a transcript.
Make a check fail on purpose once, to prove it is checking. State in
`PRIMITIVE.md` that a port passing all of them will work.

Never emit code claiming it works without running it.

## The designed-but-unbuilt brief

**Check for this explicitly.** A source project that has been thought about
longer than it has been built carries roadmap material -- a design settled on
paper, with the alternatives already tried and rejected -- and that material
is usually **the most portable thing in the project**, because nothing in it
is entangled with the source's existing code.

It is also the easiest to under-represent, because it has no module to write a
micro brief about. A one-paragraph mention in a "what this does not carry"
list is not coverage.

So: grep the source's own notes for sections marked *not built*, *designed*,
*roadmap*, *out of scope*, *decided against* and *proposed*, measure them, and
if what you find is large or is close to DESTINATION's purpose, give it its
own document. What goes in it:

- **The framing decisions, and the ones that were reversed.** "We tried X
  first and dropped it for these three reasons" is worth more than the design
  it replaced, and it is the first thing a fresh implementer would otherwise
  re-try.
- **The layering**, and which layer varies between deployments. That is
  normally the only real interface in the design.
- **The wire or schema sketches**, verbatim.
- **The conventions as a numbered checklist**, because that is the form
  somebody implements from.
- **What is already built versus what the glue actually is**, named piece by
  piece.
- **Out-of-scope answers that were worked out anyway**, kept so they are on
  the shelf rather than rediscovered.
- **Facts about other people's protocols or systems** turned up along the way,
  separated from the design, because they outlive it.

## assets/README.md

- What CONSUMER actually asks for, verbatim: paths, names, parameters. If that
  was discovered by observation rather than from documentation, say so.
- The constraints of whatever renders or consumes them, and the floors those
  constraints set.
- **The wiring rule**, and the failure of getting it wrong. This is usually the
  most confusing failure in the whole surface, because the artifact arrives
  correctly and nothing looks wrong.
- One short section per file in the directory, saying what it is and which
  decisions in it were forced.
- Anything referenced but not redistributable: ship the manifest that
  describes it, and say what it would have held.

## modules/*.md

One file per module of the source. Same five headings every time:

```markdown
# `path/to/module` -- one-line role

**Role.** What it is, in two or three lines.

**In the primitive.** Lifted verbatim / folded into X / not lifted, and why.

## What it provides CONSUMER
## What CONSUMER expects
## Findings encoded here
## Lifting it
```

`Findings encoded here` is the body of the file and the reason it exists. One
bullet per non-obvious decision, each **naming the failure that caused it**.
If a module has no findings, say so in two lines and move on; do not pad.

`modules/README.md` indexes them grouped by concern, one line each.

## Method, in this order

1. **Read before writing anything.** Every module, every existing document,
   and the **test names** -- a suite named in sentences is a list of findings
   someone already paid for.
2. **Collect findings, not descriptions.** A finding is something that cost
   somebody time: an observation that contradicts the documentation, a
   constraint that is not where you would look for it, a failure whose symptom
   points at the wrong cause. Descriptions of what the code does are worth
   almost nothing in a handoff; the code says that.
3. **Materialise anything generated.** If the source renders a page, a config
   or a schema at runtime, render it to a file and put it in the bundle, then
   say in prose that the live one is generated and from what.
4. **Write the primitive, and run its tests.** Before the prose, so the prose
   describes something that exists.
5. **Then write the prose**, longest document last.
6. **Verify.** Resolve every internal link. Match STYLE. Confirm the source
   project is unmodified (`git status`).

## Quality bars

- **Every claim earns its line.** A rule without the failure behind it is
  advice; a rule with it is a finding. "Do X" is weak; "Do X, because doing Y
  produced Z and the symptom pointed somewhere else" is the deliverable.
- **Separate observed from documented**, always, and name which source each
  came from.
- **Rank where you can.** "These five break it, in this order" is more useful
  than five equal bullets.
- **State the honest limits.** Where the source project guarantees something,
  say so; where it only mitigates, say that instead. A bundle that overclaims
  gets a downstream project trusting a seal that is not one.
- **Say what was left out, and where it is written up.** An omission with a
  pointer is a decision; an omission without one is a hole.
- **Preserve verbatim strings** the consumer or its users actually see. They
  are data, not prose, and paraphrasing them loses them.
- **No filler.** No section that exists because the template had one.

## Pitfalls that cost time

- **Large reads get truncated or persisted to a side file.** Read long
  documents in line ranges and long modules in parts; do not work from a
  preview.
- **Generated artifacts are invisible until rendered.** Grep for the
  template-expansion or rendering entry points early.
- **House style.** Check the newest files in the source rather than the
  biggest: the convention usually moved. Dashes, headings, voice, table style.
- **The primitive drifting into a summary.** If a section of it would not run,
  it belongs in a brief instead.
- **Tests that pass vacuously.** A conformance check that never saw the
  behaviour it names is worse than no check.
- **Counting the source's modules before writing the index.** Enumerate from
  the filesystem, not from memory, or the index will be short by two.
- **Under-representing the roadmap.** Designed-but-unbuilt work has no module,
  so a module-driven bundle silently drops it -- and it is often the part
  closest to DESTINATION's purpose. Measure it in lines against what the
  bundle gives it, before calling the bundle done.

## Done means

- [ ] `primitive/` runs, and its checks pass, and I ran them in this session
- [ ] every generated artifact the consumer loads exists in the bundle as a file
- [ ] one micro brief per module, enumerated from the filesystem
- [ ] every internal link resolves
- [ ] the corrections section is numbered and says which source each finding
      contradicts
- [ ] every omission has a pointer
- [ ] designed-but-unbuilt material is measured and either given its own
      document or explicitly judged too small for one
- [ ] STYLE matched
- [ ] `git status` shows only the new directory
