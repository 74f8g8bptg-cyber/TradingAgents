# Stellar Sound System V1

**Status:** implemented in the Visual Prototype.
- **Unchanged:** the visual baseline (frozen at `92db7fc`), the Life System (`eab88c2`), every room, furniture item, door, room function and the dog occupancy rule.
- **Decision VW-8** (Visual World Plan §23, "Sound", previously defaulting to *None*) is now taken by the owner's request: ambient sound plus event cues, **off until the user enables it**.

**Files:**
- `tools/visual_prototype/templates/stellar_sound.js`: the Director (pure) and the Engine (Web Audio). `render.py` inlines it at `/*SOUND*/`.
- The page bridge is the "SOUND LAYER" block in `visual_prototype.html`.
- Tests:
  - `tools/visual_prototype/sound_test.js` (Node);
  - the `sound` case in `smoke_test.js` (browser).

## 1. Reference station sound architecture (studied at `fbddbf99`, read-only)

The reference station has **no in-world audio**:
- no ambience, room tone, doors, footsteps or machinery sounds;
- its generative background score was removed by decision;
- its station world is silent.

What it has is a small, well-built **UI and notification sound system**:

| Part | What it actually does |
|---|---|
| `frontend/js/util.js` `SFX` | A procedural Web Audio engine. **Lazy boot:** nothing touches `AudioContext` until a user gesture, so it is safe headless. **Master chain:** gain → high-shelf cut (−9 dB at 5.4 kHz) → soft limiter → out, plus one shared convolver reverb send built from a synthetic impulse. **Voices:** `voice()` (detuned oscillators → low-pass → attack/decay envelope) and `noise()` (a filtered burst from a shared noise buffer). **Per-cue gates:** a repeat inside a window is dropped and the first always sounds. **Variation:** a small pitch drift (±4 %) on clicks. **Panning:** optional stereo pan. **Cleanup:** every node is self-terminating (`stop` is scheduled) |
| Samples | 16 UI `.wav` files (the Bleeoop "Interface Bleeps" pack), fetched lazily after boot, with the synth as fallback. **Licence:** "free to use… within this application"; not transferable. Our reuse audit (S55) says **do not use** |
| `frontend/js/audio.js` (the "Director") | Listens on the app event bus to **real** events only (task done or failed, work item delivered, tool error, permission prompt…) and plays one cue per event. It **never emits**. It arms the audio context on the first pointer, key or touch event (autoplay rules). Delegated UI click sounds yield to explicit cues |
| Categories, music, spatial | One master volume. No categories, no loops, no music (removed), no attenuation or room audio |

**Inventory:**

| Cue family | Trigger | Loop or one-shot | Variation | Volume | Spatial | Priority | Gameplay link | Asset |
|---|---|---|---|---|---|---|---|---|
| UI clicks, toggles, ticks | DOM clicks and changes | one-shot | pitch drift | per cue × master | pan only | yields to explicit cues | none (UI) | sample, synth fallback |
| Window open / close | Panel actions | one-shot | rate 1.0 / 0.85 | per cue | — | gate 80 ms | none | sample, synth |
| Notifications (chime, ship, alarm, msg) | Real bus events | one-shot | — | per cue | — | gate 300 ms | real events only | sample, synth |
| "Awakening" sequence | Scripted intro | one-shot swells | — | per cue | — | — | intro only | synth |

## 2. Principles adapted for Stellar

1. **A listening director.** Sound reacts only to real events. It never emits into the simulation and never invents triggers.
2. **Gesture-armed, lazily built audio.** Nothing is created before the user presses **Sound**.
3. **One master chain** (gain → high-shelf → limiter) plus **one shared reverb send** from a synthetic impulse.
4. **Procedural voices** (filtered noise for touch, tones for body). **No audio files**, so the page stays self-contained.
5. **Per-cue gates** against event storms, and **small seeded variation** (rate, level, alternate recipe).
6. **Self-terminating nodes** that are released when they end.

