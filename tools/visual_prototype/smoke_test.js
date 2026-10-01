// Optional browser smoke test for the Visual Prototype (needs Node + Playwright with Chromium).
//   NODE_PATH="$(npm root -g)" node tools/visual_prototype/smoke_test.js [screenshot-dir]
// Opens the committed page in every camera view and the key room focuses, fails on any page
// error, and checks the frozen default camera (Iso · right). Screenshots are optional.
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const page = path.resolve(__dirname, "../../docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html");
const shotDir = process.argv[2];
const cases = [
  ["default", ""],
  ["station_iso_right", "?focus=Station"],
  ["station_iso_left", "?view=iso&focus=Station"],
  ["station_plan", "?view=plan&focus=Station"],
  ["H-CMD_oblique", "?view=obl&focus=H-CMD"],
  ["H-LAB_oblique", "?view=obl&focus=H-LAB"],
  ["wing_oblique", "?view=obl&x=600&y=660&z=1.6"],
  ["L10_restricted", "?x=744&y=924&z=4"],
  ["H-HAB_oblique", "?view=obl&focus=H-HAB"],
  ["H-HAB_park", "?x=1420&y=692&z=5"],
  ["R1_zen", "?focus=R1"],
  ["R2_cinema", "?focus=R2"],
  ["R3_decompression", "?focus=R3"],
  ["R4_dog_play", "?focus=R4"],
  ["vocabulary", "?vocab=1"],
  ["vocabulary_oblique", "?vocab=1&view=obl"],
  ["L2", "?focus=L2"],
  ["H-CMD", "?focus=H-CMD"],
  ["H-LAB", "?focus=H-LAB"],
  ["H-HAB", "?focus=H-HAB"],
  ["reserved", "?focus=Reserved"],
  ["grid_preview", "?focus=L3&grid=1&anchors=1&preview=1"],
  ["life_off_baseline", "?life=0&focus=Station"],
  ["life_station", "?lifeT=1500&focus=Station"],
  ["life_habitat", "?lifeT=1500&x=1400&y=690&z=2.6"],
  ["life_recreation", "?lifeT=2700&x=1500&y=640&z=1.8"],
];

