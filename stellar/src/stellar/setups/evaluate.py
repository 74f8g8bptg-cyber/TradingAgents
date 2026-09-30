"""The deterministic Setup evaluator (T6 ``pullback_setup``; Foundation §4.11–4.12, §7.2).

It reads Phase 5 evidence and the Phase 6 decision support **as given**. It recomputes no
indicator, pivot, zone, leg or pullback measurement, and it calls no model.

**Inputs are point in time and intact.** The technical analysis must match its own content
hash (Phase 5 ``verify``). The technical analysis, the decision support and the optional
multi-timeframe analysis must be dated at or before ``as_of``, for the same instrument, and the
decision support must have reviewed exactly this technical analysis (id and content hash).
Otherwise ``SetupInputError`` is raised: nothing is evaluated on mismatched evidence. Only
CONFIRMED pivots reach legs and zones in Phase 5, and the evaluator also checks that every
pivot it cites is CONFIRMED by ``as_of``.

**Rules, in order** (the first that applies decides the status):
1. Structure INSUFFICIENT → INSUFFICIENT_EVIDENCE. RANGE or MIXED → NO_SETUP.
2. UP → LONG, DOWN → SHORT. The last completed leg must be a WITH_STRUCTURE leg in that
   direction, with a pullback against it (depth above zero). Otherwise → NO_SETUP. A count of
   red or green candles is never a rule: only Phase 5 legs and pullback measurements are.
3. A structure break against the state, or a pullback beyond the leg's start swing (the
   invalidation level) → INVALIDATED.
4. ``valid_until`` reached (when validity is configured) → EXPIRED.
5. Research that cannot support a setup (run FAILED, grade INSUFFICIENT, stance
   INSUFFICIENT_EVIDENCE) → INSUFFICIENT_EVIDENCE.
6. Disagreement (stance MIXED or opposite to the direction, a TECHNICAL_MACRO_DISAGREEMENT
   finding, a multi-timeframe alignment that disagrees or points the other way) →
   CONFLICTING_EVIDENCE. Disagreement is reported, never averaged.
7. Otherwise CANDIDATE, and READY_FOR_PROPOSAL only when all of these hold:
   - the research stance supports the direction;
   - the evidence grade is one of ``ready_evidence_grades``;
   - validity is configured;
   - the optional retracement bounds (if configured) hold;
   - there is at least one entry, one stop and one target option.
   Each unmet condition is a reason.

**Options** (every number sourced; see ``models``):
- *entry*: MARKET_AT_QUOTE (no price here: the quote is read at build time) and
  LIMIT_AT_ZONE for each supporting zone (SUPPORT/MIXED for LONG, RESISTANCE/MIXED for SHORT)
  lying strictly between the invalidation level and the leg's end swing;
- *stop*: STRUCTURE_STOP beyond the invalidation level (plus the configured buffer, if any),
  and ATR_STOP when ``atr_stop_multiple`` is set and ATR is ready;
- *target*: PRIOR_SWING_TARGET at the leg's end swing, and ZONE_TARGET at the near edge of
  each opposing zone beyond it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from stellar.marketdata.timeframes import DURATIONS
from stellar.pipeline.records import ChallengeKind, DecisionSupport, EvidenceGrade, RunStatus
from stellar.reasoning.contracts import Stance
from stellar.serialization import canonical_json, content_hash, sha256_hex
from stellar.setups.config import EntryModelKind, SetupConfig
from stellar.setups.models import (
    ROLE_FOR_KIND,
    STATE_FOR_STATUS,
    LevelOption,
    LevelRole,
    NumericSource,
    OptionKind,
    Setup,
    SetupDirection,
    SetupEvidence,
    SetupStatus,
    SetupType,
)
from stellar.technical import MultiTimeframeAnalysis, StructureState, TechnicalAnalysis
from stellar.technical.engine import verify
from stellar.technical.models import (
    LegDirection,
    LegRole,
    PivotStatus,
    PriceZone,
    StructureLeg,
    ZoneKind,
)
from stellar.technical.mtf import Alignment
from stellar.technical.numeric import calc

SUPPORTING = {SetupDirection.LONG: Stance.SUPPORTS_UPSIDE,
              SetupDirection.SHORT: Stance.SUPPORTS_DOWNSIDE}
AGREEING = {SetupDirection.LONG: Alignment.AGREE_UP, SetupDirection.SHORT: Alignment.AGREE_DOWN}
LEG_FOR = {SetupDirection.LONG: LegDirection.UP, SetupDirection.SHORT: LegDirection.DOWN}
ENTRY_ZONES = {SetupDirection.LONG: {ZoneKind.SUPPORT, ZoneKind.MIXED},
               SetupDirection.SHORT: {ZoneKind.RESISTANCE, ZoneKind.MIXED}}
TARGET_ZONES = {SetupDirection.LONG: {ZoneKind.RESISTANCE, ZoneKind.MIXED},
                SetupDirection.SHORT: {ZoneKind.SUPPORT, ZoneKind.MIXED}}


class SetupInputError(ValueError):
    """The inputs are not one consistent, point-in-time body of evidence."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _check_inputs(technical: TechnicalAnalysis, decision: DecisionSupport, as_of: datetime,
                  mtf: MultiTimeframeAnalysis | None) -> None:
    if as_of.tzinfo is None:
        raise SetupInputError("naive_as_of")
    if not verify(technical):
        raise SetupInputError("technical_hash_mismatch", technical.analysis_id)
    if decision.instrument != technical.instrument:
        raise SetupInputError("instrument_mismatch", "decision support vs technical analysis")
    if technical.as_of > as_of:
        raise SetupInputError("future_technical", technical.analysis_id)
    if decision.as_of > as_of:
        raise SetupInputError("future_research", decision.run_id)
    if not any(r.analysis_id == technical.analysis_id and r.content_hash == technical.content_hash
               for r in decision.technical):
        raise SetupInputError("technical_not_reviewed",
                              "the decision support did not review this technical analysis")
    if mtf is not None:
        if mtf.instrument != technical.instrument:
            raise SetupInputError("instrument_mismatch", "multi-timeframe analysis")
        if mtf.as_of > as_of:
            raise SetupInputError("future_technical", "multi-timeframe analysis")


