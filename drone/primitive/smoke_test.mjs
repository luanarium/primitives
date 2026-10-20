/**
 * Conformance checks for the engine. Run them, do not read them.
 *
 *   node smoke_test.mjs
 *   node smoke_test.mjs --prove      # breaks the seal on purpose
 *
 * One check per behaviour anything downstream depends on, each printing what
 * it saw, so the output doubles as a transcript of how this thing behaves. A
 * port that passes all ten sounds the same: the first check is a hash of the
 * actual samples, so there is nothing for taste to argue with.
 *
 * Two more carry their own counter-example, because a check that
 * never saw the behaviour it names is worse than no check: the band profile is
 * also run against white noise and the organ check against a deliberately
 * locked voice, and both must fail there.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
	COMPOSER,
	DEFAULTS,
	RATE,
	hertz,
	midi,
	normaliseScore,
	render,
	renderToArray,
	settings,
	sidecarNote,
} from "./drone.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const bundle = join(here, "..");
const prove = process.argv.includes("--prove");

/**
 * Ten seconds of samples, hashed little endian, for three configurations.
 *
 * These came off the generator as it stood when it was parked, and they are
 * the seal on the whole bundle: the arithmetic was lifted into this file
 * unchanged from the version Skybox carried, and proved against it sample for
 * sample rather than by ear.
 */
const SEAL = {
	"stereo, the defaults": {
		options: { minutes: 10 / 60, seed: 7 },
		sha: "ef5229c45cf304288eaace68ec25394b9d2fb8650e11bd89d56f103a0a7bc844",
	},
	"mono, no mallets": {
		options: { minutes: 10 / 60, seed: 7, stereo: false, ping: 0 },
		sha: "43f6c6ead810cd5ca085b723f9136ac12160dce01c941244d5275ec6b285cbe5",
	},
	"a transcribed score": {
		options: { minutes: 10 / 60, seed: 7, score: "samples/example-minute-score.tsv" },
		sha: "635e24cf9f4c8ca69e1abee035a4f817a6f85469dbb4ca9e9e15ef6e8e757f46",
	},
};
/** The score the third seal plays, so a changed fixture is not read as a broken engine. */
const FIXTURE = "4df7c0a58282ed6181c743254d05554c477576ad2d09ee1441b07ca098b2d83d";

let failures = 0;
let checks = 0;

function check(name, saw, ok) {
	checks++;
	const good = ok === undefined ? Boolean(saw) : ok;
	if (!good) failures++;
	console.log(`${good ? "ok  " : "FAIL"}  ${name}`);
	for (const line of String(saw).split("\n")) console.log(`        ${line}`);
}

/** Samples as the encoder gets them: signed 16 bit, interleaved, little endian. */
function packed(all) {
	const bytes = Buffer.allocUnsafe(all.length * 2);
	for (let i = 0; i < all.length; i++) bytes.writeInt16LE(all[i], i * 2);
	return bytes;
}

function sha(bytes) {
	return createHash("sha256").update(bytes).digest("hex");
}

function scoreFile(path) {
	return readFileSync(join(bundle, path), "utf8");
}

/**
 * Energy in a band, averaged over nine probes a third of an octave wide, by
 * Goertzel rather than an FFT because nine numbers is all this needs.
 */
function bandProfile(all, channels) {
	const mono = new Float64Array(Math.floor(all.length / channels));
	for (let i = 0; i < mono.length; i++) {
		let sum = 0;
		for (let c = 0; c < channels; c++) sum += all[i * channels + c];
		mono[i] = sum / (channels * 32768);
	}
	const power = (hz) => {
		const c = 2 * Math.cos((2 * Math.PI * hz) / RATE);
		let s1 = 0;
		let s2 = 0;
		for (let i = 0; i < mono.length; i++) {
			const s0 = mono[i] + c * s1 - s2;
			s2 = s1;
			s1 = s0;
		}
		return (s1 * s1 + s2 * s2 - c * s1 * s2) / mono.length;
	};
	const band = (centre) => {
		let sum = 0;
		for (let k = -4; k <= 4; k++) sum += power(centre * 2 ** (k / 12));
		return 10 * Math.log10(sum / 9 + 1e-30);
	};
	const bands = [250, 500, 1000, 2000, 4000].map(band);
	return bands.map((value) => value - bands[0]);
}

/** The genre, in two numbers: warm below 1 kHz, nothing to speak of above 2. */
function readsLikeTheGenre(profile) {
	return profile[3] < -3 && profile[4] < -20;
}

console.log(`drone.mjs conformance, node ${process.version}\n`);

/* 1. The seal. ---------------------------------------------------------- */

