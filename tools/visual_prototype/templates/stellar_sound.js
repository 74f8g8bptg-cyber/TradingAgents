/* Stellar sound layer V1: Life events -> sound events -> resolution -> play / loop -> mix. docs/STELLAR_SOUND_SYSTEM_V1.md.
   Two parts, kept apart:
   - createDirector(): PURE and seeded. No Web Audio, no DOM, no clock, no Math.random. It listens to Life events (it never
     emits into Life), watches Life state through snapshots, and returns sound requests (cue, category, position-derived gain
     and pan, variation) and ambience-bed targets. Fully testable in Node.
   - createEngine(): browser only. Builds the Web Audio graph lazily on a user gesture, synthesises every cue procedurally
     (no audio files: the page stays self-contained), keeps a fixed set of ambience loops, enforces a voice budget and
     releases every one-shot when it ends.
   Pattern sources (studied, nothing copied): a bus-listening sound director that only reacts to real events, gesture-armed
   audio, a master chain with a soft limiter and a shared reverb send, procedural noise-plus-tone voices, per-cue rate gates,
   small pitch drift for variation, self-terminating nodes. Loaded in the page (window.StellarSound) and in Node tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.StellarSound = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function fnv(str) { let h = 0x811c9dc5; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); } return h >>> 0; }
  function mulberry32(a) { return function () { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const rngFor = (...k) => mulberry32(fnv(k.join("|")));
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

  // ------------------------------------------------------------------ categories and mix (user controls: master, ambience, effects, music)
  // AMBIENCE carries every continuous bed (station, rooms, fountain, café murmur, cinema layers); EFFECTS carries one-shots in
  // four groups with fixed trims so a door never overpowers the station and the dog never overpowers H-HAB; MUSIC carries
  // only the R1 calm pad; UI carries the sound toggle confirmation.
  const CATEGORIES = { MASTER: 0.85, AMBIENCE: 0.5, EFFECTS: 0.9, MUSIC: 0.35, UI: 0.5 };
  const GROUPS = { DOORS: 0.8, AGENTS: 1.0, MACHINERY: 0.7, DOG: 0.75, WATER: 0.7 }; // WATER feeds the AMBIENCE bus (fountain detail)

  // ------------------------------------------------------------------ cue catalogue: category/group, priority, rate gate (ms), base level
  const CUES = {
    // doors: four cues per family, one per physical transition of the Life door (travel starts, end stop, travel back, seal)
    ...Object.fromEntries(["standard", "hub", "restricted"].flatMap((ty) => [[`door.travel.${ty}`, { g: "DOORS", prio: 3, gate: 300, vol: 1.0 }], [`door.stop.${ty}`, { g: "DOORS", prio: 3, gate: 300, vol: 0.8 }],
      [`door.travelback.${ty}`, { g: "DOORS", prio: 3, gate: 300, vol: 0.95 }], [`door.seal.${ty}`, { g: "DOORS", prio: 3, gate: 300, vol: 0.9 }]])),
    "step.metal": { g: "AGENTS", prio: 1, gate: 0, vol: 1.0 }, "step.wood": { g: "AGENTS", prio: 1, gate: 0, vol: 0.95 }, "step.soft": { g: "AGENTS", prio: 1, gate: 0, vol: 0.7 },
    "cafe.clink": { g: "AGENTS", prio: 1, gate: 900, vol: 0.7 }, "sofa.creak": { g: "AGENTS", prio: 1, gate: 1500, vol: 0.6 }, "console.touch": { g: "MACHINERY", prio: 1, gate: 700, vol: 0.55 },
    "seat.sit": { g: "AGENTS", prio: 1, gate: 120, vol: 0.8 }, "seat.stand": { g: "AGENTS", prio: 1, gate: 120, vol: 0.65 }, "cafe.cup": { g: "AGENTS", prio: 1, gate: 400, vol: 0.7 },
    "billiards.click": { g: "AGENTS", prio: 1, gate: 600, vol: 0.8 },
    "console.wake": { g: "MACHINERY", prio: 2, gate: 300, vol: 0.7 }, "console.sleep": { g: "MACHINERY", prio: 2, gate: 300, vol: 0.6 },
    "pod.close": { g: "MACHINERY", prio: 2, gate: 400, vol: 0.5 }, "pod.open": { g: "MACHINERY", prio: 2, gate: 400, vol: 0.45 },
    "projector.start": { g: "MACHINERY", prio: 2, gate: 1000, vol: 0.6 }, "projector.stop": { g: "MACHINERY", prio: 2, gate: 1000, vol: 0.55 },
    "cinema.lightsdown": { g: "MACHINERY", prio: 2, gate: 1000, vol: 0.5 }, "cinema.lightsup": { g: "MACHINERY", prio: 2, gate: 1000, vol: 0.5 },
    "structure.creak": { g: "MACHINERY", prio: 1, gate: 20000, vol: 0.35 }, "fountain.drop": { g: "WATER", prio: 0, gate: 0, vol: 0.5 }, "fountain.bubble": { g: "WATER", prio: 0, gate: 0, vol: 0.45 },
    "zen.bowl": { g: "MACHINERY", prio: 2, gate: 15000, vol: 0.4 }, "quiet.seal": { g: "MACHINERY", prio: 1, gate: 4000, vol: 0.25 },
    "dog.paw": { g: "DOG", prio: 0, gate: 0, vol: 0.6 }, "dog.tag": { g: "DOG", prio: 1, gate: 800, vol: 0.6 }, "dog.toy": { g: "DOG", prio: 1, gate: 900, vol: 0.7 },
    "dog.lap": { g: "DOG", prio: 1, gate: 500, vol: 0.6 }, "dog.woof": { g: "DOG", prio: 2, gate: 120000, vol: 0.4 },
  };

  // ------------------------------------------------------------------ rooms: acoustic identity (floor, reverb) and ambience beds
  const TECH = new Set(["H-CMD", "H-LAB", "L1", "L2", "L3", "L4", "L6", "L7", "L9", "L10"]);
  const SILENT = new Set(["L5", "L8", "R5", "R6"]); // reserved: sealed, no bed, no activity sound
  const FLOOR = { "H-HAB": "wood", R1: "wood", R2: "soft", R3: "soft", R4: "soft" }; // default: metal deck
  const VERB = { L3: 0.35, "H-CMD": 0.25, "H-LAB": 0.25, "H-HAB": 0.18, R1: 0.2, R2: 0.08, R3: 0.0, R4: 0.12 }; // default 0.15
  // bed recipes: noise bands [type, freq, Q, level] + hum partials [freq, level]; levels are pre-mix, the director scales them
  // beds: few broadband components, more structure. Each room has its own character (tone, pulse, band), quiet enough that
  // activity sits on top. Levels are pre-mix; the director gives the room the listener is in full weight and fades its
  // neighbours within a short distance of the walls, so crossing a door changes the room.
  const BEDS = {
    station: { noise: [["lowpass", 60, 0.7, 0.05]], hum: [[41, 0.006]] },                                   // distant hull rumble
    corridor: { noise: [["lowpass", 320, 0.7, 0.05]], hum: [[248, 0.002]], am: 0.6, rate: 0.18 },              // air moving through ducts
    "H-CMD": { noise: [["bandpass", 2200, 4, 0.008]], hum: [[60, 0.012], [120, 0.009], [180, 0.005], [7200, 0.0012]] }, // electrical, bright
    "H-LAB": { noise: [["lowpass", 170, 0.7, 0.05], ["bandpass", 3500, 9, 0.004]], hum: [[90, 0.008]], am: 0.85, rate: 0.75 }, // pump pulse + instrument whine
    "H-HAB": { noise: [["lowpass", 260, 0.7, 0.022]], hum: [], am: 0.3, rate: 0.05 },                         // soft, warm, no mains hum
    L1: { noise: [["bandpass", 1800, 3, 0.006]], hum: [[60, 0.006]] },
    L2: { noise: [["bandpass", 2400, 3, 0.006]], hum: [[75, 0.007], [9800, 0.0008]] },                       // displays
    L3: { noise: [["lowpass", 140, 0.7, 0.025]], hum: [] },                                                    // large quiet chamber
    L4: { noise: [["bandpass", 2600, 1.4, 0.022], ["bandpass", 900, 1.2, 0.01]], hum: [[120, 0.012]] },        // server fans
    L6: { noise: [["lowpass", 110, 0.7, 0.012]], hum: [] },                                                    // archive: near silent
    L7: { noise: [["bandpass", 1600, 3, 0.006]], hum: [[66, 0.006]] },
    L9: { noise: [["lowpass", 120, 0.7, 0.07]], hum: [[45, 0.016], [90, 0.006]], am: 0.8, rate: 1.4 },         // machinery cycling
    L10: { noise: [["bandpass", 2000, 3, 0.006]], hum: [[80, 0.008], [160, 0.004]] },
    R1: { noise: [["lowpass", 180, 0.7, 0.006]], hum: [], am: 0.5, rate: 0.04 },                              // almost silent, slow breath of air
    R2: { noise: [["lowpass", 160, 0.7, 0.012]], hum: [] },
    R3: { noise: [["lowpass", 90, 0.7, 0.003]], hum: [] },
    R4: { noise: [["lowpass", 300, 0.7, 0.012]], hum: [] },
    fountain: { noise: [["lowpass", 650, 0.7, 0.03], ["bandpass", 260, 1.2, 0.02]], hum: [], am: 0.55, rate: 2.3 }, // basin water body (detail = bubbles and drops)
    cafe: { noise: [["bandpass", 480, 1.8, 0.02]], hum: [], am: 0.7, rate: 0.9 },
    cinemaFan: { noise: [["bandpass", 900, 2, 0.02]], hum: [[110, 0.004]] },
    cinemaRumble: { noise: [["lowpass", 100, 0.7, 0.06]], hum: [], am: 0.5, rate: 0.07 },
    zenPad: { noise: [], hum: [[174.6, 0.012], [261.6, 0.008], [349.2, 0.005]], am: 0.3, rate: 0.05, music: true },
  };

  // every Life event type is mapped explicitly: a resolver, or null (deliberately silent: doors and footsteps already cover it)
  const EVENT_MAP = {
    AGENT_ENTER_ROOM: null, AGENT_EXIT_ROOM: null, AGENT_START_ACTIVITY: null, AGENT_END_ACTIVITY: null, DECOMPRESSION_END: null, MEDITATION_END: null,
    DOOR_OPEN: (e, d) => [{ cue: `door.travel.${d.doorType(e.door)}`, key: "door:" + e.door, at: d.doorAt(e.door), room: d.doorRoom(e.door) }],
    DOOR_OPENED: (e, d) => [{ cue: `door.stop.${d.doorType(e.door)}`, key: "doorstop:" + e.door, at: d.doorAt(e.door), room: d.doorRoom(e.door) }],
    DOOR_CLOSE: (e, d) => [{ cue: `door.travelback.${d.doorType(e.door)}`, key: "door:" + e.door, at: d.doorAt(e.door), room: d.doorRoom(e.door) }],
    DOOR_CLOSED: (e, d) => [{ cue: `door.seal.${d.doorType(e.door)}`, key: "doorstop:" + e.door, at: d.doorAt(e.door), room: d.doorRoom(e.door) }],
    AGENT_START_WORK: (e, d) => (TECH.has(e.room) ? [{ cue: "console.wake", actor: e.actor, room: e.room }] : []),
    AGENT_STOP_WORK: (e, d) => (TECH.has(e.room) ? [{ cue: "console.sleep", actor: e.actor, room: e.room }] : []),
    AGENT_SIT: (e) => (e.actor === "DEC-009" ? [] : [{ cue: "seat.sit", actor: e.actor, room: e.room }].concat(/cafe_seat/.test(e.spot || "") ? [{ cue: "cafe.cup", actor: e.actor, room: e.room, delay: 0.5 }] : [])),
    AGENT_STAND: (e) => (e.actor === "DEC-009" ? [] : [{ cue: "seat.stand", actor: e.actor, room: e.room }]),
    AGENT_START_REST: (e) => [{ cue: "pod.close", actor: e.actor, room: e.room }],
    AGENT_END_REST: (e) => [{ cue: "pod.open", actor: e.actor, room: e.room }],
    MEDITATION_START: (e) => [{ cue: "zen.bowl", actor: e.actor, room: e.room }],
    CINEMA_STATE: (e, d) => (e.state === "PREPARING" ? [{ cue: "projector.start", at: d.roomAt("R2", 46, 0), room: "R2" }] : e.state === "EMPTY" ? [{ cue: "projector.stop", at: d.roomAt("R2", 46, 0), room: "R2" }] : []),
    CINEMA_START: (e, d) => [{ cue: "cinema.lightsdown", at: d.roomAt("R2", 0, 0), room: "R2" }],
    CINEMA_END: (e, d) => [{ cue: "cinema.lightsup", at: d.roomAt("R2", 0, 0), room: "R2" }],
    DECOMPRESSION_START: (e) => [{ cue: "quiet.seal", actor: e.actor, room: e.room }],
    DOG_ENTER_R4: (e) => [{ cue: "dog.tag", actor: e.actor, room: e.room }],
    DOG_ENTER_HHAB: (e) => [{ cue: "dog.tag", actor: e.actor, room: e.room }],
    DOG_START_PLAY: (e, d) => [{ cue: "dog.toy", actor: e.actor, room: e.room }].concat(d.rng("woof", e.t)() < 0.25 ? [{ cue: "dog.woof", actor: e.actor, room: e.room, delay: 0.6 }] : []),
    DOG_STOP_PLAY: (e) => [{ cue: "dog.tag", actor: e.actor, room: e.room }],
  };

  const TICK = 100, MAX_PLAYS = 8, STEP_LEN = 11, DOG_STEP = 6;

  // ------------------------------------------------------------------ the director (pure)
  function createDirector(opt) {
    const D = opt.D, world = opt.world, seed = String(opt.seed || "stellar");
    const dogRooms = new Set(D.occupancy["DEC-009"].rooms);
    const doorInfo = Object.fromEntries(D.doors.map((d) => [d.id, d]));
    const rDoor = Object.fromEntries(D.rDoors.map((d) => [d.id, d]));
    const roomAt = (id, s, t) => { const rm = world.rooms[id]; return [rm.cx + rm.u[0] * s + rm.v[0] * t, rm.cy + rm.u[1] * s + rm.v[1] * t]; };
    const fountainF = D.furniture.find((f) => f.label === "LEI-007 park fountain");
    const cen = (f) => [f.tiles.reduce((s, t) => s + t[0], 0) / f.tiles.length * 12 + 6, f.tiles.reduce((s, t) => s + t[1], 0) / f.tiles.length * 12 + 6];
    const fountain = fountainF ? cen(fountainF) : null;
    const cafeTiles = D.furniture.filter((f) => /TBL-003/.test(f.label)); const cafe = cafeTiles.length ? cafeTiles.map(cen).reduce((a, b) => [a[0] + b[0] / cafeTiles.length, a[1] + b[1] / cafeTiles.length], [0, 0]) : null;
    const billiards = D.furniture.find((f) => f.label === "LEI-001 billiards");
    const d = {
      doorType: (id) => { if (rDoor[id]) return "hub"; const x = doorInfo[id]; return !x ? "standard" : x.restricted ? "restricted" : x.kind === "DOR-009" || /-(LAB|CMD|HAB)$/.test(id) ? "hub" : "standard"; },
      doorAt: (id) => world.doorPos[id] || null,
      doorRoom: (id) => { const x = doorInfo[id] || (rDoor[id] && { A: "H-HAB", B: rDoor[id].room, status: rDoor[id].status }); if (!x) return null; return x.status === "open" ? x.B : SILENT.has(x.A) ? x.A : x.B; }, // a reserved door belongs to its sealed room
      roomAt, rng: (...k) => rngFor(seed, ...k),
    };
    // room shapes for the listener weighting
    const shapes = [];
    for (const [id, [x, y, r]] of Object.entries(D.hubs)) shapes.push({ id, dist: (px, py) => Math.max(0, Math.hypot(px - x, py - y) - r) });
    for (const [id, [x0, x1, y0, y1]] of Object.entries({ ...D.rects, ...D.corrs })) shapes.push({ id, dist: (px, py) => Math.hypot(Math.max(x0 - px, 0, px - x1), Math.max(y0 - py, 0, py - y1)) });
    for (const [id, rm] of Object.entries(world.rooms)) shapes.push({ id, dist: (px, py) => { const s = (px - rm.cx) * rm.u[0] + (py - rm.cy) * rm.u[1], t = (px - rm.cx) * rm.v[0] + (py - rm.cy) * rm.v[1]; return Math.hypot(Math.max(Math.abs(s) - 92.5, 0), Math.max(Math.abs(t) - 57.5, 0)); } });
    const roomOf = (x, y) => { let best = null, bd = 1e9; for (const s of shapes) { const dd = s.dist(x, y); if (dd < bd) { bd = dd; best = s.id; } } return bd < 1 ? best : null; };

    let t = 0, n = 0; const queue = []; const lastAt = {}; const levels = {}; let pos = new Map();
    const stepMark = new Map(); let nextCreak = 45000; let nextDrop = 0;
    const stats = { seen: {}, unknown: 0, blocked: { dog: 0, reserved: 0 }, plays: 0, dropped: 0 };
    const hearing = (z) => clamp(420 / Math.max(z, 0.3), 140, 1000);
    function spatial(listener, x, y) {
      const R = hearing(listener.z); const dd = Math.hypot(x - listener.x, y - listener.y);
      if (dd > R) return null;
      const zoomTrim = clamp((listener.z - 0.4) / 1.2, 0.35, 1); // a station overview hears the station, not every chair
      return { gain: Math.pow(1 - dd / R, 1.6) * zoomTrim, pan: clamp((x - listener.x - (y - listener.y)) / R, -1, 1) * 0.7 };
    }
    function request(listener, q, plays) {
      const c = CUES[q.cue]; if (!c) { stats.unknown++; return; }
      if (SILENT.has(q.room)) { stats.blocked.reserved++; return; }
      const at = q.at || (q.actor && pos.get(q.actor)); if (!at) return;
      const room = q.room || roomOf(at[0], at[1]);
      if (SILENT.has(room)) { stats.blocked.reserved++; return; }
      if (c.g === "DOG" && !dogRooms.has(room)) { stats.blocked.dog++; return; }
      const gate = c.gate || 0, gk = q.key || q.cue; if (gate && lastAt[gk] !== undefined && t - lastAt[gk] < gate) return;
      const sp = spatial(listener, at[0], at[1]); if (!sp) return;
      if (listener.room === "R3" && room !== "R3") sp.gain *= 0.1; // sound isolation: little leaks into R3
      if (room === "R3" && listener.room !== "R3") sp.gain *= 0.1; // ... and little leaks out of it
      if (sp.gain < 0.01) return;
      lastAt[gk] = t;
      const r = rngFor(seed, q.cue, n++);
      plays.push({ cue: q.cue, group: c.g, prio: c.prio, gain: c.vol * sp.gain * (0.9 + 0.2 * r()), pan: sp.pan, rate: 0.94 + 0.12 * r(), variant: Math.floor(r() * 3), delay: q.delay || 0, room, verb: VERB[room] !== undefined ? VERB[room] : 0.15 });
    }
    return {
      stats, levels, CUES, EVENT_MAP, roomOf,
      get t() { return t; },
      onEvent(ev) { // the only entry from Life: queue and resolve on the next tick (never re-enters Life)
        if (!ev || typeof ev.type !== "string") { stats.unknown++; return; }
        stats.seen[ev.type] = (stats.seen[ev.type] || 0) + 1;
        if (!(ev.type in EVENT_MAP)) { stats.unknown++; return; }
        if (queue.length < 400) queue.push(ev); else stats.dropped++;
      },
      tick(dt, listener, life) {
        t += dt; const plays = [];
        const snap = (life && life.snapshot) || [];
        pos = new Map(snap.map((a) => [a.id, [a.x, a.y, a]]));
        listener = { ...listener, room: roomOf(listener.x, listener.y) };
        // 1 Life events -> cues
        for (const ev of queue.splice(0)) { const f = EVENT_MAP[ev.type]; if (!f) continue; let qs = []; try { qs = f(ev, d) || []; } catch (e) { stats.unknown++; } for (const q of qs) request(listener, q, plays); }
        // 2 movement hook: footsteps from the Life stride odometer (not from rendered frames), nearest walkers first
        const walkers = snap.filter((a) => a.phase === "walk").map((a) => ({ a, dd: Math.hypot(a.x - listener.x, a.y - listener.y) })).sort((p, q) => p.dd - q.dd);
        let steps = 0;
        for (const { a } of walkers) {
          const len = a.kind === "dog" ? DOG_STEP : STEP_LEN; const m = stepMark.get(a.id); if (m === undefined || a.stride < m) { stepMark.set(a.id, a.stride); continue; }
          if (a.stride - m < len) continue; stepMark.set(a.id, a.stride);
          if (steps >= 4) continue; steps++;
          const fl = FLOOR[a.room] || "metal";
          request(listener, { cue: a.kind === "dog" ? "dog.paw" : `step.${fl}`, at: [a.x, a.y], room: a.room }, plays);
        }
        for (const id of stepMark.keys()) if (!pos.has(id)) stepMark.delete(id);
        // 3 state watchers: intermittent sounds only while the Life state really holds
        const r = rngFor(seed, "watch", Math.floor(t / 1000));
        for (const a of snap) {
          if (a.phase !== "dwell") continue;
          if (a.act === "GAMES" && billiards && r() < 0.012) request(listener, { cue: "billiards.click", at: [a.x, a.y], room: a.room }, plays);
          if (a.kind === "dog" && a.state === "DOG_DRINKING" && r() < 0.25) request(listener, { cue: "dog.lap", at: [a.x, a.y], room: a.room }, plays);
          // presence of people actually there: cups at the café, the sofa, hands on a console while at the workstation
          if (a.kind === "agent" && a.state === "SOCIAL" && /cafe_seat/.test(a.spot || "") && r() < 0.012) request(listener, { cue: "cafe.clink", key: "clink:" + a.id, at: [a.x, a.y], room: a.room }, plays);
          if (a.kind === "agent" && a.state === "SOCIAL" && /sofa/.test(a.spot || "") && r() < 0.006) request(listener, { cue: "sofa.creak", key: "creak:" + a.id, at: [a.x, a.y], room: a.room }, plays);
          if (a.kind === "agent" && a.atHome && TECH.has(a.room) && r() < 0.004) request(listener, { cue: "console.touch", key: "touch:" + a.id, at: [a.x, a.y], room: a.room }, plays);
        }
        if (t >= nextCreak) { nextCreak = t + 45000 + rngFor(seed, "creak", t)() * 75000; request(listener, { cue: "structure.creak", at: [listener.x + 80, listener.y - 60], room: "COR-N" }, plays); }
        // the fountain's detail: small irregular bubbles and drops at the basin, only while the listener is near it
        if (fountain && Math.hypot(fountain[0] - listener.x, fountain[1] - listener.y) < hearing(listener.z) * 0.8) {
          const rr = rngFor(seed, "water", Math.floor(t / TICK));
          if (rr() < 0.55) request(listener, { cue: rr() < 0.6 ? "fountain.bubble" : "fountain.drop", at: [fountain[0] + (rr() - 0.5) * 18, fountain[1] + (rr() - 0.5) * 18], room: "H-HAB", delay: rr() * 0.09 }, plays);
        }
        // 4 budget: at most MAX_PLAYS per tick, highest priority and loudest first
        plays.sort((p, q) => q.prio - p.prio || q.gain - p.gain);
        if (plays.length > MAX_PLAYS) stats.dropped += plays.length - MAX_PLAYS;
        const out = plays.slice(0, MAX_PLAYS); stats.plays += out.length;
        // 5 ambience targets from the listener position, then smoothed (no abrupt cuts)
        const R = hearing(listener.z); const target = {};
        const zoomTrim = clamp((listener.z - 0.4) / 1.2, 0.35, 1);
        target.station = listener.room ? 0.5 : 1;
        for (const sh of shapes) {
          if (SILENT.has(sh.id)) continue;
          const key = /^COR-/.test(sh.id) ? "corridor" : sh.id; if (!BEDS[key]) continue;
          const w = sh.id === listener.room ? 1 : Math.pow(Math.max(0, 1 - sh.dist(listener.x, listener.y) / 30), 2) * 0.6;
          target[key] = Math.max(target[key] || 0, w * zoomTrim);
        }
        const near = (p, rad) => (p ? Math.pow(Math.max(0, 1 - Math.hypot(p[0] - listener.x, p[1] - listener.y) / rad), 1.5) * zoomTrim : 0);
        target.fountain = listener.room === "H-HAB" || !listener.room ? near(fountain, 120) : 0;
        const social = snap.filter((a) => a.kind === "agent" && a.room === "H-HAB" && a.state === "SOCIAL" && a.phase === "dwell").length;
        target.cafe = near(cafe, 170) * clamp(social / 4, 0, 1);
        const cin = life && life.cinema ? life.cinema : "EMPTY"; const r2 = target.R2 || 0;
        target.cinemaFan = r2 * (cin === "PREPARING" ? 0.8 : cin === "SCREENING" ? 0.35 : cin === "ENDING" ? 0.6 : 0);
        target.cinemaRumble = r2 * (cin === "SCREENING" ? 1 : 0);
        const med = snap.filter((a) => a.room === "R1" && a.state === "MEDITATING" && a.phase === "dwell").length;
        target.zenPad = (target.R1 || 0) * (med > 0 ? 1 : 0);
        if (listener.room === "R3") for (const k of Object.keys(target)) if (k !== "R3") target[k] *= 0.12; // acoustic isolation
        const k = 1 - Math.exp(-dt / 800); // ~0.8 s time constant
        for (const key of Object.keys(BEDS)) { const tg = target[key] || 0; const cur = levels[key] || 0; levels[key] = cur + (tg - cur) * k; if (levels[key] < 1e-4) levels[key] = 0; }
        return { plays: out, beds: { ...levels }, listenerRoom: listener.room };
      },
    };
  }

  // ------------------------------------------------------------------ the engine (browser only; procedural synthesis)
  function createEngine(opt = {}) {
    let ctx = null, master = null, meter = null, buses = {}, groups = {}, verbIn = null, noiseBuf = null; const loops = {}; let active = 0, created = 0;
    const vols = { ...CATEGORIES };
    const VOICES = 24;
    function build() {
      const AC = typeof window !== "undefined" && (window.AudioContext || window.webkitAudioContext); if (!AC) return false;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = vols.MASTER;
      const tame = ctx.createBiquadFilter(); tame.type = "highshelf"; tame.frequency.value = 5200; tame.gain.value = -8;
      const lim = ctx.createDynamicsCompressor(); lim.threshold.value = -12; lim.knee.value = 8; lim.ratio.value = 10; lim.attack.value = 0.004; lim.release.value = 0.25;
      const makeup = ctx.createGain(); makeup.gain.value = 2.4; // events land around -10 dBFS, ambience stays far below (measured)
      master.connect(makeup); makeup.connect(tame); tame.connect(lim); lim.connect(ctx.destination);
      meter = ctx.createAnalyser(); meter.fftSize = 2048; lim.connect(meter); // output meter (tests, diagnostics)
      for (const c of ["AMBIENCE", "EFFECTS", "MUSIC", "UI"]) { const g = ctx.createGain(); g.gain.value = vols[c]; g.connect(master); buses[c] = g; }
      for (const [gname, trim] of Object.entries(GROUPS)) { const g = ctx.createGain(); g.gain.value = trim; g.connect(gname === "WATER" ? buses.AMBIENCE : buses.EFFECTS); groups[gname] = g; }
      // seeded noise and a short synthetic room impulse (no Math.random: the same station sounds the same)
      const r = rngFor("stellar-noise");
      noiseBuf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * 2), ctx.sampleRate); const nd = noiseBuf.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = r() * 2 - 1;
      const imp = ctx.createBuffer(2, Math.floor(ctx.sampleRate * 1.4), ctx.sampleRate);
      for (let ch = 0; ch < 2; ch++) { const dd = imp.getChannelData(ch); for (let i = 0; i < dd.length; i++) dd[i] = (r() * 2 - 1) * Math.pow(1 - i / dd.length, 3); }
      const verb = ctx.createConvolver(); verb.buffer = imp; verbIn = ctx.createGain(); const wet = ctx.createGain(); wet.gain.value = 0.5; verbIn.connect(verb); verb.connect(wet); wet.connect(buses.EFFECTS);
      // ambience loops: built once, levels driven by the director (gain 0 when far away)
      let off = 0;
      for (const [key, b] of Object.entries(BEDS)) {
        const out = ctx.createGain(); out.gain.value = 0; out.connect(b.music ? buses.MUSIC : buses.AMBIENCE);
        let tgt = out;
        if (b.am) { const am = ctx.createGain(); am.gain.value = 1 - b.am * 0.5; const lfo = ctx.createOscillator(); lfo.frequency.value = b.rate || 0.07 + (fnv(key) % 100) / 900; const lg = ctx.createGain(); lg.gain.value = b.am * 0.5; lfo.connect(lg); lg.connect(am.gain); lfo.start(); am.connect(out); tgt = am; loops[key + ":lfo"] = lfo; }
        const srcs = [];
        for (const [type, f, q, lvl] of b.noise) { const s = ctx.createBufferSource(); s.buffer = noiseBuf; s.loop = true; const fl = ctx.createBiquadFilter(); fl.type = type; fl.frequency.value = f; fl.Q.value = q; const g = ctx.createGain(); g.gain.value = lvl; s.connect(fl); fl.connect(g); g.connect(tgt); s.start(0, (off = (off + 0.37) % 1.9)); srcs.push(s); }
        for (const [f, lvl] of b.hum) { const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = f; const g = ctx.createGain(); g.gain.value = lvl; o.connect(g); g.connect(tgt); o.start(); srcs.push(o); }
        loops[key] = { out, srcs };
      }
      return true;
    }
    // ---- one-shot voices (self-terminating; every node is released when its sources end)
    function voice(p) {
      if (!ctx || active >= VOICES) return false;
      const t0 = ctx.currentTime + (p.delay || 0) + 0.01; const out = ctx.createGain(); out.gain.value = p.gain;
      let dest = out; let pan = null;
      if (ctx.createStereoPanner) { pan = ctx.createStereoPanner(); pan.pan.value = p.pan || 0; out.connect(pan); dest = pan; }
      const bus = groups[p.group] || buses.UI; (pan || out).connect(bus);
      if (p.verb && verbIn) { const s = ctx.createGain(); s.gain.value = p.verb; (pan || out).connect(s); s.connect(verbIn); }
      const srcs = []; const R = p.rate || 1;
      const nz = (o) => { const s = ctx.createBufferSource(); s.buffer = noiseBuf; s.playbackRate.value = o.rate || 1; const f = ctx.createBiquadFilter(); f.type = o.type || "bandpass"; f.frequency.setValueAtTime(o.f * R, t0 + (o.at || 0)); if (o.to) f.frequency.exponentialRampToValueAtTime(o.to * R, t0 + (o.at || 0) + o.dur); f.Q.value = o.q || 1; const g = ctx.createGain(); env(g, o); s.connect(f); f.connect(g); g.connect(out); s.start(t0 + (o.at || 0), (srcs.length * 0.31) % 1.8); s.stop(t0 + (o.at || 0) + o.dur + 0.05); srcs.push(s); };
      const tn = (o) => { const s = ctx.createOscillator(); s.type = o.type || "sine"; s.frequency.setValueAtTime(o.f * R, t0 + (o.at || 0)); if (o.to) s.frequency.exponentialRampToValueAtTime(o.to * R, t0 + (o.at || 0) + o.dur); const g = ctx.createGain(); env(g, o); s.connect(g); g.connect(out); s.start(t0 + (o.at || 0)); s.stop(t0 + (o.at || 0) + o.dur + 0.05); srcs.push(s); };
      function env(g, o) { const a = o.atk || 0.004, s0 = t0 + (o.at || 0); g.gain.setValueAtTime(0.0001, s0); g.gain.linearRampToValueAtTime(o.v, s0 + a); g.gain.exponentialRampToValueAtTime(0.0001, s0 + Math.max(o.dur, a + 0.02)); }
      const recipe = RECIPES[p.cue]; if (!recipe) { out.disconnect(); return false; }
      recipe(nz, tn, p.variant || 0);
      if (!srcs.length) { out.disconnect(); return false; }
      active++; created++; let left = srcs.length;
      for (const s of srcs) s.onended = () => { if (--left === 0) { active--; try { out.disconnect(); if (pan) pan.disconnect(); } catch (e) { /* already released */ } } };
      return true;
    }
    return {
      get on() { return !!ctx; }, get active() { return active; }, get created() { return created; }, get loopCount() { return Object.keys(loops).length; }, get state() { return ctx ? ctx.state : "off"; },
      enable() { if (!ctx && !build()) return false; if (ctx.state === "suspended") ctx.resume(); voice({ cue: "ui.on", group: "UI", gain: 0.5, pan: 0 }); return true; },
      disable() { if (!ctx) return; for (const l of Object.values(loops)) { const list = l.srcs || [l]; for (const s of list) { try { s.stop(); } catch (e) { /* stopped */ } } } for (const k of Object.keys(loops)) delete loops[k]; const c = ctx; ctx = null; meter = null; buses = {}; groups = {}; active = 0; try { c.close(); } catch (e) { /* closed */ } },
      level() { if (!meter) return 0; const b = new Float32Array(meter.fftSize); meter.getFloatTimeDomainData(b); let s = 0, pk = 0; for (const x of b) { s += x * x; pk = Math.max(pk, Math.abs(x)); } return { rms: Math.sqrt(s / b.length), peak: pk }; },
      setVolume(cat, v) { vols[cat] = clamp(v, 0, 1); if (!ctx) return; const n = cat === "MASTER" ? master : buses[cat]; if (n) n.gain.setTargetAtTime(vols[cat], ctx.currentTime, 0.05); },
      volume: (cat) => vols[cat],
      apply(out) { // from the director, once per tick: loop levels (smoothed again on the audio clock) and the one-shots
        if (!ctx) return;
        const now = ctx.currentTime;
        for (const [k, v] of Object.entries(out.beds || {})) { const l = loops[k]; if (l) l.out.gain.setTargetAtTime(v, now, 0.25); }
        for (const p of out.plays || []) voice(p);
      },
    };
  }

  // ------------------------------------------------------------------ cue recipes (original, procedural; nz = filtered noise, tn = tone)
  const RECIPES = {
    "ui.on": (nz, tn) => { tn({ f: 660, dur: 0.12, v: 0.12 }); tn({ f: 990, at: 0.06, dur: 0.16, v: 0.08 }); },
    // doors (timed to the 0.9 s Life travel): travel = release clunk + motor run rising; stop = soft end-stop thud;
    // travelback = motor run falling; seal = lock clunk + seal hiss. Hub doors are heavier and lower; restricted adds an access chirp
    ...Object.fromEntries([["standard", 1, 0], ["hub", 0.72, 0], ["restricted", 0.95, 1]].flatMap(([ty, p, chirp]) => [
      [`door.travel.${ty}`, (nz, tn, k) => { if (chirp) { tn({ f: 1180, dur: 0.06, v: 0.05 }); tn({ f: 1580, at: 0.08, dur: 0.07, v: 0.045 }); } tn({ f: 70 * p, dur: 0.07, v: 0.16 }); nz({ type: "lowpass", f: 300 * p, dur: 0.06, v: 0.16 });
        tn({ type: "sawtooth", f: 52 * p + k * 3, to: 78 * p, at: 0.05, dur: 0.86, v: 0.03, atk: 0.12 }); nz({ type: "bandpass", f: 520 * p, to: 1100 * p, q: 3, at: 0.05, dur: 0.86, v: 0.06, atk: 0.12 }); }],
      [`door.stop.${ty}`, (nz, tn, k) => { tn({ f: 62 * p + k * 4, dur: 0.12, v: 0.18 }); nz({ type: "lowpass", f: 380 * p, dur: 0.1, v: 0.12 }); }],
      [`door.travelback.${ty}`, (nz, tn, k) => { tn({ type: "sawtooth", f: 78 * p + k * 3, to: 52 * p, dur: 0.86, v: 0.03, atk: 0.1 }); nz({ type: "bandpass", f: 1100 * p, to: 520 * p, q: 3, dur: 0.86, v: 0.06, atk: 0.1 }); }],
      [`door.seal.${ty}`, (nz, tn, k) => { tn({ f: 54 * p + k * 3, dur: 0.16, v: 0.24 }); nz({ type: "lowpass", f: 260 * p, dur: 0.12, v: 0.2 }); nz({ type: "highpass", f: 2600, at: 0.08, dur: 0.35, v: 0.035, atk: 0.03 });
        if (chirp) tn({ f: 980, at: 0.3, dur: 0.06, v: 0.04 }); }]])),
    // footsteps: heel + toe, a body thump and a material ring (metal deck rings, wood knocks, soft floors only thud)
    "step.metal": (nz, tn, k) => { nz({ type: "lowpass", f: 180, dur: 0.05, v: 0.3, atk: 0.002 }); nz({ type: "bandpass", f: 2300 + k * 400, q: 6, dur: 0.06, v: 0.17, atk: 0.001 }); tn({ f: 960 + k * 140, dur: 0.05, v: 0.02 }); nz({ type: "bandpass", f: 1500 + k * 200, q: 3, at: 0.07, dur: 0.035, v: 0.06, atk: 0.002 }); },
    "step.wood": (nz, tn, k) => { nz({ type: "lowpass", f: 220, dur: 0.06, v: 0.32, atk: 0.002 }); nz({ type: "bandpass", f: 650 + k * 90, q: 3, dur: 0.05, v: 0.2, atk: 0.002 }); nz({ type: "bandpass", f: 900 + k * 80, q: 2, at: 0.065, dur: 0.035, v: 0.06, atk: 0.002 }); },
    "step.soft": (nz, tn, k) => { nz({ type: "lowpass", f: 200 + k * 30, dur: 0.08, v: 0.26, atk: 0.006 }); nz({ type: "lowpass", f: 500, at: 0.06, dur: 0.05, v: 0.05, atk: 0.004 }); },
    "cafe.clink": (nz, tn, k) => { tn({ f: 2900 + k * 210, dur: 0.18, v: 0.04 }); tn({ f: 4350 + k * 260, dur: 0.1, v: 0.025 }); tn({ f: 2500 + k * 120, at: 0.11, dur: 0.12, v: 0.025 }); },
    "sofa.creak": (nz, tn, k) => { nz({ type: "bandpass", f: 300 + k * 40, to: 240, q: 5, dur: 0.35, v: 0.09, atk: 0.05 }); },
    "console.touch": (nz, tn, k) => { nz({ type: "bandpass", f: 3800, q: 4, dur: 0.018, v: 0.08, atk: 0.001 }); nz({ type: "bandpass", f: 3400, q: 4, at: 0.11 + k * 0.03, dur: 0.018, v: 0.06, atk: 0.001 }); tn({ f: 1760, at: 0.2, dur: 0.05, v: 0.012 }); },
    "seat.sit": (nz, tn, k) => { nz({ type: "lowpass", f: 420, dur: 0.18, v: 0.22, atk: 0.01 }); tn({ f: 150 - k * 10, to: 110, dur: 0.12, v: 0.06 }); },
    "seat.stand": (nz, tn, k) => { nz({ type: "bandpass", f: 900, to: 600, q: 1.2, dur: 0.22, v: 0.12, atk: 0.03 }); },
    "cafe.cup": (nz, tn, k) => { tn({ f: 2650 + k * 140, dur: 0.12, v: 0.05 }); tn({ f: 3980 + k * 160, dur: 0.08, v: 0.03 }); nz({ type: "highpass", f: 4000, dur: 0.02, v: 0.05 }); },
    "billiards.click": (nz, tn, k) => { nz({ type: "bandpass", f: 3200, q: 5, dur: 0.03, v: 0.22, atk: 0.001 }); nz({ type: "bandpass", f: 3000, q: 5, at: 0.18 + k * 0.05, dur: 0.025, v: 0.12, atk: 0.001 }); },
    "console.wake": (nz, tn, k) => { tn({ f: 880, dur: 0.06, v: 0.05 }); tn({ f: 1320, at: 0.07, dur: 0.08, v: 0.04 }); nz({ type: "highpass", f: 3500, at: 0.18, dur: 0.02, v: 0.06 }); nz({ type: "highpass", f: 3200, at: 0.27 + k * 0.03, dur: 0.02, v: 0.05 }); },
    "console.sleep": (nz, tn) => { tn({ f: 1320, dur: 0.06, v: 0.04 }); tn({ f: 740, at: 0.07, dur: 0.1, v: 0.04 }); },
    "pod.close": (nz, tn) => { nz({ type: "highpass", f: 1800, dur: 0.6, v: 0.08, atk: 0.05 }); tn({ f: 120, to: 90, dur: 0.5, v: 0.05 }); },
    "pod.open": (nz, tn) => { nz({ type: "highpass", f: 2200, dur: 0.4, v: 0.07, atk: 0.03 }); tn({ f: 90, to: 120, dur: 0.4, v: 0.04 }); },
    "projector.start": (nz, tn) => { nz({ type: "bandpass", f: 200, to: 900, q: 1.5, dur: 1.6, v: 0.12, atk: 0.3 }); tn({ f: 60, to: 110, dur: 1.6, v: 0.04, atk: 0.3 }); },
    "projector.stop": (nz, tn) => { nz({ type: "bandpass", f: 900, to: 180, q: 1.5, dur: 1.8, v: 0.1, atk: 0.05 }); },
    "cinema.lightsdown": (nz, tn) => { tn({ f: 72, dur: 0.15, v: 0.14 }); tn({ f: 392, to: 262, at: 0.1, dur: 1.2, v: 0.03, atk: 0.2 }); },
    "cinema.lightsup": (nz, tn) => { tn({ f: 72, dur: 0.15, v: 0.14 }); tn({ f: 262, to: 392, at: 0.1, dur: 1.2, v: 0.03, atk: 0.2 }); },
    "structure.creak": (nz, tn, k) => { nz({ type: "bandpass", f: 240 + k * 30, to: 170, q: 6, dur: 1.1, v: 0.12, atk: 0.2 }); tn({ f: 48, dur: 0.9, v: 0.05, atk: 0.2 }); },
    // water: a drop is a short falling plip with a splash tick; a bubble is the classic rising resonance of a small air pocket
    "fountain.drop": (nz, tn, k) => { tn({ f: 1500 + k * 300, to: 700 + k * 100, dur: 0.05, v: 0.05, atk: 0.002 }); nz({ type: "bandpass", f: 2400 + k * 300, q: 2, dur: 0.025, v: 0.025, atk: 0.001 }); },
    "fountain.bubble": (nz, tn, k) => { tn({ f: 420 + k * 180, to: 980 + k * 260, dur: 0.045, v: 0.06, atk: 0.003 }); },
    "zen.bowl": (nz, tn) => { tn({ f: 264, dur: 5.5, v: 0.06, atk: 0.01 }); tn({ f: 528, dur: 4.2, v: 0.03, atk: 0.01 }); tn({ f: 794, dur: 3, v: 0.012, atk: 0.01 }); },
    "quiet.seal": (nz, tn) => { tn({ f: 55, to: 45, dur: 0.6, v: 0.06, atk: 0.05 }); },
    "dog.paw": (nz, tn, k) => { nz({ type: "highpass", f: 4200 + k * 300, dur: 0.012, v: 0.12, atk: 0.001 }); nz({ type: "lowpass", f: 300, dur: 0.03, v: 0.06, atk: 0.002 }); },
    "dog.tag": (nz, tn, k) => { tn({ f: 3150 + k * 90, dur: 0.12, v: 0.03 }); tn({ f: 4120 + k * 70, at: 0.05, dur: 0.1, v: 0.025 }); tn({ f: 3600, at: 0.11, dur: 0.08, v: 0.02 }); },
    "dog.toy": (nz, tn, k) => { tn({ type: "triangle", f: 900 + k * 80, to: 1500, dur: 0.14, v: 0.06 }); tn({ type: "triangle", f: 1400, to: 1000, at: 0.16, dur: 0.12, v: 0.05 }); },
    "dog.lap": (nz, tn, k) => { for (let i = 0; i < 3; i++) nz({ type: "bandpass", f: 900 + k * 120, q: 4, at: i * 0.16, dur: 0.06, v: 0.08, atk: 0.004 }); },
    "dog.woof": (nz, tn) => { tn({ type: "sawtooth", f: 240, to: 160, dur: 0.16, v: 0.035, atk: 0.01 }); nz({ type: "bandpass", f: 650, q: 1.5, dur: 0.14, v: 0.06, atk: 0.01 }); },
  };

  return { CATEGORIES, GROUPS, CUES, BEDS, EVENT_MAP, RECIPES, SILENT, TICK, MAX_PLAYS, createDirector, createEngine };
});
