/**
 * A long meditative drone: the engine, as one file that nothing imports into.
 *
 * This is the condensation of a generator that was written from a
 * transcription rather than from taste. A seventy minute track of the genre
 * was run through a pure-Python piano roll, a short time FFT folded onto
 * semitones, and what it says about its own construction is nothing like what
 * it sounds like it is doing:
 *
 *   chords move every 8 to 13 seconds, not every minute, six of them in a
 *     loop of about a minute, and the same loop comes round again at 40:00
 *   notes arrive in 0.1 seconds, median of 80 onsets, 0.3 at the 90th
 *     percentile: they are struck, not swelled
 *   the notes of one chord arrive over a second or two rather than together,
 *     so a chord is rolled like a harp rather than pressed like a key
 *   holds vary wildly: a median of 1.1 seconds, six at the 75th percentile,
 *     and a top voice that rings for 25 and bridges three chord changes
 *   the voicings are plain triads with octave doublings, not stacked ninths,
 *     which is most of why an hour of it is restful
 *   nothing above 2 kHz worth the name, and nothing at all above 4
 *
 * So the pad here is not a pad. Every note is its own event with its own
 * attack, hold and release, the releases overlap the next chord instead of
 * crossfading into it, and what sounds like one instrument growing is really
 * two chords ringing through each other.
 *
 * Nothing above this line's arithmetic is imported. The whole synthesis half
 * of this file is Math, typed arrays and a sine table, so it ports to a
 * browser or an AudioWorklet unchanged; every Node call is behind a dynamic
 * import inside the command line half at the bottom, because a static
 * `import "node:fs"` at the top is the one thing that would stop that.
 *
 * Three ways in:
 *
 *   node drone.mjs --minutes 10 --out .              as a command
 *   const ctx = settings({ minutes: 10 });           as a module
 *   await render(ctx, (block) => sink(block));
 *   await render(settings({ composer: { buildScore } }), sink);   with your
 *                                                    own composition
 *
 * `render` hands blocks of interleaved signed 16 bit samples at 44100 to
 * whatever you pass it. What it does not do is encode: ffmpeg is handed
 * finished samples on a pipe by the command line half and does nothing to
 * them but compress, so a seventy minute render never holds more than a
 * second of audio in memory.
 *
 * Parked out of Skybox on 2026-10-20. See ../BRIEF.md for what is known about
 * the genre, ../PRIMITIVE.md for what each part of this file is for, and
 * ../NEXT.md for the one question still open.
 */

export const RATE = 44100;
const DRIVE = 1.07;

/**
 * Six chords in a loop, triads with the octave doublings that make them sit
 * still, written in A and transposed to whatever key is asked for. Notes
 * rather than intervals, because a chord is easier to argue with when you can
 * read it. The roots stay between 36 and 62 Hz, where the weight of this
 * music lives.
 *
 * `calm` is i VI III VII iv v, which comes home at the top of the loop.
 * `bright` is I IV vi ii V I.
 */
const MOODS = {
	bright: {
		tonality: "major",
		chords: [
			{ name: "A", root: "A1", notes: ["A3", "C#4", "E4", "A4", "C#5", "E5"] },
			{ name: "D", root: "D1", notes: ["A3", "D4", "F#4", "A4", "D5", "F#5"] },
			{ name: "F#m", root: "F#1", notes: ["A3", "C#4", "F#4", "A4", "C#5", "F#5"] },
			{ name: "Bm", root: "B1", notes: ["B3", "D4", "F#4", "B4", "D5", "F#5"] },
			{ name: "E", root: "E1", notes: ["B3", "E4", "G#4", "B4", "E5", "G#5"] },
			{ name: "A", root: "A1", notes: ["A3", "C#4", "E4", "A4", "E5", "A5"] },
		],
	},
	calm: {
		tonality: "minor",
		chords: [
			{ name: "Am", root: "A1", notes: ["A3", "C4", "E4", "A4", "C5", "E5"] },
			{ name: "F", root: "F1", notes: ["F3", "A3", "C4", "F4", "A4", "C5"] },
			{ name: "C", root: "C2", notes: ["G3", "C4", "E4", "G4", "C5", "E5"] },
			{ name: "G", root: "G1", notes: ["G3", "B3", "D4", "G4", "B4", "D5"] },
			{ name: "Dm", root: "D1", notes: ["A3", "D4", "F4", "A4", "D5", "F5"] },
			{ name: "Em", root: "E1", notes: ["G3", "B3", "E4", "B4", "E5", "G5"] },
		],
	},
};

/**
 * What one note is made of.
 *
 * Not a waveform. A fixed table of harmonics at one, a quarter and a ninth is
 * literally an organ stop: every partial locked to the fundamental's phase,
 * identical in every note, and dead still from its start to its end. That is
 * what it sounds like too.
 *
 * So each partial is its own oscillator, detuned a few cents of its own,
 * drifting on its own slow wave, panned to its own place, arriving later than
 * the one below it and dying sooner. Nothing in a note is locked to anything
 * else in it, which is the whole difference between an ensemble and a pipe.
 * The two top partials are deliberately off their exact multiples, because
 * nothing airy is exactly in tune with itself.
 */
const PARTIALS = [
	{ mult: 1, gain: 1, rise: 1, fall: 1, drift: 0.0004 },
	{ mult: 2, gain: 0.3, rise: 1.5, fall: 0.85, drift: 0.0009 },
	{ mult: 3, gain: 0.15, rise: 2, fall: 0.72, drift: 0.0014 },
	{ mult: 4, gain: 0.05, rise: 2.6, fall: 0.62, drift: 0.0019 },
	{ mult: 5.97, gain: 0.016, rise: 3.2, fall: 0.54, drift: 0.0026 },
	{ mult: 8.04, gain: 0.007, rise: 3.8, fall: 0.46, drift: 0.0034 },
];

