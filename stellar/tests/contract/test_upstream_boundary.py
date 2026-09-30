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
        "stellar.config, stellar.agents, stellar.validation, stellar.risk, stellar.marketdata, "
        "stellar.marketdata.providers, stellar.owner\n"
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


def _upstream_symbol_tables():
    tree = ast.parse((REPO_ROOT / "tradingagents" / "dataflows" / "symbols.py")
                     .read_text(encoding="utf-8"))
    tables = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and target.id in {"_ALIASES", "_FOREX_CURRENCIES"}:
                value = node.value
                if isinstance(value, ast.Call):  # frozenset({...})
                    value = value.args[0]
                tables[target.id] = ast.literal_eval(value)
    return tables


def test_stellar_classifies_upstream_symbol_substitutions_as_proxies():
    """Upstream silently maps XAUUSD to the gold future and NAS100 to the cash index
    (knowledge audit K5). Stellar's reference map must keep classifying those as
    PROXY; if upstream changes its aliases, this test forces a re-classification."""
    from stellar.marketdata import TRADINGAGENTS_YAHOO_REFERENCE as ref

    tables = _upstream_symbol_tables()
    aliases = tables["_ALIASES"]
    assert aliases["XAUUSD"] == ref.get("XAUUSD").provider_symbol == "GC=F"
    assert aliases["NAS100"] == ref.get("NAS100").provider_symbol == "^NDX"
    assert ref.get("XAUUSD").kind == ref.get("NAS100").kind == "PROXY"
    # Six-letter pairs of two ISO currencies become "<PAIR>=X" upstream.
    for pair in ("EURUSD", "USDJPY"):
        assert {pair[:3], pair[3:]} <= tables["_FOREX_CURRENCIES"]
        assert ref.get(pair).provider_symbol == f"{pair}=X"


def _calls(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            names.add(func.id if isinstance(func, ast.Name) else getattr(func, "attr", ""))
    return names


def _string_constants(path: Path) -> set[str]:
    return {n.value for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_only_the_risk_package_builds_decisions_and_order_intents():
    """Foundation §8.4: an OrderIntent (and a RiskDecision) is built only by the Risk Engine."""
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in STELLAR_SRC.rglob("*.py")
        if {"RiskDecision", "OrderIntent"} & _calls(p) and "risk" not in p.relative_to(
            STELLAR_SRC).parts[:1]
    )
    assert offenders == []


def test_only_the_owner_command_writes_breaker_resets():
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in STELLAR_SRC.rglob("*.py")
        if "circuit_breaker.reset" in _string_constants(p)
        and p.relative_to(STELLAR_SRC).parts[0] not in {"owner", "telemetry"}
        and p.name != "ledger.py"  # reads (and filters) resets; never writes one
    )
    assert offenders == []
    ledger_calls = _new_event_types(STELLAR_SRC / "risk" / "ledger.py")
    assert "circuit_breaker.reset" not in ledger_calls


def _new_event_types(path: Path) -> set[str]:
    types = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "new_event"
                and node.args and isinstance(node.args[0], ast.Constant)):
            types.add(node.args[0].value)
    return types


def test_nothing_outside_owner_imports_the_owner_package():
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in STELLAR_SRC.rglob("*.py")
        if p.relative_to(STELLAR_SRC).parts[0] != "owner"
        and any(n.startswith("stellar.owner") for n in _imported_modules(p))
    )
    assert offenders == []


def _imported_modules(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_risk_engine_has_no_llm_or_network_dependency():
    forbidden = {"langchain", "langgraph", "openai", "anthropic", "requests", "urllib", "socket",
                 "http", "tradingagents", "cli"}
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in (STELLAR_SRC / "risk").rglob("*.py")
        if {m.split(".")[0] for m in _imported_modules(p)} & forbidden
    )
    assert offenders == []


