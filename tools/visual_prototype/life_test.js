// Deterministic tests for the Stellar life layer (Node only, no browser):
//   node tools/visual_prototype/life_test.js
// Loads the life engine and the committed page data, then checks the scenarios of docs/STELLAR_LIFE_SYSTEM_V1.md §9:
// work, leaving the workstation, corridors, H-HAB, R1-R4, the dog occupancy rule, reserved rooms, furniture, doors,
// caps, permissions, determinism and the determinism lint. Exits non-zero on any failure.
const fs = require("fs");
const path = require("path");
const L = require("./templates/stellar_life.js");

const page = fs.readFileSync(path.resolve(__dirname, "../../docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html"), "utf8");
const i0 = page.indexOf("const D=");
const D = JSON.parse(page.slice(i0 + 8, page.indexOf("\n", i0)).replace(/;$/, ""));
const world = L.buildWorld(D);
const fails = [];
const ok = (cond, msg) => { if (!cond) fails.push(msg); return cond; };
const T = L.T;
const H = 3600 * 1000;

// ---------------------------------------------------------------- invariant oracle (independent of the path code)
function where(a) {
  for (const [id, rm] of Object.entries(world.rooms)) {
    const s = (a.x - rm.cx) * rm.u[0] + (a.y - rm.cy) * rm.u[1], t = (a.x - rm.cx) * rm.v[0] + (a.y - rm.cy) * rm.v[1];
    if (Math.abs(s) <= 92.5 && Math.abs(t) <= 57.5 && Math.hypot(a.x - world.hub.x, a.y - world.hub.y) > world.hub.r + 4) return { r: id, s, t };
  }
  const k = world.tileOf(a.x, a.y);
  return { k, r: world.region.get(k) };
}
function checkActor(a, life, tag) {
  const w = where(a);
  // a seat inside furniture is entered on the final leg and left on the first leg only; door crossings into R1-R4 pass the rim
  const nearDoor = Object.values(world.portals).some((p) => Math.hypot(a.x - world.doorPos[p.door][0], a.y - world.doorPos[p.door][1]) < 24);
  const exempt = a.phase === "dwell" || (a.route && ((a.route[a.ri] && a.route[a.ri].final) || a.ri === 0)) || a.fadeUntil || nearDoor;
  if (nearDoor) { ok(a.allow.has("H-HAB"), `${tag}: ${a.id} at an H-HAB door without H-HAB access`); return; }
  const allowRegion = (r) => L.regionAllowed(world, a.allow, r);
  if (w.k) {
    if (!ok(w.r !== undefined, `${tag}: ${a.id} outside the station at ${w.k}`)) return;
    ok(!["L5", "L8"].includes(w.r), `${tag}: ${a.id} inside reserved ${w.r}`);
    ok(allowRegion(w.r), `${tag}: ${a.id} (${a.cls || a.kind}) in forbidden ${w.r}`);
    if (!exempt) {
      ok(!world.blocked.has(w.k), `${tag}: ${a.id} walks through furniture at ${w.k}`);
      const ends = a.route ? [a.route[0].k, a.route[a.route.length - 1].k] : [];
      ok(!world.seats.has(w.k) || ends.includes(w.k), `${tag}: ${a.id} walks over a seat at ${w.k}`);
    }
  } else {
    ok(!["R5", "R6"].includes(w.r), `${tag}: ${a.id} inside reserved ${w.r}`);
    ok(a.allow.has(w.r), `${tag}: ${a.id} in forbidden ${w.r}`);
    if (!exempt) ok(world.rFree(w.r, w.s, w.t, 0), `${tag}: ${a.id} walks through ${w.r} furniture at (${w.s.toFixed(0)},${w.t.toFixed(0)})`);
  }
  if (a.kind === "dog") ok(["H-HAB", "R4"].includes(a.room) && (w.k ? ["H-HAB"].includes(w.r) || world.doorSides[w.r] : w.r === "R4"), `${tag}: dog outside H-HAB/R4 (${a.room}, ${w.r})`);
  if (a.cls === "MP-HOST") ok(a.room === "H-HAB", `${tag}: host left H-HAB`);
  if (a.kind === "agent" && ["L9", "L10"].includes(w.r)) ok(a.home === w.r, `${tag}: ${a.id} in restricted ${w.r}`);
  if (a.spot && a.spot.id) ok(!/recovery_pod/.test(a.spot.id), `${tag}: ambient use of a real-cooldown recovery pod`);
}
function run(life, ms, tag, every) { const end = life.t + ms; while (life.t < end) { life.step(L.STEP); for (const a of life.actors) checkActor(a, life, tag); if (every) every(life); if (fails.length > 40) return; } }
const until = (life, cond, ms, tag) => { const end = life.t + ms; while (life.t < end && !cond()) { life.step(L.STEP); for (const a of life.actors) checkActor(a, life, tag); } return cond(); };
const ev = (life, type, f = () => true) => life.events.filter((e) => e.type === type && f(e));
const agent = (life, code) => life.actors.find((a) => a.code === code && a.kind === "agent");