/** How often a drifting partial's pitch is recomputed. Slow movement, cheaply. */
const DRIFT_EVERY = 256;

/**
 * A struck bar is not a harmonic series. A xylophone's partials sit at roughly
 * three, six and nine times the fundamental rather than two and three, and the
 * high ones die first, which is why the attack has a knock in it and the tail
 * is nearly a sine. Four of them is enough to hear wood.
 */
const BAR = [
	{ ratio: 1, gain: 1, decay: 1 },
	{ ratio: 3.01, gain: 0.4, decay: 1.9 },
	{ ratio: 5.67, gain: 0.16, decay: 3.1 },
	{ ratio: 9.1, gain: 0.045, decay: 4.6 },
];

const NOTES = {
	c: 0, "c#": 1, db: 1, d: 2, "d#": 3, eb: 3, e: 4, f: 5, "f#": 6,
	gb: 6, g: 7, "g#": 8, ab: 8, a: 9, "a#": 10, bb: 10, b: 11,
};

const SINE = sineTable(8192);

/**
 * Everything the engine takes, and what it does when you give it nothing.
 *
 * These are not tasteful defaults. `chord`, `strike` and `roll` are the
 * medians measured off a real recording, and `pulse` is its low end counted
 * over a minute, so the empty case is the transcription rather than a guess.
 */
export const DEFAULTS = {
	minutes: 10,
	kbps: 64,
	pulse: 68,
	ping: 30,
	chord: 10,
	roll: 1.4,
	strike: 0.12,
	ring: 1,
	seed: 7,
	key: "a",
	mood: "bright",
	stereo: true,
	score: null,
	composer: null,
};

/**
 * The composition surface, with every method defaulted, so the empty case
 * runs and an override replaces exactly one thing.
 *
 * This is the seam to reach for when this engine is wanted under somebody
 * else's music: pass `{ composer: { buildScore } }` and the chords, the roll,
 * the holds and the mallets are yours while the voice, the filters, the room
 * and the limiter stay as measured. A `buildScore` returns
 * `{ notes: [...], roots: [...] }`, and a note is the whole interface:
 *
 *   { at, hz, step: hz / RATE, rise, sustain, release, life, gain, pan }
 *
 * `at` and `life` are seconds, `life` is the whole span after which the note
 * is dropped (rise + sustain + release, or it will be cut off mid release),
 * `gain` is linear and small (0.05 is one voice of six), and `pan` is 0 left
 * to 1 right. A root in `roots` is the same minus `hz`, `gain` and `pan`,
 * because the sub is mono, pulsed and mixed at a fixed level.
 */
export const COMPOSER = { buildScore, playScore, buildPings, buildTide, voiceOf, airOf };

/**
 * Options in, a validated context out. Every number is checked here rather
 * than in the command line half, so a module caller gets the same refusals a
 * typed flag does.
 */
export function settings(options = {}) {
	const given = { ...DEFAULTS, ...options };
	const minutes = Number(given.minutes);
	const kbps = Number(given.kbps);
	const pulses = Number(given.pulse);
	const pings = Number(given.ping);
	const chordSeconds = Number(given.chord);
	const rollSeconds = Number(given.roll);
	const strike = Number(given.strike);
	const ring = Number(given.ring);
	const seed = given.seed === "random" ? Date.now() % 2 ** 31 : Number(given.seed);
	const keyWord = String(given.key).trim().toLowerCase();
	const moodWord = String(given.mood).trim().toLowerCase();
	const stereo = given.stereo !== false;

	if (!(minutes > 0)) throw new Error("minutes wants a number of minutes above zero");
	if (!(kbps >= 32)) throw new Error("kbps wants 32 or more");
	if (!(pulses > 0 && pulses < 240)) throw new Error("pulse wants a count a minute, say 50 to 90");
	if (!(pings >= 0 && pings < 240)) throw new Error("ping wants a count a minute, say 20 to 60, or 0");
	if (!(chordSeconds >= 3)) throw new Error("chord wants three seconds or more");
	if (!(rollSeconds >= 0 && rollSeconds < chordSeconds)) throw new Error("roll wants less than chord");
	if (!(strike >= 0.02 && strike <= 4)) throw new Error("strike wants between 0.02 and 4 seconds");
	if (!(ring >= 0.5 && ring <= 3)) throw new Error("ring wants between 0.5 and 3");
	if (!(keyWord in NOTES)) throw new Error(`key does not know "${keyWord}": try a, c#, eb and so on`);
	if (!(moodWord in MOODS)) throw new Error(`mood wants bright or calm, not "${moodWord}"`);
	if (!Number.isFinite(seed)) throw new Error("seed wants a number, or the word random");

	const seconds = Math.round(minutes * 60);
	/**
	 * The progressions are written in A, so another key is a transposition. It
	 * is taken the short way round, never more than six semitones, because the
	 * roots are already where this music wants them and carrying them a whole
	 * octave would put the bass under or over the band that matters.
	 */
	const shift = ((NOTES[keyWord] - 9 + 18) % 12) - 6;

	return {
		rate: RATE,
		minutes,
		kbps,
		pulses,
		pings,
		chordSeconds,
		rollSeconds,
		strike,
		ring,
		seed,
		keyWord,
		moodWord,
		stereo,
		shift,
		seconds,
		frames: seconds * RATE,
		channels: stereo ? 2 : 1,
		progression: MOODS[moodWord].chords,
		tonality: MOODS[moodWord].tonality,
		pretty: `${keyWord.toUpperCase()} ${MOODS[moodWord].tonality}`,
		score: given.score ? normaliseScore(given.score) : null,
		composer: given.composer || null,
		/**
		 * When this was rendered, to the minute, which the sidecar and the
		 * file's own tags carry. Rendering over the same name is the usual way
		 * to work on one of these, and then there is no way to tell from the
		 * card which version is playing. There is now.
		 */
		stamped: new Date().toISOString().slice(0, 16).replace("T", " "),
	};
}

