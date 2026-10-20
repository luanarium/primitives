# analysis

Four scripts that measure audio with nothing installed. No numpy, no librosa,
no sox: this machine has python3 with no pip and 3 GB of RAM, so the FFT is
written out by hand and ffmpeg is used only to decode.

They are here because they are the half of this project that earned its
findings. Four rounds of guessing at the genre by ear got steadily closer and
stayed wrong; the first ten minutes of `roll.py` overturned most of what the
ear had assumed. Anything picked up here later should start by measuring, and
these are the instruments.

| Script | What it answers |
|---|---|
| `peaks.py` | which frequencies are actually in a window, in Hz, loudest first |
| `roll.py` | which notes sound, when they arrive, how long they hold, how many at once |
| `transcribe.py` | the same, cut into note events as a score an engine can play |
| `profile.sh` | how the energy sits across the octaves, normalised so two files compare |

## Running them

```sh
python3 -I peaks.py      FILE START SECONDS     # loudest bins, with the notes named
python3 -I roll.py       FILE START SECONDS     # the picture, plus onsets and polyphony
python3 -I transcribe.py FILE START SECONDS > score.tsv
./profile.sh FILE START                         # mean dB | 250 500 1k 2k 4k, relative
```

`-I` on python3 is deliberate: it keeps the interpreter from importing out of
the working directory, which matters because these get pointed at folders full
of downloaded audio.

A minute through `roll.py` takes about four seconds on four cores, so the whole
of a seventy minute recording is a matter of minutes rather than hours. The FFT
is 2048 points at 5512 Hz, which is a 0.37 s window, and that one choice is the
source of both of the honest limits written at the top of `transcribe.py`.

## The findings that came out of each

**`peaks.py`** gave the two facts that reframed the whole project. The
recording is in standard A440 tuning, and there is **no 396 Hz component in it
at all**, despite 396 Hz being the first thing in its title. What is there is a
Gm7 moving to Dm/F. A title is a claim, not a measurement.

**`roll.py`** overturned the ear's reading of the composition: chords every 8
to 13 seconds rather than every minute, six of them in a loop that recurs at
40:00, attacks with a median of 0.1 s over 80 onsets rather than slow swells,
chords rolled note by note over one to two seconds rather than pressed, holds
with a median of 1.1 s against 6.9 s at the 75th percentile and one voice
ringing 25 s across three changes, plain triads with octave doublings rather
than stacked ninths, and mean polyphony of 5.7 never falling below 2.

**`transcribe.py`** turned that into the A/B test in `../samples/`, which is
what finally separated the notes from the sound.

**`profile.sh`** is three cascaded highpasses and `volumedetect`, and it exists
because two earlier attempts at the same measurement were wrong. Band energy
built from cascaded one-pole lowpasses and differenced cumulative energies
barely responded to real filter changes. And `highpass=f=1000:p=4` is not valid
in ffmpeg 4.4, which is why it is `poles=2` three times over.

Every number it prints is relative to the file's own overall level, which is
not a nicety. Two rounds of work were lost to absolute comparisons: a tone
sweep rendered at 30 seconds was 6 dB quieter overall than its 60 second
reference, so every band reading moved by 6 dB and the conclusion came out
backwards, saying the mix was too dark when it was too bright.

## What is not here

The onset detector that counted the carrier ripple. It followed peaks and
reported 1773 pulses a minute on a piece that has 68. The replacement, RMS over
100 ms windows at a 25 ms hop, found the real spacing of 0.88 s. The lesson is
in `../BRIEF.md` as correction 7 rather than in code, because the working
version of that measurement lives inside `roll.py` now.