(async () => {
  const browser = await chromium.launch();
  const tab = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  tab.on("pageerror", (e) => errors.push(e.message));
  tab.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  if (shotDir) fs.mkdirSync(shotDir, { recursive: true });
  for (const [name, query] of cases) {
    await tab.goto("file://" + page + query);
    await tab.waitForTimeout(400);
    const state = await tab.evaluate(() => ({ items: window.__stellar.scene().items.length, view: document.querySelector("#v-isoR").classList.contains("on") }));
    if (!state.items) errors.push(`${name}: empty scene`);
    if (name === "default" && !state.view) errors.push("default camera is not Iso · right");
    if (name.startsWith("life_")) {
      // the life layer: frozen seeded time, actors drawn in depth order, R1-R4 footprints match the drawn furniture,
      // nobody in a reserved room, the dog only in H-HAB / R4
      const lf = await tab.evaluate(() => {
        const st = window.__stellar, life = st.life();
        const out = { on: st.lifeOn(), actors: 0, bad: [] };
        if (!out.on) return out;
        const snap = life.snapshot(); out.actors = snap.length;
        for (const a of snap) { if (["R5", "R6", "L5", "L8"].includes(a.room)) out.bad.push(`${a.id} in ${a.room}`); if (a.kind === "dog" && !["H-HAB", "R4"].includes(a.room)) out.bad.push(`dog in ${a.room}`); }
        for (const rr of rRooms.filter((r) => REC_ACTIVE.has(r.id))) {
          const fp = StellarLife.REC[rr.id].block;
          for (const it of calRecItems(rr)) {
            if (it.h <= 3) continue; const x = (it.b[0] + it.b[2]) / 2, y = (it.b[1] + it.b[3]) / 2;
            const s = (x - rr.cx) * Math.cos(rr.a) + (y - rr.cy) * Math.sin(rr.a), t = -(x - rr.cx) * Math.sin(rr.a) + (y - rr.cy) * Math.cos(rr.a);
            if (!fp.some(([bs, bt, hs, ht]) => Math.abs(s - bs) <= hs + 1 && Math.abs(t - bt) <= ht + 1)) out.bad.push(`${rr.id} item at (${s.toFixed(0)},${t.toFixed(0)}) has no navigation footprint`);
          }
        }
        return out;
      });
      if (name === "life_off_baseline") { if (lf.on) errors.push("life=0 must show the static baseline"); }
      else if (!lf.on || lf.actors !== 42) errors.push(`${name}: life layer not running (${lf.actors} actors)`);
      for (const b of lf.bad) errors.push(`${name}: ${b}`);
    }
    if (shotDir) await tab.screenshot({ path: path.join(shotDir, `${name}.png`) });
    console.log(`ok  ${name} (${state.items} scene items)`);
  }
  // sound: off by default; Sound (a user gesture) builds the procedural engine; a storm stays inside the voice budget,
  // every one-shot is released, loops are a fixed set, disabling stops them all; the canvas is untouched by sound
  {
    await tab.goto("file://" + page + "?life=0&x=1215&y=696&z=2.6");
    await tab.waitForTimeout(300);
    const before = await tab.evaluate(() => ({ on: !!window.__stellar.sound(), btn: document.querySelector("#t-sound").classList.contains("on") }));
    if (before.on || before.btn) errors.push("sound must be off until the user enables it");
    await tab.click("#t-sound");
    await tab.waitForTimeout(400);
    const st = await tab.evaluate(async () => {
      const s = window.__stellar.sound(), d = window.__stellar.director();
      const r = { state: s.state, loops: s.loopCount, mixer: document.querySelector("#mixer").style.display };
      await new Promise((ok) => setTimeout(ok, 1500)); r.amb = s.level();
      for (let i = 0; i < 3000; i++) d.onEvent({ type: "DOOR_OPEN", t: i, door: "DR-CMD-HAB" });
      for (let i = 0; i < 3000; i++) d.onEvent({ type: "AGENT_SIT", t: i, actor: "CHR-043", room: "H-HAB" });
      await new Promise((ok) => setTimeout(ok, 400)); r.gated = s.created;
      s.apply({ beds: {}, plays: Array.from({ length: 100 }, (_, i) => ({ cue: "door.open.standard", group: "DOORS", gain: 0.05, pan: 0, rate: 1, variant: i % 3 })) });
      r.peak = s.active; r.created = s.created;
      await new Promise((ok) => setTimeout(ok, 4000)); r.after = s.active; r.loops2 = s.loopCount;
      const t0 = performance.now(); let n = 0; await new Promise((ok) => { (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else ok(); })(); }); r.fps = n / 2;
      window.__stellar.setSound(false); r.off = s.state; r.loops3 = s.loopCount;
      return r;
    });
    if (st.state !== "running" && st.state !== "suspended") errors.push(`sound engine not created (${st.state})`);
    if (st.mixer !== "flex") errors.push("mixer not shown with sound on");
    if (!(st.amb.rms > 0.0005 && st.amb.peak < 0.9)) errors.push(`station ambience not audible or clipping (rms ${st.amb.rms}, peak ${st.amb.peak})`);
    if (!(st.loops > 10)) errors.push(`ambience loops missing (${st.loops})`);
    if (st.loops2 !== st.loops) errors.push(`ambience loops grew (${st.loops} -> ${st.loops2})`);
    if (st.peak > 14 || st.peak < 10) errors.push(`voice budget not enforced (${st.peak})`);
    if (!(st.created > 0)) errors.push("no sound was synthesised for the door storm");
    if (st.after > 3) errors.push(`one-shots not released (${st.after} still active)`);
    if (st.off !== "off" || st.loops3 !== 0) errors.push("disabling sound must stop every loop");
    if (st.fps < 30) errors.push(`sound costs frame rate (${st.fps} fps)`);
    console.log(`ok  sound (ambience rms ${st.amb.rms.toFixed(4)} peak ${st.amb.peak.toFixed(3)}, ${st.loops} loops, storm gated to ${st.gated} voices, 100-voice burst capped at ${st.peak}, ${st.after} left after 4 s, ${st.fps} fps)`);
  }
  await browser.close();
  if (errors.length) {
    console.error("FAILED:\n  " + errors.join("\n  "));
    process.exit(1);
  }
  console.log("smoke test passed");
})();