/**
 * A transcribed score: the notes of somebody else's recording, read out of it
 * by `../analysis/transcribe.py` and played here instead of the progression.
 *
 * This exists to answer the one question taste cannot: whether a piece sounds
 * synthetic because of the notes or because of the sound. Put a real
 * recording's notes through this engine and whatever is left over is the
 * engine's fault. What comes out is somebody else's composition, so it is a
 * measurement rather than a piece.
 *
 * Either the tab separated text the transcriber prints, or the same thing
 * already parsed.
 */
export function normaliseScore(score) {
	const notes = [];
	if (typeof score === "string") {
		for (const line of score.split(/\r?\n/)) {
			if (!line || line.startsWith("#")) continue;
			const [at, note, db, held] = line.split(/\t|\s+/).map(Number);
			if (![at, note, db, held].every(Number.isFinite)) continue;
			notes.push({ at, note, db, held });
		}
	} else {
		for (const note of score) notes.push({ ...note });
	}
	if (notes.length === 0) throw new Error("that score holds no notes");
	notes.sort((a, b) => a.at - b.at);
	return notes;
}

/**
 * The whole piece as one block of samples, for a caller that wants it in
 * memory. A ten minute stereo render is 100 MB this way, which is why the
 * command line half streams instead.
 */
export async function renderToArray(options = {}) {
	const ctx = options.rate ? options : settings(options);
	const all = new Int16Array(ctx.frames * ctx.channels);
	let at = 0;
	await render(ctx, (block) => {
		all.set(block, at);
		at += block.length;
	});
	return all.subarray(0, at);
}

/* ------------------------------------------------------------------ */

/**
 * The whole piece, a second at a time, onto whatever you pass it.
 *
 * `write` is handed an `Int16Array` of interleaved samples and may return a
 * promise to apply backpressure; the block is reused, so a sink that keeps it
 * must copy. `report` is given a whole percentage, once each.
 */