Stellar adds what the reference station never had: world ambience, rooms, attenuation, categories, loops and a voice budget. Its randomness is **seeded**, not `Math.random`.

## 3. Stellar audio architecture

```
Life engine ──(bus: on("*"))──► Director (pure, seeded)              Engine (browser, Web Audio)
  events only, no audio          1 events → cue requests              built on the Sound gesture
                                 2 movement hook: footsteps from      fixed set of ambience loops
                                   the Life stride odometer           one-shot voices (budget 14,
                                 3 state watchers (billiards, dog       released on end)
                                   drinking) + explicit ambience      master → shelf → limiter
                                   (fountain drops, structure creak)  buses / groups / reverb send
                                 4 budget: ≤ 6 cues per tick          meter (tests)
                                 5 ambience targets from the
                                   listener, smoothed (0.8 s)
                       tick every 100 ms (never per frame) ─► { plays, beds } ─► engine.apply()
```

- **Life** knows nothing about audio. The page subscribes the Director to the Life bus when sound is on. Life's bus already swallows listener errors.
- **The listener** is the camera centre on the floor, plus the zoom. Hearing radius is 420 / zoom, clamped to 140–1000 units. A station overview trims every one-shot, so it hears the station, not every chair.
- **Spatial:**
  - distance attenuation `(1 − d/R)^1.6`;
  - stereo pan from screen-relative offset;
  - per-room reverb amount (L3 chamber 0.35, hubs 0.25, R3 dry).

## 4. Sound categories

| Bus | Holds | Default | User control |
|---|---|---|---|
| MASTER | everything | 0.8 | yes |
| AMBIENCE | station base, room beds, corridor air, fountain, café murmur, cinema layers | 0.6 | yes |
| EFFECTS → DOORS (0.85) · AGENTS (0.6) · MACHINERY (0.6) · DOG (0.6) | one-shots | 0.8 | yes (the groups are fixed mix trims) |
| MUSIC | only the R1 calm pad | 0.35 | yes |
| UI | the "sound on" confirmation | 0.5 | — |

**Category choices:**
- **ENVIRONMENT** is folded into AMBIENCE: both are continuous beds.
- **DOORS, AGENTS and MACHINERY** are groups under EFFECTS, so one slider governs all one-shots while the mix stays balanced.

The mixer is a single compact row of four sliders. It appears under the toolbar only while sound is on.

## 5. Life → Sound event mapping

Every Life event type is mapped explicitly, either to a resolver or to deliberate silence. A test enforces this.

| Life event | Sound |
|---|---|
| `DOOR_OPEN` / `DOOR_CLOSE` | door cue by type (§7), at the door |
| `AGENT_START_WORK` / `AGENT_STOP_WORK` | `console.wake` / `console.sleep`, **only in technical rooms** (H-CMD, H-LAB, L rooms) |
| `AGENT_SIT` / `AGENT_STAND` | `seat.sit` / `seat.stand`; plus `cafe.cup` when the seat is a café seat |
| `AGENT_START_REST` / `AGENT_END_REST` | `pod.close` / `pod.open` (cosmetic rest pods) |
| `MEDITATION_START` | `zen.bowl` (gate 15 s). The R1 pad follows the MEDITATING state |
| `CINEMA_STATE` | PREPARING → `projector.start`; EMPTY → `projector.stop`. The R2 layers follow the state |
| `CINEMA_START` / `CINEMA_END` | `cinema.lightsdown` / `cinema.lightsup` |
| `DECOMPRESSION_START` | `quiet.seal` (very soft) |
| `DOG_ENTER_R4` / `DOG_ENTER_HHAB` / `DOG_STOP_PLAY` | `dog.tag` (collar jingle) |
| `DOG_START_PLAY` | `dog.toy`; 25 % seeded chance of one soft `dog.woof` (gate 120 s) |
| `AGENT_ENTER_ROOM`, `AGENT_EXIT_ROOM`, `AGENT_START_ACTIVITY`, `AGENT_END_ACTIVITY`, `MEDITATION_END`, `DECOMPRESSION_END` | silent (doors, footsteps and state layers already carry them) |