def test_execution_has_no_network_llm_or_broker_sdk_dependency():
    """Phase 4: the Paper Broker is internal. No MT5, broker SDK, network or LLM import."""
    forbidden = {"langchain", "langgraph", "openai", "anthropic", "requests", "urllib", "socket",
                 "http", "httpx", "aiohttp", "websockets", "MetaTrader5", "mt5", "tradingagents",
                 "cli", "random", "secrets"}
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in (STELLAR_SRC / "execution").rglob("*.py")
        if {m.split(".")[0] for m in _imported_modules(p)} & forbidden
    )
    assert offenders == []


def test_risk_does_not_depend_on_execution():
    """The dependency points one way: execution reads risk state, never the reverse."""
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in (STELLAR_SRC / "risk").rglob("*.py")
        if any(m.startswith("stellar.execution") for m in _imported_modules(p))
    )
    assert offenders == []


def test_only_the_execution_package_builds_execution_results():
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in STELLAR_SRC.rglob("*.py")
        if "ExecutionResult" in _calls(p) and p.relative_to(STELLAR_SRC).parts[0] != "execution"
    )
    assert offenders == []


def test_no_live_or_demo_execution_path_exists():
    """Phase 4 builds PAPER orders only; no module mentions a live account mode."""
    for path in (STELLAR_SRC / "execution").rglob("*.py"):
        assert "LIVE" not in _string_constants(path), path


TECHNICAL = STELLAR_SRC / "technical"


def test_technical_has_no_network_llm_broker_or_random_dependency():
    """Phase 5: deterministic, offline, Stellar-native. No upstream indicator code either."""
    forbidden = {"langchain", "langgraph", "openai", "anthropic", "requests", "urllib", "socket",
                 "http", "httpx", "aiohttp", "websockets", "MetaTrader5", "mt5", "tradingagents",
                 "cli", "random", "secrets", "stockstats", "pandas", "numpy", "yfinance", "time"}
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in TECHNICAL.rglob("*.py")
        if {m.split(".")[0] for m in _imported_modules(p)} & forbidden
    )
    assert offenders == []


def test_technical_cannot_reach_risk_execution_or_proposals():
    """Technical evidence only: no proposal, decision, order, broker, risk policy or owner path."""
    for path in TECHNICAL.rglob("*.py"):
        modules = _imported_modules(path)
        assert not any(m.startswith(("stellar.risk", "stellar.execution", "stellar.owner",
                                     "stellar.schemas.proposal", "stellar.schemas.order",
                                     "stellar.schemas.risk", "stellar.schemas.execution"))
                       for m in modules), path
        assert not {"TradeProposal", "OrderIntent", "RiskDecision", "PaperBroker",
                    "RiskService", "RiskPolicy", "ExecutionResult"} & _calls(path), path


def test_technical_calculations_never_use_float():
    for path in TECHNICAL.rglob("*.py"):
        assert "float" not in _calls(path), path


def test_nothing_imports_technical_except_its_own_package():
    """Risk, execution and owner do not depend on technical evidence in Phase 5."""
    offenders = sorted(
        str(p.relative_to(STELLAR_SRC)) for p in STELLAR_SRC.rglob("*.py")
        if p.relative_to(STELLAR_SRC).parts[0] != "technical"
        and any(m.startswith("stellar.technical") for m in _imported_modules(p))
    )
    assert offenders == []


@pytest.mark.parametrize("first", ["stellar.journal", "stellar.telemetry", "stellar.risk",
                                   "stellar.owner", "stellar.marketdata", "stellar.config",
                                   "stellar.execution", "stellar.technical"])
def test_every_package_imports_on_its_own(first):
    """Regression (Phase 3): importing stellar.journal first used to hit a circular import."""
    subprocess.run([sys.executable, "-c", f"import {first}"], cwd=STELLAR_ROOT,
                   env={"PYTHONPATH": str(STELLAR_ROOT / "src"), "PATH": ""}, check=True)