export async function render(ctx, write, report = () => {}) {
	const { frames, seconds, stereo, channels, pulses, seed, score: SCORE } = ctx;
	const composer = { ...COMPOSER, ...ctx.composer };
	const random = mulberry(seed);
	const score = SCORE ? composer.playScore(ctx) : composer.buildScore(ctx, random);
	const figure = SCORE ? [] : composer.buildPings(ctx, random);
	const tide = composer.buildTide(ctx, random);
	const verb = reverb(stereo);
	const spread = pingpong(Math.round((RATE * 60) / pulses / 2), stereo);

	/**
	 * The master slope, the single biggest thing between this and the records
	 * it came from: they have nothing above 2 kHz worth the name and nothing
	 * at all above 4. The mallets are the deliberate exception, on a slope of
	 * their own three octaves up, because a struck bar with its top taken off
	 * is a sine and then it is not a xylophone. Their echoes still take the
	 * master slope, so a ping is crisp and its answers come back warm.
	 */
	const air = [slope(1800), slope(1800)];
	const wood = [slope(2800), slope(2800)];

	const pulseHz = pulses / 60;
	const fade = Math.min(20, seconds / 8);

	const block = RATE;
	const buffer = new Int16Array(block * channels);
	let at = 0;
	let hiss = 0;

	let nextNote = 0;
	let nextPing = 0;
	let nextRoot = 0;
	const sounding = [];
	const struck = [];
	const rooted = [];

	for (let frame = 0; frame < frames; frame++) {
		const t = frame / RATE;

		let padL = 0;
		let padR = 0;
		// Moved above the notes, because each of them takes its breath from it.
		hiss = hiss * 0.86 + (random() * 2 - 1) * 0.14;

		/**
		 * Every note of every chord is its own event. Two chords ring through
		 * each other at a change because the releases are long and nothing is
		 * crossfaded, which is what the transcription shows and what makes the
		 * change sound like an arrival rather than a dissolve.
		 */
		while (nextNote < score.notes.length && score.notes[nextNote].at <= t) {
			const note = score.notes[nextNote++];
			sounding.push({ ...note, parts: composer.voiceOf(note, random), air: composer.airOf(note, random) });
		}
		const drifting = frame % DRIFT_EVERY === 0;
		for (let i = sounding.length - 1; i >= 0; i--) {
			const note = sounding[i];
			const age = t - note.at;
			if (age > note.life) {
				sounding.splice(i, 1);
				continue;
			}
			for (const part of note.parts) {
				// The drift is slow enough to recompute every few milliseconds
				// rather than every sample, which is what makes six
				// oscillators a note affordable.
				if (drifting) {
					part.step = part.base * (1 + part.depth * lookup(SINE, part.driftHz * t + part.seed));
				}
				part.phase += part.step;
				if (part.phase >= 1) part.phase -= 1;
				const env = partEnvelope(age, note, part);
				if (env === 0) continue;
				const value = lookup(SINE, part.phase, true) * part.gain * env * note.gain;
				padL += value * (stereo ? 1 - part.pan : 1);
				if (stereo) padR += value * part.pan;
			}
			// Air: the breath in it. A band of noise around the note's own
			// upper partials, arriving later than the note and going with it.
			const breath = partEnvelope(age, note, note.air);
			if (breath > 0) {
				const value =
					note.air.cell(hiss, note.hz * note.air.mult, 0.85) * note.air.gain * breath * note.gain;
				padL += value * (stereo ? 1 - note.air.pan : 1);
				if (stereo) padR += value * note.air.pan;
			}
		}

		// The low end: one note a chord, pulsing. Measured on the real thing,
		// a short attack, a long decay, around 17 dB between quietest and
		// loudest, every 0.88 s.
		let subs = 0;
		while (nextRoot < score.roots.length && score.roots[nextRoot].at <= t) {
			const root = score.roots[nextRoot++];
			rooted.push({ ...root, phase: random(), second: random() });
		}
		const beat = (t * pulseHz) % 1;
		const push = beat < 0.05 ? beat / 0.05 : Math.exp(-(beat - 0.05) / 0.26);
		for (let i = rooted.length - 1; i >= 0; i--) {
			const root = rooted[i];
			const age = t - root.at;
			if (age > root.life) {
				rooted.splice(i, 1);
				continue;
			}
			root.phase += root.step;
			if (root.phase >= 1) root.phase -= 1;
			root.second += root.step * 2;
			if (root.second >= 1) root.second -= 1;
			subs +=
				(lookup(SINE, root.phase, true) + 0.11 * lookup(SINE, root.second, true)) *
				0.7 *
				(0.13 + 0.87 * push) *
				holdEnvelope(age, root);
		}

		// The pings: a mallet walking the chord at a very slow beat.
		let woodL = 0;
		let woodR = 0;
		while (nextPing < figure.length && figure[nextPing].at <= t) {
			const ping = figure[nextPing++];
			const hz = ping.hz;
			struck.push({
				at: t,
				life: ping.life,
				gain: ping.gain,
				pan: ping.pan,
				phases: BAR.map(() => random()),
				steps: BAR.map((part) => (hz * part.ratio) / RATE),
				heard: BAR.map((part) => (hz * part.ratio < 17000 ? part.gain : 0)),
			});
		}
		for (let i = struck.length - 1; i >= 0; i--) {
			const bar = struck[i];
			const age = t - bar.at;
			if (age > bar.life) {
				struck.splice(i, 1);
				continue;
			}
			let value = 0;
			for (let k = 0; k < BAR.length; k++) {
				if (bar.heard[k] === 0) continue;
				bar.phases[k] += bar.steps[k];
				if (bar.phases[k] >= 1) bar.phases[k] -= 1;
				value +=
					lookup(SINE, bar.phases[k], true) *
					bar.heard[k] *
					Math.exp((-age * (5 / bar.life) * BAR[k].decay) / 1.6);
			}
			value *= bar.gain * (age < 0.003 ? age / 0.003 : 1);
			woodL += value * (stereo ? 1 - bar.pan : 1);
			if (stereo) woodR += value * bar.pan;
		}
		// A third of each ping goes into the delay, which is what makes it
		// ripple outward instead of simply stopping.
		const echo = spread((woodL + woodR) * 0.33);

		// Everything but the sub goes to the room, because a sub in a long
		// reverb is mud rather than depth.
		const sendL = padL * 0.75 + woodL * 0.7 + echo[0] * 0.8 + hiss * 0.02;
		const sendR = stereo ? padR * 0.75 + woodR * 0.7 + echo[1] * 0.8 + hiss * 0.016 : sendL;
		const wet = verb(sendL, sendR);

		let a = air[0](padL + echo[0] + hiss * 0.012 + wet[0] * 0.6) + wood[0](woodL) + subs;
		let b = stereo
			? air[1](padR + echo[1] + hiss * 0.01 + wet[1] * 0.6) + wood[1](woodR) + subs
			: a;

		// The tide, long in, longer out, and a knee that rounds off only peaks.
		const level =
			tide(t) * Math.min(1, t / fade) * Math.min(1, (seconds - t) / (fade * 1.4)) * 0.86;
		a = knee(a * DRIVE) * level;
		b = knee(b * DRIVE) * level;

		buffer[at++] = Math.round(a * 32767);
		if (stereo) buffer[at++] = Math.round(b * 32767);

		if (at === buffer.length) {
			at = 0;
			await write(buffer);
			report(Math.floor((frame / frames) * 10) * 10);
		}
	}
	if (at > 0) await write(buffer.subarray(0, at));
	report(100);
}

/**
 * A transcribed score as events this engine can play.
 *
 * Two adjustments, both from measurement rather than preference. The attack is
 * not taken from the transcription, because the analysis window is 0.37 s long
 * and the real attacks are a tenth of that: the measured median of 80 onsets
 * is used instead. And anything under C3 gets its fundamental restored an
 * octave below at 3 dB louder, because the analyser's range stops at A1 while
 * the music's root is a fifth under that, so what it reports as a bass note is
 * really that note's second harmonic. Measured at 600 s: 48.8 Hz at -5.8 dB
 * with its octave at 98.0 Hz and -9.3.
 */
function playScore(ctx) {
	const { score: SCORE, strike, ring, stereo } = ctx;
	const notes = [];
	for (const note of SCORE) {
		// Under C3 the analyser is reporting a second harmonic, because the
		// music's root sits below the range it can resolve, so the fundamental
		// is put back an octave down. And everything above C3 is lifted 6 dB,
		// because a semitone's bin sum is not a level: without the lift the
		// playback carries 8 dB more bass relative to its own total than the
		// recording does, measured on normalised band profiles.
		const voices = note.note < 48 ? [[note.note - 12, 0], [note.note, 0]] : [[note.note, 6]];
		for (const [pitch, lift] of voices) {
			const hz = 440 * 2 ** ((pitch - 69) / 12);
			if (hz < 20 || hz > 12000) continue;
			const release = (note.held < 1 ? 0.8 : 3.5) * ring;
			notes.push({
				at: note.at,
				hz,
				step: hz / RATE,
				rise: Math.min(strike, Math.max(0.03, note.held * 0.4)),
				sustain: note.held,
				release,
				life: strike + note.held + release,
				gain: 0.27 * 10 ** ((note.db + lift) / 20),
				pan: 0.5 + (((pitch % 7) - 3) / 3) * (stereo ? 0.16 : 0),
			});
		}
	}
	return { notes, roots: [] };
}