**Movement hook.** Footsteps are not tied to rendered frames:
- The Director reads each walking actor's **Life stride odometer** every tick and plays one step per 11 units (dog: 6).
- At most 3 steps per tick, nearest first.
- The floor material comes from the room:
  - metal deck in technical rooms and corridors;
  - wood in H-HAB and R1;
  - soft in R2, R3 and R4.

**State watchers** (only while the Life state holds):
- billiard ball clicks while an agent is at the billiards (`GAMES`);
- water laps while the dog is `DOG_DRINKING`.

**Explicit ambience** (station life, not agent activity):
- fountain drops;
- a rare structural creak (45–120 s).

## 6. Room ambience

There are 22 fixed beds (26 loop entries including their 4 drift LFOs). Each is filtered noise bands plus hum partials; some have a slow amplitude drift. Their levels come from the listener.

| Area | Character |
|---|---|
| Station base | Low rumble (90 Hz) + faint 50 Hz mains; always present, trimmed when zoomed out |
| Corridors | Ventilation air (low-pass 900 Hz + airy band) |
| H-CMD | Technical: fan band (1.8 kHz), low room tone, 60/120 Hz electrical hum |
| H-LAB | Scientific: 90/180 Hz equipment hum, a thin high instrument whine, low tone |
| L1 / L2 / L7 / L10 | Desk rooms: light fans and display hum (different pitch per room) |
| L3 | Debate chamber: large, quiet, low room tone (more reverb) |
| L4 | Data core: the strongest server-fan band and 120 Hz hum |
| L6 | Archive: very quiet low tone |
| L9 | Execution bay: low machinery rumble, 45/90 Hz |
| H-HAB | Warmer and quieter: soft low-passed tone, no electrical hum |
| R1 Zen | Very calm room tone; calm pad (MUSIC) only while someone meditates |
| R2 Cinema | Dark room tone; projector-fan layer in PREPARING / ENDING; low screening rumble with slow swells in SCREENING. **No film audio** |
| R3 Decompression | Near-silent 120 Hz tone. **Isolation:** while the listener is in R3, every other bed and every cue from outside is cut to ~10 % (measured about 20 dB quieter than H-HAB). Little leaks out of R3 either |
| R4 Dog Play | Soft rubber-floored room tone |
| L5, L8, R5, R6 | **No bed and no cue.** They are sealed |

**Transitions:** bed levels are smoothed in the Director (0.8 s time constant) and again on the audio clock (`setTargetAtTime`), so walking the camera from H-HAB into R1 crossfades with no cut. In the test, the largest step is under 0.15 per 100 ms.

**Measured output (headless, defaults):**

| Area | RMS |
|---|---|
| L4 | 0.034 |
| H-CMD | 0.032 |
| Corridor | 0.031 |
| H-LAB | 0.028 |
| H-HAB | 0.024 |
| R1 | 0.020 |
| R4 | 0.019 |
| R2 | 0.019 |
| R3 | 0.0024 |

The peak is always below 0.13.

## 7. Door sounds

The door artwork is unchanged; the sound follows the type the station already shows.

| Type | Doors | Sound |
|---|---|---|
| Standard (`DOR-001`) | L-room doors | Servo sweep up, short pneumatic hiss, latch thud. Close: sweep down and a deeper thud |
| Hub (`DOR-009`) | Hub ↔ corridor, H-CMD ↔ H-HAB, R1–R4 | Heavier and slower: lower sweep, longer travel, deeper landing |
| Restricted | L9, L10 | Short two-tone access chirp, then the standard travel; the close ends with a single confirm tick |

There are 3 alternates per cue, plus seeded ±6 % rate and ±10 % level. A close door peaks at about 0.16, against about 0.1 for the ambience peak: noticeable, not dominant.

## 8. Agent sounds

