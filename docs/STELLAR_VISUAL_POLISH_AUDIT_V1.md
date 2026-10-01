# Stellar Visual Polish Audit V1 (global, final)

**Scope:** a polish audit of the approved station, not a rebuild. No room layout, topology, door, anchor, room function, dog rule or reserved-room status changed. No new rooms and no exterior hull.

**Inspected:**
- the whole station in Iso · right, Iso · left, Oblique and Plan;
- every transition: H-HAB ↔ R1–R6, H-HAB ↔ H-CMD, H-CMD ↔ COR-N / COR-S, H-LAB ↔ COR-N / COR-S, and the corridors ↔ L rooms.

## A. Real issues found (fixed)

| # | Issue | Fix |
|---|---|---|
| A1 | The straight door-side wall of each radial room (R1–R6) ran across the curved H-HAB rim. Inside the habitat, the part where the rim bends away showed as a dark low rail on the H-HAB floor in front of the rim bulkhead, most visibly in Oblique next to the ZEN, CINEMA, QUIET and the two sealed doors. It was a leftover of the original straight-quad construction. | The door-side wall is now drawn only where it lies outside the rim's outer face (R + 7, the rim bulkhead depth). The rim already closes the rest. The rest of each room is unchanged: the walls, the R5 / R6 sealed shells, the doors and the floors. |

## B. Already good, do not touch

- **Construction language:** the H-CMD, H-LAB and wing rooms keep the dark industrial bulkheads, physical displays, structured floors and amber / brass details. The habitat keeps warm wood, plants, glass and the park.
- **Recreation rooms:** each keeps its own warmer or softer treatment (R1 wood, R2 dark cinema, R3 padding, R4 dog room). These differences are intentional.
- **Doors:** every opening has exactly one industrial assembly. The rim-end bulkhead caps next to the hub doors are the approved closures from the door pass.
- **Corridors:** COR-N / COR-S keep their bay rhythm, wall repeaters and direction chevrons. The L-room doors integrate with the corridor walls.
- **Reserved rooms:** L5, L8, R5 and R6 are dark sealed shells, as intended.
- **H-HAB:** the park, fountain, café, lounge, games and recovery areas, and the resident dog (allowed in H-HAB and R4 only).
- **Lighting:** the balance is coherent. R2 is dim by design; the technical rooms are cooler, the habitat warmer.
- **Scale and density:** no oversized or undersized objects were found. The open floor areas (hub rings, the habitat circulation, the R3 and R4 centres) are intentional.
- **Rim shelves:** the habitat's open rim shelves read as frames when seen edge-on in Oblique. That is the approved construction.

## C. Optional future ideas (not implemented)

- **Exterior hull:** the station stays a cutaway. An exterior hull would be a separate owner decision with its own pass.
- **R-room wall heights:** the end and side bulkheads of R1–R4 can hide floor near them from some cameras (for example, the far end of R4 in Iso · right). Making them camera-aware like the hub walls would be a separate, opt-in change.
- **Dead code:** the old flat builders that the calibrated vocabulary superseded are still in the template. Removing them is a code clean-up with no visual effect.

## Status

After this audit, the Stellar visual language is **frozen**. Further visual changes happen only on an explicit request.
