"""Position-sizing infrastructure. No sizing *strategy* is chosen here.

Risk of a trade = volume × stop distance × value per price unit per lot, in the
account currency, divided by equity. Every factor must be an explicit input:
- stop distance: from the proposal's single entry price. An entry *zone* has no
  agreed sizing reference yet (see RK-4), so it is reported, not guessed;
- value per price unit per lot, lot step, min/max volume: broker- or
  owner-declared ``InstrumentRiskMetadata`` in the account currency (no currency
  conversion, no contract-size or pip-value default);
- equity: ``AccountRiskState``.

Volume comes from one of two explicit sources:
- ``requested_volume`` in the context (validated only), or
- the formula, when the owner's policy sets ``size_to_max_risk`` (Foundation
  §8.1 "sizing by formula"): equity × max risk × size factor / (distance × value),
  rounded **down** to the lot step, rejected below the minimum volume.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from stellar.risk.policy import ControlState, RiskPolicy
from stellar.risk.state import RiskContext
from stellar.schemas.common import Label, StellarModel


class SizingOutcome(StellarModel):
    ok: bool
    reason: Label
    missing_input: bool = False
    volume: Decimal | None = None
    stop_distance: Decimal | None = None
    risk_amount: Decimal | None = None
    risk_fraction: Decimal | None = None
    mode: Label | None = None


def _fail(reason: str, *, missing: bool = False, **known) -> SizingOutcome:
    return SizingOutcome(ok=False, reason=reason, missing_input=missing, **known)


def size_trade(ctx: RiskContext, policy: RiskPolicy) -> SizingOutcome:
    proposal = ctx.proposal
    if proposal.entry.price is None:
        return _fail("entry_zone_sizing_reference_undecided")
    distance = abs(proposal.entry.price - proposal.stop_loss.price)
    meta, account = ctx.metadata, ctx.account
    if meta is None:
        return _fail("missing_instrument_metadata", missing=True, stop_distance=distance)
    if meta.instrument != proposal.instrument:
        return _fail("instrument_metadata_mismatch", stop_distance=distance)
    if account is None:
        return _fail("missing_account_state", missing=True, stop_distance=distance)
    if meta.account_currency != account.currency:
        return _fail("account_currency_mismatch", stop_distance=distance)

    per_lot = distance * meta.value_per_price_unit_per_lot
    if ctx.requested_volume is not None:
        volume, mode = ctx.requested_volume, "requested"
        if volume % meta.lot_step != 0:
            return _fail("volume_not_multiple_of_lot_step", stop_distance=distance, volume=volume)
    elif policy.size_to_max_risk and policy.max_risk_per_trade.state is ControlState.ENABLED:
        budget = account.equity * policy.max_risk_per_trade.limit * proposal.size_factor
        steps = (budget / per_lot / meta.lot_step).to_integral_value(rounding=ROUND_FLOOR)
        volume, mode = steps * meta.lot_step, "formula"
    else:
        return _fail("missing_requested_volume", missing=True, stop_distance=distance)

    if volume < meta.min_volume:
        return _fail("below_min_volume", stop_distance=distance, volume=volume, mode=mode)
    if meta.max_volume is not None and volume > meta.max_volume:
        return _fail("above_broker_max_volume", stop_distance=distance, volume=volume, mode=mode)
    risk_amount = volume * per_lot
    return SizingOutcome(ok=True, reason="sized", volume=volume, stop_distance=distance,
                         risk_amount=risk_amount, risk_fraction=risk_amount / account.equity,
                         mode=mode)