for (const [what, { options, sha: want }] of Object.entries(SEAL)) {
	const given = { ...options };
	if (given.score) given.score = scoreFile(given.score);
	if (prove && what.startsWith("stereo")) given.seed = 8;
	const all = await renderToArray(settings(given));
	const got = sha(packed(all));
	check(
		`ten seconds of "${what}" hashes to the parked engine's samples`,
		`${all.length} samples, sha256 ${got.slice(0, 16)}…\n` +
			`want ${want.slice(0, 16)}… ${got === want ? "(same)" : "(DIFFERENT)"}`,
		got === want
	);
}

check(
	"the score fixture is the one those hashes were taken against",
	`samples/example-minute-score.tsv sha256 ${sha(scoreFile("samples/example-minute-score.tsv")).slice(0, 16)}…`,
	sha(scoreFile("samples/example-minute-score.tsv")) === FIXTURE
);

/* 2. A seed means what it says. ------------------------------------------ */

const twice = [
	await renderToArray(settings({ minutes: 2 / 60, seed: 11 })),
	await renderToArray(settings({ minutes: 2 / 60, seed: 11 })),
];
const other = await renderToArray(settings({ minutes: 2 / 60, seed: 12 }));
check(
	"the same seed gives the same piece back, a different one does not",
	`seed 11 twice: ${sha(packed(twice[0])).slice(0, 12)} and ${sha(packed(twice[1])).slice(0, 12)}\n` +
		`seed 12:       ${sha(packed(other)).slice(0, 12)}`,
	sha(packed(twice[0])) === sha(packed(twice[1])) && sha(packed(other)) !== sha(packed(twice[0]))
);

/* 3. The ceiling. ------------------------------------------------------- */

const loud = await renderToArray(settings({ minutes: 20 / 60, seed: 3 }));
let peak = 0;
for (const value of loud) peak = Math.max(peak, Math.abs(value));
const dbfs = 20 * Math.log10(peak / 32767);
check(
	"the limiter lands the piece under the ceiling without leaving it quiet",
	`peak ${peak} of 32767, ${dbfs.toFixed(2)} dBFS`,
	peak <= 32767 && dbfs > -6 && dbfs < -0.1
);

/* 4. The band profile: the one measurement that says this is the genre. -- */

const profile = bandProfile(loud, 2);
const noise = new Int16Array(RATE * 4);
let state = 1;
for (let i = 0; i < noise.length; i++) {
	state = (state * 1103515245 + 12345) & 0x7fffffff;
	noise[i] = ((state / 0x7fffffff) * 2 - 1) * 8000;
}
const noiseProfile = bandProfile(noise, 1);
const shown = (p) => p.map((v, i) => `${[250, 500, 1000, 2000, 4000][i]}Hz ${v.toFixed(1)}`).join("  ");
check(
	"warm below 1 kHz and nothing to speak of above 2, as the genre measures",
	`rendered: ${shown(profile)}\n` +
		`white noise through the same check: ${shown(noiseProfile)} ${
			readsLikeTheGenre(noiseProfile) ? "(PASSED, so the check is vacuous)" : "(fails, so the check is checking)"
		}`,
	readsLikeTheGenre(profile) && !readsLikeTheGenre(noiseProfile)
);

/* 5. A note is not an organ. -------------------------------------------- */

const roll = (() => {
	let a = 99;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
})();
const note = { hz: 220, pan: 0.5 };
const first = COMPOSER.voiceOf(note, roll);
const second = COMPOSER.voiceOf(note, roll);
const exact = (parts) =>
	parts.filter((part) => {
		const ratio = (part.base * RATE) / 220;
		return Math.abs(ratio - Math.round(ratio)) < 1e-9;
	}).length;
const phases = new Set(first.map((part) => part.phase));
const locked = [1, 2, 3, 4].map((mult) => ({ base: (220 * mult) / RATE, phase: 0 }));
check(
	"no partial of a note is locked to its fundamental, and two notes of one pitch differ",
	`partials: ${first.map((part) => (part.base * RATE).toFixed(2)).join(", ")}\n` +
		`the same pitch again: ${second.map((part) => (part.base * RATE).toFixed(2)).join(", ")}\n` +
		`exact multiples: ${exact(first)}, distinct starting phases: ${phases.size} of ${first.length}\n` +
		`an organ stop through the same check: ${exact(locked)} exact multiples ${
			exact(locked) === 0 ? "(PASSED, so the check is vacuous)" : "(fails, so the check is checking)"
		}`,
	exact(first) === 0 &&
		phases.size === first.length &&
		first[0].base !== second[0].base &&
		exact(locked) > 0
);

/* 6. The composer seam: somebody else's notes, this engine's voice. ----- */