// ---------------------------------------------------------------- 0 model
ok(Object.keys(world.portals).sort().join() === "DR-R1,DR-R2,DR-R3,DR-R4", "portals are exactly R1-R4 (R5/R6 sealed)");
ok(![...world.cells.values()].some((c) => c.room === "R5" || c.room === "R6"), "R5/R6 have no walk cells");
for (const a of D.anchors) { const p = L.findPath(world, { allow: new Set(world.region.values()) }, world.key(48, 46), world.key(...a.tile)); if (!/^(L5|L8)/.test(a.room)) ok(!!p, `anchor ${a.name} unreachable`); }

// ---------------------------------------------------------------- 1-4 work, leaving, corridor, H-HAB, doors
{
  const life = L.create(world, { seed: "t1" });
  const fx = agent(life, "FX");
  life.step(L.STEP);
  ok(life.assign(fx.id, "CAFE"), "FX may visit the café");
  ok(ev(life, "AGENT_STOP_WORK", (e) => e.actor === fx.id).length === 1, "1/2 leaving the workstation emits AGENT_STOP_WORK");
  ok(until(life, () => fx.phase === "dwell", 6 * 60000, "s2"), "2 FX reaches the café");
  ok(ev(life, "AGENT_EXIT_ROOM", (e) => e.actor === fx.id && e.room === "L1").length >= 1, "2 FX exits L1");
  const corr = ev(life, "AGENT_ENTER_ROOM", (e) => e.actor === fx.id && /^COR-/.test(e.room));
  ok(corr.length >= 1, "3 FX walks through a corridor");
  const hab = ev(life, "AGENT_ENTER_ROOM", (e) => e.actor === fx.id && e.room === "H-HAB");
  ok(hab.length === 1, "4 FX enters H-HAB");
  ok(fx.room === "H-HAB" && fx.state === "SOCIAL" && /cafe_seat/.test(fx.spot.id), "4 FX sits at a café seat");
  ok(ev(life, "AGENT_SIT", (e) => e.actor === fx.id).length === 1, "4 AGENT_SIT at the café");
  // 12 doors: DR-L1 opens before FX enters the corridor and closes after it has passed
  const open = ev(life, "DOOR_OPEN", (e) => e.door === "DR-L1"), close = ev(life, "DOOR_CLOSE", (e) => e.door === "DR-L1");
  ok(open.length >= 1 && corr.length && open[0].t <= corr[0].t, "12 DR-L1 opens before FX passes");
  ok(close.length >= 1 && close[0].t > open[0].t && close[0].t >= corr[0].t, "12 DR-L1 closes after FX has passed");
  for (const d of ["DR-CMD-HAB"]) ok(ev(life, "DOOR_OPEN", (e) => e.door === d && e.actor === fx.id).length >= 1, `12 ${d} opens for FX`);
  // 1 back to work
  ok(life.assign(fx.id, "WORKING"), "FX can be sent back");
  ok(until(life, () => fx.phase === "dwell" && fx.act === "WORKING", 6 * 60000, "s1"), "1 FX returns to its workstation");
  ok(fx.x === fx.homeSpot.x && fx.y === fx.homeSpot.y && fx.room === "L1", "1 FX is at its home anchor");
  ok(ev(life, "AGENT_START_WORK", (e) => e.actor === fx.id && e.t > 0).length === 1, "1 AGENT_START_WORK on return");
  ok(life.events.every((e) => e.ambient === true), "every event is flagged ambient (no engine link)");
}
// ---------------------------------------------------------------- 5-8 recreation rooms
{
  const life = L.create(world, { seed: "t5" });
  const u1 = agent(life, "U1"), v1 = agent(life, "V1"), t3 = agent(life, "T3"), met = agent(life, "MET");
  life.step(L.STEP);
  ok(life.assign(u1.id, "MEDITATE"), "U1 may meditate");
  ok(until(life, () => u1.phase === "dwell", 8 * 60000, "s5"), "5 U1 reaches R1");
  ok(u1.room === "R1" && u1.state === "MEDITATING" && ev(life, "MEDITATION_START", (e) => e.actor === u1.id).length === 1, "5 meditating in R1");
  ok(life.assign(v1.id, "DECOMPRESS"), "V1 may decompress");
  ok(until(life, () => v1.phase === "dwell", 8 * 60000, "s7"), "7 V1 reaches R3");
  ok(v1.room === "R3" && v1.state === "DECOMPRESSING" && ev(life, "DECOMPRESSION_START", (e) => e.actor === v1.id).length === 1, "7 decompressing in R3");
  // 8 R4: the dog goes to play first, then a person joins
  ok(life.assign(life.dog.id, "DOG_PLAYING"), "the dog can go to R4");
  ok(until(life, () => life.dog.room === "R4", 5 * 60000, "s8"), "8 dog enters R4");
  ok(ev(life, "DOG_ENTER_R4").length >= 1, "8 DOG_ENTER_R4");
  ok(life.assign(t3.id, "DOG_PLAY"), "T3 may play with the dog");
  ok(until(life, () => t3.phase === "dwell", 8 * 60000, "s8b"), "8 T3 reaches R4");
  ok(t3.room === "R4" && t3.state === "PLAYING_WITH_DOG", "8 T3 plays with the dog in R4");
  ok(ev(life, "DOG_START_PLAY").length >= 1, "8 DOG_START_PLAY");
  // 6 R2: wait for the cinema to prepare, then a viewer takes a seat and stays until the screening ends
  ok(until(life, () => life.cinema === "PREPARING", 40 * 60000, "s6"), "6 cinema reaches PREPARING");
  ok(life.assign(met.id, "CINEMA"), "MET may go to the cinema");
  ok(until(life, () => met.phase === "dwell", 8 * 60000, "s6b"), "6 MET takes a seat in R2");
  ok(met.room === "R2" && met.state === "WATCHING_CINEMA", "6 watching in R2");
  ok(until(life, () => life.cinema === "SCREENING", 6 * 60000, "s6c") && ev(life, "CINEMA_START").length >= 1, "6 CINEMA_START");
  ok(met.act === "CINEMA" && met.room === "R2", "6 MET stays during the screening");
  ok(until(life, () => met.act !== "CINEMA", 20 * 60000, "s6d") && ev(life, "CINEMA_END").length >= 1, "6 CINEMA_END, then MET leaves");
  const states = ev(life, "CINEMA_STATE").map((e) => e.state);
  ok(["PREPARING", "SCREENING", "ENDING"].every((s) => states.includes(s)), "6 cinema session states EMPTY → PREPARING → SCREENING → ENDING");
}
// ---------------------------------------------------------------- 9-11 permissions, dog rule, reserved rooms, furniture
{
  const dogActor = { allow: L.allowedRooms({ kind: "dog" }, world) };
  ok([...dogActor.allow].sort().join() === "H-HAB,R4", "9 dog allowed rooms are exactly H-HAB and R4 (D.occupancy)");
  const habTile = world.key(121, 61);
  for (const room of ["L1", "H-CMD", "COR-N", "H-LAB"]) { const t = D.tiles.find((x) => x[2] === room); ok(!L.findPath(world, dogActor, habTile, world.key(t[0], t[1])), `9 no dog route to ${room}`); }
  for (const id of ["R1", "R2", "R3"]) { const c = [...world.cells].find(([, v]) => v.room === id); ok(!L.findPath(world, dogActor, habTile, c[0]), `9 no dog route into ${id}`); }
  const human = { allow: L.allowedRooms({ kind: "agent", cls: "MP-FREE", home: "L1" }, world) };
  for (const room of ["L5", "L8"]) { const t = D.tiles.find((x) => x[2] === room); ok(!L.findPath(world, human, world.key(39, 31), world.key(t[0], t[1])), `10 no route into reserved ${room}`); }
  for (const room of ["L9", "L10", "L2"]) { const t = D.tiles.find((x) => x[2] === room && world.tileWalk(world.key(x[0], x[1]))); ok(!L.findPath(world, human, world.key(39, 31), world.key(t[0], t[1])), `10 an L1 agent is never routed into ${room}`); }
  const host = { allow: L.allowedRooms({ kind: "agent", cls: "MP-HOST", home: "H-HAB" }, world) };
  ok([...host.allow].join() === "H-HAB", "the café host is H-HAB only");
  const life = L.create(world, { seed: "t9" });
  ok(!life.assign(life.actors.find((a) => a.cls === "MP-HOST").id, "MEDITATE"), "the host cannot be sent to R1");
}
// ---------------------------------------------------------------- soak: two simulated hours, every actor checked every step
{
  const life = L.create(world, { seed: "soak" });
  let maxAway = 0, peak = {};
  let doorViol = 0, closeOnActor = 0, stuck = 0;
  run(life, 2 * H, "soak", (lf) => {
    for (const a of lf.actors) {
      if (a.phase !== "walk" || !a.route) continue;
      if ((a.waitMs || 0) > 8000) stuck++;
      for (let i = Math.max(1, a.ri - 1); i < Math.min(a.route.length, a.ri + 2); i++) {
        const w = a.route[i], d = w.door || w.via; if (!d) continue; const [dx, dy] = world.doorPos[d]; const dd = Math.hypot(a.x - dx, a.y - dy);
        const st = lf.doors[d];
        if (dd < 5 && (!st || st.k < 0.8)) doorViol++;               // walking through a panel
        if (dd < 12 && st && st.state === "CLOSING") closeOnActor++; // closing on someone in the passage
      }
    }
    const c = { away: 0 };
    for (const a of lf.actors) { if (a.kind !== "agent" || a.act === "WORKING") continue; const dest = a.spot && a.spot.room ? a.spot.room : a.room; if (dest !== a.home) c.away++; if (a.phase === "dwell") c[a.room] = (c[a.room] || 0) + 1; }
    maxAway = Math.max(maxAway, c.away); for (const k of Object.keys(c)) peak[k] = Math.max(peak[k] || 0, c[k]);
  });
  ok(doorViol === 0, `12 nobody passes a door that is not open (${doorViol} violations)`);
  ok(closeOnActor === 0, `12 a door never closes on someone in the passage (${closeOnActor})`);
  ok(stuck === 0, "nobody waits at a door for more than 8 s");
  { const seq = {}; let bad = 0; const nextOk = { DOOR_OPEN: ["CLOSED", "CLOSING", undefined], DOOR_OPENED: ["OPENING"], DOOR_CLOSE: ["OPEN"], DOOR_CLOSED: ["CLOSING"] }, to = { DOOR_OPEN: "OPENING", DOOR_OPENED: "OPEN", DOOR_CLOSE: "CLOSING", DOOR_CLOSED: "CLOSED" };
    for (const e of life.events) { if (!(e.type in to)) continue; if (!nextOk[e.type].includes(seq[e.door])) bad++; seq[e.door] = to[e.type]; }
    ok(bad === 0, `12 every door follows CLOSED → OPENING → OPEN → CLOSING → CLOSED (${bad} bad transitions)`);
    ok(Object.keys(seq).length >= 8, `12 many doors cycled (${Object.keys(seq).length})`);
    ok(!Object.keys(seq).some((d) => /DR-(L5|L8|R5|R6)$/.test(d)), "12 reserved doors never open"); }
  ok(maxAway <= L.CAPS.away, `11 beat budget: at most ${L.CAPS.away} agents away (peak ${maxAway})`);
  ok((peak.R1 || 0) <= 3 && (peak.R3 || 0) <= 2, `R1 calm (peak ${peak.R1 || 0}) and R3 quiet (peak ${peak.R3 || 0})`);
  ok((peak.R4 || 0) <= 2, `R4 at most two people (peak ${peak.R4 || 0})`);
  ok((peak.R2 || 0) >= 2 && (peak.R2 || 0) <= 8, `the cinema draws a small audience (peak ${peak.R2 || 0})`);
  const types = new Set(life.events.map((e) => e.type));
  ok([...types].every((t) => L.EVENTS.includes(t)), "every emitted event is in the catalogue");
  for (const t of ["AGENT_START_WORK", "AGENT_STOP_WORK", "AGENT_ENTER_ROOM", "AGENT_SIT", "AGENT_STAND", "DOOR_OPEN", "DOOR_OPENED", "DOOR_CLOSE", "DOOR_CLOSED", "DOG_ENTER_R4", "DOG_ENTER_HHAB", "DOG_START_PLAY", "DOG_STOP_PLAY", "CINEMA_START", "CINEMA_END"])
    ok(types.has(t), `soak emits ${t}`);
  const working = life.actors.filter((a) => a.kind === "agent" && a.act === "WORKING").length;
  ok(working >= 20, `most agents stay at work (${working} of ${life.actors.length - 1} at their workstation)`);
  console.log(`soak: 2 h, ${life.events.length} events, peak away ${maxAway}, peaks ${JSON.stringify(peak)}`);
}
// ---------------------------------------------------------------- determinism + lint
{
  const sig = (seed) => { const lf = L.create(world, { seed }); lf.advanceTo(30 * 60000); return JSON.stringify(lf.events.map((e) => [e.type, e.t, e.actor || e.door || e.room])) + JSON.stringify(lf.snapshot()); };
  const a = sig("same"), b = sig("same"), c = sig("other");
  ok(a === b, "same seed and steps give the same station (determinism)");
  ok(a !== c, "a different seed gives a different station");
  const lifeSrc = fs.readFileSync(path.join(__dirname, "templates/stellar_life.js"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  ok(!/Math\.random\s*\(|Date\.now\s*\(|performance\.now\s*\(/.test(lifeSrc), "determinism lint: no Math.random, Date.now or performance.now in the life engine");
  ok(!/starnet/i.test(fs.readFileSync(path.join(__dirname, "templates/stellar_life.js"), "utf8")), "the life engine carries no reference-station name");
}

if (fails.length) { console.error("FAILED:\n  " + fails.slice(0, 60).join("\n  ")); process.exit(1); }
console.log("life test passed");
