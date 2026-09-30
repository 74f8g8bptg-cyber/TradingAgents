"""Valid example records for tests.

All numbers are illustrative test values: they are not risk limits, sizing
rules or recommendations, and nothing outside the tests uses them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from stellar.schemas import (
    AnalysisReport,
    Candle,
    CandleSeries,
    ClaimValidation,
    ExecutionResult,
    MarketSnapshot,
    OrderIntent,
    ResearchItem,
    RiskDecision,
    TradeProposal,
    idempotency_key_for,
)
from stellar.serialization import sha256_hex
from stellar.telemetry import StellarEvent

T0 = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
CONFIG_HASH = sha256_hex("test-config")


def provenance(agent: str, *inputs: str) -> dict[str, Any]:
    return {"produced_by": agent, "config_hash": CONFIG_HASH, "input_ids": list(inputs)}


def proposal_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "proposal_id": "prop_01",
        "run_id": "run_2026-09-29_XAUUSD_a1",
        "snapshot_id": "snap_01",
        "setup_id": "setup_01",
        "instrument": "XAUUSD",
        "profile": "profile_a",
        "direction": "SHORT",
        "source_rating": "Buy",
        "size_factor": "1",
        "entry": {"type": "limit", "price": "2400.00"},
        "stop_loss": {"price": "2412.00", "basis": "structure_high"},
        "take_profits": [{"price": "2376.00", "basis": "structure_low"}],
        "reward_risk": "2.0000",
        "valid_until": T0 + timedelta(hours=1),
        "created_at": T0,
        "provenance": provenance("trade_proposal_builder", "snap_01", "setup_01"),
    }
    data.update(overrides)
    return data


def make_proposal(**overrides: Any) -> TradeProposal:
    return TradeProposal.model_validate(proposal_data(**overrides))


def decision_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "decision_id": "dec_01",
        "proposal_id": "prop_01",
        "run_id": "run_2026-09-29_XAUUSD_a1",
        "instrument": "XAUUSD",
        "outcome": "APPROVED",
        "checks": [{"rule": "stop_loss_required", "passed": True}],
        "volume": "0.10",
        "risk_pct_equity": "0.004",
        "decided_at": T0 + timedelta(minutes=1),
        "provenance": provenance("risk_engine", "prop_01"),
    }
    data.update(overrides)
    return data


def make_decision(**overrides: Any) -> RiskDecision:
    return RiskDecision.model_validate(decision_data(**overrides))


def intent_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "intent_id": "int_01",
        "proposal_id": "prop_01",
        "decision_id": "dec_01",
        "account_mode": "PAPER",
        "instrument": "XAUUSD",
        "broker_symbol": "XAUUSD",
        "side": "SELL",
        "volume": "0.10",
        "order_type": "limit",
        "price": "2400.00",
        "stop_loss": "2412.00",
        "take_profit": "2376.00",
        "max_slippage": "0.50",
        "idempotency_key": idempotency_key_for("prop_01"),
        "expires_at": T0 + timedelta(minutes=30),
        "created_at": T0 + timedelta(minutes=2),
        "provenance": provenance("risk_engine", "prop_01", "dec_01"),
    }
    data.update(overrides)
    return data


def make_intent(**overrides: Any) -> OrderIntent:
    return OrderIntent.model_validate(intent_data(**overrides))


def result_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "order_id": "ord_01",
        "intent_id": "int_01",
        "instrument": "XAUUSD",
        "account_mode": "PAPER",
        "side": "SELL",
        "status": "filled",
        "requested_volume": "0.10",
        "filled_volume": "0.10",
        "fill_id": "fill_01",
        "fill_price": "2399.90",
        "slippage": "0.10",
        "ts": T0 + timedelta(minutes=3),
        "provenance": provenance("paper_execution", "int_01"),
    }
    data.update(overrides)
    return data


def make_result(**overrides: Any) -> ExecutionResult:
    return ExecutionResult.model_validate(result_data(**overrides))


def candle_data(hour: int, **overrides: Any) -> dict[str, Any]:
    data = {
        "instrument": "XAUUSD",
        "timeframe": "H1",
        "open_time": T0 - timedelta(hours=hour),
        "close_time": T0 - timedelta(hours=hour - 1),
        "open": "2401.00",
        "high": "2405.00",
        "low": "2398.00",
        "close": "2400.50",
        "volume": "1520",
        "volume_kind": "tick",
        "price_side": "bid",
        "source": "fixture",
        "provider_symbol": "XAUUSD",
        "is_closed": True,
    }
    data.update(overrides)
    return data


def make_series(*candles: dict[str, Any]) -> CandleSeries:
    built = [Candle.model_validate(c) for c in (candles or (candle_data(2), candle_data(1)))]
    return CandleSeries.build(built[0].timeframe, built)


def snapshot_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "snapshot_id": "snap_01",
        "instrument": "XAUUSD",
        "as_of": T0,
        "series": [make_series().model_dump()],
        "quote": {
            "instrument": "XAUUSD",
            "bid": "2400.40",
            "ask": "2400.70",
            "ts": T0 - timedelta(seconds=5),
            "source": "fixture",
            "provider_symbol": "XAUUSD",
        },
        "created_at": T0,
        "provenance": provenance("data_validator"),
    }
    data.update(overrides)
    return data


def make_snapshot(**overrides: Any) -> MarketSnapshot:
    return MarketSnapshot.model_validate(snapshot_data(**overrides))


def research_item_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "item_id": "ri_01",
        "role": "research_economic_data",
        "source_id": "owner_calendar_file",
        "source_ref": "calendar.csv row 12",
        "published_at": T0 - timedelta(hours=3),
        "retrieved_at": T0 - timedelta(hours=2),
        "affected": ["USD", "XAUUSD"],
        "excerpt": "US CPI release: actual versus prior.",
        "content_hash": sha256_hex("item"),
        "claims": [
            {"claim_id": "clm_01", "statement": "US CPI y/y actual", "value": "3.1",
             "unit": "percent", "period": "2026-08"},
        ],
    }
    data.update(overrides)
    return data


def make_research_item(**overrides: Any) -> ResearchItem:
    return ResearchItem.model_validate(research_item_data(**overrides))


def validation_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "validation_id": "val_01",
        "item_id": "ri_01",
        "claim_id": "clm_01",
        "label": "FACT",
        "label_confidence": "0.9",
        "checks": [
            {"validator": "source_validator", "outcome": "accepted"},
            {"validator": "freshness_checker", "outcome": "accepted"},
            {"validator": "duplicate_detector", "outcome": "accepted"},
            {"validator": "claim_classifier", "outcome": "accepted"},
        ],
        "status": "ACCEPTED",
        "validated_at": T0 - timedelta(hours=1),
        "provenance": provenance("claim_classifier", "ri_01", "clm_01"),
    }
    data.update(overrides)
    return data


def make_validation(**overrides: Any) -> ClaimValidation:
    return ClaimValidation.model_validate(validation_data(**overrides))


def analysis_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "analysis_id": "an_01",
        "kind": "macro",
        "research_snapshot_id": "rsnap_01",
        "as_of": T0,
        "created_at": T0 + timedelta(seconds=30),
        "coverage": {
            "contributed": ["research_central_bank", "research_economic_data"],
            "missing": ["research_rates_bonds"],
        },
        "cited_claim_ids": ["clm_01"],
        "excerpt": "Driver board summary.",
        "chars": 21,
        "sha256": sha256_hex("Driver board summary."),
        "provenance": provenance("causal_macro_analyst", "rsnap_01"),
    }
    data.update(overrides)
    return data


def make_analysis(**overrides: Any) -> AnalysisReport:
    return AnalysisReport.model_validate(analysis_data(**overrides))


ULIDS = [f"01J8Z6Q3T6V4Y1M2N3P4Q5R6{i:02d}" for i in range(10, 99)]


def event_data(n: int = 0, **overrides: Any) -> dict[str, Any]:
    data = {
        "event_id": ULIDS[n],
        "type": "agent.state.changed",
        "ts": T0 + timedelta(seconds=n),
        "station_id": "stellar-01",
        "source": "stellar.system",
        "agent_id": "supervisor",
        "payload": {"from": "IDLE", "to": "ASSIGNED", "reason": "schedule"},
    }
    data.update(overrides)
    return data


def make_event(n: int = 0, **overrides: Any) -> StellarEvent:
    return StellarEvent.model_validate(event_data(n, **overrides))
