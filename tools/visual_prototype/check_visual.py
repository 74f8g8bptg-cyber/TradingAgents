"""Visual consistency check: the prototype data against the approved registries.

Checks displays (Screen Registry), characters (Character Registry), furniture assets (Asset
Registry), doors, rooms, the corridor repeater walls (Corridor Design CD-11) and that the page is
self-contained (no external URL, image or StarNet reference). Never edits a registry.
"""

import re


def check_visual(d, registries, html):
    """Return (fails, notes, summary). An empty `fails` list means the check passed."""
    asset_rows = registries["assets"]
    chars = registries["chars"]
    screens = registries["screens"]

    fails, notes = [], []

    def ok(cond, msg):
        if not cond:
            fails.append(msg)

    ROOMCODE = {
        "CMD": "H-CMD",
        "LAB": "H-LAB",
        "HAB": "H-HAB",
        "SPC": "L1",
        "TEC": "L2",
        "DEB": "L3",
        "DCR": "L4",
        "MEM": "L6",
        "PRF": "L7",
        "EXB": "L9",
        "RSK": "L10",
        "CRN": "COR-N",
        "CRS": "COR-S",
        "CCH": "R1",
    }
    by_label = {}
    for f in d["furniture"]:
        by_label.setdefault(f["label"], f["room"])
    # 1 displays
    shown = [x["id"] for x in d["displays"]]
    ok(len(shown) == len(set(shown)), "duplicate display")
    for sid, s in screens.items():
        if s["av"] == "X":
            ok(sid not in shown, f"planned display rendered: {sid}")
        else:
            ok(sid in shown, f"display missing: {sid}")
    for x in d["displays"]:
        s = screens[x["id"]]
        p = x["place"]
        code = x["id"].split("-")[1]
        room = (
            p[1]
            if p[0] in ("rim", "wall", "wallx")
            else ("COR-S" if p[0] == "door" else by_label.get(p[1].split("@")[0]))
        )
        if p[0] == "surface" and "@" in p[1]:
            room = p[1].split("@")[1]
        expect = ROOMCODE[code]
        ok(
            room == expect or (x["id"] == "DSP-RSK-09" and room == "COR-S"),
            f"{x['id']} placed in {room}, registry room {expect}",
        )
        ok(x["hw"] == s["hw"], f"{x['id']} hardware {x['hw']} != {s['hw']}")
        ok(x["av"] == s["av"], f"{x['id']} availability mismatch")
        if s["av"] == "N":
            ok(
                x["text"].startswith("NOT AVAILABLE"),
                f"{x['id']} has no producer but shows {x['text']}",
            )
        for t in [x["text"]] + x["sub"]:
            ok(not re.search(r"\d", t), f"{x['id']} shows a number: {t}")
        ok(
            x["text"] in ("AWAITING DATA", "MODE UNKNOWN", "NO TELEMETRY")
            or x["text"].startswith("NOT AVAILABLE"),
            f"{x['id']} unexpected state {x['text']}",
        )
    # 1b corridor repeaters (CD-11): south walls, clear of every door niche on that wall
    for x in d["displays"]:
        p = x["place"]
        if x["id"] in ("DSP-CRN-01", "DSP-CRS-01"):
            ok(p[2] == "S", f"{x['id']} not on the south wall")
            half = p[4] * 12 / 2
            lo, hi = p[3] - half, p[3] + half
            for dr in d["doors"]:
                if p[1] in (dr["A"], dr["B"]):
                    for f in dr["frames"]:
                        x0, x1 = sorted((f["p1"][0], f["p2"][0]))
                        ysouth = (d["bbox"][p[1]][3] + 1) * 12
                        if f["p1"][1] == f["p2"][1] == ysouth:
                            ok(hi <= x0 - 4 or lo >= x1 + 4, f"{x['id']} overlaps {dr['id']} niche")
    # 2 furniture assets
    for f in d["furniture"]:
        a = f["asset"]
        if a.startswith("("):
            notes.append(f"{f['label']}: no asset ID (marking only)")
            continue
        ok(a in asset_rows, f"asset {a} not in Asset Registry")
        if a in asset_rows:
            row = asset_rows[a]
            ok("RETIRED" not in row, f"asset {a} is RETIRED")
            hub = f["room"]
            if hub not in row and not (
                hub.startswith("L") and re.search(r"\bL rooms\b|most rooms|everywhere", row)
            ):
                notes.append(f"{a} ({f['label']}) in {hub}: room not named in its registry row")
    # 2b occupancy: a decorative resident is only ever placed inside its permitted zone
    for asset, rule in d.get("occupancy", {}).items():
        for f in d["furniture"]:
            if f["asset"] == asset:
                ok(
                    f["room"] in rule["rooms"],
                    f"{asset} placed in {f['room']}, outside {rule['rooms']}",
                )
    # 3 characters
    rendered = {a["chr"]: a for a in d["agents"]}
    for cid, c in chars.items():
        st = c["status"]
        home = c["home"]
        if re.search(r"RETIRED|DEFERRED|FUTURE", st):
            ok(cid not in rendered, f"{cid} ({st[:20]}) rendered")
        elif len(home) >= 2:
            ok(cid in rendered, f"{cid} active with home {home} but not rendered")
    for cid, a in rendered.items():
        c = chars[cid]
        ok(
            c["home"][:2] == [a["room"], a["anchor"]],
            f"{cid} home {c['home'][:2]} != rendered {a['room']} {a['anchor']}",
        )
        ok(c["dept"].split()[0] == a["dept"], f"{cid} dept {c['dept']} != {a['dept']}")
    # 4 doors
    ids = {x["id"]: x for x in d["doors"]}
    ok(len(ids) == 15 and len(d["rDoors"]) == 6, "door count != 21")
    ok(
        {k for k, v in ids.items() if v["restricted"]} == {"DR-L9", "DR-L10"},
        "restricted doors != DR-L9, DR-L10",
    )
    kinds = {}
    for x in d["doors"]:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    kinds["DOR-009"] = kinds.get("DOR-009", 0) + len(d["rDoors"])
    ok(
        kinds == {"DOR-001": 8, "DOR-008": 2, "DOR-009": 11},
        f"door kinds {kinds} vs Asset Registry DOR-001 ×8, DOR-008 ×2, DOR-009 ×11",
    )
    ok(
        all(
            x["status"] == "reserved"
            for x in d["doors"]
            if x["B"] in ("L5", "L8") or x["A"] in ("L5", "L8")
        ),
        "L5/L8 doors not sealed",
    )
    # 5 rooms
    for r in [
        "H-CMD",
        "H-LAB",
        "H-HAB",
        "COR-N",
        "COR-S",
        "L1",
        "L2",
        "L3",
        "L4",
        "L6",
        "L7",
        "L9",
        "L10",
        "L5",
        "L8",
    ]:
        ok(r in d["bbox"] or r in d["hubs"], f"room {r} missing")
    ok(sorted(d["rRooms"]) == [f"R{i}" for i in range(1, 7)], "R1-R6 missing")
    # 6 self-contained, no StarNet material, no external resources
    ok(not re.search(r"https?://", html), "external URL in prototype")
    ok(
        not re.search(r"<img|\.png|\.webp|\.gif|starnet", html, re.I),
        "image or StarNet reference in prototype",
    )
    summary = (
        f"displays {len(shown)} rendered / {sum(1 for s in screens.values() if s['av'] == 'X')} planned not rendered; "
        f"agents {len(rendered)}; furniture {len(d['furniture'])}"
    )
    return fails, notes, summary
