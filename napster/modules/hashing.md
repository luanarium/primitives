# `napster/hashing.py` -- the checksum

**Role.** The file checksum as the client actually computes it, which is not
what the spec describes.

**In the primitive.** §4, verbatim minus `compute_spec` and the
`NAP_PREFIX_BYTES` variant helper (both kept as constants).

## What the client sends

```
5fa48ee73a3eba1f3f7b31249ce6e830-1087737
```

`<md5>-<bytes-hashed>`. On a 1,087,849-byte file the suffix is the whole file
minus 112 bytes: **an ID3v2 tag skipped, then the remainder hashed** -- not the
spec's bare MD5 over roughly the first 299,008 bytes.

Two independent installs computed a byte-identical value for the same file, so
it is a deterministic function of the content and can be used to match sources
for resume (215/216).

## Findings encoded here

- **Store it verbatim.** `Checksum.raw` is always what came off the wire, and
  `parse()` never rejects anything: an unrecognised field is kept whole so it
  can be echoed back unchanged. **OpenNap 0.44 cannot parse the hyphenated
  form, writes a zero hash instead, and silently kills resume** -- the one bug
  most worth not reproducing. `test_checksum_round_trips_verbatim` is that
  bug, pinned.
- **`.wma` files send the literal `WMA-FILE`** in place of a hash. That is
  because the client validates every file against a per-format module before
  sharing it (`VWMA.NVM`), so the sentinel is a property of the validator
  rather than of the protocol.
- **The linux `nap` client 0.7–0.9 hashed exactly 300,000 bytes** --
  incompatible, and a known source of failed resumes between client families.
  Kept as a named constant because identifying *which* convention a peer used
  is diagnostic information.
- **`id3v2_length` refuses to guess.** If a size byte has its high bit set the
  tag is not syncsafe, and the function returns 0 rather than computing
  nonsense.
- **`matches()` compares the md5 when both sides carry one**, so a bare hash
  still matches a hyphenated one of the same content and prefix.

## Lifting it
Copy it. Do not "normalise" the hyphenated form away at the boundary; that is
precisely the bug.
