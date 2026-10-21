# samples

The audio itself, which is the only thing in this bundle that cannot be
reconstructed from the rest of it. One rendered file, the score and the
measurements of two more that are **not in this repository**, and the commands
that make those two again.

## What is here

| File | What it is |
|---|---|
| `AB original minute.mp3` | **not here**: minute 10:00 to 11:00 of the recording this was all measured from, stream copied out of it with no re-encode |
| `AB resynthesised minute.mp3` | **not here**: the 373 notes transcribed out of that same minute, played on this engine |
| `Drone in A major, 10 min.mp3` | the engine composing for itself: `--minutes 10 --mood bright --key a --seed 7` |
| `Drone in A major, 10 min.mp3.md` | the sidecar note that render wrote beside itself, left exactly as it was written |
| `example-minute-score.tsv` | the transcription: 373 notes, one a line, onset, midi, peak dB, seconds held |
| `profiles.tsv` | the measured band profile of each file, and what the mallets cost |

The sidecar is the renderer's own output and has not been touched, so the
command line in it still reads `node tools/drone.mjs`, which is where the engine
lived inside Skybox. It is `../primitive/drone.mjs` now; everything else in the
note, including the hash and the seed, is still true of the file beside it.

## The pair is the point

Neither of the two one minute files is in this repository. The first is sixty
seconds of somebody else's commercial recording and is not redistributed here,
and the second is derived from it note for note, so both are left out together
rather than publishing half of a comparison. Making them again is the two
commands below, given the recording. Everything the comparison produced is
still here: the transcription, the measured profiles of both files, and the
verdict.

The two one minute files are an A/B test for one question that nothing else can
separate: whether a piece sounds synthetic because of **the notes** or because
of **the sound**. Play them back to back. The notes are identical, the band
profiles agree within a couple of dB up to 1 kHz, and the loudness is matched
to within 0.3 dB, so whatever is left over is the engine's voice and nothing
else.

That test is what moved this project furthest. Run on the version of the engine
that used a fixed wavetable, it produced the verdict that `../NEXT.md` opens
with: the original reads as an airy synth and the resynthesis as an unpleasant
church organ. The wavetable came out because of that one comparison, and
nothing short of it would have said which of the two to change.

The resynthesis here was re-rendered at 21:48 on 2026-10-20, after the
oscillator was rebuilt, and has not been listened to since.

## How to make them again

```sh
ffmpeg -ss 600 -t 60 -i "<the long recording>" -c copy "AB original minute.mp3"
python3 -I ../analysis/transcribe.py "<the long recording>" 600 60 > score.tsv
node ../primitive/drone.mjs --minutes 1 --kbps 192 --score score.tsv --out .
```

`-c copy` rather than a re-encode, because the comparison is against what the
recording actually sounds like, and a second pass through an encoder at a
different bitrate is a change to the thing being measured.

192 kbps for both, which is four times what a render normally needs, for the
same reason: at 64 kbps the encoder is making decisions about the top octave
and that is the octave the question is about.

## What is not here

The A/B pair, for the reason above, and the recording it was cut from.

The recording the measurements came from: `396 Hz Adrenal Fatigue Flush`, 4270
seconds, 192 kbps, 97.7 MB, held in a local vault. It is somebody else's work
and it is large, so what travels is the transcription of the minute the findings
were taken from. The name is also the first correction in `../BRIEF.md`:
there is no 396 Hz component in it at all.

The band profiles in `profiles.tsv` are normalised, each band against its own
file's overall level. Comparing raw band levels between two files without
matching their loudness first is the measurement mistake that cost two rounds
of work, and the normalisation is there so it cannot be made again by accident.
