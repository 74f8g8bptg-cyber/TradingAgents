"""Render the two static HTML pages: the geometry preview and the Visual Prototype."""

import json
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent / "templates"
PLACEHOLDER = "/*DATA*/null"
# The reusable Stellar visual vocabulary (construction families) lives in its own file and is inlined
# into the page at this marker, so every room composition shares one construction language.
VOCABULARY = "/*VOCABULARY*/"
VOCABULARY_FILE = "stellar_vocabulary.js"
# The life layer (ambient activity, navigation, doors, event hooks) is a pure module inlined at this marker
LIFE = "/*LIFE*/"
LIFE_FILE = "stellar_life.js"
# The sound layer (director + procedural Web Audio engine) is inlined at this marker
SOUND = "/*SOUND*/"
SOUND_FILE = "stellar_sound.js"


def _fill(template_name, data):
    html = (TEMPLATES / template_name).read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError(f"{template_name}: data placeholder missing")
    if VOCABULARY in html:
        html = html.replace(
            VOCABULARY, (TEMPLATES / VOCABULARY_FILE).read_text(encoding="utf-8").rstrip("\n")
        )
    if LIFE in html:
        html = html.replace(LIFE, (TEMPLATES / LIFE_FILE).read_text(encoding="utf-8").rstrip("\n"))
    if SOUND in html:
        html = html.replace(
            SOUND, (TEMPLATES / SOUND_FILE).read_text(encoding="utf-8").rstrip("\n")
        )
    return html.replace(PLACEHOLDER, json.dumps(data, separators=(",", ":")))


def render_geometry_preview(g):
    """Top-down geometry / scale preview (docs/preview/STELLAR_GEOMETRY_PREVIEW_V1.html)."""

    T = g["scale"]["tile"]
    reg = {(c, r): n for c, r, n in g["tiles"]}
    door_edges = {}
    for d in g["doors"]:
        for ch in d["lanes"]:
            for a, b in zip(ch, ch[1:], strict=False):
                door_edges[frozenset((tuple(a), tuple(b)))] = d["status"]
    seams = {frozenset((tuple(a), tuple(b))) for a, b in g["seams"]}
    walls = []
    for (c, r), n in reg.items():
        for dc, dr in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            u = (c + dc, r + dr)
            m = reg.get(u)
            if m == n:
                continue
            e = frozenset(((c, r), u))
            if e in door_edges and door_edges[e] == "open":
                continue
            if m is not None and (u < (c, r)):
                continue
            # edge segment in world units
            if dc == 1:
                seg = ((c + 1) * T, r * T, (c + 1) * T, (r + 1) * T)
            elif dc == -1:
                seg = (c * T, r * T, c * T, (r + 1) * T)
            elif dr == 1:
                seg = (c * T, (r + 1) * T, (c + 1) * T, (r + 1) * T)
            else:
                seg = (c * T, r * T, (c + 1) * T, r * T)
            walls.append(seg)
    glass = []
    for e in seams:
        a, b = sorted(e)
        if a[0] == b[0]:
            glass.append((a[0] * T, b[1] * T, (a[0] + 1) * T, b[1] * T))
        else:
            glass.append((b[0] * T, a[1] * T, b[0] * T, (a[1] + 1) * T))
    door_marks = []
    for d in g["doors"]:
        for ch in d["lanes"]:
            for a, b in zip(ch, ch[1:], strict=False):
                a, b = tuple(a), tuple(b)
                if a[0] == b[0]:
                    y = max(a[1], b[1]) * T
                    door_marks.append([a[0] * T, y, (a[0] + 1) * T, y, d["status"], d["id"]])
                else:
                    x = max(a[0], b[0]) * T
                    door_marks.append([x, a[1] * T, x, (a[1] + 1) * T, d["status"], d["id"]])
    data = {
        "T": T,
        "H": g["scale"]["agent_height"],
        "sp": g["scale"]["spacing_tiles"],
        "tiles": g["tiles"],
        "walls": walls,
        "glass": glass,
        "doors": door_marks,
        "doorInfo": [
            {"id": d["id"], "x": d["x"], "y": d["y"], "status": d["status"]} for d in g["doors"]
        ],
        "furn": g["furniture"],
        "anchors": g["anchors"],
        "bbox": g["bbox"],
        "rRooms": g["r_rooms"],
        "rDoors": g["r_doors"],
        "hubs": g["hubs"],
        "reserved": g["reserved"],
    }
    return _fill("geometry_preview.html", data)


def render_prototype(proto_data):
    """Visual Prototype page (docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html)."""
    return _fill("visual_prototype.html", proto_data)
