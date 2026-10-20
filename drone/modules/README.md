# modules

One brief per part of the source, enumerated from the files rather than from
memory. The source is two programs: an engine of 968 lines that is now
`primitive/drone.mjs`, and four measuring scripts that are now `analysis/`.
Since the engine is one file, its briefs are per concern, with the line numbers
of each concern in `primitive/drone.mjs` at the top.

Each brief says what the part puts into the sound, what it needs, the findings
encoded in it and how to lift it out. The findings are the body and the reason
the briefs exist; what the code does, the code says.

**The sound itself is what has to be preserved**, by ear and by the band
profile a measurement takes off it. Where the template these briefs follow says
"what it provides the consumer", that is what is meant.

## The engine

| Brief | Concern |
|---|---|
| [voice.md](voice.md) | what one note is made of: six drifting partials and a band of noise |
| [score.md](score.md) | the composition, which is the transcription expressed as code |
| [sub.md](sub.md) | the low end and the only rhythm in the piece |
| [mallets.md](mallets.md) | the struck bar, and the one layer measurably outside the genre |
| [filters.md](filters.md) | the state variable filter and the master slope |
| [space.md](space.md) | the reverb and the cross fed delay |
| [mix.md](mix.md) | the sample loop, the routing, the swell and the ceiling |
| [encode.md](encode.md) | samples to an mp3, and the note that travels beside it |

## The measuring instruments

| Brief | Instrument |
|---|---|
| [peaks.md](peaks.md) | `analysis/peaks.py`, which frequencies are there at all |
| [roll.md](roll.md) | `analysis/roll.py`, the piano roll that corrected the composition |
| [transcribe.md](transcribe.md) | `analysis/transcribe.py`, notes as a playable score |
| [profile.md](profile.md) | `analysis/profile.sh`, the ruler every calibration was set with |

`primitive/smoke_test.mjs` has no brief of its own because it is new in this
bundle rather than part of the source. What it checks and why each check is
there is in [../PRIMITIVE.md](../PRIMITIVE.md).
