"""The deterministic rule catalogue. Each rule: ``(context, policy, sizing) → RuleResult``.

Rules never call a model or the network, never read the clock (time is
``context.as_of``), and never estimate a missing value. Statuses:

- PASS / NOT_APPLICABLE: does not block.
- FAIL: blocks; the decision is REJECTED.
- REVIEW: blocks; the decision is REVIEW (owner attention, never an order).
- NOT_CONFIGURED: never a pass. Blocks (REVIEW) when the control is UNSET; does
  not block when the owner explicitly DISABLED it.

A missing input yields FAIL or REVIEW according to ``policy.missing_input_outcome``
(default FAIL, Foundation §8.1 "missing input → reject").

Calendar-naive market-data signals (Phase 2 ``STALE``, ``GAP_DETECTED``,
``PARTIAL_SERIES``, freshness status) are recorded but are **never** risk
evidence here (Phase 2 doc §15.1): they cannot reject a trade or trip the breaker.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from pydantic import ValidationError

from stellar.marketdata import INSTRUMENTS, MappingKind
from stellar.risk.breaker import BreakerStatus
from stellar.risk.policy import ControlState, MissingInputOutcome, RiskPolicy
from stellar.risk.sizing import SizingOutcome
from stellar.risk.state import RiskContext
from stellar.schemas.common import Direction, FiniteDecimal, Label, StellarModel
from stellar.schemas.market import DataQualityFlag
from stellar.schemas.order import idempotency_key_for
from stellar.schemas.proposal import Rating, TradeProposal
from stellar.schemas.risk import CheckStatus, RiskCheck, RiskRule

CALENDAR_NAIVE_FLAGS = frozenset(
    {DataQualityFlag.STALE, DataQualityFlag.GAP_DETECTED, DataQualityFlag.PARTIAL_SERIES}
)


class RuleResult(StellarModel):
    check: Label
    rule: RiskRule
    status: CheckStatus
    reason: Label
    blocking: bool
    value: FiniteDecimal | None = None
    limit: FiniteDecimal | None = None
    unit: Label | None = None
    trips_breaker: bool = False

    def to_check(self) -> RiskCheck:
        return RiskCheck(rule=self.rule, passed=self.status in {CheckStatus.PASS,
                                                                CheckStatus.NOT_APPLICABLE},
                         value=self.value, limit=self.limit, status=self.status,
                         reason=self.reason, blocking=self.blocking)


Rule = Callable[[RiskContext, RiskPolicy, SizingOutcome], RuleResult]


def _r(check, rule, status, reason, *, blocking=None, **kw) -> RuleResult:
    if blocking is None:
        blocking = status in {CheckStatus.FAIL, CheckStatus.REVIEW}
    return RuleResult(check=check, rule=rule, status=status, reason=reason, blocking=blocking,
                      **kw)


def _pass(check, rule, reason="ok", **kw):
    return _r(check, rule, CheckStatus.PASS, reason, **kw)


def _fail(check, rule, reason, **kw):
    return _r(check, rule, CheckStatus.FAIL, reason, **kw)


def _review(check, rule, reason, **kw):
    return _r(check, rule, CheckStatus.REVIEW, reason, **kw)


def _na(check, rule, reason, **kw):
    return _r(check, rule, CheckStatus.NOT_APPLICABLE, reason, **kw)


def _unconfigured(check, rule, state: ControlState, reason="limit_not_configured", **kw):
    disabled = state is ControlState.DISABLED
    return _r(check, rule, CheckStatus.NOT_CONFIGURED,
              "disabled_by_policy" if disabled else reason, blocking=not disabled, **kw)


def _missing(check, rule, policy: RiskPolicy, what: str, **kw):
    status = (CheckStatus.FAIL if policy.missing_input_outcome is MissingInputOutcome.FAIL
              else CheckStatus.REVIEW)
    return _r(check, rule, status, f"missing_{what}", **kw)


# --------------------------------------------------------------- structural ---


def proposal_schema(ctx, policy, sizing):
    try:
        TradeProposal.model_validate(ctx.proposal.model_dump())
    except ValidationError:
        return _fail("proposal_schema", RiskRule.SCHEMA_INVALID, "proposal_invalid")
    return _pass("proposal_schema", RiskRule.SCHEMA_INVALID)


def instrument_supported(ctx, policy, sizing):
    instrument = ctx.proposal.instrument
    if instrument not in INSTRUMENTS or instrument not in ctx.enabled_instruments:
        return _fail("instrument_supported", RiskRule.INSTRUMENT_UNSUPPORTED,
                     "instrument_not_enabled")
    return _pass("instrument_supported", RiskRule.INSTRUMENT_UNSUPPORTED)


def proposal_time(ctx, policy, sizing):
    if ctx.proposal.created_at > ctx.as_of:
        return _fail("proposal_time", RiskRule.LOOK_AHEAD, "proposal_created_after_as_of")
    return _pass("proposal_time", RiskRule.LOOK_AHEAD)


def proposal_expiry(ctx, policy, sizing):
    if ctx.proposal.valid_until <= ctx.as_of:
        return _fail("proposal_expiry", RiskRule.PROPOSAL_EXPIRED, "proposal_expired")
    return _pass("proposal_expiry", RiskRule.PROPOSAL_EXPIRED)


def execution_mode(ctx, policy, sizing):
    mode = ctx.execution.mode
    if mode == "LIVE":
        return _fail("execution_mode", RiskRule.EXECUTION_MODE, "live_not_permitted")
    if mode == "DEMO":
        return _fail("execution_mode", RiskRule.EXECUTION_MODE, "demo_gate_closed")
    return _pass("execution_mode", RiskRule.EXECUTION_MODE, "paper")


def circuit_breaker(ctx, policy, sizing):
    if ctx.breaker.status is BreakerStatus.TRIPPED:
        return _fail("circuit_breaker", RiskRule.CIRCUIT_BREAKER, "breaker_tripped")
    return _pass("circuit_breaker", RiskRule.CIRCUIT_BREAKER, "breaker_armed")


def size_factor(ctx, policy, sizing):
    if ctx.proposal.source_rating is Rating.OVERWEIGHT and not policy.overweight_allowed:
        return _review("size_factor", RiskRule.SIZE_FACTOR, "overweight_size_factor_undecided_d9",
                       value=ctx.proposal.size_factor)
    return _pass("size_factor", RiskRule.SIZE_FACTOR, value=ctx.proposal.size_factor)


def stop_loss(ctx, policy, sizing):
    p = ctx.proposal
    stop = p.stop_loss.price
    q = ctx.quote.quote if ctx.quote is not None else None
    if q is not None and not q.proxy:
        long = p.direction is Direction.LONG
        if (long and stop >= q.bid) or (not long and stop <= q.ask):
            return _fail("stop_loss", RiskRule.STOP_LOSS_REQUIRED, "stop_through_current_market")
    meta = ctx.metadata
    if meta is not None and meta.min_stop_distance is not None:
        edges = [e for e in (p.entry.price, p.entry.zone_low, p.entry.zone_high) if e is not None]
        distance = min(abs(e - stop) for e in edges)
        if distance < meta.min_stop_distance:
            return _fail("stop_loss", RiskRule.STOP_LOSS_REQUIRED, "below_broker_stops_level",
                         value=distance, limit=meta.min_stop_distance, unit="price")
    return _pass("stop_loss", RiskRule.STOP_LOSS_REQUIRED, "present_correct_side")


def duplicate_order(ctx, policy, sizing):
    key = idempotency_key_for(ctx.proposal.proposal_id)
    keys = set(ctx.prior_idempotency_keys)
    keys |= {o.idempotency_key for o in ctx.pending_orders or ()}
    keys |= {p.idempotency_key for p in ctx.positions or () if p.idempotency_key}
    if key in keys:
        return _fail("duplicate_order", RiskRule.DUPLICATE_ORDER, "order_already_exists")
    return _pass("duplicate_order", RiskRule.DUPLICATE_ORDER)


def min_reward_risk(ctx, policy, sizing):
    # Reward:risk has no agreed measurement method (Phase 1 decision); not evaluable.
    return _r("min_reward_risk", RiskRule.MIN_REWARD_RISK, CheckStatus.NOT_CONFIGURED,
              "reward_risk_method_undecided", blocking=False)


# -------------------------------------------------------------- market data ---


def market_data_present(ctx, policy, sizing):
    if ctx.snapshot is None:
        return _missing("market_data_present", RiskRule.MARKET_DATA_UNAVAILABLE, policy,
                        "market_snapshot")
    return _pass("market_data_present", RiskRule.MARKET_DATA_UNAVAILABLE)


def market_data_consistent(ctx, policy, sizing):
    snap = ctx.snapshot
    if snap is None:
        return _na("market_data_consistent", RiskRule.MARKET_DATA_INVALID, "no_snapshot")
    if snap.instrument != ctx.proposal.instrument:
        return _fail("market_data_consistent", RiskRule.MARKET_DATA_INVALID,
                     "snapshot_instrument_mismatch")
    if snap.as_of > ctx.as_of or snap.last_bar_close_time > ctx.as_of:
        return _fail("market_data_consistent", RiskRule.LOOK_AHEAD, "snapshot_after_as_of")
    return _pass("market_data_consistent", RiskRule.MARKET_DATA_INVALID)


def market_data_source(ctx, policy, sizing):
    snap = ctx.snapshot
    if snap is None:
        return _na("market_data_source", RiskRule.PROXY_DATA, "no_snapshot")
    if snap.mapping.kind is not MappingKind.EXACT:
        if not policy.allow_proxy_market_data:
            return _fail("market_data_source", RiskRule.PROXY_DATA,
                         f"{snap.mapping.kind.value.lower()}_snapshot_not_authorised")
        return _pass("market_data_source", RiskRule.PROXY_DATA, "proxy_allowed_for_analysis_only")
    return _pass("market_data_source", RiskRule.PROXY_DATA, "exact_source")


def market_data_quality(ctx, policy, sizing):
    snap = ctx.snapshot
    if snap is None:
        return _na("market_data_quality", RiskRule.MARKET_DATA_INVALID, "no_snapshot")
    flags = set(snap.quality.flags)
    if DataQualityFlag.SOURCE_PRECISION_LOSS in flags:
        return _review("market_data_quality", RiskRule.MARKET_DATA_INVALID,
                       "source_precision_loss")
    if flags & CALENDAR_NAIVE_FLAGS or snap.freshness.status.value == "STALE":
        # Recorded, never used as evidence until session-aware validation exists (MD-2).
        return _na("market_data_quality", RiskRule.MARKET_DATA_INVALID,
                   "calendar_naive_signal_not_risk_evidence")
    return _pass("market_data_quality", RiskRule.MARKET_DATA_INVALID)


def quote_integrity(ctx, policy, sizing):
    qr = ctx.quote
    if qr is None:
        return _na("quote_integrity", RiskRule.MARKET_DATA_INVALID, "no_quote")
    if qr.instrument != ctx.proposal.instrument:
        return _fail("quote_integrity", RiskRule.MARKET_DATA_INVALID, "quote_instrument_mismatch")
    if qr.as_of > ctx.as_of or qr.quote.ts > ctx.as_of:
        return _fail("quote_integrity", RiskRule.LOOK_AHEAD, "quote_after_as_of")
    if qr.mapping.kind is not MappingKind.EXACT:
        return _fail("quote_integrity", RiskRule.PROXY_DATA, "proxy_quote_never_for_order_levels")
    return _pass("quote_integrity", RiskRule.MARKET_DATA_INVALID)


def max_spread(ctx, policy, sizing):
    control, instrument = policy.max_spread, ctx.proposal.instrument
    if control.state is not ControlState.ENABLED:
        return _unconfigured("max_spread", RiskRule.MAX_SPREAD, control.state)
    limit = control.limits.get(instrument)
    if limit is None:
        return _unconfigured("max_spread", RiskRule.MAX_SPREAD, ControlState.UNSET,
                             "limit_not_configured_for_instrument")
    if ctx.quote is None:
        return _missing("max_spread", RiskRule.MAX_SPREAD, policy, "quote", limit=limit,
                        unit="price")
    spread = ctx.quote.quote.ask - ctx.quote.quote.bid
    if spread > limit:
        return _fail("max_spread", RiskRule.MAX_SPREAD, "spread_above_limit", value=spread,
                     limit=limit, unit="price")
    return _pass("max_spread", RiskRule.MAX_SPREAD, value=spread, limit=limit, unit="price")


def quote_age(ctx, policy, sizing):
    control = policy.max_quote_age_seconds
    if control.state is not ControlState.ENABLED:
        return _unconfigured("quote_age", RiskRule.STALE_QUOTE, control.state)
    limit = Decimal(control.limit)
    if ctx.quote is None:
        return _missing("quote_age", RiskRule.STALE_QUOTE, policy, "quote", limit=limit,
                        unit="seconds")
    age = Decimal(int((ctx.as_of - ctx.quote.quote.ts).total_seconds()))
    if age > limit:
        # Objective age, but calendar-naive (a closed market also ages quotes): REVIEW, not FAIL.
        return _review("quote_age", RiskRule.STALE_QUOTE, "quote_age_exceeds_limit_calendar_naive",
                       value=age, limit=limit, unit="seconds")
    return _pass("quote_age", RiskRule.STALE_QUOTE, value=age, limit=limit, unit="seconds")


def slippage_tolerance(ctx, policy, sizing):
    control = policy.max_slippage
    if control.state is not ControlState.ENABLED:
        return _unconfigured("slippage_tolerance", RiskRule.SLIPPAGE_TOLERANCE, control.state)
    limit = control.limits.get(ctx.proposal.instrument)
    if limit is None:
        return _unconfigured("slippage_tolerance", RiskRule.SLIPPAGE_TOLERANCE,
                             ControlState.UNSET, "limit_not_configured_for_instrument")
    return _pass("slippage_tolerance", RiskRule.SLIPPAGE_TOLERANCE, "tolerance_configured",
                 limit=limit, unit="price")


# ------------------------------------------------------------------ sizing ---


def position_sizing(ctx, policy, sizing):
    if sizing.ok:
        return _pass("position_sizing", RiskRule.POSITION_SIZING, f"sized_{sizing.mode}",
                     value=sizing.volume, unit="lots")
    if sizing.missing_input:
        return _missing("position_sizing", RiskRule.POSITION_SIZING, policy,
                        sizing.reason.removeprefix("missing_"), value=sizing.volume, unit="lots")
    if sizing.reason == "entry_zone_sizing_reference_undecided":
        return _review("position_sizing", RiskRule.POSITION_SIZING, sizing.reason)
    return _fail("position_sizing", RiskRule.POSITION_SIZING, sizing.reason, value=sizing.volume,
                 unit="lots")


def max_risk_per_trade(ctx, policy, sizing):
    control = policy.max_risk_per_trade
    if control.state is not ControlState.ENABLED:
        return _unconfigured("max_risk_per_trade", RiskRule.MAX_RISK_PER_TRADE, control.state)
    if not sizing.ok:
        return _review("max_risk_per_trade", RiskRule.MAX_RISK_PER_TRADE, "risk_not_computable",
                       limit=control.limit, unit="fraction_of_equity")
    if sizing.risk_fraction > control.limit:
        return _fail("max_risk_per_trade", RiskRule.MAX_RISK_PER_TRADE, "risk_above_limit",
                     value=sizing.risk_fraction, limit=control.limit, unit="fraction_of_equity")
    return _pass("max_risk_per_trade", RiskRule.MAX_RISK_PER_TRADE, value=sizing.risk_fraction,
                 limit=control.limit, unit="fraction_of_equity")


def max_position_volume(ctx, policy, sizing):
    control = policy.max_position_volume
    if control.state is not ControlState.ENABLED:
        return _unconfigured("max_position_volume", RiskRule.MAX_POSITION_SIZE, control.state)
    limit = control.limits.get(ctx.proposal.instrument)
    if limit is None:
        return _unconfigured("max_position_volume", RiskRule.MAX_POSITION_SIZE,
                             ControlState.UNSET, "limit_not_configured_for_instrument")
    if not sizing.ok:
        return _review("max_position_volume", RiskRule.MAX_POSITION_SIZE, "volume_not_computable",
                       limit=limit, unit="lots")
    if sizing.volume > limit:
        return _fail("max_position_volume", RiskRule.MAX_POSITION_SIZE, "volume_above_limit",
                     value=sizing.volume, limit=limit, unit="lots")
    return _pass("max_position_volume", RiskRule.MAX_POSITION_SIZE, value=sizing.volume,
                 limit=limit, unit="lots")


# ------------------------------------------------------------ book / exposure ---


def _count_rule(check, rule, control, items, what, policy):
    if control.state is not ControlState.ENABLED:
        return _unconfigured(check, rule, control.state)
    limit = Decimal(control.limit)
    if items is None:
        return _missing(check, rule, policy, what, limit=limit, unit="count")
    count = Decimal(len(items))
    if count >= limit:
        return _fail(check, rule, f"{what}_at_limit", value=count, limit=limit, unit="count")
    return _pass(check, rule, value=count, limit=limit, unit="count")


def open_positions(ctx, policy, sizing):
    return _count_rule("open_positions", RiskRule.MAX_OPEN_POSITIONS, policy.max_open_positions,
                       ctx.positions, "open_positions", policy)


def pending_orders(ctx, policy, sizing):
    return _count_rule("pending_orders", RiskRule.MAX_PENDING_ORDERS, policy.max_pending_orders,
                       ctx.pending_orders, "pending_orders", policy)


def _open_risk(ctx, instruments) -> Decimal | None:
    """Known open risk in ``instruments`` (positions + pending), or None if any is unknown."""
    total = Decimal(0)
    for item in (*(ctx.positions or ()), *(ctx.pending_orders or ())):
        if item.instrument in instruments:
            if item.open_risk is None:
                return None
            total += item.open_risk
    return total


def _exposure_rule(check, rule, ctx, policy, sizing, control_state, limit, instruments):
    if ctx.positions is None or ctx.pending_orders is None:
        return _missing(check, rule, policy, "book_state", limit=limit,
                        unit="fraction_of_equity")
    if ctx.account is None:
        return _missing(check, rule, policy, "account_state", limit=limit,
                        unit="fraction_of_equity")
    existing = _open_risk(ctx, instruments)
    if existing is None:
        return _missing(check, rule, policy, "open_risk", limit=limit, unit="fraction_of_equity")
    if not sizing.ok:
        return _review(check, rule, "new_risk_not_computable", limit=limit,
                       unit="fraction_of_equity")
    fraction = (existing + sizing.risk_amount) / ctx.account.equity
    if fraction > limit:
        return _fail(check, rule, "exposure_above_limit", value=fraction, limit=limit,
                     unit="fraction_of_equity")
    return _pass(check, rule, value=fraction, limit=limit, unit="fraction_of_equity")


def instrument_exposure(ctx, policy, sizing):
    control = policy.max_instrument_exposure
    if control.state is not ControlState.ENABLED:
        return _unconfigured("instrument_exposure", RiskRule.MAX_INSTRUMENT_EXPOSURE,
                             control.state)
    return _exposure_rule("instrument_exposure", RiskRule.MAX_INSTRUMENT_EXPOSURE, ctx, policy,
                          sizing, control.state, control.limit, {ctx.proposal.instrument})


def correlated_exposure(ctx, policy, sizing):
    control = policy.correlated_exposure
    if control.state is not ControlState.ENABLED:
        return _unconfigured("correlated_exposure", RiskRule.CORRELATED_EXPOSURE, control.state)
    clusters = [set(c) for c in control.clusters if ctx.proposal.instrument in c]
    if not clusters:
        return _na("correlated_exposure", RiskRule.CORRELATED_EXPOSURE, "instrument_in_no_cluster")
    worst = None
    for cluster in clusters:
        result = _exposure_rule("correlated_exposure", RiskRule.CORRELATED_EXPOSURE, ctx, policy,
                                sizing, control.state, control.limit, cluster)
        if result.blocking:
            return result
        worst = result if worst is None or result.value > worst.value else worst
    return worst


def daily_loss(ctx, policy, sizing):
    control = policy.max_daily_loss
    if control.state is not ControlState.ENABLED:
        return _unconfigured("daily_loss", RiskRule.MAX_DAILY_LOSS, control.state)
    day = ctx.daily
    if day is None:
        return _missing("daily_loss", RiskRule.MAX_DAILY_LOSS, policy, "daily_state",
                        limit=control.limit, unit="fraction_of_equity")
    unrealised = day.unrealised_pnl
    if unrealised is None:
        if ctx.positions is None or ctx.positions:
            return _missing("daily_loss", RiskRule.MAX_DAILY_LOSS, policy, "unrealised_pnl",
                            limit=control.limit, unit="fraction_of_equity")
        unrealised = Decimal(0)  # known flat book
    loss = max(Decimal(0), -(day.realised_pnl + unrealised))
    fraction = loss / day.start_equity
    if fraction >= control.limit:
        return _fail("daily_loss", RiskRule.MAX_DAILY_LOSS, "daily_loss_limit_reached",
                     value=fraction, limit=control.limit, unit="fraction_of_equity",
                     trips_breaker=policy.trip.on_daily_loss_breach)
    return _pass("daily_loss", RiskRule.MAX_DAILY_LOSS, value=fraction, limit=control.limit,
                 unit="fraction_of_equity")


def drawdown(ctx, policy, sizing):
    control = policy.max_drawdown
    if control.state is not ControlState.ENABLED:
        return _unconfigured("drawdown", RiskRule.MAX_DRAWDOWN, control.state)
    account = ctx.account
    if account is None or account.peak_equity is None:
        return _missing("drawdown", RiskRule.MAX_DRAWDOWN, policy, "peak_equity",
                        limit=control.limit, unit="fraction_of_equity")
    fraction = (account.peak_equity - account.equity) / account.peak_equity
    if fraction >= control.limit:
        return _fail("drawdown", RiskRule.MAX_DRAWDOWN, "drawdown_limit_reached", value=fraction,
                     limit=control.limit, unit="fraction_of_equity",
                     trips_breaker=policy.trip.on_drawdown_breach)
    return _pass("drawdown", RiskRule.MAX_DRAWDOWN, value=fraction, limit=control.limit,
                 unit="fraction_of_equity")


# ---------------------------------------------------------- external restrictions ---


def cooldown(ctx, policy, sizing):
    control = policy.cooldowns
    if control.state is not ControlState.ENABLED:
        return _unconfigured("cooldown", RiskRule.COOLDOWN, control.state,
                             "cooldowns_not_configured")
    if ctx.cooldowns is None:
        return _missing("cooldown", RiskRule.COOLDOWN, policy, "cooldown_state")
    for c in ctx.cooldowns:
        if c.until > ctx.as_of and c.instrument in (None, ctx.proposal.instrument):
            return _fail("cooldown", RiskRule.COOLDOWN, "cooldown_active")
    return _pass("cooldown", RiskRule.COOLDOWN)


def event_restriction(ctx, policy, sizing):
    control = policy.event_restrictions
    if control.state is not ControlState.ENABLED:
        return _unconfigured("event_restriction", RiskRule.NEWS_RESTRICTION, control.state,
                             "event_restrictions_not_configured")
    er = ctx.event_restriction
    if er is None:
        # Foundation §8.1: calendar unavailable = unknown = reject.
        return _missing("event_restriction", RiskRule.NEWS_RESTRICTION, policy,
                        "event_restriction_state")
    if er.instrument != ctx.proposal.instrument:
        return _fail("event_restriction", RiskRule.NEWS_RESTRICTION,
                     "restriction_for_other_instrument")
    if er.evaluated_at > ctx.as_of:
        return _fail("event_restriction", RiskRule.LOOK_AHEAD, "restriction_after_as_of")
    if er.restricted:
        return _fail("event_restriction", RiskRule.NEWS_RESTRICTION, "event_window_active")
    return _pass("event_restriction", RiskRule.NEWS_RESTRICTION)


RULES: tuple[Rule, ...] = (
    # Fixed evaluation order (Foundation §8.2 rule 2): schema → proposal rules →
    # sizing → portfolio rules → pre-flight-style data checks.
    proposal_schema,
    instrument_supported,
    proposal_time,
    proposal_expiry,
    execution_mode,
    circuit_breaker,
    size_factor,
    stop_loss,
    duplicate_order,
    min_reward_risk,
    position_sizing,
    max_risk_per_trade,
    max_position_volume,
    open_positions,
    pending_orders,
    instrument_exposure,
    correlated_exposure,
    daily_loss,
    drawdown,
    cooldown,
    event_restriction,
    market_data_present,
    market_data_consistent,
    market_data_source,
    market_data_quality,
    quote_integrity,
    max_spread,
    quote_age,
    slippage_tolerance,
)