/**
 * The score: every note of every chord of the whole piece, written out before
 * a sample is rendered.
 *
 * A chord is rolled rather than pressed. Its notes arrive one after another
 * across a second or so, usually from the bottom up, and each one is struck in
 * a tenth of a second. Holds are deliberately uneven, because the transcribed
 * ones are: most of a chord lets go a few seconds after the next one arrives,
 * one voice holds on long enough to ring through two or three changes, and the
 * occasional note is gone almost at once.
 */
function buildScore(ctx, random) {
	const { seconds, progression: PROGRESSION, chordSeconds, rollSeconds, strike, ring, stereo, shift } = ctx;
	const notes = [];
	const roots = [];
	let at = 0;
	let index = 0;

	while (at < seconds) {
		const chord = PROGRESSION[index % PROGRESSION.length];
		// Eight to thirteen seconds, as transcribed, rather than a metronome.
		const hold = chordSeconds * (0.85 + random() * 0.3);
		const pitches = chord.notes.map((note) => midi(note));
		// Usually bottom to top, now and then the other way, which is the
		// difference between a harp and a machine.
		const order = pitches.map((_, i) => i);
		if (random() < 0.3) order.reverse();

		order.forEach((which, step) => {
			const note = pitches[which];
			const spread = rollSeconds * (step / Math.max(1, pitches.length - 1));
			const top = which === pitches.length - 1;
			/**
			 * Two voices a chord ring on through the chords that follow them,
			 * which is what keeps the texture full: transcribed, the example
			 * has five or six notes sounding at any moment and never fewer
			 * than two, and the only way to get there with six-note chords is
			 * for the last chord to still be audible under this one.
			 */
			const rings = (top && random() < 0.75) || (!top && random() < 0.3);
			const quick = !top && !rings && random() < 0.1;
			const sustain = quick ? 0.4 + random() * 1.4 : hold * (rings ? 2.3 + random() * 1.5 : 1);
			const release = (quick ? 1.2 : 5 + random() * 4) * ring;
			const hz = hertz(note, shift);
			notes.push({
				at: at + spread + (random() - 0.5) * 0.12,
				hz,
				step: hz / RATE,
				rise: strike * (0.7 + random() * 0.7),
				sustain,
				release,
				life: strike + sustain + release,
				// The top of a chord carries less, or it becomes the tune.
				gain: (top ? 0.046 : 0.065) * (0.8 + random() * 0.4),
				pan: 0.5 + (which - (pitches.length - 1) / 2) * (stereo ? 0.11 : 0),
			});
		});

		const hz = hertz(midi(chord.root), shift);
		roots.push({
			at,
			step: hz / RATE,
			rise: 0.35,
			sustain: hold * 0.92,
			release: 2.6,
			life: 0.35 + hold * 0.92 + 2.6,
		});

		at += hold;
		index++;
	}
	return { notes, roots };
}


/**
 * One note's oscillators: a partial each, none of them locked to any other.
 *
 * The detune is a few cents, fresh for every partial of every note, so two
 * notes an octave apart never fuse into one tone the way an organ's do. The
 * pans are spread around the note's own place for the same reason.
 */
function voiceOf(note, random) {
	return PARTIALS.map((part) => {
		const base = (note.hz * part.mult * (1 + (random() * 2 - 1) * 0.0022)) / RATE;
		return {
			base,
			step: base,
			depth: part.drift,
			driftHz: 0.07 + random() * 0.33,
			seed: random(),
			phase: random(),
			gain: part.gain,
			rise: part.rise,
			fall: part.fall,
			pan: Math.min(0.95, Math.max(0.05, note.pan + (random() * 2 - 1) * 0.2)),
		};
	}).filter((part) => part.base * RATE < 15000);
}

/** The breath on a note: a band of the shared noise, around its own partials. */
function airOf(note, random) {
	return {
		cell: bandpass(),
		mult: 2.6 + random() * 2.4,
		gain: 0.3 + random() * 0.3,
		rise: 3.4,
		fall: 0.8,
		pan: Math.min(0.95, Math.max(0.05, note.pan + (random() * 2 - 1) * 0.3)),
		cellGain: 1,
	};
}

/**
 * A partial's own envelope: up later than the one below it, holding while the
 * note does with the faintest sag, and letting go sooner. A note therefore
 * arrives bright and warms as it rings, which is what a struck thing does and
 * what a fixed waveform can never do.
 */
function partEnvelope(age, note, part) {
	const rise = note.rise * part.rise;
	if (age < rise) return 0.5 * (1 - Math.cos((Math.PI * age) / rise));
	const sat = age - rise;
	const sag = Math.exp(-sat / 40);
	if (sat < note.sustain) return sag;
	const left = sag * Math.exp((-(sat - note.sustain) * 3 * part.fall) / note.release);
	return left < 0.0004 ? 0 : left;
}

/** The same shape, for the root underneath, which has no sag worth having. */
function holdEnvelope(age, note) {
	if (age < note.rise) return 0.5 * (1 - Math.cos((Math.PI * age) / note.rise));
	const sat = age - note.rise;
	if (sat < note.sustain) return 1;
	return Math.exp((-(sat - note.sustain) * 3) / note.release);
}

