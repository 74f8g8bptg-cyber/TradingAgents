# Stellar visual prototype — build pipeline

This pipeline generates and validates two static pages:

- `docs/preview/STELLAR_GEOMETRY_PREVIEW_V1.html`: the top-down geometry and scale preview (`docs/STELLAR_SPATIAL_SCALE_V1.md`).
- `docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html`: the Visual Prototype V1 (`docs/STELLAR_VISUAL_PROTOTYPE_V1.md`). The default camera is **Iso · right**.

These are **design tools, not production code**. Nothing here is imported by `stellar/` or `tradingagents/`. The pipeline only *reads* the approved registries under `docs/` and never edits them. It uses the Python standard library only.

## Layout

| File | Role |
|---|---|
| `build.py` | Entry point. It runs the whole pipeline, writes or verifies the two pages, and can dump the intermediate JSON models |
| `geometry.py` | **Geometry model and geometry validation.** It contains the approved Floor Plan coordinates, room layouts, furniture footprints and anchors. It rasterises the plan at 12 units per tile and runs the consistency checks: footprints, anchors, door approaches, connectivity, corridor width, two-agent passing and camera occlusion |
| `registry.py` | **Registry loading.** Read-only parsers for the Screen, Character and Asset registries |
| `prototype_data.py` | **Data assembly.** Turns the geometry and the registries into the prototype's data: walls, hull, doors, characters, and displays with their approved offline states and placements |
| `render.py` | Fills the two HTML templates with the JSON data (**generation**) |
| `check_visual.py` | **Visual consistency validation.** Checks the data and the page against the registries (see "What the checks cover" below) |
| `templates/geometry_preview.html`, `templates/visual_prototype.html` | The page templates (renderer code). The data is injected at `/*DATA*/null` |
| `templates/stellar_vocabulary.js` | The reusable **Stellar Visual Vocabulary** (`docs/STELLAR_VISUAL_VOCABULARY_V1.md`): construction grammar, materials, screens, and the workstation, console, equipment, chair, table, wall, floor and small-prop families. `render.py` inlines it into the prototype at `/*VOCABULARY*/`. Rooms compose these families; they do not redefine them. The page's **Vocabulary** button (`?vocab=1`) renders every family on its own |
| `templates/stellar_life.js` | The **life layer** (`docs/STELLAR_LIFE_SYSTEM_V1.md`): ambient activity, navigation on the geometry model, doors, cinema session, resident dog and the event hooks. Pure and seeded; `render.py` inlines it at `/*LIFE*/`. The page's **Life** button (`?life=0` for the static baseline, `?lifeT=SECONDS` to freeze a simulated time, `?seed=`, `?speed=`) |
| `life_test.js` | Deterministic life-layer tests (Node only): work, corridors, H-HAB, R1–R4, the dog rule, reserved rooms, furniture, doors, caps, determinism |
| `smoke_test.js` | Optional browser smoke test (Node + Playwright) |

## Rebuild

Run these from the repository root.

```bash
# Rebuild both pages (runs both consistency checks first; writes nothing if a check fails)
python tools/visual_prototype/build.py

# Rebuild test: rebuild in memory and require byte-identical output against the committed pages
python tools/visual_prototype/build.py --check

# Also print the room-fit report and the check notes, and keep the intermediate models
python tools/visual_prototype/build.py --check -v --dump /tmp/stellar_visual_build
```

`build.py` exits with a non-zero code when any of these happens:
- a geometry issue;
- a visual consistency failure;
- in `--check` mode, a committed page that differs from the rebuild.

Optional browser smoke test:

```bash
NODE_PATH="$(npm root -g)" node tools/visual_prototype/smoke_test.js [screenshot-dir]

# Life layer: deterministic scenario and soak tests (Node only, no browser)
node tools/visual_prototype/life_test.js
```

It opens the committed page in every camera view, on the key room focuses and in the vocabulary catalogue. It fails on any page error, and it confirms that the default camera is Iso · right.

## What the checks cover

- **Geometry:**
  - every footprint lies inside its room, with no overlaps;
  - anchors are walkable, unique, next to the furniture they serve, and reachable through open doors;
  - two tiles on each side of every door, and the hub side of the R-room doors, are clear;
  - the billiards clearance ring is free;
  - corridors are 3 tiles wide;
  - no character stands directly behind tall furniture as seen from the camera.
- **Visual:**
  - every non-planned Screen Registry display is rendered once, in its registry room, with matching hardware and availability;
  - no display text contains a number;
  - no-producer displays show NOT AVAILABLE;
  - the rendered characters are exactly the Character Registry's ACTIVE characters that have a home anchor, with matching home and department;
  - every furniture asset ID exists in the Asset Registry and is not retired;
  - 21 doors with the registry door types;
  - the corridor repeaters are on the south walls (Corridor Design CD-11), clear of the door openings;
  - the page has no external URL, image or StarNet reference.

## Changing things

- A change to the geometry, layouts, anchors, display placements or camera is a **design change**. It needs owner approval and the matching doc update first. Then edit `geometry.py`, `prototype_data.py` or the template, run `build.py`, and commit the regenerated pages with it.
- After any registry edit, run `build.py --check`. The registries feed the pages, so a registry change can change a page.