const one = {
	buildScore: () => ({
		notes: [
			{
				at: 0.1,
				hz: 440,
				step: 440 / RATE,
				rise: 0.1,
				sustain: 3,
				release: 0.5,
				life: 3.6,
				gain: 0.3,
				pan: 0.5,
			},
		],
		roots: [],
	}),
	buildPings: () => [],
};
const single = await renderToArray(settings({ minutes: 4 / 60, seed: 5, ping: 0, composer: one }));
const sung = bandProfile(single, 2);
const probe = (hz) => {
	const c = 2 * Math.cos((2 * Math.PI * hz) / RATE);
	let s1 = 0;
	let s2 = 0;
	for (let i = 0; i < single.length / 2; i++) {
		const x = (single[i * 2] + single[i * 2 + 1]) / 65536;
		const s0 = x + c * s1 - s2;
		s2 = s1;
		s1 = s0;
	}
	return 10 * Math.log10((s1 * s1 + s2 * s2 - c * s1 * s2) / (single.length / 2) + 1e-30);
};
const asked = probe(440);
const unasked = probe(440 * 2 ** (6 / 12));
check(
	"an overridden buildScore is what gets played, and nothing else is",
	`one note at 440 Hz asked for\n` +
		`440 Hz: ${asked.toFixed(1)} dB, a tritone up: ${unasked.toFixed(1)} dB, ${(asked - unasked).toFixed(1)} dB apart`,
	asked - unasked > 20
);

/* 7. Backpressure, and every sample accounted for. ---------------------- */

const ctx = settings({ minutes: 3 / 60, seed: 2 });
let total = 0;
let blocks = 0;
let biggest = 0;
await render(ctx, async (block) => {
	await new Promise((keep) => setImmediate(keep));
	total += block.length;
	blocks++;
	biggest = Math.max(biggest, block.length);
});
check(
	"a sink that returns a promise is waited for, and gets every sample once",
	`${blocks} blocks, biggest ${biggest}, ${total} samples for ${ctx.frames} frames of ${ctx.channels}`,
	total === ctx.frames * ctx.channels && biggest <= RATE * ctx.channels
);

/* 8. The refusals. ------------------------------------------------------ */

const refusals = [
	["minutes", { minutes: 0 }],
	["chord", { chord: 2 }],
	["roll", { roll: 20 }],
	["key", { key: "h" }],
	["mood", { mood: "sad" }],
	["ring", { ring: 9 }],
];
const said = [];
for (const [flag, options] of refusals) {
	let message = "took it";
	try {
		settings(options);
	} catch (error) {
		message = error.message;
	}
	said.push(`${flag}: ${message}`);
}
check(
	"every setting that cannot work is refused by name before a sample is made",
	said.join("\n"),
	said.every((line, i) => line.startsWith(`${refusals[i][0]}:`) && !line.endsWith("took it")) &&
		said.every((line) => line.includes(refusals[said.indexOf(line)][0]))
);

/* 9. The transcriber, round trip. --------------------------------------- */

const ffmpeg = spawnSync("ffmpeg", ["-version"]);
const python = spawnSync("python3", ["--version"]);
if (ffmpeg.status !== 0 || python.status !== 0) {
	check("the transcriber reads back a note this engine played", "skipped: ffmpeg or python3 missing", true);
} else {
	const wav = join(bundle, "primitive", ".round-trip.wav");
	const wrote = spawnSync(
		"ffmpeg",
		["-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ar", String(RATE), "-ac", "2", "-i", "pipe:0", wav],
		{ input: packed(single) }
	);
	const got = spawnSync("python3", ["-I", join(bundle, "analysis", "transcribe.py"), wav, "0", "4"], {
		encoding: "utf8",
	});
	const events = (got.stdout || "")
		.split("\n")
		.filter((line) => line && !line.startsWith("#"))
		.map((line) => line.split("\t").map(Number));
	const loudest = events.sort((a, b) => b[2] - a[2])[0] || [];
	spawnSync("rm", ["-f", wav]);
	check(
		"the transcriber reads back a note this engine played",
		`played A4, midi ${midi("A4")}, 440.00 Hz\n` +
			`${events.length} events transcribed, loudest is midi ${loudest[1]} at ${loudest[2]} dB held ${loudest[3]}s\n` +
			`${wrote.status === 0 ? "" : "ffmpeg refused the samples"}`,
		loudest[1] === midi("A4")
	);
}

/* 10. The note beside the file. ----------------------------------------- */

const beside = sidecarNote(settings({ minutes: 10, key: "c#", mood: "calm", seed: 42 }), "deadbeef");
check(
	"the sidecar says what was rendered and what to run to hear it again",
	beside.split("\n").slice(0, 9).join("\n"),
	beside.includes("hash: deadbeef") &&
		/rendered: \d{4}-\d\d-\d\d \d\d:\d\d/.test(beside) &&
		beside.includes("--key c#") &&
		beside.includes("--seed 42") &&
		beside.includes("tags: [music, drone]")
);

/* ----------------------------------------------------------------------- */

console.log(
	`\n${checks - failures} of ${checks} checks passed${prove ? ", with --prove breaking one on purpose" : ""}`
);
if (prove && failures === 0) {
	console.log("--prove broke nothing, so the checks are not checking");
	process.exit(1);
}
process.exit(prove ? (failures > 0 ? 0 : 1) : failures > 0 ? 1 : 0);
