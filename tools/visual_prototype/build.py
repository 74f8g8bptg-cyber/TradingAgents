"""Rebuild (or verify) the Stellar geometry preview and Visual Prototype.

    python tools/visual_prototype/build.py            # rebuild both pages into docs/
    python tools/visual_prototype/build.py --check    # rebuild in memory; fail if docs/ differs
    python tools/visual_prototype/build.py --dump DIR # also write the intermediate JSON models

Both modes run the geometry consistency check and the visual consistency check first and stop on
any failure. The pipeline only reads the registries; it never edits them.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check_visual import check_visual  # noqa: E402
from geometry import build_geometry, print_report  # noqa: E402
from prototype_data import build_prototype_data  # noqa: E402
from registry import load_all  # noqa: E402
from render import render_geometry_preview, render_prototype  # noqa: E402

REPO = HERE.parents[1]
DOCS = REPO / "docs"
OUTPUTS = {
    "geometry preview": DOCS / "preview" / "STELLAR_GEOMETRY_PREVIEW_V1.html",
    "visual prototype": DOCS / "prototype" / "STELLAR_VISUAL_PROTOTYPE_V1.html",
}


def _json_roundtrip(obj):
    # The pages embed JSON, so every stage works on plain JSON values (tuples become lists).
    return json.loads(json.dumps(obj, default=list))


def build(verbose=False):
    """Run the whole pipeline in memory. Returns (pages, models, ok)."""
    geo = _json_roundtrip(build_geometry())
    if verbose:
        print_report(geo)
    print(f"geometry consistency: {len(geo['issues'])} issue(s)")
    for issue in geo["issues"]:
        print("  -", issue)

    registries = load_all(DOCS)
    data = _json_roundtrip(build_prototype_data(geo, registries))
    pages = {
        "geometry preview": render_geometry_preview(geo),
        "visual prototype": render_prototype(data),
    }

    fails, notes, summary = check_visual(data, registries, pages["visual prototype"])
    print(f"visual consistency: {len(fails)} failure(s), {len(notes)} note(s); {summary}")
    for f in fails:
        print("  -", f)
    if verbose:
        for n in notes:
            print("  ·", n)
    return (
        pages,
        {"geometry.json": geo, "prototype_data.json": data},
        not geo["issues"] and not fails,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--check", action="store_true", help="verify the committed pages instead of writing them"
    )
    ap.add_argument(
        "--dump", type=Path, help="write the intermediate JSON models into this directory"
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="print the room-fit report and check notes"
    )
    args = ap.parse_args(argv)

    pages, models, ok = build(args.verbose)
    if not ok:
        print("FAILED: consistency checks did not pass; nothing written.")
        return 1
    if args.dump:
        args.dump.mkdir(parents=True, exist_ok=True)
        for name, model in models.items():
            (args.dump / name).write_text(
                json.dumps(model, separators=(",", ":")), encoding="utf-8"
            )
    status = 0
    for key, html in pages.items():
        path = OUTPUTS[key]
        rel = path.relative_to(REPO)
        if args.check:
            same = path.exists() and path.read_text(encoding="utf-8") == html
            print(f"{'OK      ' if same else 'DIFFERS '} {rel}")
            status |= 0 if same else 1
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
            print(f"wrote    {rel} ({len(html)} bytes)")
    if args.check and status:
        print("FAILED: the committed pages are not reproducible from the pipeline.")
    return status


if __name__ == "__main__":
    sys.exit(main())
