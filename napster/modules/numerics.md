# `napster/numerics.py` -- the message number space

**Role.** Every number, named, including the ones whose meaning is unknown and
the ones that only ever return a refusal. Pure data, and the most valuable
single table in the project.

**In the primitive.** §3, complete. The `DOCUMENTED_GAPS` tuple and
`in_documented_gap()` were dropped as the only parts nothing calls.

## What it provides
`M` (IntEnum), `NAMES`, `REFUSAL_ONLY`, `DOCUMENTED_GAPS`, `TERMINATORS`,
`name(number)`.

## What the client expects

`napster.txt` tabulates **155 numbered entries**: about 133 with a defined
format, **12 marked `???`**, and 10 missing-range markers. Numbers run 0–920
with large documented gaps.

**Direction tags in the spec are not a complete picture.** Several numbers are
used both ways with *different field layouts* -- 205, 320, 326, 613, 617, 821,
822, 824, 827, 830. Model direction-dependent layouts explicitly; one struct
per number loses the distinction the wire makes.

## Findings encoded here

- **`TERMINATORS` is the table that keeps the client alive.** Request number →
  the server→client number that closes the list: 200→202, 211→213, 215→217,
  and three where the request and the terminator **share one number** (617,
  827, 830). A missing terminator hangs the original client, which is the
  commonest way to break it, so the framework owns these and a provider must
  not be *able* to omit one.
- **`REFUSAL_ONLY` is an implementation, not a gap.** 11/12 answer "parameters
  are unparsable", 310 returns `0`, 602 answers `*gulp* Drink milk, it does a
  body good!`, and 650/651/770/771/805/811/831 all answer permission denied.
  Preserving the refusal *is* the implementation; "unknown" is documented
  behaviour.
- **Numbers marked OBSERVED were seen on the wire** against a live BETA 9.4;
  the rest come from the spec. That distinction is worth keeping in the
  comments, because it is the difference between a fact and a claim.
- **5 is remote code execution**, 900/901 are a server-directed port scanner
  and reflector, and 748 is never actually sent. The names are here so the
  interaction is *recorded*, not so it is convenient.

## Lifting it
Copy the enum wholesale; it is the preservation payload. Keep the per-member
comments -- `# OBSERVED`, `# MANDATORY pre-login`, `# never sent by default` --
because they are the only place that information lives at a call site.
