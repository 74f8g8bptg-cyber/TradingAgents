"""Assemble the Visual Prototype data from the geometry model and the approved registries."""

import math
import re

T = 12


def build_prototype_data(g, registries):
    """Return the JSON-ready data embedded in the Visual Prototype page."""
    reg = {(c, r): n for c, r, n in g["tiles"]}
    hubs = g["hubs"]
    screens = registries["screens"]
    chars = registries["chars"]

    ROOMS = {
        "H-CMD": ("Main Command", "CMD", "hub"),
        "H-LAB": ("Lab / Research Hub", "SCI", "hub"),
        "H-HAB": ("Habitat", "HAB", "hub"),
        "L1": ("Market Specialists", "SCI", "room"),
        "L2": ("Technical Deck", "SCI", "room"),
        "L3": ("Debate Chamber", "SCI", "room"),
        "L4": ("Data Core", "OPS", "room"),
        "L6": ("Memory Archive", "SCI", "room"),
        "L7": ("Performance Lab", "SCI", "room"),
        "L9": ("Execution Bay", "OPS", "room"),
        "L10": ("Risk Control Room", "OPS", "room"),
        "COR-N": ("Upper corridor", "NEU", "corr"),
        "COR-S": ("Lower corridor", "NEU", "corr"),
        "L5": ("Reserved", "RES", "reserved"),
        "L8": ("Reserved", "RES", "reserved"),
    }
    FLOOR = {
        "H-CMD": "FLR-001",
        "H-LAB": "FLR-001",
        "H-HAB": "FLR-004",
        "L10": "FLR-003",
        "COR-N": "FLR-005",
        "COR-S": "FLR-005",
    }

    # ---------------- walls (straight edges; hub rims are drawn as arcs) ----------------
    open_door_edges = set()
    res_door_edges = set()
    for d in g["doors"]:
        for ch in d["lanes"]:
            for a, b in zip(ch, ch[1:], strict=False):
                (open_door_edges if d["status"] == "open" else res_door_edges).add(
                    frozenset((tuple(a), tuple(b)))
                )

    def is_hub(n):
        return n is not None and n.startswith("H-")

    walls = []
    seen = set()
    for (c, r), n in reg.items():
        if is_hub(n):
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u = (c + dc, r + dr)
            m = reg.get(u)
            if m == n or is_hub(m):
                continue
            e = frozenset(((c, r), u))
            if e in open_door_edges or e in res_door_edges or e in seen:
                continue
            seen.add(e)
            if dc == 1:
                p1, p2 = ((c + 1) * T, r * T), ((c + 1) * T, (r + 1) * T)
            elif dc == -1:
                p1, p2 = (c * T, r * T), (c * T, (r + 1) * T)
            elif dr == 1:
                p1, p2 = (c * T, (r + 1) * T), ((c + 1) * T, (r + 1) * T)
            else:
                p1, p2 = (c * T, r * T), ((c + 1) * T, r * T)
            walls.append(
                {"p1": p1, "p2": p2, "n": [dc, dr], "a": n, "b": m}
            )  # n = normal from region a toward b
    seam_glass = []
    for e in g["seams"]:
        a, b = sorted(map(tuple, e))
        if a[0] == b[0]:
            seam_glass.append({"p1": (a[0] * T, b[1] * T), "p2": ((a[0] + 1) * T, b[1] * T)})
        else:
            seam_glass.append({"p1": (b[0] * T, a[1] * T), "p2": (b[0] * T, (a[1] + 1) * T)})

    # hull infill (WAL-009): non-floor tiles enclosed between floor along a row or column
    floor = set(reg)
    xs = [c for c, r in floor]
    ys = [r for c, r in floor]
    hull = []
    for c in range(min(xs) - 1, max(xs) + 2):
        for r in range(min(ys) - 1, max(ys) + 2):
            if (c, r) in floor:
                continue

            def hit(dc, dr, c=c, r=r):
                for k in range(1, 5):
                    t = reg.get((c + dc * k, r + dr * k))
                    if t is not None:
                        return True
                return False

            if (hit(1, 0) and hit(-1, 0)) or (hit(0, 1) and hit(0, -1)):
                hull.append([c, r])

    # ---------------- doors ----------------
    door_out = []
    RESTRICTED = {"DR-L9", "DR-L10"}
    for d in g["doors"]:
        frames = []
        for side in (0, -1):
            segs = []
            for ch in d["lanes"]:
                a, b = (tuple(ch[0]), tuple(ch[1])) if side == 0 else (tuple(ch[-1]), tuple(ch[-2]))
                if a[0] == b[0]:
                    y = max(a[1], b[1]) * T
                    segs.append(((a[0] * T, y), ((a[0] + 1) * T, y)))
                else:
                    x = max(a[0], b[0]) * T
                    segs.append(((x, a[1] * T), (x, (a[1] + 1) * T)))
            pts = [p for s in segs for p in s]
            p1 = min(pts)
            p2 = max(pts)
            frames.append(
                {"p1": p1, "p2": p2, "region": reg[tuple(d["lanes"][0][0 if side == 0 else -1])]}
            )
        if d["depth"] == 0:
            frames = frames[:1]
        hubside = next((h for h in (d["A"], d["B"]) if is_hub(h)), None)
        kind = "DOR-009" if hubside else ("DOR-008" if d["id"] in RESTRICTED else "DOR-001")
        door_out.append(
            {
                "id": d["id"],
                "status": d["status"],
                "kind": kind,
                "restricted": d["id"] in RESTRICTED,
                "A": d["A"],
                "B": d["B"],
                "frames": frames,
                "threshold": [list(t) for ch in d["lanes"] for t in ch[1:-1]],
            }
        )
    r_doors = []
    hx, hy, hr = hubs["H-HAB"]
    for rid, (x, y) in g["r_doors"].items():
        ang = math.atan2(y - hy, x - hx)
        r_doors.append({"id": rid, "x": x, "y": y, "ang": ang, "room": "R" + rid[-1]})

    # hub rim door gaps (angles) from the door frames
    hub_gaps = {h: [] for h in hubs}
    for d in door_out:
        for h in (d["A"], d["B"]):
            if is_hub(h):
                cx, cy, _ = hubs[h]
                f = d["frames"][0]
                angs = [math.atan2(p[1] - cy, p[0] - cx) for p in (f["p1"], f["p2"])]
                hub_gaps[h].append({"door": d["id"], "a0": min(angs), "a1": max(angs)})
    for rd in r_doors:
        half = 12 / (hr + 7)
        hub_gaps["H-HAB"].append({"door": rd["id"], "a0": rd["ang"] - half, "a1": rd["ang"] + half})

    # ---------------- characters ----------------
    agents = []
    for a in g["anchors"]:
        if not a["chr"]:
            continue
        ch = chars[a["chr"]]
        st = ch["status"]
        no_prod = bool(re.search(r"no producer|not built|dormant", st, re.I))
        fur = [f for f in g["furniture"] if f["label"] == a.get("serves")]
        if fur:
            fx = sum(t[0] for t in fur[0]["tiles"]) / len(fur[0]["tiles"])
            fy = sum(t[1] for t in fur[0]["tiles"]) / len(fur[0]["tiles"])
            face = [fx - a["tile"][0], fy - a["tile"][1]]
        else:
            face = [0, 1]
        dept = {"CMD": "CMD", "SCI": "SCI", "OPS": "OPS", "SYN": "SYN"}.get(
            ch["dept"].split()[0], "SCI"
        )
        role_states = [
            s.strip()
            for s in re.split(r",", re.sub(r"\(.*?\)", "", ch["states"]))
            if s.strip() and "ambient" not in s
        ]
        agents.append(
            {
                "chr": a["chr"],
                "code": a["code"],
                "name": ch["name"],
                "role": ch["role"],
                "dept": dept,
                "room": a["room"],
                "anchor": a["name"],
                "tile": a["tile"],
                "face": face,
                "noProducer": no_prod,
                "status": st,
                "roleStates": role_states,
                "cls": ch["cls"],
            }
        )

    # ---------------- displays: approved placement (room sheets / registry) ----------------
    P = {
        # H-CMD (rim clock positions)
        "DSP-CMD-01": ("rim", "H-CMD", 12.0, 84, 24, 14),
        "DSP-CMD-04": ("rim", "H-CMD", 12.0, 100, 5, 7.5),
        "DSP-CMD-07": ("rim", "H-CMD", 12.0, 70, 4, 39.5),
        "DSP-CMD-08": ("rim", "H-CMD", 1.0, 22, 7, 16),
        "DSP-CMD-03": ("rim", "H-CMD", 10.75, 34, 16, 12),
        "DSP-CMD-02": ("rim", "H-CMD", 1.75, 34, 16, 12),
        "DSP-CMD-05": ("rim", "H-CMD", 4.0, 34, 16, 12),
        "DSP-CMD-06": ("rim", "H-CMD", 5.2, 34, 16, 12),
        "DSP-CMD-09": ("console", "CON-004 trader"),
        "DSP-CMD-10": ("console", "CON-005 proposal"),
        "DSP-CMD-11": ("console", "CON-003 ops"),
        "DSP-CMD-12": ("console", "CON-022 budget"),
        # H-LAB
        "DSP-LAB-06": ("rim", "H-LAB", 12.0, 60, 16, 12),
        "DSP-LAB-07": ("rim", "H-LAB", 1.2, 30, 12, 12),
        "DSP-LAB-08": ("rim", "H-LAB", 10.6, 30, 12, 12),
        "DSP-LAB-01": ("rim", "H-LAB", 9.0, 44, 16, 12),
        "DSP-LAB-04": ("rim", "H-LAB", 7.9, 14, 14, 13),
        "DSP-LAB-05": ("console", "SCR-006 projector column"),
        "DSP-LAB-02": ("rim", "H-LAB", 5.6, 36, 14, 12),
        "DSP-LAB-03": ("rim", "H-LAB", 6.4, 36, 14, 12),
        # H-HAB
        "DSP-HAB-01": ("rim", "H-HAB", 1.45, 16, 8, 14),
        "DSP-HAB-02": ("rim", "H-HAB", 9.65, 22, 12, 12),
        "DSP-HAB-03": ("rim", "H-HAB", 10.05, 18, 10, 12),
        "DSP-HAB-04": ("rim", "H-HAB", 10.4, 18, 10, 12),
        # L rooms: (wall, room, side, centre along the wall in tiles from the west / north end, width tiles, height units, bottom units)
        "DSP-SPC-01": ("console", "CON-009 metals"),
        "DSP-SPC-02": ("console", "CON-009 FX desk"),
        "DSP-SPC-03": ("console", "CON-009 indices"),
        "DSP-SPC-04": ("wall", "L1", "W", 11.5, 2, 12, 12),
        "DSP-TEC-02": ("wall", "L2", "N", 2.0, 3, 14, 12),
        "DSP-TEC-03": ("wall", "L2", "N", 7.0, 3, 14, 12),
        "DSP-TEC-01": ("surface", "TBL-002 holo chart table"),
        "DSP-TEC-04": ("wall", "L2", "E", 4.5, 4, 4, 22),
        "DSP-TEC-05": ("wall", "L2", "E", 7.6, 1.3, 9, 12),
        "DSP-TEC-06": ("wall", "L2", "E", 9.1, 1.3, 9, 12),
        "DSP-TEC-07": ("wall", "L2", "W", 11.5, 1.2, 12, 12),
        "DSP-DEB-04": ("wall", "L3", "N", 1.5, 2, 10, 14),
        "DSP-DEB-06": ("wall", "L3", "N", 5.0, 3, 12, 14),
        "DSP-DEB-01": ("wall", "L3", "W", 6.5, 3, 14, 12),
        "DSP-DEB-02": ("wall", "L3", "E", 6.5, 3, 14, 12),
        "DSP-DEB-03": ("surface", "TBL-007 evidence stage"),
        "DSP-DEB-05": ("wall", "L3", "W", 12.5, 2, 10, 12),
        "DSP-DCR-02": ("wall", "L4", "N", 2.0, 2.5, 12, 12),
        "DSP-DCR-06": ("wall", "L4", "N", 7.5, 1.5, 9, 13),
        "DSP-DCR-03": ("wall", "L4", "W", 3.0, 2, 12, 12),
        "DSP-DCR-04": ("wall", "L4", "W", 5.6, 2, 12, 12),
        "DSP-DCR-01": ("console", "EQP-001 + SCR-006 column"),
        "DSP-DCR-05": ("console", "CON-027 recon."),
        "DSP-MEM-01": ("wall", "L6", "N", 2.5, 3, 13, 12),
        "DSP-MEM-02": ("wall", "L6", "N", 6.5, 3, 13, 12),
        "DSP-MEM-03": ("wall", "L6", "W", 6.0, 2, 11, 12),
        "DSP-MEM-04": ("surface", "TBL-005 table@L6"),
        "DSP-PRF-01": ("wall", "L7", "N", 2.5, 3, 13, 12),
        "DSP-PRF-02": ("wall", "L7", "N", 6.5, 3, 13, 12),
        "DSP-PRF-04": ("wall", "L7", "E", 2.5, 2, 11, 12),
        "DSP-PRF-03": ("wall", "L7", "W", 5.5, 2, 11, 12),
        "DSP-PRF-05": ("wall", "L7", "E", 5.5, 2, 11, 12),
        "DSP-EXB-04": ("console", "CON-016 pre-flight"),
        "DSP-EXB-02": ("wall", "L9", "E", 3.0, 3, 13, 12),
        "DSP-EXB-03": ("wall", "L9", "E", 10.0, 3, 13, 12),
        "DSP-EXB-01": ("wall", "L9", "S", 4.5, 3, 10, 14),
        "DSP-EXB-05": ("wall", "L9", "S", 4.5, 5, 8, 26),
        "DSP-RSK-01": ("console", "CON-012 intake"),
        "DSP-RSK-02": ("console", "CON-001 contradiction desk"),
        "DSP-RSK-07": ("console", "CON-029 outbox"),
        "DSP-RSK-06": ("wall", "L10", "W", 7.0, 2, 11, 12),
        "DSP-RSK-05": ("console", "CON-015 breaker panel"),
        "DSP-RSK-04": ("console", "CON-014 sizing"),
        "DSP-RSK-03": ("wall", "L10", "S", 4.5, 3, 12, 14),
        "DSP-RSK-08": ("wall", "L10", "S", 8.0, 2, 10, 12),
        "DSP-RSK-09": ("door", "DR-L10"),
        "DSP-CRN-01": ("wallx", "COR-N", "S", 613, 1.4, 8, 14),
        "DSP-CRS-01": ("wallx", "COR-S", "S", 676, 1.4, 8, 14),  # CD-11: south walls
    }

    def offline_state(sid, s):
        if s["av"] == "N":
            m = re.search(r"\*\*(NOT AVAILABLE[^*]*)\*\*", s["missing"])
            return "NOT_AVAILABLE", (m.group(1) if m else "NOT AVAILABLE")
        if "MODE UNKNOWN" in s["missing"]:
            return "UNKNOWN", "MODE UNKNOWN"
        if "NO TELEMETRY" in s["missing"]:
            return "NO_TELEMETRY", "NO TELEMETRY"
        return "AWAITING", "AWAITING DATA"

    SUBLINES = {
        "DSP-CMD-01": ["Live quotes: NOT AVAILABLE"],
        "DSP-CMD-05": ["Drawdown: NOT AVAILABLE"],
        "DSP-CMD-10": ["Reward:risk: NOT AVAILABLE"],
        "DSP-CMD-06": ["Link: NOT CONNECTED (prototype)"],
        "DSP-SPC-01": ["XAG: NOT CONFIGURED"],
        "DSP-EXB-01": ["sent / acknowledged / partially filled: NOT AVAILABLE"],
        "DSP-TEC-07": ["Ring: UTC (UI clock)"],
        "DSP-CMD-04": ["stages unlit until their events arrive"],
    }
    displays = []
    for sid, s in screens.items():
        if s["av"] == "X":
            continue
        if sid not in P:
            continue
        st, text = offline_state(sid, s)
        displays.append(
            {
                "id": sid,
                "name": re.sub(r"\s*\(.*?\)", "", s["name"]),
                "fullName": s["name"],
                "hw": s["hw"],
                "av": s["av"],
                "io": s["io"],
                "src": s["src"],
                "state": st,
                "text": text,
                "sub": SUBLINES.get(sid, []),
                "place": P[sid],
            }
        )

    data = {
        "T": T,
        "hubs": hubs,
        "rects": g["rects"],
        "corrs": g["corrs"],
        "bbox": g["bbox"],
        "tiles": g["tiles"],
        "rooms": ROOMS,
        "floorMat": FLOOR,
        "rRooms": g["r_rooms"],
        "rDoors": r_doors,
        "hubGaps": hub_gaps,
        "walls": walls,
        "glass": seam_glass,
        "hull": hull,
        "doors": door_out,
        "furniture": g["furniture"],
        "anchors": g["anchors"],
        "agents": agents,
        "displays": displays,
        "engineOrder": [
            "MARKET_DATA",
            "TECHNICAL",
            "RESEARCH",
            "SETUP",
            "PROPOSAL",
            "RISK",
            "ORDER_AUTHORISATION",
            "PAPER_SUBMISSION",
        ],
    }
    return data
