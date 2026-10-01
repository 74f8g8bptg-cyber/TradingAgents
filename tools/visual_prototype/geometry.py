"""Geometry pass: rasterise the approved Floor Plan at 12 world units per tile, place the
approved furniture footprints and anchors, and run the geometry consistency checks.

The Floor Plan coordinates, room layouts and anchors below are the approved geometry
(docs/STELLAR_SPATIAL_SCALE_V1.md). Changing them is a design change, not a build change.
"""

import math
from collections import deque

T = 12  # world units per tile (approved)
AGENT_H = 19
SPACING = 0.8

# ---------------- Floor Plan (sketch px = world units) ----------------
HUBS = {"H-LAB": (280, 689, 182), "H-CMD": (975, 692, 224), "H-HAB": (1377, 692, 180)}
RECTS = {
    "L1": (420, 533, 345, 522),
    "L2": (550, 664, 343, 520),
    "L3": (689, 803, 341, 518),
    "L4": (489, 603, 588, 694),
    "L5": (620, 734, 588, 694),
    "L6": (489, 603, 697, 788),
    "L7": (620, 734, 697, 788),
    "L8": (428, 541, 832, 1009),
    "L9": (557, 671, 833, 1010),
    "L10": (690, 805, 836, 1015),
}
CORRS = {"COR-N": (367, 823, 538, 585), "COR-S": (371, 829, 790, 828)}
ROW_OVERRIDE = {"COR-N": (45, 47)}  # normalised to the 3-tile baseline
RESERVED = {"L5", "L8"}
R_ROOMS = {
    "R1": (1144, 1322, 351, 558),
    "R2": (1355, 1487, 333, 521),
    "R3": (1504, 1714, 456, 641),
    "R4": (1545, 1736, 665, 800),
    "R5": (1387, 1557, 835, 1041),
    "R6": (1156, 1335, 815, 1024),
}
# id, x, y, A, B, axis ('h' = door in a horizontal wall), status
DOORS = [
    ("DR-L1", 473, 525, "L1", "COR-N", "h", "open"),
    ("DR-L2", 604, 526, "L2", "COR-N", "h", "open"),
    ("DR-L3", 737, 524, "L3", "COR-N", "h", "open"),
    ("DR-L4", 548, 587, "COR-N", "L4", "h", "open"),
    ("DR-L5", 678, 586, "COR-N", "L5", "h", "reserved"),
    ("DR-L6", 542, 783, "L6", "COR-S", "h", "open"),
    ("DR-L7", 682, 786, "L7", "COR-S", "h", "open"),
    ("DR-L8", 480, 834, "COR-S", "L8", "h", "reserved"),
    ("DR-L9", 612, 834, "COR-S", "L9", "h", "open"),
    ("DR-L10", 741, 833, "COR-S", "L10", "h", "open"),
    ("DR-N-LAB", 388, 563, "H-LAB", "COR-N", "v", "open"),
    ("DR-N-CMD", 801, 566, "COR-N", "H-CMD", "v", "open"),
    ("DR-S-LAB", 383, 809, "H-LAB", "COR-S", "v", "open"),
    ("DR-S-CMD", 817, 805, "COR-S", "H-CMD", "v", "open"),
    ("DR-CMD-HAB", 1194, 692, "H-CMD", "H-HAB", "v", "open"),
]
R_DOORS = {
    "DR-R1": (1274, 538),
    "DR-R2": (1403, 522),
    "DR-R3": (1525, 586),
    "DR-R4": (1558, 718),
    "DR-R5": (1433, 850),
    "DR-R6": (1286, 840),
}


def cen(c):
    return c * T + T / 2


def tiles_in_range(lo, hi):
    return [c for c in range(math.floor(lo / T) - 1, math.ceil(hi / T) + 1) if lo <= cen(c) <= hi]