- **Footsteps:** see the movement hook (§5).
- **Seats:** a soft settle (sit) and a chair-release swish (stand).
- **Workstations:** a two-note wake chirp with a couple of key ticks when an agent arrives at a technical workstation, and a falling chirp when it leaves.
- **Restraint:** there are no continuous typing or console sounds. Agents are idle (no engine link), and sound must not imply operational work.

## 9. H-HAB sounds

- **Habitat bed:** warm, quiet.
- **Fountain:** a continuous water bed (two noise bands with slow drift) within about 150 units of the fountain, plus sparse seeded water drops.
- **Café murmur:** only while agents are actually SOCIAL in H-HAB; it scales with how many (full at 4).
- **Café cup:** a clink when someone sits at a café seat.
- **Billiards:** occasional ball clicks while someone plays.
- **Movement:** footsteps on wood.

## 10. R1–R4 sounds

- **R1:** very calm room tone. `MEDITATION_START` → a single soft singing-bowl tone. While anyone is MEDITATING, a quiet three-partial pad (MUSIC bus) fades in; it fades out when they leave.
- **R2:** the four session states (§6) drive the layers. `projector.start` / `projector.stop` and lights down / up mark the session. The screen stays a placeholder; a future content system can feed the MUSIC bus.
- **R3:** isolation (§6) and one very soft `quiet.seal` at `DECOMPRESSION_START`. Nothing else.
- **R4:** room tone and the dog (§11). People playing with the dog make footsteps on the soft floor.

## 11. Dog sounds

| Sound | Trigger |
|---|---|
| Paw clicks | Life stride odometer, every 6 units, while it walks or runs |
| Collar tag jingle | Entering R4 or H-HAB; stopping play |
| Toy squeak | `DOG_START_PLAY` |
| Water laps | While `DOG_DRINKING` |
| One soft woof | 25 % of play starts, at most one per 2 minutes. **No constant barking** |

**Restriction:** any DOG-group cue whose room is not in `D.occupancy["DEC-009"].rooms` (H-HAB, R4) is blocked, counted and tested.

## 12. Browser audio handling

- **Off by default.** The **Sound** button is the user gesture that creates and resumes the `AudioContext`, as browser autoplay rules require; nothing is bypassed.
- **Turning it off** stops every loop and closes the context. Turning it on again rebuilds it.
- **No external files:** no `fetch` and no media elements. The prototype stays one self-contained HTML file. Everything is synthesised at run time from a seeded noise buffer and oscillators.
- The page works unchanged in browsers without Web Audio: sound simply stays off.

## 13. Performance decisions

- **Rate:** the Director ticks every 100 ms of real time, never per rendered frame; it allocates one small object per actor per tick.
- **Fixed loops:** 22 ambience beds plus 4 drift LFOs are created once. Distant beds sit at gain 0. Nothing loops per event.
- **One-shots:**
  - at most 6 per tick;
  - a hard voice budget of 14;
  - every voice releases its nodes when its sources end (tested: 0 voices active 4 s after a 100-voice burst);
  - the event queue is bounded at 400.
- **Measured:** 61 fps headless with sound on (the life-only baseline is about 50–60 fps).

## 14. Current limitations

- Footstep timing follows the 100 ms tick, so cadence is quantised; this is fine at walking speed.
- No HRTF or true 3-D panning: stereo pan plus distance only.
- No door-leaf animation, so the door sound has no matching motion yet.
- Ambience is synthetic: convincing as hum, air and water, but not recorded material.
- The café murmur is filtered noise, not voices, by design (no implied conversation content).

## 15. Future sound work (V2)

- Recorded or designed original samples behind the same cue names (licensed, Stellar-owned), keeping the synth as fallback.
- Operational cues from real telemetry once the engine link exists (`agent.task.*`, risk decisions, executions), on a separate category louder than ambient.
- Door-leaf animation synchronised to the door cue.
- Per-room occlusion through walls, and a better listener model (follow a selected agent).
- A cinema content channel (MUSIC bus).
- Day/night ambience variation.
- Saved mixer settings.
