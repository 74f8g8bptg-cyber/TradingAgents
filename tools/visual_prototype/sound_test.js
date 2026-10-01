// Deterministic tests for the Stellar sound layer's Director (Node only, no browser, no audio device):
//   node tools/visual_prototype/sound_test.js
// The Director is pure: Life events + Life state + a listener -> sound requests and ambience levels. These tests drive it
// with a real Life simulation and with synthetic events (docs/STELLAR_SOUND_SYSTEM_V1.md §J). The Web Audio engine is
// exercised by the browser smoke test.
const fs = require("fs");
const path = require("path");
const L = require("./templates/stellar_life.js");
const S = require("./templates/stellar_sound.js");

const page = fs.readFileSync(path.resolve(__dirname, "../../docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html"), "utf8");
const i0 = page.indexOf("const D=");
const D = JSON.parse(page.slice(i0 + 8, page.indexOf("\n", i0)).replace(/;$/, ""));
const world = L.buildWorld(D);
const fails = [];
const ok = (c, m) => { if (!c) fails.push(m); return c; };
const roomPt = (id, s = 0, t = 0) => { const rm = world.rooms[id]; return { x: rm.cx + rm.u[0] * s + rm.v[0] * t, y: rm.cy + rm.u[1] * s + rm.v[1] * t }; };
const hub = (id) => ({ x: D.hubs[id][0], y: D.hubs[id][1] });
const listenAt = (p, z = 2.6) => ({ x: p.x, y: p.y, z });