/**
 * The mallet figure: a slow beat, two octaves above the chord, walking it
 * mostly upward and dropping back when it runs out of room.
 *
 * It is a figure rather than an arpeggio because of the rate. At thirty a
 * minute a note has two seconds to ring out, which is long enough that what
 * you hear is one note at a time rather than a pattern, and that is the point
 * of a slow ping.
 */
function buildPings(ctx, random) {
	const { pings, seconds, chordSeconds, progression: PROGRESSION, shift } = ctx;
	if (pings === 0) return [];
	const every = 60 / pings;
	const notes = [];
	let place = 0;
	let chordAt = 0;
	let index = 0;
	for (let step = 0; ; step++) {
		const at = 4 + step * every;
		if (at > seconds - 4) break;
		// Which chord is sounding, walked forward at the nominal rate. It does
		// not have to be exact: being a beat behind the change is how a real
		// player sounds anyway.
		while (at > chordAt + chordSeconds) {
			chordAt += chordSeconds;
			index++;
		}
		const pitches = PROGRESSION[index % PROGRESSION.length].notes.map((note) => midi(note));
		const roll = random();
		if (roll < 0.14) {
			place += 1;
			continue;
		}
		if (roll < 0.19) {
			place = 0;
			continue;
		}
		const lift = random() < 0.25 ? 12 : 24;
		notes.push({
			at: at + (random() - 0.5) * 0.06,
			hz: hertz(pitches[place % pitches.length] + lift, shift),
			life: lift === 24 ? 1.1 + random() * 0.7 : 1.6 + random() * 0.9,
			gain: 0.05 + random() * 0.04,
			pan: 0.5 + (random() - 0.5) * 0.52,
		});
		place += random() < 0.76 ? 1 : -2;
		if (place < 0) place += pitches.length;
	}
	return notes;
}

/**
 * The tide: a slow swell over the whole piece, a few sines of unrelated
 * periods added together. Three dB either way, which is not a lot to look at
 * and is the difference between a recording and a test tone.
 */
function buildTide(ctx, random) {
	const parts = [];
	for (let i = 0; i < 4; i++) {
		parts.push({ hz: 0.004 + random() * 0.02, phase: random() * Math.PI * 2, gain: random() });
	}
	const total = parts.reduce((sum, part) => sum + part.gain, 0) || 1;
	return (t) => {
		let value = 0;
		for (const part of parts) value += part.gain * Math.sin(2 * Math.PI * part.hz * t + part.phase);
		return 1 + 0.17 * (value / total);
	};
}

/**
 * A ceiling with a soft corner, rather than a squeeze on everything.
 *
 * Running the whole mix through a tanh bends four samples in a hundred, and
 * those four carry harmonics nobody wrote. Below the corner this is exactly
 * linear, and only the peaks are rounded off.
 */
function knee(x) {
	const over = Math.abs(x) - 0.72;
	if (over <= 0) return x;
	return Math.sign(x) * (0.72 + 0.28 * Math.tanh(over / 0.28));
}

/**
 * A two-pole resonant lowpass, the state variable kind. The cutoff is given
 * fresh every sample so it can follow an envelope, and the sine it needs comes
 * from the same table the oscillators read rather than from Math.
 */
function filter() {
	let low = 0;
	let band = 0;
	return (input, cut, q) => {
		const f = 2 * lookup(SINE, Math.min(6000, Math.max(60, cut)) / (2 * RATE));
		low += f * band;
		const high = input - low - q * band;
		band += f * high;
		return low;
	};
}

/** The same filter, taking its band output instead: noise becomes a breath. */
function bandpass() {
	let low = 0;
	let band = 0;
	return (input, cut, q) => {
		const f = 2 * lookup(SINE, Math.min(6000, Math.max(60, cut)) / (2 * RATE));
		low += f * band;
		const high = input - low - q * band;
		band += f * high;
		return band;
	};
}

/** Two of those in series at one cutoff: 24 dB an octave, no resonant bump. */
function slope(cut) {
	const one = filter();
	const two = filter();
	return (input) => two(one(input, cut, 1.4), cut, 1.4);
}

/**
 * A cross-fed delay: what goes in comes back on the other side, half a pulse
 * later, a little darker each time. One struck note becomes a line of them
 * walking outward, which is the rippling.
 */
function pingpong(length, stereo) {
	const left = new Float64Array(length);
	const right = new Float64Array(length);
	const feedback = 0.58;
	let at = 0;
	let dampL = 0;
	let dampR = 0;
	const pair = [0, 0];
	return (input) => {
		const outL = left[at];
		const outR = right[at];
		dampL = dampL * 0.42 + outR * 0.58;
		dampR = dampR * 0.42 + outL * 0.58;
		left[at] = input * 0.6 + dampL * feedback;
		right[at] = input * 0.4 + dampR * feedback;
		at = (at + 1) % length;
		pair[0] = input * 0.7 + outL;
		pair[1] = stereo ? input * 0.7 + outR : pair[0];
		return pair;
	};
}

/**
 * A plain Schroeder reverb: six combs in parallel for the body, four allpasses
 * in series to smear it, the right channel offset from the left so the tail is
 * wide. The feedback is set long on purpose, since the tail is most of what
 * makes this kind of music feel like a room rather than a synthesiser.
 */
