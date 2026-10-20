# `napster/personas.py` -- invented users

**Role.** The people a puppeteered sandbox needs names for. Everything it
produces is invented, and the project's rule is that **anything fabricated is
labelled as fabricated**.

**In the primitive.** Not lifted. `BRIEF.md` §7 carries the rules.

## Seventeen names are not invented

They are read whole off the **one surviving screenshot of the client in use**
-- the download-section screenshot on the Wikipedia article; fair use, not
redistributed, only the names, which are facts about it:

`ldhull`, `mrbrin`, `big_bang_`, `adie_m`, `dude_way`, `hittermerbitter`,
`Creano1`, `stearch`, `albear69`, `catalina2136`, `angel3339`, `raybauduc`,
`cybermoose`, `4StringMF`, `aoldude67`, `tubbedbird`, and the logged-in user
in the status bar, `fgjfkdftdvbfvcv`.

They are **handed out first, before anything is generated** -- the real ones
should be the ones you actually meet. They are also the ground truth for what
a 2000-01 Napster nick actually looked like, and every generated name is built
from the shapes they exhibit rather than from a modern idea of a username:
word+digits, `word_word`, compound noun, initials+surname, digit+CamelCase,
and keyboard mash.

**Names visible but cut off by the column width are deliberately never
emitted.** A truncated nick is a guess about its ending, and this project
would rather have a gap. They are recorded in `TRUNCATED` so the omission is a
decision rather than an oversight. One reading is genuinely uncertain and
recorded as such: the leading glyph of `ldhull` is a lowercase L or a capital
I, which that sans face draws identically.

## Findings encoded here

- **`fabricated` is not decoration.** It is how a caller -- a whois assembler,
  a roster, a log -- can tell an invented user from a real one without
  consulting a list, which matters the moment a chat bridge puts real people
  on the same server.
- **`disclosure()` counts invented and observed separately**, because they are
  not the same claim: the observed nicks belonged to someone, once.
- **Deterministic from a seed.** The same collection indexes to the same names
  every run, so a museum does not reshuffle its population between restarts
  and a capture stays reproducible.
- **Link speed and ping are drawn together**, because they are one fact about
  one person: a 56k line with a T1's ping would be the kind of detail that
  gives a fiction away. `PING_RANGE` is per link type, skewed towards the
  quick end of each range because the slow end is a bad night rather than a
  normal one.
- **`PING_FLOOR_MS = 35` is the honest part.** Every number here is invented --
  the real round trip to a file on this machine is a fraction of a millisecond
  -- and a floor keeps the best connections from reading as what they are: **a
  2 ms ping in a 2001 client is not a fast user, it is a local disk.**
- **Link speeds are weighted the way 2001 actually looked**: mostly modems,
  some cable and DSL, a few T1s on campus, and a real share of `Unknown` --
  which is what the screenshot shows side by side.
- **`for_key()` assigns once and remembers**, which is what makes attribution
  stable across searches.
- **`_legal()` is about the wire, not taste.** Space and double-quote are the
  ones that actually break things: the protocol separates fields on space and
  quotes unescaped, so either would corrupt a 201 row rather than merely look
  wrong.
- **Roughly one generated name in forty is a founder's first name with a
  number** -- `shawn`, `sean`, `jordan`, `john` -- flagged `easter_egg` so it is
  never mistaken for observed data. Rare enough to be a find rather than a
  theme.

## Lifting it
Lift the rules and the two counters. Re-derive the word lists; they are
editorial. Keep `OBSERVED` and `TRUNCATED` if the next project is also a
preservation project, because those seventeen names are the only primary
source on the question there is.