// 1 every Life event type is mapped (a resolver or an explicit silence), and reaches the Director
ok(L.EVENTS.every((e) => e in S.EVENT_MAP), "every Life event type has an explicit sound mapping");
ok(Object.keys(S.EVENT_MAP).every((e) => L.EVENTS.includes(e)), "the sound map holds no event Life does not emit");
for (const [cue] of Object.entries(S.CUES)) ok(typeof S.RECIPES[cue] === "function", `cue ${cue} has a recipe`);
{
  const dir = S.createDirector({ D, world, seed: "t" });
  for (const type of L.EVENTS) dir.onEvent({ type, t: 0, ambient: true, actor: "CHR-023", room: "H-HAB", door: "DR-L1", state: "PREPARING", spot: "habitat.cafe_seat_1" });
  let threw = null; try { dir.tick(100, listenAt(hub("H-HAB")), { snapshot: [{ id: "CHR-023", kind: "agent", x: 1377, y: 692, phase: "dwell", room: "H-HAB", stride: 0 }], cinema: "EMPTY" }); } catch (e) { threw = e; }
  ok(!threw, "resolving every event type never throws");
  ok(L.EVENTS.every((e) => dir.stats.seen[e] === 1), "every event type reaches the sound layer");
  // 2 unknown and malformed events are ignored, never crash
  for (const ev of [{ type: "NOT_A_LIFE_EVENT" }, null, {}, { type: 42 }]) dir.onEvent(ev);
  let t2 = null; try { dir.tick(100, listenAt(hub("H-HAB")), { snapshot: [], cinema: "EMPTY" }); } catch (e) { t2 = e; }
  ok(!t2 && dir.stats.unknown >= 4, "unknown or malformed events are counted and ignored");
}
// 3 dog sounds only in H-HAB / R4; reserved rooms make no activity sound
{
  const dir = S.createDirector({ D, world, seed: "t" });
  const dogAt = (room, p) => ({ snapshot: [{ id: "DEC-009", kind: "dog", x: p.x, y: p.y, phase: "dwell", room, stride: 0 }], cinema: "EMPTY" });
  dir.onEvent({ type: "DOG_START_PLAY", t: 1, actor: "DEC-009", room: "L1" });
  let out = dir.tick(100, listenAt({ x: 474, y: 430 }), dogAt("L1", { x: 474, y: 430 }));
  ok(out.plays.every((p) => p.group !== "DOG") && dir.stats.blocked.dog >= 1, "a dog cue outside H-HAB/R4 is blocked");
  dir.onEvent({ type: "DOG_START_PLAY", t: 2000, actor: "DEC-009", room: "R4" });
  const r4 = roomPt("R4");
  out = dir.tick(1000, listenAt(r4), dogAt("R4", r4));
  ok(out.plays.some((p) => p.cue === "dog.toy"), "the dog plays in R4 and is heard");
  dir.onEvent({ type: "DOOR_OPEN", t: 3000, door: "DR-L5" });
  dir.onEvent({ type: "DOOR_OPEN", t: 3000, door: "DR-R5" });
  dir.onEvent({ type: "AGENT_SIT", t: 3000, actor: "X", room: "R6" });
  out = dir.tick(1000, listenAt(roomPt("R5")), { snapshot: [{ id: "X", kind: "agent", x: roomPt("R6").x, y: roomPt("R6").y, phase: "dwell", room: "R6", stride: 0 }], cinema: "EMPTY" });
  ok(out.plays.length === 0 || out.plays.every((p) => !["L5", "L8", "R5", "R6"].includes(p.room)), "no activity sound in a reserved room");
  ok(dir.stats.blocked.reserved >= 3, "reserved-room cues are blocked");
  ok(!["L5", "L8", "R5", "R6"].some((r) => r in S.BEDS), "reserved rooms have no ambience bed");
}
// 4 no runaway: an event storm stays inside the per-tick budget and the queue is bounded
{
  const dir = S.createDirector({ D, world, seed: "t" });
  for (let i = 0; i < 5000; i++) dir.onEvent({ type: "DOOR_OPEN", t: i, door: ["DR-L1", "DR-L2", "DR-N-CMD", "DR-CMD-HAB"][i % 4] });
  const out = dir.tick(100, listenAt({ x: 600, y: 560 }, 1.5), { snapshot: [], cinema: "EMPTY" });
  ok(out.plays.length <= S.MAX_PLAYS, `an event storm is capped (${out.plays.length} plays)`);
  ok(dir.stats.dropped >= 4000, "the event queue is bounded");
  const doors = out.plays.filter((p) => p.cue.startsWith("door."));
  ok(doors.length <= 4, `per-door gates stop machine-gunning (${doors.length} door sounds for 5000 events on 4 doors)`);
}
// 5 ambience: transitions are smooth, rooms differ, R3 is isolated, reserved stay silent
{
  const dir = S.createDirector({ D, world, seed: "t" });
  const hab = hub("H-HAB"), r1 = roomPt("R1"), r3 = roomPt("R3", 10, 0);
  let prev = null, maxJump = 0, out;
  for (let i = 0; i < 40; i++) { out = dir.tick(100, listenAt(hab), { snapshot: [], cinema: "EMPTY" }); }
  const atHab = { ...out.beds };
  for (let i = 0; i <= 60; i++) { // walk the listener from H-HAB into R1 over 6 s
    const k = Math.min(1, i / 30); out = dir.tick(100, listenAt({ x: hab.x + (r1.x - hab.x) * k, y: hab.y + (r1.y - hab.y) * k }), { snapshot: [], cinema: "EMPTY" });
    if (prev) for (const key of Object.keys(out.beds)) maxJump = Math.max(maxJump, Math.abs(out.beds[key] - (prev[key] || 0)));
    prev = out.beds;
  }
  ok(atHab["H-HAB"] > 0.5 && atHab.R1 < atHab["H-HAB"], "in H-HAB the habitat bed leads");
  ok(out.beds.R1 > 0.5 && out.beds.R1 > out.beds["H-HAB"], "in R1 the zen bed leads (H-HAB → R1 transition)");
  ok(maxJump < 0.15, `ambience transitions are smooth (largest step ${maxJump.toFixed(3)} per 100 ms)`);
  for (let i = 0; i < 60; i++) out = dir.tick(100, listenAt(r3), { snapshot: [], cinema: "EMPTY" });
  const others = Object.entries(out.beds).filter(([k]) => k !== "R3" && k !== "station").reduce((m, [, v]) => Math.max(m, v), 0);
  ok(out.listenerRoom === "R3" && others < 0.13 && out.beds.station < 0.13, `R3 is acoustically isolated (loudest other bed ${others.toFixed(3)})`);
  const cor = dir.tick(100, listenAt({ x: 600, y: 560 }), { snapshot: [], cinema: "EMPTY" });
  ok(cor.listenerRoom === "COR-N", "the corridor is recognised");
}
// 6 cinema states drive the R2 layers; R1 pad only while someone meditates
{
  const dir = S.createDirector({ D, world, seed: "t" });
  const r2 = roomPt("R2"), r1 = roomPt("R1");
  let out; for (let i = 0; i < 60; i++) out = dir.tick(100, listenAt(r2), { snapshot: [], cinema: "SCREENING" });
  ok(out.beds.cinemaRumble > 0.4, "SCREENING raises the screening layer in R2");
  for (let i = 0; i < 80; i++) out = dir.tick(100, listenAt(r2), { snapshot: [], cinema: "EMPTY" });
  ok(out.beds.cinemaRumble < 0.02 && out.beds.cinemaFan < 0.02, "EMPTY stops the cinema layers (loop stops)");
  for (let i = 0; i < 60; i++) out = dir.tick(100, listenAt(r1), { snapshot: [], cinema: "EMPTY" });
  ok(out.beds.zenPad < 0.02, "R1 pad silent without meditation");
  const med = [{ id: "A", kind: "agent", x: r1.x, y: r1.y, phase: "dwell", room: "R1", state: "MEDITATING", stride: 0 }];
  for (let i = 0; i < 60; i++) out = dir.tick(100, listenAt(r1), { snapshot: med, cinema: "EMPTY" });
  ok(out.beds.zenPad > 0.4, "MEDITATING in R1 brings in the calm pad");
}
// 7 a real Life soak: listener tours the station; every heard cue maps to a real event or state, dog cues only in H-HAB/R4
{
  const life = L.create(world, { seed: "sound-soak" });
  const dir = S.createDirector({ D, world, seed: "sound-soak" });
  life.on("*", (ev) => dir.onEvent(ev));
  const tour = [hub("H-HAB"), roomPt("R4"), roomPt("R1"), roomPt("R2"), hub("H-CMD"), { x: 600, y: 560 }, hub("H-LAB"), roomPt("R3")];
  const heard = {}; let maxPlays = 0; let leak = 0;
  for (let step = 0; step < 36000; step++) { // one simulated hour in 100 ms ticks
    life.step(100);
    const p = tour[Math.floor(step / 4500) % tour.length];
    const out = dir.tick(100, listenAt(p), { snapshot: life.snapshot(), cinema: life.cinema });
    maxPlays = Math.max(maxPlays, out.plays.length);
    for (const pl of out.plays) { heard[pl.cue] = (heard[pl.cue] || 0) + 1; if (pl.group === "DOG" && !["H-HAB", "R4"].includes(pl.room)) leak++; if (["L5", "L8", "R5", "R6"].includes(pl.room)) leak++; }
  }
  ok(leak === 0, "no dog sound outside H-HAB/R4 and no sound from reserved rooms over the soak");
  ok(maxPlays <= S.MAX_PLAYS, "never more than the per-tick budget");
  for (const c of ["door.travel.standard", "door.seal.standard", "door.travel.hub", "door.stop.hub", "step.metal", "step.wood", "seat.sit", "console.wake", "fountain.bubble"]) ok(heard[c] > 0, `soak hears ${c}`);
  ok(L.EVENTS.filter((e) => !["CINEMA_START"].includes(e)).every((e) => !life.events.some((x) => x.type === e) || dir.stats.seen[e] > 0), "every event Life emitted reached the Director");
  console.log(`sound soak: 1 h, ${dir.stats.plays} cues, heard ${JSON.stringify(heard)}`);
}
// 7b doors: the four door sounds follow the physical door, in order, timed to the 0.9 s panel travel; a door that does not
// move makes no sound
{
  const life = L.create(world, { seed: "doorsync" });
  const dir = S.createDirector({ D, world, seed: "doorsync" });
  life.on("*", (ev) => dir.onEvent(ev));
  const fx = life.actors.find((a) => a.code === "FX"); life.step(100); life.assign(fx.id, "CAFE");
  const at = world.doorPos["DR-L1"]; const plays = [];
  for (let i = 0; i < 400; i++) { life.step(100); const o = dir.tick(100, { x: at[0], y: at[1], z: 4 }, { snapshot: life.snapshot(), cinema: life.cinema }); for (const p of o.plays) if (/^door\./.test(p.cue)) plays.push([life.t, p.cue]); }
  const seq = plays.map((p) => p[1].split(".")[1]);
  ok(seq.slice(0, 4).join() === "travel,stop,travelback,seal", `DR-L1 sounds follow the door: ${seq.slice(0, 4).join(",")}`);
  const dt = plays.length >= 2 ? plays[1][0] - plays[0][0] : 0;
  ok(dt >= 800 && dt <= 1100, `the end stop sounds when the panels reach OPEN (${dt} ms after travel starts)`);
  const doorEv = life.events.filter((e) => /^DOOR_/.test(e.type) && e.door === "DR-L1").length;
  ok(plays.length <= doorEv, "no door sound without a door transition");
}
// 8 determinism + lint
{
  const sig = (seed) => { const life = L.create(world, { seed: "d" }); const dir = S.createDirector({ D, world, seed }); life.on("*", (e) => dir.onEvent(e)); const plays = []; for (let i = 0; i < 6000; i++) { life.step(100); const o = dir.tick(100, listenAt(hub("H-HAB")), { snapshot: life.snapshot(), cinema: life.cinema }); for (const p of o.plays) plays.push([i, p.cue, p.gain.toFixed(4), p.rate.toFixed(4)]); } return JSON.stringify(plays); };
  ok(sig("a") === sig("a"), "same seed, same inputs -> the same sounds (determinism)");
  ok(sig("a") !== sig("b"), "a different seed varies the sounds");
  const src = fs.readFileSync(path.join(__dirname, "templates/stellar_sound.js"), "utf8");
  const code = src.replace(/\/\*[\s\S]*?\*\//g, "");
  ok(!/Math\.random\s*\(|Date\.now\s*\(|performance\.now\s*\(/.test(code), "determinism lint: no Math.random, Date.now or performance.now in the sound layer");
  ok(!/starnet|bleeoop|\.wav|\.mp3|\.ogg|fetch\s*\(/i.test(src), "no reference-station names, no audio files, no fetch: the page stays self-contained");
  const lifeSrc = fs.readFileSync(path.join(__dirname, "templates/stellar_life.js"), "utf8");
  ok(!/AudioContext|StellarSound|createOscillator|createGain|\.play\s*\(/.test(lifeSrc), "the Life engine knows nothing about audio playback");
}
// 9 no leak: Director state stays bounded under a long run with many actors coming and going
{
  const dir = S.createDirector({ D, world, seed: "leak" });
  for (let i = 0; i < 20000; i++) { const id = "A" + (i % 500); dir.onEvent({ type: "AGENT_SIT", t: i, actor: id, room: "H-HAB" }); dir.tick(100, listenAt(hub("H-HAB")), { snapshot: [{ id, kind: "agent", x: 1377, y: 692, phase: "walk", room: "H-HAB", stride: i }], cinema: "EMPTY" }); }
  ok(Object.keys(dir.levels).length <= Object.keys(S.BEDS).length, "ambience state is bounded");
}

if (fails.length) { console.error("FAILED:\n  " + fails.join("\n  ")); process.exit(1); }
console.log("sound test passed");
