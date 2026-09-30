"""The boundary between Stellar and upstream TradingAgents.

- Stellar may depend on TradingAgents; TradingAgents never imports Stellar.
- Phase 1 Stellar code does not import TradingAgents at all, so it cannot change
  upstream behaviour at import time.
- The upstream surfaces Stellar's registry and rating contract rely on still
  exist (layer design §1.5 C6, C7).
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

STELLAR_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = STELLAR_ROOT.parent
STELLAR_SRC = STELLAR_ROOT / "src" / "stellar"
UPSTREAM_PACKAGES = ("tradingagents", "cli")


def _imported_roots(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def test_upstream_never_imports_stellar():
    offenders = sorted(
        str(path.relative_to(REPO_ROOT))
        for package in (*UPSTREAM_PACKAGES, "tests")
        for path in (REPO_ROOT / package).rglob("*.py")
        if "stellar" in _imported_roots(path)
    )
    assert offenders == []
    assert "stellar" not in (REPO_ROOT / "main.py").read_text(encoding="utf-8")


def test_upstream_packaging_does_not_include_stellar():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "stellar" not in pyproject.lower()


def test_phase1_stellar_code_does_not_import_upstream():
    offenders = sorted(
        str(path.relative_to(STELLAR_ROOT))
        for path in STELLAR_SRC.rglob("*.py")
        if _imported_roots(path) & set(UPSTREAM_PACKAGES)
    )
    assert offenders == []


def test_importing_stellar_loads_no_upstream_module():
    code = (
        "import sys, stellar, stellar.schemas, stellar.telemetry, stellar.journal, "
        "stellar.config, stellar.agents, stellar.validation, stellar.risk\n"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in {'tradingagents', 'cli'}))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=STELLAR_ROOT,
        env={"PYTHONPATH": str(STELLAR_ROOT / "src"), "PATH": ""},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "[]"


def test_stellar_may_depend_on_tradingagents():
    pyproject = (STELLAR_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"tradingagents"' in pyproject


def test_upstream_node_names_used_by_the_registry_still_exist():
    from stellar.agents import default_registry

    setup = (REPO_ROOT / "tradingagents" / "graph" / "setup.py").read_text(encoding="utf-8")
    nodes = [a.upstream_node for a in default_registry() if a.upstream_node]
    assert len(nodes) == 8
    for node in nodes:
        assert f'add_node("{node}"' in setup, node


def test_rating_vocabulary_matches_upstream():
    from stellar.schemas import Rating

    tree = ast.parse(
        (REPO_ROOT / "tradingagents" / "agents" / "rating.py").read_text(encoding="utf-8")
    )
    values = {}
    for node in ast.walk(tree):
        target = getattr(node, "target", None) or (getattr(node, "targets", [None]) or [None])[0]
        if isinstance(target, ast.Name) and target.id in {"RATINGS_5_TIER", "RATING_REVIEW"}:
            values[target.id] = ast.literal_eval(node.value)
    assert [r.value for r in Rating] == [*values["RATINGS_5_TIER"], values["RATING_REVIEW"]]