function reverb(stereo) {
	const combs = [1116, 1188, 1277, 1356, 1422, 1491];
	const passes = [556, 441, 341, 225];
	const offset = 23;
	const feedback = 0.942;
	const damp = 0.32;

	const make = (sizes, shift) =>
		sizes.map((size) => ({
			line: new Float64Array(size + shift),
			at: 0,
			store: 0,
		}));

	const left = { combs: make(combs, 0), passes: make(passes, 0) };
	const right = stereo ? { combs: make(combs, offset), passes: make(passes, offset) } : null;

	const run = (side, input) => {
		let sum = 0;
		for (const comb of side.combs) {
			const out = comb.line[comb.at];
			comb.store = out * (1 - damp) + comb.store * damp;
			comb.line[comb.at] = input + comb.store * feedback;
			comb.at = (comb.at + 1) % comb.line.length;
			sum += out;
		}
		let value = sum / side.combs.length;
		for (const pass of side.passes) {
			const out = pass.line[pass.at];
			pass.line[pass.at] = value + out * 0.5;
			pass.at = (pass.at + 1) % pass.line.length;
			value = out - value;
		}
		return value;
	};

	const pair = [0, 0];
	return (a, b) => {
		pair[0] = run(left, a * 0.5);
		pair[1] = right ? run(right, b * 0.5) : pair[0];
		return pair;
	};
}

