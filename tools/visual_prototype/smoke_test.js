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
  await browser.close();
  if (errors.length) {
    console.error("FAILED:\n  " + errors.join("\n  "));
    process.exit(1);
  }
  console.log("smoke test passed");
})();
