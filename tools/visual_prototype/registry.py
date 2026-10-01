"""Read-only loaders for the approved Stellar registries (Markdown tables under docs/)."""

import re
from pathlib import Path


def md_cells(line):
    """Split one Markdown table row into stripped cell strings."""
    return [x.strip() for x in line.strip().strip("|").split("|")]


def load_screens(docs: Path):
    """Screen Registry: every `DSP-…` row -> name, hardware, source, availability, I/O, missing text."""
    screens = {}
    for line in (docs / "STELLAR_SCREEN_REGISTRY.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `DSP-"):
            continue
        c = md_cells(line)
        sid = c[0].strip("`")
        if len(c) >= 8:
            screens[sid] = {
                "name": c[1],
                "hw": re.findall(r"SCR-\d+", c[2])[0],
                "src": c[4],
                "av": c[5],
                "io": c[6],
                "missing": c[7],
            }
        elif len(c) == 7:  # corridor repeaters: no content-source column
            screens[sid] = {
                "name": c[1],
                "hw": re.findall(r"SCR-\d+", c[2])[0],
                "src": "derived (Screen Registry §2.2)",
                "av": c[4],
                "io": c[5],
                "missing": c[6],
            }
        else:  # planned rows (PLANNED / not rendered)
            screens[sid] = {
                "name": c[1],
                "hw": "",
                "src": c[2],
                "av": c[3],
                "io": "",
                "missing": "",
            }
    return screens


def load_characters(docs: Path):
    """Character Registry roster: name, role, department, home room / anchor, role states, class, status."""
    chars = {}
    for line in (docs / "STELLAR_CHARACTER_REGISTRY.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| `(CHR-\d+)` \|", line)
        if not m:
            continue
        c = md_cells(line)
        chars[m.group(1)] = {
            "name": c[1],
            "role": re.sub(r"\*", "", c[2]),
            "dept": c[3],
            "home": re.findall(r"`([\w\-\.]+)`", c[4]),
            "states": c[6],
            "cls": c[7],
            "status": re.sub(r"\*", "", c[8]),
        }
    return chars


def load_assets(docs: Path):
    """Asset Registry: asset ID -> its raw table row."""
    assets = {}
    for line in (docs / "STELLAR_ASSET_REGISTRY.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| `([A-Z]{3}-\d{3})` \|", line)
        if m:
            assets[m.group(1)] = line
    return assets


def load_all(docs: Path):
    return {
        "screens": load_screens(docs),
        "chars": load_characters(docs),
        "assets": load_assets(docs),
    }
