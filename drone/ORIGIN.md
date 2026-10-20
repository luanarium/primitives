# Where this came from

The hundred lines below were the "Making one instead of finding one" section of
Skybox's own README, cut out of it when the generator was parked (`ce45528`).
They are kept here as provenance, because they are the only continuous account
of how the engine arrived at its shape, and because the writing is the project's
own voice rather than a summary of it.

Two things to know before reading it as documentation.

The headings have been demoted one level and `tools/drone.mjs` repointed to
`drone.mjs`, which now lives in `primitive/`. That is the only editing done to
it.

And one of its claims has since been re-measured. It says the resynthesis
"matched the recording's normalised band profile within 2.4 dB at every octave
from 250 Hz to 4 kHz". Measured again on the files now in `samples/`, that holds
from 250 Hz to 1 kHz, and the resynthesis runs 4.8 dB bright at 2 kHz and
4.2 dB bright at 4 kHz. The numbers in `samples/profiles.tsv` are the measured
ones and `BRIEF.md` is the current account. Where this file and that one
disagree, that one is right.

---

## How it works

An hour of meditative drone is a large download for what it is, and none of it is a recording of
anything, so it can be computed instead.

```sh
node drone.mjs --minutes 10 --out ~/vault/music
node drone.mjs --mood calm --ping 0        # the minor one, without mallets
node drone.mjs --help
```

Ten minutes in A at the defaults comes to under 5 MB at 64 kbps, so it crosses the hub to a phone
without touching **Largest file to carry**. Each render stamps the time into the sidecar's
properties and into the file's own tags, because working on one of these means rendering over the
same name again and again, and then there is no way to tell from the card which version is playing.
Obsidian's player may also hold the bytes of a card that was already open, so a card reopened after
a re-render is the honest way to hear the new one. Length, key, mood, bitrate, pulse rate, ping rate, how
long a chord holds, how long it takes to roll in, how fast a note is struck, how long notes ring and
the seed are all flags, and the same seed gives the same piece back. The sidecar is written too,
carrying the hash so importing the file later opens the card it already has, and carrying the
settings and the chords so the note says what to run to hear it again longer or in another key.

This is written from a transcription rather than from taste, and that is the whole point of it.
Four attempts guessed at the genre by ear and got steadily closer and stayed wrong. The fifth ran a
seventy minute track of it through a piano roll, written for the job in pure Python: a short time
FFT, every bin folded onto its nearest semitone, so what comes out is note energy against time
rather than frequency against time. What that says about the music is nothing like what the music
sounds like it is doing.

Chords move every 8 to 13 seconds, six of them in a loop of about a minute, and the same loop comes
round again forty minutes later. Notes arrive in a tenth of a second, median of eighty onsets, three
tenths at the ninetieth percentile: they are struck, not swelled. The notes of one chord arrive one
after another over a second or two, so a chord is rolled like a harp rather than pressed like a key.
Holds are wildly uneven, a median of 1.1 seconds against 6.9 at the three quarter mark, with a top
voice that rings for 25 seconds and bridges three chord changes. And the voicings are plain triads
with octave doublings rather than stacked ninths, which is most of why an hour of it is restful.

So the pad here is not a pad. Every note is its own event with its own attack, hold and release;
nothing is crossfaded; and what sounds like one instrument growing is two chords ringing through
each other. Measured back against the source with the same tool, this now has five notes sounding
at an average moment against the source's six, the same tenth of a second median attack, and the
same loudness to half a decibel.

A note is not a waveform here, and that is the hardest thing on this page to have arrived at. Two
attempts used a wavetable of harmonics, falling first as one over n and then as one over n squared,
on the reasoning that a gentler rolloff is a warmer tone. Both were described, accurately, as an
organ. A fixed table of harmonics at one, a quarter and a ninth is literally an organ stop: every
partial locked to the fundamental's phase, every note carrying the identical timbre, and nothing in
a note moving between its start and its end. No amount of tuning that table's rolloff could have
fixed it, because the table was the thing.

So each partial is its own oscillator. Six a note, each detuned a few cents of its own drawn fresh
for every partial of every note, each drifting on its own slow wave between 0.07 and 0.4 Hz, each
panned to its own place, each arriving later than the one below it and dying sooner. Nothing in a
note is locked to anything else in it, which is the difference between an ensemble and a pipe, and
two notes an octave apart stop fusing into one tone. The two top partials sit slightly off their
exact multiples, because nothing airy is exactly in tune with itself. On top of that each note takes
a band of noise around its own upper partials, arriving later than the note and leaving with it,
which is the breath in it. The pitch drift is recomputed every 256 samples rather than every one,
which is what makes six oscillators and a bandpass a note affordable.

Two more things, both found by getting them wrong first. None of the filters emphasise their own
cutoff, because a resonant peak sweeping across the harmonics of a chord is a wah, and a wah is not
restful. And the gain stage is a knee rather than a tanh across everything: running the whole mix
through a tanh bends four samples in a hundred, and those four carry harmonics nobody wrote.

Then the master slope, which is the single biggest thing between this and the records it came from.
Measured with steep highpasses: a seventy minute track of the genre has nothing above 2 kHz worth
the name, 24 dB under what this was producing at one point, and nothing at all above 4 kHz. All of
its warmth is below 1500 Hz. So everything but the sub and the mallets goes through a 24 dB slope
there. The mallets are the deliberate exception, on a slope of their own three octaves up, because a
struck bar with its top taken off is a sine and then it is not a xylophone. Their echoes still take
the master slope, so a ping is crisp and its answers come back warm.

### Playing somebody else's notes, to find out whose fault a sound is

Taste cannot separate two things that both make a piece sound synthetic: the notes and the sound.
So `transcribe.py` cuts a recording into note events, one a line, and `--score` plays them on
this engine instead of the progression. Whatever is left over after that is the engine's fault,
because the notes are no longer in question.

```sh
python3 -I transcribe.py track.mp3 600 60 > score.tsv
node drone.mjs --minutes 1 --kbps 192 --score score.tsv --out .
```

Run against a minute of the genre, 373 notes came out, and the playback matched the recording's
normalised band profile within 2.4 dB at every octave from 250 Hz to 4 kHz at the same loudness.
That is the point at which the test earned itself. With the notes settled and the spectrum matched,
the playback was still an organ beside a recording that is airy, and that can only be the engine. The
wavetable went out and the independent partials came in because of that one comparison, and nothing
short of it would have said which of the two to change. The same test found that each note's filter
was closing at twice its own fundamental, throwing away the second harmonic, and that the master
slope sat 300 Hz too low. The output of a score is somebody else's composition, so it is a
measurement rather than a piece.

Two honest limits on the transcription. The analysis window is 0.37 s long, so onsets are placed to
about a tenth of a second and no attack shorter than that can be measured, which is why the attack
comes from the median of the whole piece instead. And a note's own harmonics land on real semitones,
so a loud low note can post a quieter octave or twelfth above itself; in this genre those are notes
that are played anyway. Below C3 the opposite happens, since the music's root sits under the lowest
semitone the window can resolve, so what gets reported there is really a second harmonic and the
fundamental is put back an octave down.