/** `A3`, `C#4`, `Eb1`: the note, then the octave, as midi. */
export function midi(note) {
	const parts = /^([a-gA-G][b#]?)(-?\d)$/.exec(note.trim());
	if (!parts) throw new Error(`${note} is not a note name`);
	return (Number(parts[2]) + 1) * 12 + NOTES[parts[1].toLowerCase()];
}

export function hertz(note, shift = 0) {
	return 440 * 2 ** ((note + shift - 69) / 12);
}

/** One cycle of a sine, which every oscillator here reads. */
function sineTable(size) {
	const table = new Float64Array(size + 1);
	for (let i = 0; i <= size; i++) table[i] = Math.sin((2 * Math.PI * i) / size);
	return table;
}

/**
 * A table, read with a straight line between neighbours. The error is far
 * below anything audible here, and this is what keeps a seventy minute render
 * to a few minutes of arithmetic.
 */
function lookup(table, phase, already = false) {
	const size = table.length - 1;
	let turn = already ? phase : phase % 1;
	if (turn < 0) turn += 1;
	const x = turn * size;
	const i = x | 0;
	const f = x - i;
	return table[i] + (table[i + 1] - table[i]) * f;
}

/** A small deterministic generator, so --seed means what it says. */
function mulberry(start) {
	let a = start >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

/** The note that travels beside the file: its hash, its settings, its chords. */
export function sidecarNote(ctx, hash) {
	const { pretty, stamped, minutes, pulses, pings, chordSeconds, rollSeconds, strike, seed } = ctx;
	const { moodWord, keyWord, progression: PROGRESSION } = ctx;
	return `---
tags: [music, drone]
hash: ${hash}
key: ${pretty}
rendered: ${stamped}
minutes: ${trimNumber(minutes)}
pulse: ${pulses}
ping: ${pings}
chord: ${trimNumber(chordSeconds)}
seed: ${seed}
---

Rendered here rather than downloaded, by \`drone.mjs\`, and written from a
transcription of the genre rather than from taste: six chords of about
${trimNumber(chordSeconds)} seconds, each rolled note by note over ${trimNumber(rollSeconds)} seconds
and struck in ${trimNumber(strike)}, holding unevenly so that two chords ring through each
other at every change, over a root pulsing ${pulses} times a minute, with a struck
bar walking the chord ${pings} times a minute.

${PROGRESSION.map((chord) => chord.name).join(" · ")}

To hear it again at another length or in another key:

\`\`\`
node drone.mjs --minutes ${trimNumber(minutes)} --mood ${moodWord} --key ${keyWord} --seed ${seed}
\`\`\`
`;
}

function trimNumber(value) {
	return String(Number(Number(value).toFixed(2))).replace(/\.00$/, "");
}

/* ------------------------------------------------------------------ *
 * The command line half. Every Node call in this file is below this   *
 * line and behind a dynamic import, so the half above it loads in a   *
 * browser.                                                            *
 * ------------------------------------------------------------------ */

function usage() {
	console.log(`A long meditative drone, rendered here.

  node drone.mjs [options]

  --minutes N     how long, in minutes (default 10)
  --out PATH      folder to write into, or a path ending .mp3 (default .)
  --name TEXT     what to call it (default is made from the key and length)
  --mood WORD     bright or calm (default bright)
  --key NOTE      the key it sits in: a, c#, eb and so on (default a)
  --kbps N        mp3 bitrate (default 64, which is plenty for a pad)
  --pulse N       pulses a minute in the low end (default 68)
  --ping N        mallet notes a minute (default 30, 0 for none)
  --chord SEC     seconds a chord holds (default 10, as transcribed)
  --roll SEC      seconds a chord takes to arrive, note by note (default 1.4)
  --strike SEC    how fast one note arrives (default 0.12, as transcribed)
  --ring N        how long notes hold on, 0.5 to 3 (default 1)
  --seed N        the same number gives the same piece back (default 7)
  --score FILE    play a transcribed score instead of the progression:
                  one note a line, onset, midi, peak dB, seconds held
  --mono          one channel, half the size, no stereo drift
  --raw           write signed 16 bit samples rather than an mp3, which is
                  what the conformance checks compare
  --no-sidecar    just the mp3, without the note beside it

  Ten minutes at the defaults is around 5 MB.`);
}

async function main() {
	const { spawn } = await import("node:child_process");
	const { createHash } = await import("node:crypto");
	const { createReadStream, createWriteStream, readFileSync } = await import("node:fs");
	const { mkdir, stat, writeFile } = await import("node:fs/promises");
	const { homedir } = await import("node:os");
	const { basename, join, resolve } = await import("node:path");

	const args = process.argv.slice(2);
	if (args.includes("--help") || args.includes("-h")) {
		usage();
		return;
	}

	const opt = (name, fallback) => {
		const at = args.indexOf(name);
		return at === -1 || at + 1 >= args.length ? fallback : args[at + 1];
	};
	const flag = (name) => args.includes(name);
	const untilde = (path) => (path.startsWith("~") ? join(homedir(), path.slice(1)) : path);
	const die = (message) => {
		console.error(`${basename(process.argv[1])}: ${message}`);
		process.exit(1);
	};

	const scorePath = opt("--score", "");
	let ctx;
	try {
		ctx = settings({
			minutes: opt("--minutes", DEFAULTS.minutes),
			kbps: opt("--kbps", DEFAULTS.kbps),
			pulse: opt("--pulse", DEFAULTS.pulse),
			ping: opt("--ping", DEFAULTS.ping),
			chord: opt("--chord", DEFAULTS.chord),
			roll: opt("--roll", DEFAULTS.roll),
			strike: opt("--strike", DEFAULTS.strike),
			ring: opt("--ring", DEFAULTS.ring),
			seed: opt("--seed", DEFAULTS.seed),
			key: opt("--key", DEFAULTS.key),
			mood: opt("--mood", DEFAULTS.mood),
			stereo: !flag("--mono"),
			score: scorePath ? readFileSync(untilde(scorePath), "utf8") : null,
		});
	} catch (error) {
		die(error.message.replace(/^(\w+)/, "--$1"));
	}

	const raw = flag("--raw");
	const out = resolve(untilde(String(opt("--out", "."))));
	const suffix = raw ? ".pcm" : ".mp3";
	const name = String(
		opt("--name", `Drone in ${ctx.pretty}, ${trimNumber(ctx.minutes)} min`)
	).replace(/\.(mp3|pcm)$/i, "");
	const named = out.toLowerCase().endsWith(suffix);
	const target = named ? out : join(out, `${name}${suffix}`);
	await mkdir(named ? resolve(target, "..") : out, { recursive: true });

	console.log(
		`${trimNumber(ctx.minutes)} minutes in ${ctx.pretty}, ${ctx.pulses} pulses a minute, seed ${ctx.seed}`
	);
	console.log(
		ctx.score
			? `playing ${ctx.score.length} transcribed notes from ${scorePath}`
			: `${ctx.progression.length} chords of ${trimNumber(ctx.chordSeconds)}s, rolled over ${trimNumber(
					ctx.rollSeconds
				)}s, struck in ${trimNumber(ctx.strike)}s${ctx.pings ? `, pinging ${ctx.pings} a minute` : ""}`
	);
	console.log(`writing ${target}`);

	let sink;
	let closed;
	if (raw) {
		sink = createWriteStream(target);
		closed = new Promise((keep, drop) => {
			sink.on("close", keep);
			sink.on("error", drop);
		});
	} else {
		const lame = spawn(
			"ffmpeg",
			[
				"-hide_banner", "-loglevel", "error", "-y",
				"-f", "s16le", "-ar", String(RATE), "-ac", String(ctx.channels), "-i", "pipe:0",
				"-c:a", "libmp3lame", "-b:a", `${ctx.kbps}k`,
				"-metadata", `title=${name}`,
				"-metadata", "artist=drone.mjs",
				"-metadata", `comment=rendered by drone.mjs at ${ctx.stamped}, seed ${ctx.seed}`,
				"-metadata", `date=${ctx.stamped.slice(0, 10)}`,
				target,
			],
			{ stdio: ["pipe", "inherit", "inherit"] }
		);
		lame.on("error", (error) => die(`ffmpeg would not start: ${error.message}`));
		closed = new Promise((keep, drop) => {
			lame.on("close", (code) => (code === 0 ? keep() : drop(new Error(`ffmpeg exited ${code}`))));
		});
		sink = lame.stdin;
	}

	/**
	 * The engine hands out an `Int16Array` in the host's own byte order and
	 * this packs it little endian, which is the one place in the pipeline an
	 * endianness bug could hide: `-f s16le` is a promise about bytes, and a
	 * zero-copy view of the engine's block would only keep that promise on a
	 * little endian machine. Packing also copies, which the reused block
	 * needs, since the stream keeps a reference to whatever it is handed.
	 */
	const pack = (block) => {
		const bytes = Buffer.allocUnsafe(block.length * 2);
		for (let i = 0; i < block.length; i++) bytes.writeInt16LE(block[i], i * 2);
		return bytes;
	};
	const write = (block) =>
		sink.write(pack(block))
			? undefined
			: new Promise((keep) => sink.once("drain", keep));

	let told = -1;
	await render(ctx, write, (percent) => {
		if (percent === told) return;
		told = percent;
		process.stdout.write(percent === 100 ? "\r100%\n" : `\r${percent}% `);
	});
	sink.end();
	await closed;

	const size = (await stat(target)).size;
	console.log(`${(size / (1024 * 1024)).toFixed(1)} MB, rendered ${ctx.stamped}`);

	if (!raw && !flag("--no-sidecar")) {
		const sum = createHash("sha256");
		for await (const chunk of createReadStream(target)) sum.update(chunk);
		const note = `${target}.md`;
		await writeFile(note, sidecarNote(ctx, sum.digest("hex")), "utf8");
		console.log(`and ${note}`);
	}
}

if (typeof process !== "undefined" && Array.isArray(process.argv) && process.argv[1]) {
	const { pathToFileURL } = await import("node:url");
	if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
}