def _exact(fn) -> Decimal:
    """Decimal arithmetic under the Phase 5 calculation context (no float, no ambient context)."""
    with calc():
        return fn()


def indicator_ref(analysis_id: str, name: str) -> str:
    return "ind_" + sha256_hex(f"{analysis_id}|{name}")[:16]


def _option(identity: str, kind: OptionKind, *, sources, evidence, basis: str,
            **values) -> LevelOption:
    body = {"identity": identity, "kind": kind.value, "evidence": list(evidence),
            **{k: str(v) for k, v in values.items() if v is not None}}
    return LevelOption(option_id="opt_" + sha256_hex(canonical_json(body))[:16], kind=kind,
                       role=ROLE_FOR_KIND[kind], sources=tuple(sources),
                       evidence_ids=tuple(evidence), basis=basis, **values)


class _Evaluation:
    def __init__(self, technical: TechnicalAnalysis, decision: DecisionSupport,
                 as_of: datetime, config: SetupConfig,
                 mtf: MultiTimeframeAnalysis | None) -> None:
        self.t, self.d, self.as_of, self.cfg, self.mtf = technical, decision, as_of, config, mtf
        self.reasons: list[str] = []
        self.unevaluated: list[str] = []
        self.pivots = {p.evidence_id: p for p in technical.pivots}

    def confirmed(self, pivot_id: str) -> bool:
        p = self.pivots.get(pivot_id)
        return p is not None and p.status is PivotStatus.CONFIRMED and \
            p.confirmed_at is not None and p.confirmed_at <= self.as_of

    # ------------------------------------------------------------------ options --

    def atr(self) -> Decimal | None:
        v = self.t.volatility
        atr = v.atr if v is not None else None
        if atr is None or not atr.ready or atr.value is None or atr.value <= 0:
            return None
        return atr.value

    def options(self, identity: str, direction: SetupDirection,
                leg: StructureLeg, invalidation: Decimal) -> list[LevelOption]:
        long = direction is SetupDirection.LONG
        out: list[LevelOption] = []
        atr = self.atr()
        atr_ref = indicator_ref(self.t.analysis_id, self.t.volatility.atr.name) \
            if atr is not None and self.t.volatility and self.t.volatility.atr else None
        zones = [z for z in self.t.zones if z.first_known_at <= self.as_of
                 and all(self.confirmed(p) for p in z.source_pivot_ids)]
        # entries
        for model in self.cfg.entry_models:
            if model is EntryModelKind.MARKET_AT_QUOTE:
                out.append(_option(identity, OptionKind.MARKET_AT_QUOTE,
                                   sources=(NumericSource.MARKET_QUOTE,), evidence=(),
                                   basis="market_at_quote"))
            elif model is EntryModelKind.LIMIT_AT_ZONE:
                for z in zones:
                    inside = (z.lower > invalidation and z.upper < leg.end_price) if long else \
                        (z.upper < invalidation and z.lower > leg.end_price)
                    if z.kind in ENTRY_ZONES[direction] and inside:
                        out.append(self._zone_entry(identity, z))
        if not self.cfg.entry_models:
            self.unevaluated.append("entry_models_unset")
        # stops
        buffer, buffer_sources, buffer_evidence = self._buffer(atr, atr_ref)
        if buffer is not None:
            stop = _exact(lambda: invalidation - buffer if long else invalidation + buffer)
            if stop > 0:
                out.append(_option(
                    identity, OptionKind.STRUCTURE_STOP, price=stop,
                    buffer=buffer if self.cfg.stop_buffer.configured else None,
                    sources=(NumericSource.PHASE5_PIVOT, *buffer_sources),
                    evidence=(leg.start_pivot_id, leg.evidence_id, *buffer_evidence),
                    basis=("structure_swing_low" if long else "structure_swing_high")
                    + ("_buffered" if self.cfg.stop_buffer.configured else "_no_buffer")))
        if self.cfg.atr_stop_multiple is not None:
            if atr is None:
                self.unevaluated.append("atr_stop_atr_not_ready")
            else:
                distance = _exact(lambda: self.cfg.atr_stop_multiple * atr)
                out.append(_option(identity, OptionKind.ATR_STOP, atr_distance=distance,
                                   sources=(NumericSource.PHASE5_ATR, NumericSource.SETUP_CONFIG),
                                   evidence=(atr_ref,), basis="atr_multiple_from_entry"))
        # targets
        seen: set[Decimal] = set()
        out.append(_option(identity, OptionKind.PRIOR_SWING_TARGET, price=leg.end_price,
                           sources=(NumericSource.PHASE5_PIVOT,),
                           evidence=(leg.end_pivot_id, leg.evidence_id),
                           basis="prior_swing_high" if long else "prior_swing_low"))
        seen.add(leg.end_price)
        beyond = sorted((z for z in zones if z.kind in TARGET_ZONES[direction]
                         and (z.lower > leg.end_price if long else z.upper < leg.end_price)),
                        key=lambda z: z.lower if long else -z.upper)
        for z in beyond:
            price = z.lower if long else z.upper
            if price in seen:
                continue
            seen.add(price)
            out.append(_option(identity, OptionKind.ZONE_TARGET, price=price,
                               sources=(NumericSource.PHASE5_ZONE,), evidence=(z.evidence_id,),
                               basis="opposing_zone_near_edge"))
        return out

    def _zone_entry(self, identity: str, z: PriceZone) -> LevelOption:
        if z.lower == z.upper:
            return _option(identity, OptionKind.LIMIT_AT_ZONE, price=z.lower,
                           sources=(NumericSource.PHASE5_ZONE,), evidence=(z.evidence_id,),
                           basis="zone_level")
        return _option(identity, OptionKind.LIMIT_AT_ZONE, zone_low=z.lower, zone_high=z.upper,
                       sources=(NumericSource.PHASE5_ZONE,), evidence=(z.evidence_id,),
                       basis="zone")

    def _buffer(self, atr, atr_ref):
        b = self.cfg.stop_buffer
        if b.price is not None:
            return b.price, (NumericSource.SETUP_CONFIG,), ()
        if b.atr_multiple is not None:
            if atr is None:
                self.unevaluated.append("stop_buffer_atr_not_ready")
                return None, (), ()
            return _exact(lambda: b.atr_multiple * atr), \
                (NumericSource.PHASE5_ATR, NumericSource.SETUP_CONFIG), (atr_ref,)
        return Decimal(0), (), ()

    # --------------------------------------------------------------------- rules --

    def research_blockers(self, direction: SetupDirection) -> SetupStatus | None:
        d = self.d
        insufficient = []
        if d.status is RunStatus.FAILED:
            insufficient.append("research_run_failed")
        if d.quality.grade is EvidenceGrade.INSUFFICIENT:
            insufficient.append("evidence_grade_insufficient")
        if d.final_stance is Stance.INSUFFICIENT_EVIDENCE:
            insufficient.append("research_stance_insufficient")
        if insufficient:
            self.reasons += insufficient
            return SetupStatus.INSUFFICIENT_EVIDENCE
        conflicts = []
        if d.final_stance is Stance.MIXED:
            conflicts.append("research_stance_mixed")
        opposite = SUPPORTING[SetupDirection.SHORT if direction is SetupDirection.LONG
                              else SetupDirection.LONG]
        if d.final_stance is opposite:
            conflicts.append("research_stance_opposes_direction")
        if ChallengeKind.TECHNICAL_MACRO_DISAGREEMENT in d.challenge.kinds():
            conflicts.append("technical_macro_disagreement")
        if self.mtf is not None and self.mtf.alignment in (
                Alignment.DISAGREE, AGREEING[SetupDirection.SHORT if direction is
                                             SetupDirection.LONG else SetupDirection.LONG]):
            conflicts.append(f"mtf_{self.mtf.alignment.value.lower()}")
        if conflicts:
            self.reasons += conflicts
            return SetupStatus.CONFLICTING_EVIDENCE
        return None

    def readiness(self, direction: SetupDirection, valid_until, options, pullback) -> None:
        cfg = self.cfg
        if self.d.final_stance is not SUPPORTING[direction]:
            self.reasons.append("research_does_not_support_direction")
        if not cfg.ready_evidence_grades:
            self.reasons.append("ready_evidence_grades_unset")
        elif self.d.quality.grade not in cfg.ready_evidence_grades:
            self.reasons.append("evidence_grade_not_ready")
        if valid_until is None:
            self.reasons.append("setup_validity_unset")
        ratio = pullback.retracement_ratio
        if cfg.min_retracement_ratio is None and cfg.max_retracement_ratio is None:
            self.unevaluated.append("retracement_bounds_unset")
        elif ratio is None:
            self.reasons.append("retracement_unmeasured")
        else:
            if cfg.min_retracement_ratio is not None and ratio < cfg.min_retracement_ratio:
                self.reasons.append("retracement_below_min")
            if cfg.max_retracement_ratio is not None and ratio > cfg.max_retracement_ratio:
                self.reasons.append("retracement_above_max")
        for role, reason in ((LevelRole.ENTRY, "no_entry_option"),
                             (LevelRole.STOP, "no_stop_option"),
                             (LevelRole.TARGET, "no_target_option")):
            if not any(o.role is role for o in options):
                self.reasons.append(reason)

    def run(self) -> Setup:
        t = self.t
        s = t.structure
        direction = {StructureState.UP: SetupDirection.LONG,
                     StructureState.DOWN: SetupDirection.SHORT}.get(s.state)
        leg = None
        pullback = t.pullback
        status: SetupStatus | None = None
        if s.state is StructureState.INSUFFICIENT:
            status, direction = SetupStatus.INSUFFICIENT_EVIDENCE, SetupDirection.NONE
            self.reasons.append("technical_structure_insufficient")
        elif direction is None:
            status, direction = SetupStatus.NO_SETUP, SetupDirection.NONE
            self.reasons.append(f"structure_{s.state.value.lower()}")
        else:
            leg = next((g for g in t.legs if pullback is not None
                        and g.evidence_id == pullback.reference_leg_id), None)
            if pullback is None or leg is None:
                status, reason = SetupStatus.NO_SETUP, "no_pullback"
            elif leg.direction is not LEG_FOR[direction] or \
                    leg.role is not LegRole.WITH_STRUCTURE:
                status, reason = SetupStatus.NO_SETUP, "last_leg_not_with_structure"
            elif not (self.confirmed(leg.start_pivot_id) and self.confirmed(leg.end_pivot_id)):
                status, reason = SetupStatus.NO_SETUP, "leg_pivot_unconfirmed"
            elif pullback.depth is None or pullback.depth <= 0:
                status, reason = SetupStatus.NO_SETUP, "no_retracement"
            else:
                reason = None
            if status is not None:
                self.reasons.append(reason)
                direction, leg = SetupDirection.NONE, None

        identity = content_hash({
            "instrument": t.instrument.value, "timeframe": t.timeframe.value,
            "type": SetupType.PULLBACK_CONTINUATION.value, "direction": direction.value,
            "leg": leg.evidence_id if leg else None,
            # Phase 5 pivot / leg ids name bar times and windows, not prices: bind the prices
            "leg_prices": [str(leg.start_price), str(leg.end_price)] if leg else None,
            "config": self.cfg.config_hash()})
        invalidation = valid_from = valid_until = None
        options: list[LevelOption] = []
        if leg is not None:
            invalidation, valid_from = leg.start_price, leg.confirmed_at
            if self.cfg.setup_validity_bars is not None:
                valid_until = valid_from + DURATIONS[t.timeframe] * self.cfg.setup_validity_bars
            else:
                self.unevaluated.append("setup_validity_unset")
            long = direction is SetupDirection.LONG
            beyond = pullback.max_adverse_price is not None and (
                pullback.max_adverse_price < invalidation if long
                else pullback.max_adverse_price > invalidation)
            if s.break_against_state:
                status = SetupStatus.INVALIDATED
                self.reasons.append("structure_break_against_state")
            elif beyond:
                status = SetupStatus.INVALIDATED
                self.reasons.append("invalidation_level_breached")
            elif valid_until is not None and self.as_of >= valid_until:
                status = SetupStatus.EXPIRED
                self.reasons.append("valid_until_reached")
            else:
                status = self.research_blockers(direction)
            if status is None:
                options = self.options(identity, direction, leg, invalidation)
                self.readiness(direction, valid_until, options, pullback)
                status = SetupStatus.CANDIDATE if self.reasons else \
                    SetupStatus.READY_FOR_PROPOSAL
        assert status is not None
        d = self.d
        body = {
            "setup_id": "setup_" + identity[:40], "instrument": t.instrument,
            "timeframe": t.timeframe, "setup_type": SetupType.PULLBACK_CONTINUATION,
            "direction": direction, "status": status, "state": STATE_FOR_STATUS[status],
            "as_of": self.as_of, "reasons": tuple(self.reasons),
            "limitations": tuple(sorted({x.value for x in t.limitations} | set(d.limitations))),
            "unevaluated": tuple(self.unevaluated),
            "reference_leg_id": leg.evidence_id if leg else None,
            "invalidation_level": invalidation,
            "invalidation_evidence_id": leg.start_pivot_id if leg else None,
            "valid_from": valid_from, "valid_until": valid_until, "options": tuple(options),
            "evidence": SetupEvidence(
                technical_analysis_id=t.analysis_id, technical_content_hash=t.content_hash,
                technical_as_of=t.as_of, run_id=d.run_id,
                research_snapshot_id=d.research_snapshot_id,
                decision_outputs_hash=d.outputs_hash, decision_as_of=d.as_of,
                decision_status=d.status, final_stance=d.final_stance,
                evidence_grade=d.quality.grade,
                challenge_kinds=tuple(sorted(d.challenge.kinds(), key=lambda k: k.value)),
                mtf_content_hash=self.mtf.content_hash if self.mtf else None,
                mtf_alignment=self.mtf.alignment if self.mtf else None),
            "config_hash": self.cfg.config_hash()}
        probe = Setup.model_validate({**body, "fingerprint": "0" * 64})
        fingerprint = content_hash(probe.model_dump(mode="json", exclude={"fingerprint"}))
        return probe.model_copy(update={"fingerprint": fingerprint})


def evaluate_setup(*, technical: TechnicalAnalysis, decision: DecisionSupport, as_of: datetime,
                   config: SetupConfig, mtf: MultiTimeframeAnalysis | None = None) -> Setup:
    """Evaluate one setup from Phase 5 and Phase 6 evidence. Pure and deterministic."""
    _check_inputs(technical, decision, as_of, mtf)
    return _Evaluation(technical, decision, as_of, config, mtf).run()


def verify_setup(setup: Setup) -> bool:
    """True when the setup's fingerprint matches its content."""
    return setup.fingerprint == content_hash(setup.model_dump(mode="json",
                                                              exclude={"fingerprint"}))
