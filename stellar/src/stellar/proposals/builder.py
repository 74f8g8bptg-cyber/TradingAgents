"""The deterministic Trade Proposal Builder (P1 ``trade_proposal_builder``; Foundation §4.13).

``build_proposal`` turns one READY_FOR_PROPOSAL setup, an explicit level selection, an explicit
approval rating and the current market snapshot into a typed ``TradeProposal``, or refuses
with a typed ``ProposalFailure``. It is pure: no model, no journal, no Risk Engine, no broker.
Journaling and the lifecycle are the caller's job (``stellar.trader.desk``).

**Refusals, in order:**
1. the setup is not READY_FOR_PROPOSAL, or the selection is for other evidence;
2. no approval (APPROVAL_REQUIRED); an approval for another setup or the other direction
   (APPROVAL_FOR_OTHER_SETUP / APPROVAL_DIRECTION_MISMATCH); Overweight
   (OVERWEIGHT_D9_UNRESOLVED: D-9's safe default is no trade); Hold, Underweight, Sell or
   REVIEW (RATING_DOES_NOT_APPROVE). Only Buy builds, at the schema's size factor 1 (a rating
   strength, not a position size);
3. no profile (PROFILE_NOT_CONFIGURED); a setup evaluated under another config
   (CONFIG_MISMATCH); ``valid_until`` missing or reached;
4. market data for another instrument, dated after ``created_at``, older than the setup's
   technical evidence, or STALE / NO_DATA;
5. an unknown option id or one used for the wrong role; no target;
6. entry: a market entry needs a quote (ask for LONG, bid for SHORT); a limit entry must not
   already be marketable against the current reference price (the quote side, or the latest
   bar close when there is no quote);
7. geometry: LONG stop < every entry price < every target; SHORT reversed. A zone entry is
   checked on both edges and is never collapsed to a midpoint.

**Direction (LONG and SHORT).** ``TradeProposal.direction`` is copied from the setup and from
nowhere else. ``source_rating`` is the approval strength (always Buy here) and carries no side:
- LONG setup + Buy → ``direction=LONG``; the Risk Engine's intent side is BUY
  (``SIDE_FOR_DIRECTION``);
- SHORT setup + Buy → ``direction=SHORT``; the Risk Engine's intent side is SELL
  (``SIDE_FOR_DIRECTION``), a Stellar order side, not the upstream "Sell" rating;
- the upstream Sell / Underweight ratings never build a proposal in either direction.

**Order type** follows from the entry option: MARKET_AT_QUOTE → ``market``;
LIMIT_AT_ZONE → ``limit`` (a price or a zone).

**Identity.** ``proposal_id`` is ``prop_`` + a hash of the setup fingerprint, the selection,
the approval, the market snapshot and quote, the config hash and ``created_at``. The same
inputs always give the same proposal; any change gives a different one. The proposal is a
frozen record.

**Not decided here:** reward:risk (``reward_risk`` stays None; the measurement method is
undecided), the Risk Engine's sizing of a zone (RK-4: REVIEW), the take-profit sent on an
order (RK-9), and advisory Trader levels parsed from text (not parsed: see the Phase 6b doc).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from stellar.marketdata.contracts import FreshnessStatus
from stellar.marketdata.snapshot import VerifiedMarketSnapshot
from stellar.proposals.models import (
    Approval,
    LevelSelection,
    ProposalFailure,
    ProposalOutcome,
    ProposalStatus,
)
from stellar.schemas.common import Direction, Label, Provenance, StellarModel
from stellar.schemas.proposal import (
    Contradiction,
    EntrySpec,
    EntryType,
    PriceLevel,
    Rating,
    TradeProposal,
)
from stellar.serialization import content_hash
from stellar.setups.config import ORDER_TYPE_FOR_ENTRY, SetupConfig
from stellar.setups.models import (
    ENTRY_MODEL_FOR_KIND,
    LevelOption,
    LevelRole,
    OptionKind,
    Setup,
    SetupStatus,
)
from stellar.technical.numeric import calc

PRODUCER = "trade_proposal_builder"


class _Refused(Exception):
    def __init__(self, failure: ProposalFailure, detail: str | None = None) -> None:
        self.failure = failure
        self.detail = detail
        super().__init__(failure.value)


class ResolvedLevels(StellarModel):
    entry: EntrySpec
    stop: PriceLevel
    targets: tuple[PriceLevel, ...]
    reference_price: Decimal
    reference_basis: Label


def _refuse(setup: Setup, failure: ProposalFailure, detail: str | None = None) -> ProposalOutcome:
    return ProposalOutcome(status=ProposalStatus.REFUSED, failure=failure, detail=detail,
                           setup_id=setup.setup_id, setup_fingerprint=setup.fingerprint)


def _option(setup: Setup, option_id: str, role: LevelRole) -> LevelOption:
    option = setup.option(option_id)
    if option is None:
        raise _Refused(ProposalFailure.UNKNOWN_OPTION, option_id)
    if option.role is not role:
        raise _Refused(ProposalFailure.OPTION_ROLE_MISMATCH, option_id)
    return option


def _reference(market: VerifiedMarketSnapshot, direction: Direction) -> tuple[Decimal, str]:
    quote = market.latest_quote
    if quote is not None:
        return (quote.ask, "quote_ask") if direction is Direction.LONG else (quote.bid,
                                                                           "quote_bid")
    return market.latest_bar.close, "latest_bar_close"


def resolve_levels(setup: Setup, selection: LevelSelection,
                   market: VerifiedMarketSnapshot) -> ResolvedLevels:
    """Turn the selected options into typed levels and check their geometry."""
    direction = setup.direction.trade_direction()
    assert direction is not None
    long = direction is Direction.LONG
    entry_opt = _option(setup, selection.entry_option_id, LevelRole.ENTRY)
    stop_opt = _option(setup, selection.stop_option_id, LevelRole.STOP)
    if not selection.target_option_ids:
        raise _Refused(ProposalFailure.MISSING_TARGET)
    target_opts = [_option(setup, t, LevelRole.TARGET) for t in selection.target_option_ids]
    reference, basis = _reference(market, direction)

    model = ENTRY_MODEL_FOR_KIND[entry_opt.kind]
    order_type = EntryType(ORDER_TYPE_FOR_ENTRY[model])
    if entry_opt.kind is OptionKind.MARKET_AT_QUOTE:
        if market.latest_quote is None:
            raise _Refused(ProposalFailure.NO_QUOTE)
        entry = EntrySpec(type=order_type, price=reference)
    else:
        if entry_opt.price is not None:
            entry = EntrySpec(type=order_type, price=entry_opt.price)
        elif entry_opt.zone_low is not None and entry_opt.zone_high is not None:
            entry = EntrySpec(type=order_type, zone_low=entry_opt.zone_low,
                              zone_high=entry_opt.zone_high)
        else:  # pragma: no cover - LevelOption validation guarantees a price or a zone
            raise _Refused(ProposalFailure.ENTRY_UNRESOLVED)
        low, high = entry.bounds()
        if (long and not high < reference) or (not long and not low > reference):
            raise _Refused(ProposalFailure.LIMIT_WOULD_BE_MARKETABLE,
                           f"entry vs {basis} {reference}")
    low, high = entry.bounds()

    if stop_opt.kind is OptionKind.ATR_STOP:
        assert stop_opt.atr_distance is not None
        with calc():
            stop_price = low - stop_opt.atr_distance if long else high + stop_opt.atr_distance
    else:
        assert stop_opt.price is not None
        stop_price = stop_opt.price
    if stop_price <= 0 or (long and not stop_price < low) or (not long and not stop_price > high):
        raise _Refused(ProposalFailure.INVALID_STOP_GEOMETRY,
                       f"stop {stop_price} vs entry {low}-{high}")

    prices = []
    for t in target_opts:
        assert t.price is not None
        if (long and not t.price > high) or (not long and not t.price < low):
            raise _Refused(ProposalFailure.INVALID_TARGET_GEOMETRY,
                           f"target {t.price} vs entry {low}-{high}")
        prices.append((t.price, t.basis))
    if len({p for p, _ in prices}) != len(prices):
        raise _Refused(ProposalFailure.INVALID_TARGET_GEOMETRY, "duplicate target price")
    prices.sort(key=lambda x: x[0], reverse=not long)
    return ResolvedLevels(entry=entry, stop=PriceLevel(price=stop_price, basis=stop_opt.basis),
                          targets=tuple(PriceLevel(price=p, basis=b) for p, b in prices),
                          reference_price=reference, reference_basis=basis)


def proposal_identity(setup: Setup, selection: LevelSelection, approval: Approval,
                      market: VerifiedMarketSnapshot, config: SetupConfig,
                      created_at: datetime) -> str:
    return content_hash({
        "setup": setup.fingerprint, "selection": selection.model_dump(mode="json"),
        "approval": approval.model_dump(mode="json"), "market": market.snapshot_id,
        "series": market.series_hash,
        "quote": market.latest_quote.model_dump(mode="json") if market.latest_quote else None,
        "config": config.config_hash(), "created_at": created_at.isoformat()})


def build_proposal(*, setup: Setup, selection: LevelSelection | None,
                   approval: Approval | None, market: VerifiedMarketSnapshot,
                   config: SetupConfig, created_at: datetime) -> ProposalOutcome:
    if setup.status is not SetupStatus.READY_FOR_PROPOSAL:
        return _refuse(setup, ProposalFailure.SETUP_NOT_READY, setup.status.value)
    if selection is None:
        return _refuse(setup, ProposalFailure.SELECTION_REQUIRED)
    if selection.setup_id != setup.setup_id or selection.setup_fingerprint != setup.fingerprint:
        return _refuse(setup, ProposalFailure.SELECTION_FOR_OTHER_EVIDENCE)
    if approval is None:
        return _refuse(setup, ProposalFailure.APPROVAL_REQUIRED)
    if approval.setup_id != setup.setup_id:
        return _refuse(setup, ProposalFailure.APPROVAL_FOR_OTHER_SETUP)
    if approval.direction is not setup.direction.trade_direction():
        return _refuse(setup, ProposalFailure.APPROVAL_DIRECTION_MISMATCH,
                       f"{approval.direction.value} approval for a {setup.direction.value} setup")
    if approval.rating is Rating.OVERWEIGHT:
        return _refuse(setup, ProposalFailure.OVERWEIGHT_D9_UNRESOLVED)
    if approval.rating is not Rating.BUY:
        return _refuse(setup, ProposalFailure.RATING_DOES_NOT_APPROVE, approval.rating.value)
    if config.profile is None:
        return _refuse(setup, ProposalFailure.PROFILE_NOT_CONFIGURED)
    if setup.config_hash != config.config_hash():
        return _refuse(setup, ProposalFailure.CONFIG_MISMATCH)
    if created_at.tzinfo is None or created_at < setup.as_of:
        return _refuse(setup, ProposalFailure.CREATED_BEFORE_SETUP)
    if setup.valid_until is None:  # pragma: no cover - READY_FOR_PROPOSAL requires it
        return _refuse(setup, ProposalFailure.EXPIRY_NOT_CONFIGURED)
    if created_at >= setup.valid_until:
        return _refuse(setup, ProposalFailure.SETUP_EXPIRED)
    if market.instrument != setup.instrument:
        return _refuse(setup, ProposalFailure.MARKET_DATA_MISMATCH)
    if market.as_of > created_at:
        return _refuse(setup, ProposalFailure.FUTURE_MARKET_DATA)
    if market.as_of < setup.evidence.technical_as_of:
        return _refuse(setup, ProposalFailure.MARKET_DATA_OLDER_THAN_EVIDENCE)
    if market.freshness.status in (FreshnessStatus.STALE, FreshnessStatus.NO_DATA):
        return _refuse(setup, ProposalFailure.MARKET_DATA_STALE,
                       market.freshness.status.value)
    try:
        levels = resolve_levels(setup, selection, market)
    except _Refused as refused:
        return _refuse(setup, refused.failure, refused.detail)

    direction = setup.direction.trade_direction()
    ev = setup.evidence
    identity = proposal_identity(setup, selection, approval, market, config, created_at)
    hashes = {ev.decision_outputs_hash, ev.technical_content_hash, setup.fingerprint}
    if ev.mtf_content_hash:
        hashes.add(ev.mtf_content_hash)
    inputs = [setup.setup_id, ev.run_id, ev.research_snapshot_id, market.snapshot_id,
              ev.technical_analysis_id]
    try:
        proposal = TradeProposal(
            proposal_id="prop_" + identity[:40], run_id=ev.run_id,
            snapshot_id=market.snapshot_id, setup_id=setup.setup_id,
            instrument=setup.instrument, profile=config.profile, direction=direction,
            source_rating=approval.rating, size_factor=Decimal(1), entry=levels.entry,
            stop_loss=levels.stop, take_profits=levels.targets, reward_risk=None,
            valid_until=setup.valid_until, llm_levels_advisory=None,
            contradictions=tuple(Contradiction(code=k.value.lower()) for k in ev.challenge_kinds),
            report_hashes=tuple(sorted(hashes)), created_at=created_at,
            provenance=Provenance(produced_by=PRODUCER, config_hash=config.config_hash(),
                                  input_ids=tuple(dict.fromkeys(inputs))))
    except ValidationError as exc:  # defence in depth: the schema has the last word
        return _refuse(setup, ProposalFailure.PROPOSAL_SCHEMA_REJECTED,
                       str(exc.errors()[0]["msg"])[:200])
    return ProposalOutcome(status=ProposalStatus.BUILT, proposal=proposal,
                           proposal_hash=content_hash(proposal.model_dump(mode="json")),
                           setup_id=setup.setup_id, setup_fingerprint=setup.fingerprint,
                           reference_price=levels.reference_price,
                           reference_basis=levels.reference_basis)


def load_proposal(data: dict) -> TradeProposal:
    """Re-validate a journaled proposal (for example from ``trade.proposed``). Builds nothing
    new: the record must pass the full schema again, including ``produced_by``."""
    return TradeProposal.model_validate(data)