def build_geometry():
    """Return the geometry model (JSON-ready) and its check results."""
    region = {}
    bbox = {}
    issues = []
    for h, (cx, cy, r) in HUBS.items():
        for col in range(math.floor((cx - r) / T) - 1, math.ceil((cx + r) / T) + 1):
            for row in range(math.floor((cy - r) / T) - 1, math.ceil((cy + r) / T) + 1):
                if math.hypot(cen(col) - cx, cen(row) - cy) <= r:
                    if (col, row) in region:
                        issues.append(f"overlap {h} / {region[(col, row)]} at {(col, row)}")
                    region[(col, row)] = h
    for name, (x0, x1, y0, y1) in list(RECTS.items()) + list(CORRS.items()):
        cols = tiles_in_range(x0, x1)
        rows = (
            list(range(ROW_OVERRIDE[name][0], ROW_OVERRIDE[name][1] + 1))
            if name in ROW_OVERRIDE
            else tiles_in_range(y0, y1)
        )
        bbox[name] = (cols[0], rows[0], cols[-1], rows[-1])
        for col in cols:
            for row in rows:
                if (col, row) in region:
                    if name.startswith("COR") and region[(col, row)].startswith("H-"):
                        continue  # the corridor ends at the hub rim
                    issues.append(f"overlap {name} / {region[(col, row)]} at {(col, row)}")
                region[(col, row)] = name
    for h in HUBS:
        ts = [t for t, n in region.items() if n == h]
        bbox[h] = (
            min(t[0] for t in ts),
            min(t[1] for t in ts),
            max(t[0] for t in ts),
            max(t[1] for t in ts),
        )

    # ---------------- doors: seams or threshold tiles ----------------
    allowed = set()  # frozenset({a, b}) edges that cross a region boundary
    door_info = {}
    for did, x, y, A, B, axis, status in DOORS:
        along = sorted(
            range(math.floor(x / T) - 2, math.floor(x / T) + 3)
            if axis == "h"
            else range(math.floor(y / T) - 2, math.floor(y / T) + 3),
            key=lambda k: abs(cen(k) - (x if axis == "h" else y)),
        )[:2]
        along.sort()
        lanes = []
        for k in along:
            line = [
                ((k, j) if axis == "h" else (j, k))
                for j in range(
                    math.floor((y if axis == "h" else x) / T) - 6,
                    math.floor((y if axis == "h" else x) / T) + 7,
                )
            ]
            best = None
            for i, t in enumerate(line):
                for j2 in range(i + 1, len(line)):
                    u = line[j2]
                    ra, rb = region.get(t), region.get(u)
                    if (
                        {ra, rb} == {A, B}
                        and all(region.get(m) is None for m in line[i + 1 : j2])
                        and (best is None or j2 - i < best[1] - best[0])
                    ):
                        best = (i, j2)
            if best is None:
                issues.append(f"{did}: no {A}/{B} crossing on lane {k}")
                continue
            chain = line[best[0] : best[1] + 1]
            for m in chain[1:-1]:
                region[m] = did
            for a, b in zip(chain, chain[1:], strict=False):
                allowed.add((frozenset((a, b)), did))
            lanes.append(chain)
        door_info[did] = {
            "id": did,
            "x": x,
            "y": y,
            "A": A,
            "B": B,
            "axis": axis,
            "status": status,
            "lanes": lanes,
            "depth": len(lanes[0]) - 2 if lanes else None,
        }
    allowed_open = {e for e, d in allowed if door_info[d]["status"] == "open"}

    # ---------------- furniture and anchors ----------------
    furn, anchors, seams = [], [], set()

    def L(room, u, v):
        c0, r0, _, _ = bbox[room]
        return (c0 + u, r0 + v)

    def rect(room, u, v, w, h):
        return [L(room, u + i, v + j) for j in range(h) for i in range(w)]

    def absrect(c, r, w, h):
        return [(c + i, r + j) for j in range(h) for i in range(w)]

    def F(room, asset, tiles, label, kind="block", tall=False):
        furn.append(
            {
                "room": room,
                "asset": asset,
                "tiles": tiles,
                "label": label,
                "kind": kind,
                "tall": tall,
            }
        )

    def A_(room, name, tile, chr_=None, code=None, serves=None):
        anchors.append(
            {"room": room, "name": name, "tile": tile, "chr": chr_, "code": code, "serves": serves}
        )

    def clock(h, hours, rt):
        cx, cy, _ = HUBS[h]
        th = math.radians(hours * 30)
        return (
            math.floor((cx + rt * T * math.sin(th)) / T),
            math.floor((cy - rt * T * math.cos(th)) / T),
        )

    # L1 Market Specialists (9 x 15, door south)
    F("L1", "CON-009", rect("L1", 3, 1, 3, 1), "CON-009 FX desk")
    F("L1", "CON-009", rect("L1", 0, 6, 1, 2), "CON-009 metals")
    F("L1", "CON-009", rect("L1", 8, 6, 1, 2), "CON-009 indices")
    # PLT-003 desk plants sit on the CON-009 desks (Asset Registry: "on desks", no footprint); drawn by the prototype
    for u in (0, 1, 2, 6, 7, 8):
        seams.add(frozenset((L("L1", u, 3), L("L1", u, 4))))  # WAL-005 glass partition (seam)
    A_("L1", "specialists.desk_fx", L("L1", 4, 2), "CHR-023", "FX", "CON-009 FX desk")
    A_("L1", "specialists.desk_metals", L("L1", 1, 6), "CHR-022", "MET", "CON-009 metals")
    A_("L1", "specialists.desk_indices", L("L1", 7, 6), "CHR-025", "IDX", "CON-009 indices")
    A_("L1", "specialists.visitor", L("L1", 6, 12))
    # L2 Technical Deck (9 x 14, door south)
    for code, u, v in (
        ("T3", 0, 2),
        ("T4", 0, 5),
        ("T5", 0, 8),
        ("T6", 8, 2),
        ("T7", 8, 5),
        ("T8", 8, 10),
    ):
        F("L2", "CON-002", rect("L2", u, v, 1, 2), f"CON-002 {code}")
    F("L2", "TBL-002", rect("L2", 3, 3, 3, 4), "TBL-002 holo chart table")
    F("L2", "CON-010", rect("L2", 0, 11, 1, 1), "CON-010 clock")
    for n, (c, u, v) in {
        "t3": ("CHR-027", 1, 2),
        "t4": ("CHR-028", 1, 5),
        "t5": ("CHR-029", 1, 8),
        "t6": ("CHR-030", 7, 2),
        "t7": ("CHR-031", 7, 5),
        "t8": ("CHR-032", 7, 10),
    }.items():
        A_("L2", f"technical.station_{n}", L("L2", u, v), c, n.upper(), f"CON-002 {n.upper()}")
    A_("L2", "technical.session_clock", L("L2", 1, 11), "CHR-026", "T2", "CON-010 clock")
    A_("L2", "technical.table_1", L("L2", 2, 4), serves="TBL-002 holo chart table")
    A_("L2", "technical.table_2", L("L2", 6, 5), serves="TBL-002 holo chart table")
    # L3 Debate Chamber (10 x 15, door south)
    F("L3", "CON-023", rect("L3", 3, 2, 3, 1), "CON-023 review desk")
    F("L3", "SEA-003", [L("L3", 4, 1)], "SEA-003", kind="seat")
    F("L3", "TBL-007", rect("L3", 3, 5, 3, 3), "TBL-007 evidence stage")
    for lab, u, v in (
        ("bull", 2, 6),
        ("bear", 6, 6),
        ("risk_1", 2, 10),
        ("risk_2", 4, 10),
        ("risk_3", 6, 10),
    ):
        F("L3", "CON-011", [L("L3", u, v)], f"CON-011 {lab}")
    A_("L3", "debate.judge_seat", L("L3", 4, 1), serves="CON-023 review desk")
    A_("L3", "debate.podium_bull", L("L3", 1, 6), "CHR-006", "U1", "CON-011 bull")
    A_("L3", "debate.podium_bear", L("L3", 7, 6), "CHR-007", "U2", "CON-011 bear")
    for i, (c, u) in enumerate((("CHR-008", 2), ("CHR-009", 4), ("CHR-010", 6)), 1):
        A_("L3", f"debate.podium_risk_{i}", L("L3", u, 11), c, f"U{4 + i}", f"CON-011 risk_{i}")
    A_("L3", "debate.visitor", L("L3", 7, 13))
    # L4 Data Core (9 x 9, door north)
    F("L4", "EQP-001", rect("L4", 4, 4, 1, 1), "EQP-001 + SCR-006 column", tall=True)
    F("L4", "CON-018", rect("L4", 4, 6, 2, 1), "CON-018 validator")
    F("L4", "SRV-001", rect("L4", 8, 2, 1, 2), "SRV-001 rack", tall=True)
    F("L4", "SRV-002", rect("L4", 8, 5, 1, 2), "SRV-002 rack", tall=True)
    F("L4", "CON-027", rect("L4", 0, 8, 2, 1), "CON-027 recon.")
    A_("L4", "datacore.reactor_console", L("L4", 4, 7), "CHR-035", "T1", "CON-018 validator")
    A_("L4", "datacore.rack_check", L("L4", 7, 6), serves="SRV-002 rack")
    A_("L4", "datacore.visitor", L("L4", 2, 1))
    # L6 Memory Archive (9 x 8, door south)
    F("L6", "CON-019", rect("L6", 0, 2, 1, 2), "CON-019 terminal")
    F("L6", "STO-004", rect("L6", 8, 2, 1, 3), "STO-004 record shelf", tall=True)
    F("L6", "TBL-005", rect("L6", 3, 4, 2, 1), "TBL-005 table")
    A_("L6", "archive.terminal", L("L6", 1, 2), "CHR-033", "L1", "CON-019 terminal")
    A_("L6", "archive.shelf", L("L6", 7, 3), serves="STO-004 record shelf")
    A_("L6", "archive.table_1", L("L6", 4, 3), serves="TBL-005 table")
    # L7 Performance Lab (9 x 8, door south)
    F("L7", "CON-020", rect("L7", 0, 2, 1, 2), "CON-020 terminal")
    F("L7", "TBL-005", rect("L7", 4, 4, 2, 1), "TBL-005 table")
    A_("L7", "perflab.terminal", L("L7", 1, 2), "CHR-034", "L2", "CON-020 terminal")
    A_("L7", "perflab.table_1", L("L7", 4, 3), serves="TBL-005 table")
    # L9 Execution Bay (10 x 15, door north)
    F("L9", "CON-016", rect("L9", 0, 2, 1, 2), "CON-016 pre-flight")
    F("L9", "CON-017", rect("L9", 3, 8, 1, 2), "CON-017 execution")
    F("L9", "EQP-002", rect("L9", 0, 8, 1, 2), "EQP-002 Dispatch Tube", tall=True)
    F("L9", "EQP-003", rect("L9", 3, 14, 3, 1), "EQP-003 docking board")
    F("L9", "FLR-008", rect("L9", 0, 6, 10, 9), "FLR-008 launch deck", kind="floor")
    A_("L9", "execbay.preflight", L("L9", 1, 2), "CHR-038", "P4", "CON-016 pre-flight")
    A_("L9", "execbay.launch", L("L9", 4, 8), "CHR-039", "E1", "CON-017 execution")
    A_("L9", "execbay.entry", L("L9", 3, 1))
    # L10 Risk Control (10 x 15, door north)
    F("L10", "CON-012", rect("L10", 0, 2, 3, 1), "CON-012 intake")
    F("L10", "CON-001", rect("L10", 0, 4, 1, 2), "CON-001 contradiction desk")
    F("L10", "CON-029", rect("L10", 9, 1, 1, 2), "CON-029 outbox")
    F("L10", "CON-015", rect("L10", 0, 9, 1, 1), "CON-015 breaker panel")
    F("L10", "CON-014", rect("L10", 9, 9, 1, 2), "CON-014 sizing")
    F("L10", "CON-013", rect("L10", 3, 14, 3, 1), "CON-013 rule checklist")
    F("L10", "(marking)", rect("L10", 0, 7, 10, 1), "risk.core line (marking)", kind="floor")
    A_("L10", "risk.intake_drop", L("L10", 1, 1), serves="CON-012 intake")
    A_("L10", "risk.intake_desk", L("L10", 1, 4), "CHR-036", "P2", "CON-001 contradiction desk")
    A_("L10", "risk.entry_wait", L("L10", 3, 1))
    A_("L10", "risk.outbox_pickup", L("L10", 8, 1), serves="CON-029 outbox")
    A_("L10", "risk.breaker_panel", L("L10", 1, 9), serves="CON-015 breaker panel")
    A_("L10", "risk.sizing_console", L("L10", 8, 9), serves="CON-014 sizing")
    A_("L10", "risk.rule_console", L("L10", 4, 13), "CHR-037", "P3", "CON-013 rule checklist")
    # H-CMD (circle, 37 tiles across)
    cc, cr = math.floor(975 / T), math.floor(692 / T)
    F(
        "H-CMD",
        "FLR-002",
        [
            (c, r)
            for c in range(cc - 6, cc + 7)
            for r in range(cr - 6, cr + 7)
            if math.hypot(c - cc, r - cr) <= 5.6
        ],
        "FLR-002 dais",
        kind="floor",
    )
    F(
        "H-CMD",
        "TBL-001",
        [
            (c, r)
            for c in range(cc - 3, cc + 4)
            for r in range(cr - 3, cr + 4)
            if math.hypot(c - cc, r - cr) <= 2.3
        ],
        "TBL-001 circular table",
    )
    F("H-CMD", "SEA-001", [(cc, cr - 3)], "SEA-001 command chair", kind="seat")
    F("H-CMD", "CON-003", absrect(cc - 9, cr - 13, 3, 1), "CON-003 ops")
    F("H-CMD", "CON-004", absrect(cc + 7, cr - 13, 3, 1), "CON-004 trader")
    F("H-CMD", "CON-005", absrect(cc - 9, cr + 13, 3, 1), "CON-005 proposal")
    F("H-CMD", "CON-022", absrect(cc - 1, cr + 15, 3, 1), "CON-022 budget")
    F("H-CMD", "SEA-005", absrect(cc + 10, cr + 10, 2, 1), "SEA-005 bench", kind="seat")
    A_("H-CMD", "command.chair", (cc, cr - 3), "CHR-001", "U8", "TBL-001 circular table")
    A_("H-CMD", "command.table_head", (cc, cr + 3), "CHR-002", "U3", "TBL-001 circular table")
    for n, (dc, dr) in {"n1": (-2, -2), "n2": (2, -2), "s1": (-2, 2), "s2": (2, 2)}.items():
        A_("H-CMD", f"command.table_{n}", (cc + dc, cr + dr), serves="TBL-001 circular table")
    A_("H-CMD", "command.console_ops", (cc - 8, cr - 12), "CHR-003", "O1", "CON-003 ops")
    A_("H-CMD", "command.console_trader", (cc + 8, cr - 12), "CHR-004", "U4", "CON-004 trader")
    A_("H-CMD", "command.console_proposal", (cc - 8, cr + 12), "CHR-005", "P1", "CON-005 proposal")
    A_("H-CMD", "command.console_budget", (cc, cr + 14), "CHR-042", "QM", "CON-022 budget")
    A_("H-CMD", "command.bench_1", (cc + 10, cr + 10), serves="SEA-005 bench")
    A_("H-CMD", "command.bench_2", (cc + 11, cr + 10), serves="SEA-005 bench")
    A_("H-CMD", "command.visitor_1", (cc + 9, cr + 8))
    A_("H-CMD", "command.visitor_2", (cc + 12, cr + 8))
    # ---- H-CMD calibration room V1 (StarNet visual adaptation; docs/STELLAR_HCMD_CALIBRATION_V1.md)
    # Approved H-CMD items above are unchanged. Additions: seats at the consoles and the table
    # (SEA-002), a perimeter bank of console modules on the rim ring (CON-030, dark glass, no data,
    # no anchors), wall lockers flanking the doors (STO-001) and floor markings (FLR-009, FLR-010).
    for an in (
        "command.console_ops",
        "command.console_trader",
        "command.console_proposal",
        "command.console_budget",
        "command.table_head",
        "command.table_n1",
        "command.table_n2",
        "command.table_s1",
        "command.table_s2",
    ):
        t = next(a["tile"] for a in anchors if a["name"] == an)
        F("H-CMD", "SEA-002", [t], f"SEA-002 chair {an.split('.')[1]}", kind="seat")
    hcx, hcy, hcr = HUBS["H-CMD"]
    door_mids = []
    for did in ("DR-N-CMD", "DR-S-CMD", "DR-CMD-HAB"):
        lane_tiles = [t for ch in door_info[did]["lanes"] for t in ch]
        door_mids.append(
            (
                sum(cen(t[0]) for t in lane_tiles) / len(lane_tiles),
                sum(cen(t[1]) for t in lane_tiles) / len(lane_tiles),
            )
        )
    ring = []
    for t, n in region.items():
        if n != "H-CMD":
            continue
        if all(
            region.get((t[0] + dc, t[1] + dr)) == "H-CMD"
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            continue
        if min(math.hypot(cen(t[0]) - x, cen(t[1]) - y) for x, y in door_mids) < 4.5 * T:
            continue
        ring.append(t)
    ring.sort(key=lambda t: math.atan2(cen(t[1]) - hcy, cen(t[0]) - hcx))
    runs, cur = [], []
    for t in ring:
        if cur and max(abs(t[0] - cur[-1][0]), abs(t[1] - cur[-1][1])) > 1:
            runs.append(cur)
            cur = []
        cur.append(t)
    if cur:
        if runs and max(abs(cur[-1][0] - runs[0][0][0]), abs(cur[-1][1] - runs[0][0][1])) <= 1:
            runs[0] = cur + runs[0]  # the run that wraps past -pi joins the first run
        else:
            runs.append(cur)
    # calibration V5: the perimeter is composed with a rhythm instead of identical 3-tile chunks: bank modules of
    # 3 / 2 / 1 tiles (wide / double / single), a tall relay rack between groups, and an occasional gap where the
    # wall system shows through. The cycle restarts at every run so each run reads as a designed group
    # calibration V5.1: the cycle also carries ring-mounted equipment bays ("B", STO-005, 2 tiles) and
    # service cabinets ("S", STO-006), so the perimeter alternates consoles, racks, bays, storage and gaps
    rhythm = (3, 2, "R", "B", 3, "G", 1, "S", 2, "R")
    ring_gaps = []
    for run in runs:
        ends = (run[0], run[-1])
        body = run[1:-1] if len(run) > 4 else run
        for e in ends if len(run) > 4 else ():
            F("H-CMD", "STO-001", [e], "STO-001 wall locker", tall=True)
        i = k = 0
        while i < len(body):
            step = rhythm[k % len(rhythm)]
            k += 1
            if step == "G":
                ring_gaps.append(body[i])
                i += 1
            elif step == "S":
                F("H-CMD", "STO-006", [body[i]], f"STO-006 perimeter service cabinet {len(furn)}")
                i += 1
            elif step == "B" and i + 1 < len(body):
                F(
                    "H-CMD",
                    "STO-005",
                    body[i : i + 2],
                    f"STO-005 perimeter equipment bay {len(furn)}",
                )
                i += 2
            elif step == "B":
                i += 1
            elif step == "R":
                F("H-CMD", "SRV-005", [body[i]], f"SRV-005 perimeter rack {len(furn)}", tall=True)
                i += 1
            else:
                F("H-CMD", "CON-030", body[i : i + step], f"CON-030 perimeter bank {len(furn)}")
                i += step
    # ---- calibration V2: secondary consoles, operations clusters, bank seating, deck markings
    used = {t for f in furn for t in f["tiles"]} | {a["tile"] for a in anchors}

    def free(tiles):
        return all(
            region.get(t) == "H-CMD"
            and t not in used
            and not 6.6 <= math.hypot(t[0] - cc, t[1] - cr) <= 9.4
            for t in tiles
        )

    def place(asset, tiles, label, kind="block", tall=False):
        if not free(tiles):
            issues.append(f"H-CMD calibration: {label} {tiles} not placeable")
            return
        F("H-CMD", asset, tiles, label, kind=kind, tall=tall)
        used.update(tiles)

    for i, (c, r, face) in enumerate(
        ((cc - 4, cr - 14, 1), (cc + 3, cr - 14, 1), (cc - 5, cr + 14, -1), (cc + 4, cr + 14, -1))
    ):
        place("CON-031", absrect(c, r, 2, 1), f"CON-031 secondary console {i + 1}")
        for dc in (0, 1):
            place("SEA-002", [(c + dc, r + face)], f"SEA-002 chair secondary {i + 1}", kind="seat")
    for i, t in enumerate(
        (
            (cc - 15, cr - 3),
            (cc - 15, cr - 1),
            (cc - 15, cr + 1),
            (cc - 15, cr + 3),
            (cc + 14, cr - 7),
            (cc + 14, cr - 5),
        )
    ):
        place("SRV-005", [t], f"SRV-005 relay stack {i + 1}", tall=True)
    for i, (c, r) in enumerate(((cc - 14, cr + 6), (cc + 12, cr + 4), (cc + 11, cr - 11))):
        place("STO-005", absrect(c, r, 2, 1), f"STO-005 equipment bay {i + 1}")
    banks = [f for f in furn if f["asset"] == "CON-030"]
    for i, f in enumerate(banks):
        if i % 2:
            continue
        mid = f["tiles"][len(f["tiles"]) // 2]
        dx, dy = cc - mid[0], cr - mid[1]
        step = (round(dx / max(abs(dx), abs(dy))), round(dy / max(abs(dx), abs(dy))))
        seat = (mid[0] + step[0], mid[1] + step[1])
        if (
            free([seat])
            and min(math.hypot(seat[0] - a["tile"][0], seat[1] - a["tile"][1]) for a in anchors)
            >= 2
        ):
            F("H-CMD", "SEA-002", [seat], f"SEA-002 chair bank {i}", kind="seat")
            used.add(seat)
    # ---- calibration V3: layered second row (planters PLT-001 at the rim, STO-006 service cabinets), more deck detail
    cand = []
    for i, f in enumerate(banks):
        if not i % 2:
            continue
        mid = f["tiles"][len(f["tiles"]) // 2]
        dx, dy = cc - mid[0], cr - mid[1]
        step = (round(dx / max(abs(dx), abs(dy))), round(dy / max(abs(dx), abs(dy))))
        t = (mid[0] + step[0], mid[1] + step[1])
        if (
            free([t])
            and min(math.hypot(t[0] - a["tile"][0], t[1] - a["tile"][1]) for a in anchors) >= 2
        ):
            cand.append((math.atan2(t[0] - cc, -(t[1] - cr)) % (2 * math.pi), t))
    planters = set()
    for clock in (11.2, 12.8 % 12, 5.2, 6.8):
        if cand:
            ang = clock * math.pi / 6
            best = min(
                (c for c in cand if c[1] not in planters),
                key=lambda c: abs(math.atan2(math.sin(c[0] - ang), math.cos(c[0] - ang))),
            )
            planters.add(best[1])
    for i, (_, t) in enumerate(cand):
        if t in planters:
            place(
                "PLT-001",
                [t],
                f"PLT-001 planter {len([p for p in furn if p['asset'] == 'PLT-001']) + 1}",
            )
        else:
            place("STO-006", [t], f"STO-006 service cabinet {i + 1}")
    # ---- calibration V3b: east operations bay (the reference station's paired desks + rack pair on the
    # side wall), so the outer deck reads as layered equipment on every side; the centre stays clear
    for i, (c, r, face) in enumerate(((cc + 11, cr - 5, 1), (cc + 11, cr + 6, -1)), 5):
        place("CON-031", absrect(c, r, 2, 1), f"CON-031 secondary console {i}")
        for dc in (0, 1):
            place("SEA-002", [(c + dc, r + face)], f"SEA-002 chair secondary {i}", kind="seat")
    for i, t in enumerate(((cc + 15, cr + 5), (cc + 15, cr + 7)), 7):
        place("SRV-005", [t], f"SRV-005 relay stack {i}", tall=True)
    # ---- calibration V5.1: whole-room composition. Equipment GROUPS instead of isolated objects: rack pairs
    # beside the role workstations, a south command group around the budget console, a west engineering island
    # between the two door approaches, a north-east rack / bay / rack line and a south operations arc; every group
    # cabled to the perimeter by a conduit. Door approaches keep a 3-tile corridor to the walkway ring.
    corridor = set()
    for x, y in door_mids:
        L = math.hypot(cen(cc) - x, cen(cr) - y)
        for k in range(0, int(L / T * 2) + 1):
            px_ = x + (cen(cc) - x) * k / (L / T * 2)
            py_ = y + (cen(cr) - y) * k / (L / T * 2)
            if math.hypot(px_ - cen(cc), py_ - cen(cr)) < 9.4 * T:
                break
            for dc in range(-2, 3):
                for dr in range(-2, 3):
                    t = (int(px_ // T) + dc, int(py_ // T) + dr)
                    if math.hypot(cen(t[0]) - px_, cen(t[1]) - py_) <= 1.6 * T:
                        corridor.add(t)

    def all_reachable(extra):
        blocked_ = {t for f in furn if f["kind"] == "block" for t in f["tiles"]} | set(extra)
        open_ = {t for t, n in region.items() if n == "H-CMD" and t not in blocked_}
        start = next(iter(open_))
        seen, todo = {start}, [start]
        while todo:
            c0, r0 = todo.pop()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                u = (c0 + dc, r0 + dr)
                if u in open_ and u not in seen:
                    seen.add(u)
                    todo.append(u)
        return len(seen) == len(open_)

    def try_place(asset, tiles, label, kind="block", tall=False):
        if not free(tiles) or any(t in corridor for t in tiles):
            return False
        if kind == "block" and not all_reachable(tiles):
            return False
        F("H-CMD", asset, tiles, label, kind=kind, tall=tall)
        used.update(tiles)
        return True

    groups = []  # (tile, label) group centres, cabled to the perimeter below
    for sg in (-1, 1):  # rack pairs on the outer side of the north and south role workstations
        for base in (cr - 13, cr + 13):
            out = 1 if base > cr else -1
            for row in (base, base + out, base - out):
                pair = [(cc + sg * 11, row), (cc + sg * 12, row)]
                if free(pair) and not any(t in corridor for t in pair) and all_reachable(pair):
                    for t in pair:
                        F("H-CMD", "SRV-005", [t], f"SRV-005 group rack {len(furn)}", tall=True)
                        used.add(t)
                    groups.append(pair[1])
                    break
    for sg in (
        -1,
        1,
    ):  # south command group: secondary desk | service cabinet | budget console | ...
        try_place("STO-006", [(cc + sg * 3, cr + 15)], f"STO-006 command group cabinet {len(furn)}")
    west = [
        ("CON-031", absrect(cc - 13, cr - 3, 1, 2), [(cc - 12, cr - 3), (cc - 12, cr - 2)]),
        ("STO-005", absrect(cc - 13, cr - 1, 1, 2), []),
        ("CON-031", absrect(cc - 13, cr + 1, 1, 2), [(cc - 12, cr + 1), (cc - 12, cr + 2)]),
    ]
    for i, (asset, tiles, chairs) in enumerate(west, 9):
        if try_place(asset, tiles, f"{asset} west engineering {i}"):
            for t in chairs:
                try_place("SEA-002", [t], f"SEA-002 chair west engineering {i}", kind="seat")
    groups.append((cc - 13, cr))
    ne = [
        ("SRV-005", [(cc + 7, cr - 9)]),
        ("STO-005", absrect(cc + 8, cr - 9, 2, 1)),
        ("SRV-005", [(cc + 10, cr - 9)]),
    ]
    for asset, tiles in ne:
        try_place(asset, tiles, f"{asset} north-east line {len(furn)}", tall=asset == "SRV-005")
    groups.append((cc + 10, cr - 9))
    for i, (c, face) in enumerate(((cc - 6, -1), (cc + 5, -1)), 11):  # south operations arc
        if try_place("CON-031", absrect(c, cr + 10, 2, 1), f"CON-031 south arc {i}"):
            for dc in (0, 1):
                try_place(
                    "SEA-002",
                    [(c + dc, cr + 10 + face)],
                    f"SEA-002 chair south arc {i}",
                    kind="seat",
                )
            groups.append((c, cr + 10))
    more_vents = [
        (cc + dc, cr + dr)
        for dc, dr in (
            (-11, -4),
            (11, -4),
            (-11, 5),
            (11, 5),
            (-5, -11),
            (5, -11),
            (-6, 10),
            (6, 10),
        )
    ]
    F(
        "H-CMD",
        "FLR-010",
        [t for t in more_vents if free([t])],
        "FLR-010 floor vents (outer deck)",
        kind="floor",
    )
    aprons = []
    for lab in ("CON-003 ops", "CON-004 trader", "CON-005 proposal", "CON-022 budget"):
        ts = next(f["tiles"] for f in furn if f["label"] == lab)
        c0, r0 = min(t[0] for t in ts), min(t[1] for t in ts)
        aprons += [
            (c, r) for c in range(c0 - 1, c0 + 4) for r in range(r0 - 1, r0 + 2) if (c, r) not in ts
        ]
    F("H-CMD", "FLR-009", aprons, "FLR-009 hazard border (console aprons)", kind="floor")
    conduits = [(cc, r) for r in range(cr - 13, cr - 3)]  # from the back bank to the dais
    for lab in ("CON-003 ops", "CON-004 trader", "CON-005 proposal", "CON-022 budget"):
        ts = next(f["tiles"] for f in furn if f["label"] == lab)
        mc = sum(t[0] for t in ts) / len(ts)
        mr = sum(t[1] for t in ts) / len(ts)
        L = math.hypot(mc - cc, mr - cr)
        for k in range(1, 8):  # outward to the rim bank
            t = (round(mc + (mc - cc) / L * k), round(mr + (mr - cr) / L * k))
            if region.get(t) != "H-CMD" or any(
                t in f["tiles"] for f in furn if f["asset"] in ("CON-030", "STO-001")
            ):
                break
            conduits.append(t)
    blocking = {t for f in furn if f["kind"] != "floor" for t in f["tiles"]}
    for t0 in (
        groups + ring_gaps
    ):  # V5.1: every equipment group (and each perimeter gap) cabled outward
        L = math.hypot(t0[0] - cc, t0[1] - cr) or 1
        for k in range(1, 9):
            t = (round(t0[0] + (t0[0] - cc) / L * k), round(t0[1] + (t0[1] - cr) / L * k))
            if t0 in ring_gaps:
                t = t0
            if region.get(t) != "H-CMD" or t in blocking or t in corridor:
                break
            if t not in conduits:
                conduits.append(t)
            if t0 in ring_gaps:
                break
    F("H-CMD", "FLR-011", conduits, "FLR-011 cable conduit", kind="floor")
    # calibration V5.3: large framed floor grates in symmetric pairs (the reference bridge's paired deck grates),
    # 2 x 2 tiles of FLR-010, on free outer-deck tiles only (walk-over; never on markings, conduits or approaches)
    marked = {t for f in furn if f["room"] == "H-CMD" for t in f["tiles"]}
    big = []

    def sq_ok(c0, r0):
        sq = [(c0 + i, r0 + j) for i in (0, 1) for j in (0, 1)]
        ok = all(
            region.get(t) == "H-CMD" and t not in marked and t not in used and t not in corridor
            for t in sq
        ) and all(9.8 < math.hypot(t[0] + 0.5 - cc, t[1] + 0.5 - cr) < 15 for t in sq)
        return sq if ok else None

    picked = []  # mirror pairs across the north-south axis, spread around the room
    for dr in range(-15, 15):
        for dc in range(-16, -1):
            a, b = sq_ok(cc + dc, cr + dr), sq_ok(cc - dc - 1, cr + dr)
            if not (a and b):
                continue
            ang = math.atan2(dr + 1, dc + 1)
            if all(abs(math.atan2(math.sin(ang - q), math.cos(ang - q))) > 0.75 for q in picked):
                picked.append(ang)
                big += a + b
                marked.update(a + b)
    if big:
        F("H-CMD", "FLR-010", big, "FLR-010 large floor grates (paired)", kind="floor")
    dais = [
        (c, r)
        for c in range(cc - 7, cc + 8)
        for r in range(cr - 7, cr + 8)
        if 5.7 <= math.hypot(c - cc, r - cr) <= 6.4
    ]
    F("H-CMD", "FLR-009", dais, "FLR-009 hazard border (dais)", kind="floor")
    vents = [(cc + dc, cr + dr) for dc, dr in ((0, -8), (8, 0), (0, 8), (-8, 0))]
    F("H-CMD", "FLR-010", vents, "FLR-010 floor vents", kind="floor")
    # H-LAB (circle, 30 tiles across)
    lc, lr = math.floor(280 / T), math.floor(689 / T)
    F("H-LAB", "CON-008", absrect(lc - 1, lr - 12, 3, 1), "CON-008 driver board")
    for i, (c, r) in enumerate(
        (
            (lc - 12, lr - 5),
            (lc - 12, lr - 2),
            (lc - 12, lr + 1),
            (lc - 8, lr - 5),
            (lc - 8, lr - 2),
            (lc - 8, lr + 1),
        ),
        1,
    ):
        F("H-LAB", "CON-006", absrect(c, r, 1, 2), f"CON-006 R{i}")
        A_("H-LAB", f"lab.feed_r{i}", (c + 1, r), f"CHR-0{11 + i}", f"R{i}", f"CON-006 R{i}")
    F("H-LAB", "EQP-005", absrect(lc + 1, lr - 1, 3, 3), "EQP-005 dome ring", tall=False)
    F(
        "H-LAB", "SCR-006", [(lc + 4, lr)], "SCR-006 projector column"
    )  # DSP-LAB-05; added in the visual pass (missing from geometry V1)
    F("H-LAB", "CON-007", absrect(lc - 2, lr + 11, 4, 1), "CON-007 bench")
    for i in range(4):
        A_(
            "H-LAB",
            f"lab.bench_{i + 1}",
            (lc - 2 + i, lr + 10),
            f"CHR-0{18 + i}",
            f"V{i + 1}",
            "CON-007 bench",
        )
    A_("H-LAB", "lab.driver_board", (lc, lr - 11), "CHR-011", "M1", "CON-008 driver board")
    A_("H-LAB", "lab.handoff_n", (lc + 5, lr - 9))
    A_("H-LAB", "lab.visitor_1", (lc + 4, lr + 5))
    A_("H-LAB", "lab.visitor_2", (lc + 5, lr + 5))
    # ---- H-LAB calibration (Stellar Visual Vocabulary; docs/STELLAR_HLAB_CALIBRATION_V1.md). Approved H-LAB items
    # above are unchanged. One composition pass: a lab perimeter rhythm, and equipment GROUPS around each function zone
    # (feeds west, macro north, validation south, core centre). Kept clear: the east walkway between the two doors, the
    # door approaches and the FUTURE_RESEARCH experiment-bench zone (south-west, not rendered). No anchors are added
    lx, ly, _lr = HUBS["H-LAB"]
    lcc, lcr = int(lx // T), int(ly // T)
    lab_used = {t for f in furn for t in f["tiles"]} | {a["tile"] for a in anchors}
    lab_doors = []
    for did in ("DR-N-LAB", "DR-S-LAB"):
        lt = [t for ch in door_info[did]["lanes"] for t in ch]
        lab_doors.append(
            (sum(cen(t[0]) for t in lt) / len(lt), sum(cen(t[1]) for t in lt) / len(lt))
        )
    door_ang = sorted(math.atan2(y - ly, x - lx) for x, y in lab_doors)
    lab_keep = set()
    for t, n in region.items():
        if n != "H-LAB":
            continue
        x, y = cen(t[0]), cen(t[1])
        ang = math.atan2(y - ly, x - lx)
        d = math.hypot(x - lx, y - ly)
        if door_ang[0] - 0.2 <= ang <= door_ang[1] + 0.2 and d > 9 * T:
            lab_keep.add(t)  # lab.walkway (east arc between the doors)
        if x < lx - 2 * T and y > ly + 4 * T and d < 13.2 * T and x > lx - 11 * T:
            lab_keep.add(t)  # lab.experiment_bench (FUTURE_RESEARCH): left clear
        if min(math.hypot(x - dx, y - dy) for dx, dy in lab_doors) < 4.5 * T:
            lab_keep.add(t)  # door approaches

    def lab_reachable(extra):
        blocked_ = {t for f in furn if f["kind"] == "block" for t in f["tiles"]} | set(extra)
        open_ = {t for t, n in region.items() if n == "H-LAB" and t not in blocked_}
        start = next(iter(open_))
        seen, todo = {start}, [start]
        while todo:
            c0, r0 = todo.pop()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                u = (c0 + dc, r0 + dr)
                if u in open_ and u not in seen:
                    seen.add(u)
                    todo.append(u)
        return len(seen) == len(open_)

    def lab_place(asset, tiles, label, kind="block", tall=False):
        if any(region.get(t) != "H-LAB" or t in lab_used or t in lab_keep for t in tiles):
            return False
        if kind == "block" and not lab_reachable(tiles):
            return False
        F("H-LAB", asset, tiles, label, kind=kind, tall=tall)
        lab_used.update(tiles)
        return True

    # perimeter rhythm: wide / double / single console modules, racks, equipment bays, service cabinets, gaps; lockers
    # close each run
    lring = []
    for t, n in region.items():
        if n != "H-LAB" or t in lab_keep:
            continue
        if all(
            region.get((t[0] + dc, t[1] + dr)) == "H-LAB"
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            continue
        lring.append(t)
    lring.sort(key=lambda t: math.atan2(cen(t[1]) - ly, cen(t[0]) - lx))
    lruns, cur = [], []
    for t in lring:
        if cur and max(abs(t[0] - cur[-1][0]), abs(t[1] - cur[-1][1])) > 1:
            lruns.append(cur)
            cur = []
        cur.append(t)
    if cur:
        if lruns and max(abs(cur[-1][0] - lruns[0][0][0]), abs(cur[-1][1] - lruns[0][0][1])) <= 1:
            lruns[0] = cur + lruns[0]
        else:
            lruns.append(cur)
    lab_rhythm = (2, "R", 3, "B", 1, "G", 2, "S", 3, "R", "B")
    lab_gaps = []
    for run in lruns:
        body = run[1:-1] if len(run) > 4 else run
        for e in (run[0], run[-1]) if len(run) > 4 else ():
            lab_place("STO-001", [e], "STO-001 lab perimeter locker", tall=True)
        i = k = 0
        while i < len(body):
            step = lab_rhythm[k % len(lab_rhythm)]
            k += 1
            if step == "G":
                lab_gaps.append(body[i])
                i += 1
            elif step == "R":
                lab_place(
                    "SRV-005", [body[i]], f"SRV-005 lab perimeter rack {len(furn)}", tall=True
                )
                i += 1
            elif step == "S":
                lab_place("STO-006", [body[i]], f"STO-006 lab perimeter cabinet {len(furn)}")
                i += 1
            elif step == "B":
                if i + 1 < len(body) and lab_place(
                    "STO-005", body[i : i + 2], f"STO-005 lab perimeter bay {len(furn)}"
                ):
                    i += 2
                else:
                    i += 1
            else:
                seg = body[i : i + step]
                if not lab_place("CON-030", seg, f"CON-030 lab perimeter bank {len(furn)}"):
                    for t in seg:
                        lab_place("CON-030", [t], f"CON-030 lab perimeter bank {len(furn)}")
                i += step
    # seats at the lab work anchors (feeds, validation bench, driver board)
    for a in [a for a in anchors if a["room"] == "H-LAB" and a.get("serves")]:
        F("H-LAB", "SEA-002", [a["tile"]], f"SEA-002 chair {a['name'].split('.')[1]}", kind="seat")
    lab_groups = []
    fx = sorted({t[0] for f in furn if f["asset"] == "CON-006" for t in f["tiles"]})
    for c in fx:  # feeds: screen-cluster columns in the gaps of each console column, rack pairs capping the ends
        rows = sorted(
            t[1] for f in furn if f["asset"] == "CON-006" for t in f["tiles"] if t[0] == c
        )
        for r in range(rows[0], rows[-1] + 1):
            if r not in rows:
                lab_place("SCR-013", [(c, r)], f"SCR-013 feed screen cluster {len(furn)}")
        for r in (rows[0] - 1, rows[-1] + 1):
            lab_place("SRV-005", [(c, r)], f"SRV-005 feed rack {len(furn)}", tall=True)
        lab_groups.append((c, rows[0] - 1))
    dbx = sorted(t[0] for f in furn if f["asset"] == "CON-008" for t in f["tiles"])
    dby = next(t[1] for f in furn if f["asset"] == "CON-008" for t in f["tiles"])
    for c in (dbx[0] - 1, dbx[-1] + 1):  # macro: screen clusters flanking the driver board
        lab_place("SCR-013", [(c, dby)], f"SCR-013 macro screen cluster {len(furn)}")
    if lab_place(
        "CON-031", [(dbx[0] - 5, dby + 2), (dbx[0] - 4, dby + 2)], "CON-031 macro desk west"
    ):
        for dc in (0, 1):
            lab_place(
                "SEA-002", [(dbx[0] - 5 + dc, dby + 3)], "SEA-002 chair macro desk", kind="seat"
            )
    for t in ((dbx[-1] + 4, dby + 1), (dbx[-1] + 5, dby + 1)):
        lab_place("SRV-005", [t], f"SRV-005 macro rack {len(furn)}", tall=True)
    lab_place("STO-005", [(dbx[-1] + 4, dby + 2), (dbx[-1] + 5, dby + 2)], "STO-005 macro bay")
    lab_groups += [(dbx[0] - 5, dby + 2), (dbx[-1] + 5, dby + 1)]
    bx = sorted(t[0] for f in furn if f["asset"] == "CON-007" for t in f["tiles"])
    byy = next(t[1] for f in furn if f["asset"] == "CON-007" for t in f["tiles"])
    for c in (
        bx[0] - 1,
        bx[-1] + 1,
    ):  # validation: sample carts flanking the bench, specimen tanks beside it
        lab_place("STO-007", [(c, byy)], f"STO-007 sample cart {len(furn)}")
    lab_place("EQP-007", [(bx[-1] + 3, byy - 1), (bx[-1] + 4, byy - 1)], "EQP-007 specimen tank 1")
    lab_place("EQP-007", [(bx[-1] + 3, byy - 3), (bx[-1] + 4, byy - 3)], "EQP-007 specimen tank 2")
    lab_groups.append((bx[-1] + 4, byy - 1))
    dome = [t for f in furn if f["asset"] == "EQP-005" for t in f["tiles"]]
    dx0, dx1 = min(t[0] for t in dome), max(t[0] for t in dome)
    dy0, dy1 = min(t[1] for t in dome), max(t[1] for t in dome)
    for t in ((dx0 - 2, dy0 - 2), (dx1 + 2, dy0 - 2), (dx0 - 2, dy1 + 2), (dx1 + 2, dy1 + 2)):
        lab_place("EQP-006", [t], f"EQP-006 optics column {len(furn)}", tall=True)
    # east analysis island (facing the core) and a north-east analysis group, so the room's east half is worked space too
    for i, rows in enumerate(((lcr - 2, lcr - 1), (lcr + 1, lcr + 2)), 1):
        if lab_place("CON-031", [(lcc + 7, r) for r in rows], f"CON-031 lab analysis {i}"):
            for r in rows:
                lab_place("SEA-002", [(lcc + 6, r)], f"SEA-002 chair lab analysis {i}", kind="seat")
    lab_place("SCR-013", [(lcc + 7, lcr)], f"SCR-013 analysis screen cluster {len(furn)}")
    lab_place("STO-006", [(lcc + 2, lcr - 7)], f"STO-006 lab analysis cabinet {len(furn)}")
    if lab_place("CON-031", [(lcc + 3, lcr - 7), (lcc + 4, lcr - 7)], "CON-031 lab analysis 3"):
        for dc in (0, 1):
            lab_place(
                "SEA-002", [(lcc + 3 + dc, lcr - 6)], "SEA-002 chair lab analysis 3", kind="seat"
            )
    lab_place("SRV-005", [(lcc + 5, lcr - 7)], f"SRV-005 analysis rack {len(furn)}", tall=True)
    lab_groups += [(lcc + 7, lcr), (lcc + 4, lcr - 7)]
    # deck: conduits from each group and each perimeter gap outward; paired floor grates; vents
    lab_block = {t for f in furn if f["kind"] != "floor" for t in f["tiles"]}
    lab_cond = []
    for t0 in lab_groups + lab_gaps:
        L = math.hypot(cen(t0[0]) - lx, cen(t0[1]) - ly) or 1
        for k in range(1, 9):
            t = (
                round(t0[0] + (cen(t0[0]) - lx) / L * k),
                round(t0[1] + (cen(t0[1]) - ly) / L * k),
            )
            if t0 in lab_gaps:
                t = t0
            if region.get(t) != "H-LAB" or t in lab_block or t in lab_keep:
                break
            if t not in lab_cond:
                lab_cond.append(t)
            if t0 in lab_gaps:
                break
    if lab_cond:
        F("H-LAB", "FLR-011", lab_cond, "FLR-011 lab cable conduit", kind="floor")
    lab_mark = set(lab_cond) | lab_block | {a["tile"] for a in anchors}
    lab_big = []
    lab_picked = []
    for dc in range(-13, 13):
        for dr in range(-13, -1):
            a_ = [(lcc + dc + i, lcr + dr + j) for i in (0, 1) for j in (0, 1)]
            b_ = [(lcc + dc + i, lcr - dr - 1 + j) for i in (0, 1) for j in (0, 1)]
            if not all(
                region.get(t) == "H-LAB"
                and t not in lab_mark
                and t not in lab_keep
                and 4 < math.hypot(t[0] + 0.5 - lx / T, t[1] + 0.5 - ly / T) < 13
                for t in a_ + b_
            ):
                continue
            ang = math.atan2(dr, dc)
            if all(abs(math.atan2(math.sin(ang - q), math.cos(ang - q))) > 0.9 for q in lab_picked):
                lab_picked.append(ang)
                lab_big += a_ + b_
                lab_mark.update(a_ + b_)
    if lab_big:
        F("H-LAB", "FLR-010", lab_big, "FLR-010 large floor grates (paired)", kind="floor")
    # H-HAB (circle, 30 tiles across)
    hc, hr = math.floor(1377 / T), math.floor(692 / T)
    F("H-HAB", "PLT-005", absrect(hc - 1, hr - 1, 3, 3), "PLT-005 central tree", tall=True)
    F("H-HAB", "LEI-002", absrect(hc + 5, hr - 10, 3, 1), "LEI-002 counter")
    F("H-HAB", "LEI-003", absrect(hc + 8, hr - 10, 1, 1), "LEI-003 dispenser")
    A_("H-HAB", "habitat.counter", (hc + 6, hr - 11), "CHR-043", "HOST", "LEI-002 counter")
    for i, c in enumerate((hc + 3, hc + 6, hc + 9)):
        F("H-HAB", "TBL-003", [(c, hr - 6)], "TBL-003 café table")
        for j, dc in enumerate((-1, 1)):
            F("H-HAB", "SEA-007", [(c + dc, hr - 6)], "SEA-007", kind="seat")
            A_(
                "H-HAB",
                f"habitat.cafe_seat_{2 * i + j + 1}",
                (c + dc, hr - 6),
                serves="TBL-003 café table",
            )
    for i, c in enumerate((hc - 10, hc - 8, hc - 6)):
        F(
            "H-HAB",
            "EQP-004",
            absrect(c, hr - 8, 1, 2),
            f"EQP-004 recovery pod {i + 1}",
            kind="seat",
            tall=True,
        )
        A_(
            "H-HAB",
            f"habitat.recovery_pod_{i + 1}",
            (c, hr - 8),
            serves=f"EQP-004 recovery pod {i + 1}",
        )
    F("H-HAB", "CON-021", [(hc - 8, hr - 4)], "CON-021 vitals")
    A_("H-HAB", "habitat.vitals", (hc - 7, hr - 4), "CHR-041", "O2", "CON-021 vitals")
    F("H-HAB", "LEI-001", absrect(hc + 9, hr + 6, 3, 2), "LEI-001 billiards")
    F("H-HAB", "(clearance)", absrect(hc + 8, hr + 5, 5, 4), "LEI-001 +1 clearance", kind="floor")
    A_("H-HAB", "habitat.billiards_1", (hc + 8, hr + 6), serves="LEI-001 billiards")
    A_("H-HAB", "habitat.billiards_2", (hc + 12, hr + 7), serves="LEI-001 billiards")
    F("H-HAB", "STO-003", absrect(hc + 10, hr + 10, 2, 1), "STO-003 cue rack", tall=True)
    F("H-HAB", "LEI-004", absrect(hc - 2, hr + 6, 5, 3), "LEI-004 rug", kind="floor")
    F("H-HAB", "SEA-006", absrect(hc - 2, hr + 6, 1, 2), "SEA-006 sofa W", kind="seat")
    F("H-HAB", "SEA-006", absrect(hc + 2, hr + 6, 1, 2), "SEA-006 sofa E", kind="seat")
    F("H-HAB", "TBL-004", absrect(hc, hr + 6, 1, 2), "TBL-004")
    for i, t in enumerate(
        ((hc - 2, hr + 6), (hc - 2, hr + 7), (hc + 2, hr + 6), (hc + 2, hr + 7)), 1
    ):
        A_("H-HAB", f"habitat.sofa_{i}", t, serves="SEA-006 sofa W" if i <= 2 else "SEA-006 sofa E")
    F("H-HAB", "SEA-009", absrect(hc - 3, hr + 14, 2, 1), "SEA-009 window bench", kind="seat")
    F("H-HAB", "SEA-009", absrect(hc + 1, hr + 14, 2, 1), "SEA-009 window bench", kind="seat")
    A_("H-HAB", "habitat.window_1", (hc - 3, hr + 14), serves="SEA-009 window bench")
    A_("H-HAB", "habitat.window_2", (hc + 2, hr + 14), serves="SEA-009 window bench")
    for i, t in enumerate(((hc - 11, hr + 4), (hc - 11, hr + 6), (hc - 10, hr + 8)), 1):
        F("H-HAB", "LEI-005", [t], f"LEI-005 rest pod {i}", kind="seat")
        A_("H-HAB", f"habitat.rest_pod_{i}", t, serves=f"LEI-005 rest pod {i}")

    # ---------------- checks ----------------
    blocked = {}
    for f in furn:
        for t in f["tiles"]:
            if f["kind"] == "block":
                if t in blocked:
                    issues.append(f"furniture overlap {f['label']} / {blocked[t]} at {t}")
                blocked[t] = f["label"]
            if region.get(t) != f["room"]:
                issues.append(f"{f['label']} tile {t} outside {f['room']} (is {region.get(t)})")
    anchor_at = {}
    for a in anchors:
        t = a["tile"]
        if region.get(t) != a["room"]:
            issues.append(f"anchor {a['name']} {t} outside {a['room']} ({region.get(t)})")
        if t in blocked:
            issues.append(f"anchor {a['name']} on furniture {blocked[t]}")
        if t in anchor_at:
            issues.append(f"anchor {a['name']} shares tile with {anchor_at[t]}")
        anchor_at[t] = a["name"]
        if a.get("serves"):
            ft = [tt for f in furn if f["label"] == a["serves"] for tt in f["tiles"]]
            if not ft:
                issues.append(f"anchor {a['name']} serves unknown {a['serves']}")
            elif t not in ft and min(abs(t[0] - x) + abs(t[1] - y) for x, y in ft) > 1:
                issues.append(f"anchor {a['name']} not adjacent to {a['serves']}")

    def walkable(t):
        reg = region.get(t)
        if reg is None or reg in RESERVED or t in blocked:
            return False
        return not (reg in door_info and door_info[reg]["status"] != "open")

    def can_step(a, b):
        if not (walkable(a) and walkable(b)):
            return False
        e = frozenset((a, b))
        if e in seams:
            return False
        return region[a] == region[b] or e in allowed_open

    def nbrs(t):
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u = (t[0] + d[0], t[1] + d[1])
            if can_step(t, u):
                yield u

    def bfs(src):
        dist = {src: 0}
        prev = {}
        q = deque([src])
        while q:
            t = q.popleft()
            for u in nbrs(t):
                if u not in dist:
                    dist[u] = dist[t] + 1
                    prev[u] = t
                    q.append(u)
        return dist, prev

    # station-wide connectivity from the COR-N centre
    start = (math.floor(600 / T), 46)
    dist, prev = bfs(start)
    walk_tiles = [t for t in region if walkable(t)]
    unreached = [t for t in walk_tiles if t not in dist]
    by_room_unreached = {}
    for t in unreached:
        by_room_unreached.setdefault(region[t], []).append(t)
    for rm, ts in by_room_unreached.items():
        issues.append(f"{len(ts)} walkable tiles in {rm} unreachable, e.g. {ts[:3]}")
    for a in anchors:
        if a["tile"] not in dist:
            issues.append(f"anchor {a['name']} unreachable")

    # door approach: 2 tiles deep on each open side must be free of furniture and anchors
    def door_approach(d):
        out = []
        for ch in d["lanes"]:
            a0, a1, b0, b1 = ch[0], ch[1], ch[-1], ch[-2]
            for end, nxt in ((a0, a1), (b0, b1)):
                dx, dy = end[0] - nxt[0], end[1] - nxt[1]
                out += [end, (end[0] + dx, end[1] + dy)]
        return out

    for d in door_info.values():
        if d["status"] != "open":
            continue
        for t in door_approach(d):
            if t in blocked:
                issues.append(f"{d['id']} approach {t} blocked by {blocked[t]}")
            if t in anchor_at:
                issues.append(f"{d['id']} approach {t} holds anchor {anchor_at[t]}")
            if not walkable(t):
                issues.append(f"{d['id']} approach {t} not walkable ({region.get(t)})")
    for rid, (
        x,
        y,
    ) in R_DOORS.items():  # reserved R-doors: keep the hub-side approach clear (H-HAB sheet)
        for t, reg in region.items():
            if (
                reg == "H-HAB"
                and math.hypot(cen(t[0]) - x, cen(t[1]) - y) <= 30
                and (t in blocked or t in anchor_at)
            ):
                issues.append(f"{rid} approach {t} occupied")
    # H-HAB billiards clearance
    clr = [f for f in furn if f["label"] == "LEI-001 +1 clearance"][0]["tiles"]
    for t in clr:
        if t in blocked and not blocked[t].startswith("LEI-001"):
            issues.append(f"billiards clearance {t} blocked by {blocked[t]}")
    # H-CMD circulation ring (calibration room V1): the walkway between the dais and the consoles stays clear
    for t, n in region.items():
        if n == "H-CMD" and 6.6 <= math.hypot(t[0] - cc, t[1] - cr) <= 9.4 and t in blocked:
            issues.append(f"H-CMD circulation ring {t} blocked by {blocked[t]}")

    # two-agent passing: a tile supports passing if it sits in a free 2x2 block of one region
    def pass2(t):
        for ox in (0, -1):
            for oy in (0, -1):
                sq = [(t[0] + ox + i, t[1] + oy + j) for i in (0, 1) for j in (0, 1)]
                if (
                    all(walkable(s) and s not in anchor_at for s in sq)
                    and len({region[s] for s in sq}) == 1
                ):
                    return True
        return False

    def path(src, dst):
        ds, pv = bfs(src)
        if dst not in ds:
            return None
        p = [dst]
        while p[-1] != src:
            p.append(pv[p[-1]])
        return p[::-1]

    room_rep = {}
    for rm in list(RECTS) + list(CORRS) + list(HUBS):
        if rm in RESERVED:
            continue
        ts = [t for t, r in region.items() if r == rm]
        free = [t for t in ts if walkable(t)]
        c0, r0, c1, r1 = bbox[rm]
        doors = [d for d in door_info.values() if rm in (d["A"], d["B"]) and d["status"] == "open"]
        single = []
        for a in [a for a in anchors if a["room"] == rm]:
            for d in doors:
                ch = d["lanes"][0]
                inner = ch[0] if region[ch[0]] == rm else ch[-1]
                p = path(inner, a["tile"])
                if p is None:
                    continue
                run = 0
                worst = 0
                for t in p[2:-1]:
                    run = 0 if pass2(t) else run + 1
                    worst = max(worst, run)
                single.append((a["name"], d["id"], len(p) - 1, worst))
        occl = []
        for a in [a for a in anchors if a["room"] == rm and a.get("chr")]:
            s = (a["tile"][0], a["tile"][1] + 1)
            if s in blocked and any(f["tall"] and s in f["tiles"] for f in furn):
                occl.append(a["name"])
        room_rep[rm] = {
            "size_tiles": (c1 - c0 + 1, r1 - r0 + 1),
            "size_units": ((c1 - c0 + 1) * T, (r1 - r0 + 1) * T),
            "floor_tiles": len(ts),
            "free_tiles": len(free),
            "furniture_tiles": sum(1 for t in ts if t in blocked),
            "pass2_share": round(sum(1 for t in free if pass2(t)) / max(1, len(free)), 2),
            "routes": single,
            "occluded": occl,
        }
        if occl:
            issues.append(f"{rm}: anchors hidden behind tall furniture: {occl}")

    # corridor width
    for cn in CORRS:
        widths = {}
        for (c, _r), reg in region.items():
            if reg == cn:
                widths[c] = widths.get(c, 0) + 1
        room_rep[cn]["width_profile"] = sorted(set(widths.values()))
        room_rep[cn]["full_width_cols"] = sum(1 for w in widths.values() if w == 3)
        room_rep[cn]["cols"] = len(widths)

    out = {
        "scale": {
            "tile": T,
            "agent_height": AGENT_H,
            "spacing_tiles": SPACING,
            "camera": {"default": 2, "min": 0.5, "max": 6},
        },
        "hubs": HUBS,
        "rects": RECTS,
        "corrs": CORRS,
        "r_rooms": R_ROOMS,
        "r_doors": R_DOORS,
        "reserved": sorted(RESERVED),
        "tiles": [[c, r, reg] for (c, r), reg in region.items()],
        "doors": [dict(d) for d in door_info.values()],
        "seams": [sorted(e) for e in seams],
        "furniture": furn,
        "anchors": anchors,
        "bbox": bbox,
        "report": room_rep,
        "issues": issues,
    }
    return out


def print_report(geo):
    """Print the geometry check summary (issues, room fit, doors)."""
    print("ISSUES:", len(geo["issues"]))
    for i in geo["issues"]:
        print("  -", i)
    for rm, r in geo["report"].items():
        worst = max([x[3] for x in r["routes"]] or [0])
        print(
            f"{rm:6} {r['size_tiles']} floor {r['floor_tiles']} free {r['free_tiles']} "
            f"pass2 {r['pass2_share']} worst single-file run {worst}"
        )
