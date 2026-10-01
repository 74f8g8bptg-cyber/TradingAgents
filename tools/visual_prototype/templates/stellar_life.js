/* Stellar life layer: ambient activity, navigation, doors and event hooks for the Visual Prototype.
   docs/STELLAR_LIFE_SYSTEM_V1.md. Design sources (patterns only, nothing copied): the Visual World Plan §1.5-§1.7,
   §12, §16 and §21, and the engine-layer reuse audit (S5 seeded randomness, S13/S14 tile grid, explicit doors and
   path smoothing, S18 zones, S19/S25 interaction points and seat reservation, S28 beat budget).
   PURITY: no DOM, no drawing, no Math.random, no Date.now or performance.now. Time is injected through step(dtMs) and
   every choice comes from a seeded generator keyed on (seed, actor, beat), so the same seed and the same steps give
   the same station, frame for frame. Everything here is AMBIENT: the prototype has no engine link, every agent's
   runtime state is idle, and ambient behaviour never claims an operational task (plan §1.5): the HUD keeps the real
   runtime state, and every event carries ambient:true. Loaded in the page (window.StellarLife) and in Node tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.StellarLife = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const T = 12, STEP = 100; // tile size (units); fixed simulation step (ms)
  const TAU = Math.PI * 2;

  // ------------------------------------------------------------------ deterministic randomness (plan §12)
  function fnv(str) { let h = 0x811c9dc5; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); } return h >>> 0; }
  function mulberry32(a) { return function () { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const rngFor = (...keys) => mulberry32(fnv(keys.join("|")));
  const pick = (r, arr) => arr[Math.floor(r() * arr.length) % arr.length];
  const between = (r, lo, hi) => lo + (hi - lo) * r();
  function weighted(r, items) { const tot = items.reduce((s, i) => s + i[1], 0); let x = r() * tot; for (const [v, w] of items) { if ((x -= w) <= 0) return v; } return items.length ? items[items.length - 1][0] : null; }

  // ------------------------------------------------------------------ event hooks (the bridge to a future sound system)
  const EVENTS = ["AGENT_ENTER_ROOM", "AGENT_EXIT_ROOM", "AGENT_START_WORK", "AGENT_STOP_WORK", "AGENT_SIT", "AGENT_STAND",
    "AGENT_START_REST", "AGENT_END_REST", "AGENT_START_ACTIVITY", "AGENT_END_ACTIVITY", "DOOR_OPEN", "DOOR_OPENED", "DOOR_CLOSE", "DOOR_CLOSED",
    "MEDITATION_START", "MEDITATION_END", "CINEMA_STATE", "CINEMA_START", "CINEMA_END", "DECOMPRESSION_START",
    "DECOMPRESSION_END", "DOG_ENTER_R4", "DOG_ENTER_HHAB", "DOG_START_PLAY", "DOG_STOP_PLAY"];
  // suggested future sound cue per event (no audio is played anywhere in V1; a sound layer subscribes to the bus)
  const SOUND_HOOKS = { AGENT_START_WORK: "workstation.wake", AGENT_STOP_WORK: "workstation.sleep", AGENT_SIT: "seat.creak",
    AGENT_STAND: "seat.release", DOOR_OPEN: "door.open", DOOR_OPENED: "door.endstop", DOOR_CLOSE: "door.close", DOOR_CLOSED: "door.seal", MEDITATION_START: "zen.chime",
    CINEMA_START: "cinema.start", CINEMA_END: "cinema.end", DECOMPRESSION_START: "quiet.enter", DOG_START_PLAY: "dog.play",
    DOG_STOP_PLAY: "dog.settle", DOG_ENTER_R4: "dog.pawsteps", DOG_ENTER_HHAB: "dog.pawsteps", AGENT_START_REST: "rest.pod" };
  function makeBus() {
    const subs = new Map(); const log = [];
    return {
      on(type, fn) { if (!subs.has(type)) subs.set(type, []); subs.get(type).push(fn); return () => subs.set(type, subs.get(type).filter((f) => f !== fn)); },
      emit(ev) { log.push(ev); if (log.length > 20000) log.splice(0, 5000); for (const k of [ev.type, "*"]) for (const fn of subs.get(k) || []) { try { fn(ev); } catch (e) { /* a listener never breaks the simulation */ } } },
      log,
    };
  }

  // ------------------------------------------------------------------ radial recreation rooms: frames, footprints, life spots
  // Room-local coordinates (s along the room axis from the H-HAB door at s=-92.5, t across), the same frame the renderer
  // uses. Footprints [s, t, half-s, half-t] mirror the furniture in calRecItems (walk-over mats, cushions and toys have
  // none); spots are cosmetic life positions, not registry anchors. The browser life test cross-checks every R-room
  // furniture item against these footprints.
  const REC = {
    R1: { block: [[70, 0, 11, 29], [-30, -49, 11, 3.5], [-30, 49, 11, 3.5], [-80, -46, 2.5, 2.5], [-80, 46, 2.5, 2.5], [82, -48, 2.5, 2.5], [82, 48, 2.5, 2.5], [-60, -46, 4.5, 4.5], [-60, 46, 4.5, 4.5], [40, -48, 4.5, 4.5], [40, 48, 4.5, 4.5]],
      spots: { meditate: [-12, 18].flatMap((s) => [-30, 0, 30].map((t) => ({ s, t: t - 2.25, face: "u", pose: "floor", h: 0 }))) } },
    R2: { block: [[0, -55.5, 54, 2.5], ...[-20, 0, 20].flatMap((t) => [-34, 34].map((s) => [s, t, 24, 5.5])), [0, 46, 4.5, 3.5], [-74, 44, 9.5, 4.5], [-82, -48, 2.5, 2.5], [82, -48, 2.5, 2.5], [82, 46, 2.5, 2.5]],
      spots: { cinema: [[-20, 0], [0, 1.6], [20, 3.2]].flatMap(([t, h]) => [-34, 34].flatMap((s) => [-16.875, -5.625, 5.625, 16.875].map((o) => ({ s: s + o, t, face: "-v", pose: "sit", h })))) } },
    R3: { block: [[-58, -46, 10.5, 4.5], [-80, 40, 2.5, 3]],
      spots: { decompress: [{ s: -30, t: 30, face: "c", pose: "floor", h: 0 }, { s: 60, t: -36, face: "c", pose: "floor", h: 0 }, { s: 14, t: 6, face: "c", pose: "floor", h: 0 }, { s: -58, t: -46, face: "v", pose: "sit", h: 0 }] } },
    R4: { block: [[-26, -42, 13.5, 4.5], [4, -42, 4.5, 8], [32, -42, 14.5, 3.5], [63.5, 0, 12.5, 33], [42, 42, 4, 7], [10, 42, 14.5, 3], [-26, 42, 11.5, 3.6], [-50, 39, 1.5, 14.5], [-74, 44, 9.5, 6.5], [-58, 47, 4.5, 3.5], [-82, -50, 5.5, 4], [-68, -51, 3.8, 2.8]],
      spots: { play: [{ s: -14, t: 8, face: "m", pose: "stand", h: 0 }, { s: 10, t: -10, face: "m", pose: "stand", h: 0 }],
        dogBed: [{ s: -74, t: 44, face: "-v", pose: "lie", h: 3.8 }], dogWater: [{ s: -58, t: 40, face: "v", pose: "stand", h: 0 }],
        dogPlay: [[-14, -6], [6, 8], [20, -4], [-6, 24], [24, 26], [30, -26], [-10, -26], [-24, 18]].map(([s, t]) => ({ s, t, face: "m", pose: "stand", h: 0 })) } },
  };
  const R_L = 92.5, R_W = 57.5, R_DS = 12, R_S0 = -84, R_T0 = -48, R_NI = 15, R_NJ = 9;

  // ------------------------------------------------------------------ world: one navigation model for the whole station
  // Global tiles mirror geometry.py exactly (walkable, wall seams, explicit door lanes, reserved rooms). Seats are
  // furniture: a path may start or end on a seat but never walks through one. R1-R4 are room-local grids joined to
  // H-HAB through their open doors (R5 / R6 are reserved: no grid, no door, never entered).
  function buildWorld(D) {
    const key = (c, r) => c + "," + r;
    const region = new Map(); for (const [c, r, n] of D.tiles) region.set(key(c, r), n);
    const reserved = new Set(D.nav.reserved);
    const doorStatus = D.nav.doorStatus, doorSides = {};
    for (const d of D.doors) doorSides[d.id] = [d.A, d.B];
    const blocked = new Set(), seats = new Set();
    for (const f of D.furniture) {
      if (f.asset === "DEC-009") continue; // the resident dog is an actor in the life layer, not an obstacle
      for (const [c, r] of f.tiles) { if (f.kind === "block") blocked.add(key(c, r)); else if (f.kind === "seat") seats.add(key(c, r)); }
    }
    const seams = new Set(D.nav.seams.map(([a, b]) => [key(...a), key(...b)].sort().join("|")));
    const doorEdge = new Map();
    for (const [did, lanes] of Object.entries(D.nav.lanes)) for (const ch of lanes) for (let i = 0; i + 1 < ch.length; i++) doorEdge.set([key(...ch[i]), key(...ch[i + 1])].sort().join("|"), did);
    const doorPos = {};
    for (const d of D.doors) { const fs = d.frames; doorPos[d.id] = [fs.reduce((s, f) => s + (f.p1[0] + f.p2[0]) / 2, 0) / fs.length, fs.reduce((s, f) => s + (f.p1[1] + f.p2[1]) / 2, 0) / fs.length]; }
    const tileWalk = (k) => { const n = region.get(k); if (n === undefined || reserved.has(n) || blocked.has(k)) return false; return !(doorStatus[n] !== undefined && doorStatus[n] !== "open"); };
    const anchors = Object.fromEntries(D.anchors.map((a) => [a.name, a]));
    const anchorAt = new Map(D.anchors.map((a) => [key(...a.tile), a.name]));

    // radial rooms: frames (same formula as the renderer), local grids, portals through the open doors
    const [hx, hy, hr] = D.hubs["H-HAB"];
    const rooms = {};
    for (const [id, [x0, x1, y0, y1]] of Object.entries(D.rRooms)) {
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, a = Math.atan2(cy - hy, cx - hx);
      rooms[id] = { id, cx, cy, a, u: [Math.cos(a), Math.sin(a)], v: [-Math.sin(a), Math.cos(a)] };
    }
    const rP = (rm, s, t) => [rm.cx + rm.u[0] * s + rm.v[0] * t, rm.cy + rm.u[1] * s + rm.v[1] * t];
    const rFree = (id, s, t, m = 2) => { if (Math.abs(s) > R_L - 6 || Math.abs(t) > R_W - 7) return false; for (const [bs, bt, hs, ht] of (REC[id] || {}).block || []) if (Math.abs(s - bs) <= hs + m && Math.abs(t - bt) <= ht + m) return false; return true; };
    const cells = new Map(), portals = {};
    for (const rd of D.rDoors) {
      const rm = rooms[rd.room]; if (!rm || rd.status !== "open" || !REC[rd.room]) continue;
      for (let i = 0; i < R_NI; i++) for (let j = 0; j < R_NJ; j++) {
        const s = R_S0 + i * R_DS, t = R_T0 + j * R_DS;
        if (rFree(rd.room, s, t)) { const [x, y] = rP(rm, s, t); cells.set(`${rd.room}:${i},${j}`, { room: rd.room, i, j, s, t, x, y }); }
      }
      const entry = `${rd.room}:0,${(R_NJ - 1) / 2}`;
      const px = hx + (hr - 6) * Math.cos(rd.ang), py = hy + (hr - 6) * Math.sin(rd.ang);
      let hub = null, bd = 1e9;
      for (const [k, n] of region) if (n === "H-HAB" && tileWalk(k) && !seats.has(k)) { const [c, r] = k.split(",").map(Number); const d = Math.hypot(c * T + 6 - px, r * T + 6 - py); if (d < bd) { bd = d; hub = k; } }
      if (cells.has(entry) && hub) { portals[rd.id] = { door: rd.id, room: rd.room, hub, cell: entry }; doorPos[rd.id] = [rd.x, rd.y]; doorSides[rd.id] = ["H-HAB", rd.room]; }
    }
    const portalOfCell = new Map(Object.values(portals).map((p) => [p.cell, p])), portalOfHub = new Map();
    for (const p of Object.values(portals)) { if (!portalOfHub.has(p.hub)) portalOfHub.set(p.hub, []); portalOfHub.get(p.hub).push(p); }

    const nodePos = (k) => { const c = cells.get(k); if (c) return [c.x, c.y]; const [cc, rr] = k.split(",").map(Number); return [cc * T + 6, rr * T + 6]; };
    const nodeRegion = (k) => (cells.has(k) ? cells.get(k).room : region.get(k));
    const tileOf = (x, y) => key(Math.floor(x / T), Math.floor(y / T));
    function canStep(a, b) { // geometry.py can_step, on tiles that are walkable for the caller
      const e = [a, b].sort().join("|");
      if (seams.has(e)) return null;
      const ra = region.get(a), rb = region.get(b);
      if (ra === rb) return "";
      const d = doorEdge.get(e);
      return d && doorStatus[d] === "open" ? d : null;
    }
    function neighbours(k) {
      const out = [];
      const c = cells.get(k);
      if (c) {
        for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = `${c.room}:${c.i + di},${c.j + dj}`; if (cells.has(n)) out.push([n, ""]); }
        const p = portalOfCell.get(k); if (p) out.push([p.hub, p.door]);
        return out;
      }
      const [cc, rr] = k.split(",").map(Number);
      for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = key(cc + dc, rr + dr); if (!tileWalk(n)) continue; const d = canStep(k, n); if (d !== null) out.push([n, d]); }
      for (const p of portalOfHub.get(k) || []) out.push([p.cell, p.door]);
      return out;
    }
    return { D, T, key, region, reserved, doorStatus, doorSides, blocked, seats, seams, doorEdge, doorPos, tileWalk, canStep, anchors, anchorAt,
      rooms, rP, rFree, cells, portals, nodePos, nodeRegion, neighbours, tileOf, hub: { x: hx, y: hy, r: hr } };
  }

  // ------------------------------------------------------------------ permissions (Character Registry §3; Room Registry §3.3a)
  const HABITAT = ["H-HAB", "R1", "R2", "R3", "R4"], TRANSIT = ["COR-N", "COR-S", "H-CMD", "H-LAB", "H-HAB"];
  function allowedRooms(actor, world) {
    if (actor.kind === "dog") return new Set(world.D.occupancy["DEC-009"].rooms);
    if (actor.cls === "MP-HOST") return new Set(["H-HAB"]);
    if (actor.cls === "MP-NONE") return new Set();
    return new Set([actor.home, ...TRANSIT, ...HABITAT]); // own room, public transit, the Habitat; never L5/L8/R5/R6 or other rooms
  }
  function regionAllowed(world, allow, n) {
    if (n === undefined) return false;
    if (world.doorSides[n]) return world.doorStatus[n] === "open" && world.doorSides[n].every((s) => allow.has(s));
    return allow.has(n);
  }

  // ------------------------------------------------------------------ path search (BFS) + string-pulling (plan §16)
  function findPath(world, actor, from, to) {
    if (from === to) return [{ k: from, doorIn: "" }];
    const allow = actor.allow;
    const ok = (k) => { const n = world.nodeRegion(k); if (!regionAllowed(world, allow, n)) return false; if (world.cells.has(k)) return true; if (!world.tileWalk(k)) return false; return !world.seats.has(k) || k === to || k === from; };
    const prev = new Map([[from, null]]); const q = [from]; let qi = 0;
    while (qi < q.length) {
      const k = q[qi++];
      for (const [n, door] of world.neighbours(k)) {
        if (prev.has(n) || !ok(n)) continue;
        prev.set(n, [k, door]);
        if (n === to) { const out = []; let c = to; while (c !== null) { const p = prev.get(c); out.push({ k: c, doorIn: p ? p[1] : "" }); c = p ? p[0] : null; } return out.reverse(); }
        q.push(n);
      }
    }
    return null;
  }
  // straight segment test on the walk model: no blocked tile, no seat, no wall seam, no corner cutting (global grid);
  // inside a radial room the segment keeps clear of every footprint
  function segClear(world, allow, a, b, ends) {
    const ca = world.cells.get(a.k);
    const [x0, y0] = world.nodePos(a.k), [x1, y1] = world.nodePos(b.k);
    const L = Math.hypot(x1 - x0, y1 - y0), n = Math.max(1, Math.ceil(L / 1.5));
    if (ca) { const rm = world.rooms[ca.room]; for (let i = 0; i <= n; i++) { const x = x0 + (x1 - x0) * i / n, y = y0 + (y1 - y0) * i / n; const s = (x - rm.cx) * rm.u[0] + (y - rm.cy) * rm.u[1], t = (x - rm.cx) * rm.v[0] + (y - rm.cy) * rm.v[1]; if (!world.rFree(ca.room, s, t, 3)) return false; } return true; }
    let prev = a.k;
    const walk = (k) => world.tileWalk(k) && regionAllowed(world, allow, world.region.get(k)) && (!world.seats.has(k) || ends.has(k));
    for (let i = 1; i <= n; i++) {
      const k = world.tileOf(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n);
      if (k === prev) continue;
      if (!walk(k)) return false;
      const [pc, pr] = prev.split(",").map(Number), [kc, kr] = k.split(",").map(Number);
      if (Math.abs(pc - kc) + Math.abs(pr - kr) === 1) { if (world.canStep(prev, k) !== "") return false; }
      else { // diagonal: both orthogonal neighbours must be walkable and reachable without a seam
        const m1 = world.key(kc, pr), m2 = world.key(pc, kr);
        for (const m of [m1, m2]) if (!walk(m) || world.canStep(prev, m) !== "" || world.canStep(m, k) !== "") return false;
      }
      prev = k;
    }
    return true;
  }
  function smooth(world, actor, path) {
    if (path.length <= 2) return path;
    const ends = new Set([path[0].k, path[path.length - 1].k]);
    const out = [path[0]]; let i = 0;
    while (i < path.length - 1) {
      let j = i + 1;
      for (let k = path.length - 1; k > i + 1; k--) {
        let same = true; const r0 = world.nodeRegion(path[i].k);
        for (let m = i + 1; m <= k; m++) if (path[m].doorIn || world.nodeRegion(path[m].k) !== r0) { same = false; break; }
        if (same && segClear(world, actor.allow, path[i], path[k], ends)) { j = k; break; }
      }
      out.push(path[j]); i = j;
    }
    return out;
  }

  // ------------------------------------------------------------------ activities
  // state: the agent state shown by the life layer (ambient). WORKING means "at its own workstation" with no task:
  // the badge keeps the real runtime state (idle in V1) and the event carries ambient:true (plan §1.5).
  const ACTIVITIES = {
    WORKING: { state: "WORKING", where: "home", dur: [360, 900], start: "AGENT_START_WORK", end: "AGENT_STOP_WORK" },
    STROLL: { state: "STANDING", where: "home", dur: [40, 110] },
    CAFE: { state: "SOCIAL", room: "H-HAB", dur: [150, 360], w: 3 },
    LOUNGE: { state: "SOCIAL", room: "H-HAB", dur: [180, 420], w: 2 },
    GAMES: { state: "RECREATION", room: "H-HAB", dur: [180, 360], w: 1.5 },
    WINDOW: { state: "SITTING", room: "H-HAB", dur: [120, 300], w: 1 },
    REST: { state: "RESTING", room: "H-HAB", dur: [240, 540], w: 1, start: "AGENT_START_REST", end: "AGENT_END_REST" },
    PARK_BENCH: { state: "SITTING", room: "H-HAB", dur: [120, 300], w: 1.5 },
    FOUNTAIN: { state: "STANDING", room: "H-HAB", dur: [60, 150], w: 1 },
    PARK_WALK: { state: "WALKING", room: "H-HAB", dur: [20, 40], w: 1.5 },
    MEDITATE: { state: "MEDITATING", room: "R1", dur: [300, 600], w: 1.2, cap: 3, start: "MEDITATION_START", end: "MEDITATION_END" },
    CINEMA: { state: "WATCHING_CINEMA", room: "R2", dur: [0, 0], w: 2, cap: 8 },
    DECOMPRESS: { state: "DECOMPRESSING", room: "R3", dur: [240, 480], w: 0.8, cap: 2, start: "DECOMPRESSION_START", end: "DECOMPRESSION_END" },
    DOG_PLAY: { state: "PLAYING_WITH_DOG", room: "R4", dur: [120, 300], w: 1.2, cap: 2 },
    HOST_ROUND: { state: "STANDING", room: "H-HAB", dur: [40, 90] },
    DOG_IDLE: { state: "DOG_IDLE", room: "H-HAB", dur: [40, 120] },
    DOG_REST: { state: "DOG_RESTING", room: "R4", dur: [240, 480] },
    DOG_DRINK: { state: "DOG_DRINKING", room: "R4", dur: [15, 30] },
    DOG_PLAYING: { state: "DOG_PLAYING", room: "R4", dur: [60, 150], start: "DOG_START_PLAY", end: "DOG_STOP_PLAY" },
  };
  const STATES = ["IDLE", "WALKING", "WORKING", "SITTING", "STANDING", "RESTING", "SOCIAL", "RECREATION", "MEDITATING",
    "WATCHING_CINEMA", "DECOMPRESSING", "PLAYING_WITH_DOG", "DOG_IDLE", "DOG_WALKING", "DOG_RESTING", "DOG_PLAYING", "DOG_DRINKING"];
  const CAPS = { away: 12, "H-HAB": 10 }; // beat budget: the station never looks busier than it is (plan §12)
  const CINEMA_CYCLE = [["EMPTY", 360], ["PREPARING", 180], ["SCREENING", 780], ["ENDING", 120], ["EMPTY", 60]]; // seconds
  const CINEMA_PERIOD = CINEMA_CYCLE.reduce((s, c) => s + c[1], 0);
  function cinemaAt(tMs) { let x = (tMs / 1000) % CINEMA_PERIOD; for (const [st, d] of CINEMA_CYCLE) { if (x < d) return st; x -= d; } return "EMPTY"; }
  function cinemaNextEnding(tMs) { const base = Math.floor(tMs / 1000 / CINEMA_PERIOD) * CINEMA_PERIOD; let o = 0; for (const [st, d] of CINEMA_CYCLE) { if (st === "ENDING") return (base + o) * 1000; o += d; } return tMs; }

  // spots: { id, room, node, x, y, face:[fx,fy], pose, h }
  function buildSpots(world) {
    const { D, key, anchors, rooms } = world;
    const sp = {};
    const tileCentre = (t) => [t[0] * T + 6, t[1] * T + 6];
    const furnCentre = (label) => { const f = D.furniture.find((q) => q.label === label); if (!f) return null; const xs = f.tiles.map((t) => t[0] * T + 6), ys = f.tiles.map((t) => t[1] * T + 6); return [xs.reduce((a, b) => a + b) / xs.length, ys.reduce((a, b) => a + b) / ys.length]; };
    const unit = (dx, dy) => { const L = Math.hypot(dx, dy) || 1; return [dx / L, dy / L]; };
    const hub = world.hub;
    const nearestBlockFace = (t, room) => { const [x, y] = tileCentre(t); let best = null, bd = 1e9; for (const f of D.furniture) { if (f.room !== room || f.kind !== "block") continue; for (const u of f.tiles) { const d = Math.abs(u[0] - t[0]) + Math.abs(u[1] - t[1]); if (d < bd && d <= 2) { bd = d; best = tileCentre(u); } } } return best ? unit(best[0] - x, best[1] - y) : unit(hub.x - x, hub.y - y); };
    const anchorSpot = (name, pose, face) => { const a = anchors[name]; if (!a) return null; const [x, y] = tileCentre(a.tile); let f = face; if (!f) { const c = a.serves && furnCentre(a.serves); const k = key(...a.tile); f = c && !world.seats.has(k) ? unit(c[0] - x, c[1] - y) : nearestBlockFace(a.tile, a.room); } return { id: name, room: a.room, node: key(...a.tile), x, y, face: f, pose, h: 0 }; };
    const list = (re, pose, face) => D.anchors.filter((a) => re.test(a.name)).map((a) => anchorSpot(a.name, pose, face)).filter(Boolean);
    sp.CAFE = list(/^habitat\.cafe_seat_/, "sit");
    sp.LOUNGE = list(/^habitat\.sofa_/, "sit");
    sp.GAMES = list(/^habitat\.billiards_/, "stand");
    sp.WINDOW = list(/^habitat\.window_/, "sit").map((s) => ({ ...s, face: unit(s.x - hub.x, s.y - hub.y) }));
    sp.REST = list(/^habitat\.rest_pod_/, "sit"); // cosmetic rest pods only: recovery pods mean a real cooldown (plan §12)
    const fountain = furnCentre("LEI-007 park fountain");
    sp.PARK_BENCH = D.furniture.filter((f) => /SEA-009 park bench/.test(f.label)).flatMap((f) => f.tiles.map((t) => { const [x, y] = tileCentre(t); return { id: `${f.label}:${t}`, room: "H-HAB", node: key(...t), x, y, face: unit(fountain[0] - x, fountain[1] - y), pose: "sit", h: 0 }; }));
    const fTiles = D.furniture.find((f) => f.label === "LEI-007 park fountain").tiles;
    const ring = new Set();
    for (const [c, r] of fTiles) for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const k = key(c + dc, r + dr); if (world.tileWalk(k) && !world.seats.has(k) && !world.anchorAt.has(k) && world.region.get(k) === "H-HAB") ring.add(k); }
    sp.FOUNTAIN = [...ring].sort().map((k) => { const [x, y] = world.nodePos(k); return { id: "fountain:" + k, room: "H-HAB", node: k, x, y, face: unit(fountain[0] - x, fountain[1] - y), pose: "stand", h: 0 }; });
    // park loop: walkable park-ground tiles around the fountain and the planter, visited in angle order
    const park = D.furniture.find((f) => /FLR-012/.test(f.label));
    const pTiles = (park ? park.tiles : []).map((t) => key(...t)).filter((k) => world.tileWalk(k) && !world.seats.has(k) && !world.anchorAt.has(k) && world.region.get(k) === "H-HAB");
    const pc = pTiles.map((k) => world.nodePos(k)); const mx = pc.reduce((s, p) => s + p[0], 0) / (pc.length || 1), my = pc.reduce((s, p) => s + p[1], 0) / (pc.length || 1);
    sp.PARK_LOOP = pTiles.map((k) => { const [x, y] = world.nodePos(k); return { k, ang: Math.atan2(y - my, x - mx), d: Math.hypot(x - mx, y - my) }; }).filter((p) => p.d > 30).sort((a, b) => a.ang - b.ang || a.k.localeCompare(b.k));
    // host round: free tiles next to the café tables
    const tables = D.furniture.filter((f) => /TBL-003/.test(f.label));
    sp.HOST_ROUND = tables.flatMap((f) => f.tiles.flatMap(([c, r]) => [[0, 1], [0, -1]].map(([dc, dr]) => key(c + dc, r + dr)))).filter((k) => world.tileWalk(k) && !world.seats.has(k) && !world.anchorAt.has(k)).map((k) => { const [x, y] = world.nodePos(k); return { id: "host:" + k, room: "H-HAB", node: k, x, y, face: [0, -1], pose: "stand", h: 0 }; });
    // radial-room spots: node = the nearest reachable cell, then a short straight approach to the exact position
    const rSpot = (room, name) => (REC[room].spots[name] || []).map((p, i) => {
      const rm = rooms[room]; const [x, y] = world.rP(rm, p.s, p.t);
      let node = null, bd = 1e9; for (const [k, c] of world.cells) if (c.room === room) { const d = Math.hypot(c.s - p.s, c.t - p.t); if (d < bd) { bd = d; node = k; } }
      const fd = { u: rm.u, "-u": [-rm.u[0], -rm.u[1]], v: rm.v, "-v": [-rm.v[0], -rm.v[1]] }[p.face];
      const tgt = p.face === "m" ? world.rP(rm, -2, 0) : world.rP(rm, 20, 0);
      return { id: `${room}.${name}_${i + 1}`, room, node, x, y, face: fd || unit(tgt[0] - x, tgt[1] - y), pose: p.pose, h: p.h };
    });
    sp.MEDITATE = rSpot("R1", "meditate"); sp.CINEMA = rSpot("R2", "cinema"); sp.DECOMPRESS = rSpot("R3", "decompress"); sp.DOG_PLAY = rSpot("R4", "play");
    sp.DOG_REST = rSpot("R4", "dogBed"); sp.DOG_DRINK = rSpot("R4", "dogWater"); sp.DOG_PLAYING = rSpot("R4", "dogPlay");
    // the dog's habitat spots: spread over the whole H-HAB floor (free tiles, never seats or anchors), plus its home tile
    const dogHome = D.furniture.find((f) => f.asset === "DEC-009");
    const free = [...world.region].filter(([k, n]) => n === "H-HAB" && world.tileWalk(k) && !world.seats.has(k) && !world.anchorAt.has(k)).map(([k]) => k).sort((a, b) => fnv(a) - fnv(b));
    const chosen = []; for (const k of free) { const p = world.nodePos(k); if (chosen.every((q) => Math.hypot(q[0] - p[0], q[1] - p[1]) > 60)) chosen.push(p.concat([k])); if (chosen.length >= 18) break; }
    if (dogHome) chosen.unshift([...world.nodePos(key(...dogHome.tiles[0])), key(...dogHome.tiles[0])]);
    sp.DOG_IDLE = chosen.map(([x, y, k]) => ({ id: "dog:" + k, room: "H-HAB", node: k, x, y, face: unit(hub.x - x, hub.y - y), pose: "sit", h: 0 }));
    return sp;
  }

  // ------------------------------------------------------------------ the simulation
  function create(world, opt = {}) {
    const seed = String(opt.seed || "stellar");
    const bus = makeBus();
    const spots = buildSpots(world);
    const taken = new Map(); // spot id -> actor id
    let t = 0, acc = 0;
    const actors = [];
    const emit = (type, extra) => bus.emit({ type, t, ambient: true, ...extra });
    // humans: every rendered agent (V1 has no engine link: all are idle, so all are ambient-eligible)
    for (const a of world.D.agents) {
      const an = world.anchors[a.anchor];
      const k = world.key(...a.tile);
      const home = { id: a.anchor, room: a.room, node: k, x: a.tile[0] * T + 6, y: a.tile[1] * T + 6, face: a.face, pose: "desk", h: 0 };
      const act = { id: a.chr, kind: "agent", code: a.code, cls: a.cls, home: a.room, homeSpot: home, beat: 0, x: home.x, y: home.y, face: a.face.slice(), node: k, room: a.room,
        act: "WORKING", state: "WORKING", phase: "dwell", spot: home, until: 0, route: null, ri: 0, alpha: 1, fadeUntil: 0, stride: 0, anchorName: an ? an.name : a.anchor };
      act.allow = allowedRooms(act, world);
      actors.push(act);
    }
    const dogF = world.D.furniture.find((f) => f.asset === "DEC-009");
    let dog = null;
    if (dogF) {
      const k = world.key(...dogF.tiles[0]); const [x, y] = world.nodePos(k);
      const s0 = spots.DOG_IDLE[0];
      dog = { id: "DEC-009", kind: "dog", code: "DOG", home: "H-HAB", beat: 0, x, y, face: [0, 1], node: k, room: "H-HAB", act: "DOG_IDLE", state: "DOG_IDLE", phase: "dwell", spot: s0, until: 0, route: null, ri: 0, alpha: 1, fadeUntil: 0, stride: 0 };
      dog.allow = allowedRooms(dog, world); taken.set(s0.id, dog.id); actors.push(dog);
    }
    // first dwell staggered, so departures spread over the first minutes instead of all at once
    for (const a of actors) { const r = rngFor(seed, a.id, "start"); a.until = Math.round(between(r, a.kind === "dog" ? 20 : 30, a.kind === "dog" ? 90 : 600) * 1000); if (a.kind === "agent") emit("AGENT_START_WORK", { actor: a.id, room: a.room, spot: a.spot.id }); }
    let cinema = cinemaAt(0);
    const doors = {}; // door id -> { open, lastSeen, by }

    const counts = () => { const c = { away: 0 }; for (const a of actors) { if (a.kind !== "agent" || a.act === "WORKING") continue; const dest = a.spot && a.spot.room ? a.spot.room : a.room; if (dest !== a.home) c.away++; c[dest] = (c[dest] || 0) + 1; } return c; };
    const freeSpot = (list, r) => { const f = list.filter((s) => !taken.has(s.id) && s.node); return f.length ? pick(r, f) : null; };
    const dur = (r, name) => { const d = ACTIVITIES[name].dur; return Math.round(between(r, d[0], d[1]) * 1000); };

    function startActivity(a, name, spot, r, force) {
      if (a.spot && taken.get(a.spot.id) === a.id) taken.delete(a.spot.id);
      if (spot && spot.room && !a.allow.has(spot.room)) return false;
      a.act = name; a.spot = spot; if (spot && spot.id) taken.set(spot.id, a.id);
      a.dwellMs = name === "CINEMA" ? Math.max(30000, cinemaNextEnding(t) - t) : dur(r, name);
      emit("AGENT_START_ACTIVITY", { actor: a.id, activity: name, room: spot ? spot.room : a.room, ambient: true, forced: !!force });
      if (name === "PARK_WALK") { // a loop of 3-5 park waypoints walked in order, then the walk ends where it stops
        const L = spots.PARK_LOOP; if (!L.length) return false;
        const i0 = Math.floor(r() * L.length), n = 3 + Math.floor(r() * 3), step = Math.max(1, Math.floor(L.length / 6));
        a.parkQueue = []; for (let i = 0; i < n; i++) a.parkQueue.push(L[(i0 + i * step) % L.length].k);
        const k = a.parkQueue.shift(); const [x, y] = world.nodePos(k); a.spot = { id: "", room: "H-HAB", node: k, x, y, face: a.face, pose: "stand", h: 0 };
      }
      return route(a, a.spot);
    }
    function route(a, spot) {
      const p = findPath(world, a, a.node, spot.node);
      a.phase = "walk"; a.state = a.kind === "dog" ? "DOG_WALKING" : "WALKING"; a.walkStart = t;
      if (!p) { teleport(a, spot); return true; } // no route: fade out, fade in at the destination (plan §16 fallback)
      const sm = smooth(world, a, p);
      a.route = sm.map((n) => { const [x, y] = world.nodePos(n.k); return { k: n.k, x, y, door: n.doorIn }; });
      if (spot.x !== a.route[a.route.length - 1].x || spot.y !== a.route[a.route.length - 1].y) a.route.push({ k: spot.node, x: spot.x, y: spot.y, door: "", final: true });
      // a radial-room portal crossing passes through the door point itself
      for (let i = 1; i < a.route.length; i++) { const w = a.route[i]; if (w.door && world.portals[w.door]) { const [dx, dy] = world.doorPos[w.door]; a.route.splice(i, 0, { k: a.route[i - 1].k, x: dx, y: dy, door: "", via: w.door }); i++; } }
      a.ri = Math.hypot(a.x - a.route[0].x, a.y - a.route[0].y) > 0.5 ? 0 : 1; // leaving a seat inside furniture: back to its approach cell first
      return true;
    }
    function teleport(a, spot) { a.x = spot.x; a.y = spot.y; a.node = spot.node; setRoom(a, world.nodeRegion(spot.node)); a.route = null; a.alpha = 0; a.fadeUntil = t + 600; arrive(a); }
    function setRoom(a, n) {
      if (!n || world.doorSides[n] || n === a.room) return;
      const prev = a.room; a.room = n;
      if (a.kind === "dog") { if (n === "R4") emit("DOG_ENTER_R4", { actor: a.id, room: n, from: prev }); if (n === "H-HAB") emit("DOG_ENTER_HHAB", { actor: a.id, room: n, from: prev }); }
      else { emit("AGENT_EXIT_ROOM", { actor: a.id, room: prev }); emit("AGENT_ENTER_ROOM", { actor: a.id, room: n, from: prev }); }
    }
    function arrive(a) {
      const def = ACTIVITIES[a.act];
      a.phase = "dwell"; a.state = def.state; a.until = t + a.dwellMs; a.route = null;
      if (a.spot && a.spot.face) a.face = a.spot.face.slice();
      if (a.act === "PARK_WALK") { if (a.parkQueue && a.parkQueue.length) { const k = a.parkQueue.shift(); const [x, y] = world.nodePos(k); a.spot = { id: "", room: "H-HAB", node: k, x, y, face: a.face, pose: "stand", h: 0 }; route(a, a.spot); return; } a.state = "STANDING"; }
      if (a.hopping) { a.hopping = false; a.state = "DOG_PLAYING"; return; } // a play run between two play spots: no new events
      if (a.spot && ((a.spot.pose === "sit" || a.spot.pose === "floor") || a.spot.pose === "desk" && world.seats.has(a.spot.node))) emit("AGENT_SIT", { actor: a.id, room: a.room, spot: a.spot.id });
      if (def.start) emit(def.start, { actor: a.id, room: a.room, spot: a.spot && a.spot.id });
      if (a.kind === "dog" && a.act === "DOG_PLAYING") { a.hops = 5 + Math.floor(rngFor(seed, a.id, a.beat, "hops")() * 5); a.hopAt = t + 2500; }
    }
    function finish(a) {
      const def = ACTIVITIES[a.act];
      if (def.end) emit(def.end, { actor: a.id, room: a.room, spot: a.spot && a.spot.id });
      if (a.spot && ((a.spot.pose === "sit" || a.spot.pose === "floor") || a.spot.pose === "desk" && world.seats.has(a.spot.node))) emit("AGENT_STAND", { actor: a.id, room: a.room, spot: a.spot.id });
      emit("AGENT_END_ACTIVITY", { actor: a.id, activity: a.act, room: a.room });
    }
    function chooseNext(a) {
      const r = rngFor(seed, a.id, a.beat++);
      if (a.kind === "dog") return chooseDog(a, r);
      if (a.cls === "MP-HOST") { // the café host serves the tables and returns to the counter; H-HAB only
        if (a.act === "WORKING" && r() < 0.5) { const s = freeSpot(spots.HOST_ROUND, r); if (s) return startActivity(a, "HOST_ROUND", s, r); }
        return startActivity(a, "WORKING", a.homeSpot, r);
      }
      if (a.act !== "WORKING") { // after an ambient activity: usually back to the workstation, sometimes one more habitat beat
        if (a.room === "H-HAB" && r() < 0.25) { const n = pickAway(a, r, ["CAFE", "LOUNGE", "WINDOW", "PARK_BENCH", "FOUNTAIN", "PARK_WALK"]); if (n) return n; }
        return startActivity(a, "WORKING", a.homeSpot, r);
      }
      const x = r();
      if (x < 0.5 && counts().away < CAPS.away) { const n = pickAway(a, r); if (n) return n; }
      if (x < 0.7) { const s = freeSpot(strollSpots(a), r); if (s) return startActivity(a, "STROLL", s, r); }
      return startActivity(a, "WORKING", a.homeSpot, r);
    }
    function strollSpots(a) { return a.home === "H-HAB" ? [] : world.D.anchors.filter((an) => an.room === a.home && !an.chr).map((an) => ({ id: an.name, room: an.room, node: world.key(...an.tile), x: an.tile[0] * T + 6, y: an.tile[1] * T + 6, face: a.face, pose: "stand", h: 0 })).filter((s) => !world.seats.has(s.node)); }
    function pickAway(a, r, only) {
      const c = counts();
      const names = (only || ["CAFE", "LOUNGE", "GAMES", "WINDOW", "REST", "PARK_BENCH", "FOUNTAIN", "PARK_WALK", "MEDITATE", "CINEMA", "DECOMPRESS", "DOG_PLAY"]).filter((n) => {
        const d = ACTIVITIES[n]; if (!a.allow.has(d.room)) return false;
        if (d.room === "H-HAB" && (c["H-HAB"] || 0) >= CAPS["H-HAB"]) return false;
        if (d.cap && (c[d.room] || 0) >= d.cap) return false;
        if (n === "CINEMA" && cinema !== "PREPARING") return false;
        if (n === "DOG_PLAY" && !(dog && dog.room === "R4" && dog.act !== "DOG_REST")) return false;
        if (n === "PARK_WALK") return spots.PARK_LOOP.length > 0;
        return (spots[n] || []).some((s) => !taken.has(s.id));
      });
      const n = weighted(r, names.map((x) => [x, ACTIVITIES[x].w || 1]));
      if (!n) return null;
      const s = n === "PARK_WALK" ? { room: "H-HAB" } : freeSpot(spots[n], r);
      return s ? startActivity(a, n, n === "PARK_WALK" ? null : s, r) : null;
    }
    function chooseDog(a, r) {
      const prev = a.act;
      const opts = prev === "DOG_IDLE" ? [["DOG_IDLE", 5], ["DOG_PLAYING", 2], ["DOG_REST", 1.5], ["DOG_DRINK", 1.5]]
        : prev === "DOG_PLAYING" ? [["DOG_DRINK", 5], ["DOG_IDLE", 5]]
          : prev === "DOG_REST" ? [["DOG_IDLE", 6], ["DOG_PLAYING", 4]] : [["DOG_IDLE", 5], ["DOG_PLAYING", 3], ["DOG_REST", 2]];
      const n = weighted(r, opts);
      const s = freeSpot(spots[n], r) || spots.DOG_IDLE[0];
      return startActivity(a, n, s, r);
    }

    // doors: a physical state machine CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED with real travel (DOOR_MOVE ms). An actor
    // within reach of a door on its route asks for it; the door holds open while anyone is in the passage and for DOOR_HOLD
    // after the last request; a request during CLOSING reverses it. The renderer draws the leaf at fraction k (0 shut, 1 open)
    // and the sound layer hears the four transitions: DOOR_OPEN (travel starts), DOOR_OPENED (end stop), DOOR_CLOSE, DOOR_CLOSED
    const DOOR_MOVE = 900, DOOR_HOLD = 1500, DOOR_REACH = 30, DOOR_PASS = 14;
    const doorOf = (d) => doors[d] || (doors[d] = { state: "CLOSED", k: 0, lastSeen: -1e9 });
    function stepDoors() {
      const want = {}, pass = {};
      for (const a of actors) {
        if (a.phase !== "walk" || !a.route) continue;
        for (let i = Math.max(1, a.ri - 1); i < Math.min(a.route.length, a.ri + 3); i++) {
          const w = a.route[i], d = w.door || w.via; if (!d) continue;
          const [dx, dy] = world.doorPos[d]; const dd = Math.hypot(a.x - dx, a.y - dy);
          if (dd < DOOR_REACH) want[d] = want[d] || a.id;
          if (dd < DOOR_PASS) pass[d] = true;
        }
      }
      for (const [d, by] of Object.entries(want)) { const s = doorOf(d); s.lastSeen = t; if (s.state === "CLOSED" || s.state === "CLOSING") { s.state = "OPENING"; s.by = by; emit("DOOR_OPEN", { door: d, actor: by, from: +s.k.toFixed(2) }); } }
      const dk = STEP / DOOR_MOVE;
      for (const [d, s] of Object.entries(doors)) {
        if (s.state === "OPENING") { s.k = Math.min(1, s.k + dk); if (s.k >= 1) { s.state = "OPEN"; emit("DOOR_OPENED", { door: d }); } }
        else if (s.state === "CLOSING") { s.k = Math.max(0, s.k - dk); if (s.k <= 0) { s.state = "CLOSED"; emit("DOOR_CLOSED", { door: d }); } }
        else if (s.state === "OPEN" && t - s.lastSeen > DOOR_HOLD && !pass[d]) { s.state = "CLOSING"; emit("DOOR_CLOSE", { door: d }); }
      }
    }
    // an actor waits at a door that is not yet open enough to pass (it never walks through a panel)
    function blockedByDoor(a) {
      for (let i = a.ri; i < Math.min(a.route.length, a.ri + 2); i++) {
        const w = a.route[i], d = w.door || w.via; if (!d) continue;
        const s = doors[d]; const [dx, dy] = world.doorPos[d];
        if ((!s || s.k < 0.8) && Math.hypot(a.x - dx, a.y - dy) < 18) return true;
      }
      return false;
    }

    function stepActor(a, dt) {
      if (a.fadeUntil && t >= a.fadeUntil) { a.alpha = 1; a.fadeUntil = 0; } else if (a.fadeUntil) a.alpha = 1 - (a.fadeUntil - t) / 600;
      if (a.phase === "walk" && a.route) {
        const speed = a.kind === "dog" ? (a.act === "DOG_PLAYING" ? 34 : 24) : 18; // units per second
        let left = speed * dt / 1000;
        if (t - a.walkStart > 150000) { teleport(a, a.spot); return; } // walk too long: fade (plan §1.6)
        if (blockedByDoor(a)) { a.waitMs = (a.waitMs || 0) + dt; if (a.waitMs < 8000) return; } else a.waitMs = 0; // safety: never stuck forever
        while (left > 0 && a.ri < a.route.length) {
          const w = a.route[a.ri]; const dx = w.x - a.x, dy = w.y - a.y; const L = Math.hypot(dx, dy);
          if (L > 1e-6) { a.face = [dx / L, dy / L]; }
          if (L <= left) { a.x = w.x; a.y = w.y; left -= L; a.stride += L; a.node = w.k; setRoom(a, world.nodeRegion(w.k)); a.ri++; }
          else { a.x += dx / L * left; a.y += dy / L * left; a.stride += left; left = 0; }
        }
        if (a.ri >= a.route.length) arrive(a);
        return;
      }
      if (a.kind === "dog" && a.act === "DOG_PLAYING" && a.phase === "dwell" && a.hops > 0 && t >= a.hopAt) { // play: short runs between play spots
        const r = rngFor(seed, a.id, a.beat, "hop", a.hops); const s = freeSpot(spots.DOG_PLAYING, r);
        a.hops--; a.hopAt = t + 4000;
        if (s) { taken.delete(a.spot.id); a.spot = s; taken.set(s.id, a.id); a.dwellMs = Math.max(2000, a.until - t); a.hopping = true; route(a, s); a.state = "DOG_PLAYING"; return; }
      }
      if (a.phase === "dwell" && t >= a.until) {
        if (a.act === "CINEMA" && cinema !== "ENDING" && cinema !== "EMPTY") { a.until = t + 5000; return; }
        finish(a); chooseNext(a);
      }
      if (a.kind === "agent" && a.act === "DOG_PLAY" && a.phase === "dwell" && dog && dog.room !== "R4") a.until = Math.min(a.until, t); // the dog left: play ends
    }
    function stepCinema() {
      const c = cinemaAt(t); if (c === cinema) return;
      cinema = c; emit("CINEMA_STATE", { room: "R2", state: c });
      if (c === "PREPARING") { // the session is an event source: it draws a small audience from agents at their workstations
        const session = Math.floor(t / 1000 / CINEMA_PERIOD), r = rngFor(seed, "cinema", session);
        const cand = actors.filter((a) => a.kind === "agent" && a.act === "WORKING" && a.phase === "dwell" && a.allow.has("R2")).sort((p, q) => fnv(p.id + "|" + session) - fnv(q.id + "|" + session));
        for (const a of cand.slice(0, 2 + Math.floor(r() * 3))) { if (counts().away >= CAPS.away) break; const s = freeSpot(spots.CINEMA, r); if (!s) break; finish(a); startActivity(a, "CINEMA", s, r); }
      }
      if (c === "SCREENING") emit("CINEMA_START", { room: "R2", watchers: actors.filter((a) => a.act === "CINEMA").map((a) => a.id) });
      if (c === "ENDING") { emit("CINEMA_END", { room: "R2" }); for (const a of actors) if (a.act === "CINEMA" && a.phase === "dwell") a.until = Math.min(a.until, t + 2000 + (fnv(a.id) % 8000)); }
    }
    function step1() { t += STEP; stepCinema(); for (const a of actors) stepActor(a, STEP); stepDoors(); }
    return {
      bus, on: bus.on, events: bus.log, world, spots,
      get t() { return t; }, get cinema() { return cinema; }, doors,
      step(dtMs) { acc += Math.max(0, Math.min(dtMs, 2000)); while (acc >= STEP) { acc -= STEP; step1(); } },
      advanceTo(ms) { while (t + STEP <= ms) step1(); },
      actors, dog,
      // force an activity (tests, scripted scenes); permissions still apply: returns false if the actor may not go there
      assign(id, name, spotId) {
        const a = actors.find((x) => x.id === id); if (!a || !ACTIVITIES[name]) return false;
        const r = rngFor(seed, a.id, a.beat++, "assign");
        let s = name === "WORKING" ? a.homeSpot : null;
        if (!s && name !== "PARK_WALK") { const list = name === "STROLL" ? strollSpots(a) : spots[name] || []; s = spotId ? list.find((x) => x.id === spotId) : list.find((x) => !taken.has(x.id)); }
        const room = s ? s.room : ACTIVITIES[name].room; if (room && !a.allow.has(room)) return false;
        if (a.phase === "dwell") finish(a);
        return startActivity(a, name, s, r, true);
      },
      // a real task pre-empts ambient behaviour at once (plan §12): back to the workstation, fading if the walk is long
      preempt(id) { const a = actors.find((x) => x.id === id); if (!a || a.kind !== "agent") return false; if (a.phase === "dwell") finish(a); return startActivity(a, "WORKING", a.homeSpot, rngFor(seed, a.id, "preempt", t), true); },
      snapshot() { return actors.map((a) => ({ id: a.id, kind: a.kind, x: a.x, y: a.y, face: a.face, state: a.state, act: a.act, room: a.room, phase: a.phase, pose: a.phase === "walk" ? "walk" : a.spot ? a.spot.pose : "stand", h: a.phase === "walk" ? 0 : a.spot ? a.spot.h || 0 : 0, atHome: a.kind === "agent" && a.act === "WORKING" && a.phase === "dwell", alpha: a.alpha, stride: a.stride, spot: a.spot ? a.spot.id : "" })); },
    };
  }
  return { T, STEP, EVENTS, SOUND_HOOKS, STATES, ACTIVITIES, REC, CAPS, fnv, mulberry32, rngFor, buildWorld, allowedRooms, regionAllowed, findPath, smooth, segClear, cinemaAt, create };
});
