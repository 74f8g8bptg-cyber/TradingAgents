# Stellar Agents — Foundation Phase 3: Deterministic Risk Engine

| | |
|---|---|
| **Status** | Phase 3 implemented; not yet committed |
| **Implements** | Foundation Plan §8 (hard risk foundation), §4.14 (OrderIntent built by the Risk Engine only), §4.27 (circuit breaker), §8.3 (owner-only reset), §8.4 (no LLM bypass) and §11.2 Phase 3, within the owner's Phase 3 brief |
| **Builds on** | Phase 1 contracts (`TradeProposal`, `RiskDecision`, `CircuitBreakerState`, `OrderIntent`, chain validation, events, journal); Phase 2 market data (`VerifiedMarketSnapshot`, `QuoteResponse`) |
| **Does not include** | Paper Broker, order execution, MT5 or Vantage, live trading, broker credentials, strategy, indicators, price action, Research Lab runtime, news or macro feeds, visual world |

---

## 1. Architecture

```
TradeProposal ─┐
RiskContext  ──┼─> RiskEngine(policy).evaluate(context) ──> RiskEvaluation
RiskPolicy   ──┘        29 deterministic rules, fixed order     ├─ RiskDecision  APPROVED / REJECTED / REVIEW
                        one precedence                          ├─ every rule result (status, reason, value, limit)
                                                                ├─ full context + policy (replayable)
                                                                └─ proposed breaker trip (systemic rules only)

RiskService: breaker state from the journal · idempotency per evaluation fingerprint · canonical events
RiskService.authorize_intent: OrderIntent only from the current APPROVED PAPER evaluation  →  (future) Execution Checker / Paper Broker
stellar.owner: the only way to reset a tripped breaker (interactive, typed confirmation, reason)
```

- **Deterministic:**
  - time is `context.as_of`;
  - the decision id is derived from the evaluation fingerprint (engine version, policy hash,
    context hash; §11);
  - no rule reads a clock, calls a model or touches the network, and a test blocks socket access.
- **The engine never asks an LLM anything.** LLM agents cannot reach it, and a boundary test
  forbids LLM or network imports in `stellar.risk`.

### Package layout

```
stellar/src/stellar/risk/
  breaker.py    (Phase 1) CircuitBreakerState, BreakerTrip, OwnerReset (record only)
  policy.py     RiskPolicy and its controls (UNSET / DISABLED / ENABLED), TripPolicy
  state.py      RiskContext, AccountRiskState, DailyRiskState, PositionState, PendingOrderState,
                CooldownState, EventRestrictionState, InstrumentRiskMetadata, ExecutionModeInput
  sizing.py     size_trade (explicit inputs only)
  rules.py      RuleResult and the 29-rule catalogue RULES
  engine.py     RiskEngine, RiskEvaluation, evaluation_fingerprint, decide (precedence),
                InvalidRiskInput, PolicyRejected
  ledger.py     BreakerLedger: breaker state replayed from the journal; trip (sticky); no reset
  service.py    RiskService: journal-backed breaker, fingerprint idempotency, evaluation
                history, events, authorize_intent (current authorisation)
  intents.py    IntentRefused, ReevaluationRequired and the internal structural intent builder
                (APPROVED + PAPER + configured slippage only); no public builder
stellar/src/stellar/owner/
  breaker_reset.py  owner_reset_breaker (the only writer of circuit_breaker.reset)
  __main__.py       python -m stellar.owner reset-breaker --journal PATH --station-id ID
```

### Changes to existing Stellar code (additive)

| File | Change |
|---|---|
| `schemas/risk.py` | `RiskCheck` gains optional `status` (`CheckStatus`: PASS / FAIL / REVIEW / NOT_APPLICABLE / NOT_CONFIGURED), `reason` (label) and `blocking`. With a status, `passed` is true only for PASS / NOT_APPLICABLE, so NOT_CONFIGURED is never a pass. `RiskDecision` aggregates blocking checks: a blocking FAIL forces REJECTED, and REJECTED needs a FAIL. Ten new `RiskRule` reason codes. Phase 1 checks and decisions without status remain valid |
| `telemetry/catalogue.py` | Adds `risk.review.requested` (payload `proposal_id`, `decision_id`, `reasons`): the REVIEW outcome had no event in the catalogue |
| `telemetry/bus.py` | Bug fix: importing `stellar.journal` before `stellar.telemetry` hit a circular import (latent since Phase 1). The bus now binds the journal module and resolves its names at call time. A regression test imports every package on its own |
| `config/models.py` | `IMPLEMENTED_FEATURES` adds `RISK_ENGINE`. `trading_permitted()` is still always false |
| `risk/__init__.py` | Exports the Phase 3 API |
| Tests | Phase 2's gate test now expects `{MARKET_DATA, RISK_ENGINE}`; the no-prose allowlist accepts `RiskCheck.reason` (a pattern-checked label); new boundary tests |

---

## 2. Contracts

### RiskContext

Everything one evaluation may use. `None` always means **unknown**; an empty tuple means **known
to be none**.

| Field | Meaning |
|---|---|
| `as_of` | Decision time; every input must be at or before it |
| `proposal` | The `TradeProposal` |
| `execution` | `ExecutionModeInput(mode=PAPER / DEMO / LIVE, demo_gate_open=False)`. LIVE and DEMO are representable, so the *rule* refuses them, not only the config loader |
| `breaker` | `CircuitBreakerState`. The service replaces it with the journal's |
| `account` | `AccountRiskState` (currency, equity, balance, peak equity, source) |
| `daily` | `DailyRiskState` (trading day, start equity, realised and unrealised P&L) |
| `positions`, `pending_orders` | `PositionState` / `PendingOrderState` (with `open_risk` in the account currency if known, and the idempotency key) |
| `snapshot`, `quote` | Phase 2 `VerifiedMarketSnapshot` / `QuoteResponse` |
| `metadata` | `InstrumentRiskMetadata`: value per 1.0 price move per lot (account currency), lot step, min/max volume, broker stops level. Never defaulted |
| `requested_volume` | An explicit volume to validate |
| `cooldowns`, `event_restriction` | Externally produced states (hooks for later phases) |
| `enabled_instruments` | Instruments the station trades |
| `prior_idempotency_keys` | Keys of orders already created |

**Every state names its `source`** (`broker`, `paper_broker`, `owner`, `journal` or
`test_fixture`). No contract size, pip value, leverage, margin formula or currency conversion is
assumed.

### RiskEvaluation

Contains:
- the engine version, `as_of`, the **policy** and its hash, and the **context** and its hash;
- the **fingerprint** (§11) and the proposal hash;
- every `RuleResult` (check id, rule code, status, reason code, value, limit, unit, blocking,
  `trips_breaker`);
- the `RiskDecision`, the breaker status at evaluation, and the proposed `BreakerTrip`.

**Its validator refuses:**
- a record whose hashes or fingerprint do not match, or whose decision id is not derived from its
  fingerprint;
- a decision about another proposal;
- an outcome that does not follow the precedence.

---

## 3. Policy and configuration

`RiskPolicy` is versioned (`version` label), hashed and immutable. **No numeric threshold is
chosen anywhere in the code.**

| Control state | Rule status | Blocks approval? |
|---|---|---|
| `UNSET` (default) | NOT_CONFIGURED, reason `limit_not_configured` | **Yes**. The outcome is REVIEW: configuration is incomplete, so the engine fails closed (Foundation §4.26) |
| `DISABLED` (explicit owner choice) | NOT_CONFIGURED, reason `disabled_by_policy` | No, but it is still recorded as not configured, never as passed |
| `ENABLED` + limit | PASS / FAIL / REVIEW against the limit | as evaluated |

**Mandatory controls.** `max_risk_per_trade`, `max_daily_loss` and `max_drawdown` may be UNSET
(blocking) but never DISABLED.

**Controls and units:**
- **Fractions of equity:** `max_risk_per_trade`, `max_instrument_exposure`, `max_daily_loss`,
  `max_drawdown`, and `correlated_exposure` (with owner-defined instrument clusters; no correlation
  coefficient is computed or assumed).
- **Counts:** `max_open_positions`, `max_pending_orders`.
- **Seconds:** `max_quote_age_seconds`.
- **Per instrument, in price units:** `max_spread`, `max_slippage`.
- **Per instrument, in lots:** `max_position_volume`.
- **Switches:** `cooldowns`, `event_restrictions`.

**Other settings:**
- `missing_input_outcome`: FAIL by default, per Foundation §8.1 "missing input → reject"; REVIEW is
  optional.
- `allow_proxy_market_data`: False.
- `overweight_allowed`: False (D-9).
- `size_to_max_risk`: False.
- `trip` (`TripPolicy`): which systemic breaches also trip the breaker.

**Test-only policies.** A policy marked `test_only=True` is refused by `RiskEngine` unless a test
passes `allow_test_policy=True` (Foundation Phase 3: "test-only limit values are labelled as such
and never used as defaults"). The test suite's `TEST_POLICY` is such a policy.

**Loading.** `load_risk_policy(data)` validates plain data, such as a TOML table. The policy is not
yet a section of `StellarConfig` (RK-1).

---

## 4. Rule model and catalogue

A rule is `(context, policy, sizing) → RuleResult`. Rules run in a fixed order (Foundation §8.2
rule 2): schema, then proposal rules, then sizing, then portfolio rules, then data checks. Every
result is recorded and journaled.

| # | Check | Rule code | What it does |
|---|---|---|---|
| 1 | `proposal_schema` | `schema_invalid` | Re-validates the proposal (malformed input never reaches the rules, §2) |
| 2 | `instrument_supported` | `instrument_unsupported` | Canonical and enabled instrument |
| 3 | `proposal_time` | `look_ahead` | Proposal not created after `as_of` |
| 4 | `proposal_expiry` | `proposal_expired` | `valid_until > as_of` |
| 5 | `execution_mode` | `execution_mode` | PAPER passes; **LIVE → FAIL** `live_not_permitted`; **DEMO → FAIL** `demo_gate_closed` |
| 6 | `circuit_breaker` | `circuit_breaker` | **TRIPPED → FAIL** |
| 7 | `size_factor` | `size_factor` | Overweight → REVIEW (`overweight_size_factor_undecided_d9`) unless the policy allows it |
| 8 | `stop_loss` | `stop_loss_required` | Stop present and on the correct side (schema); FAIL if the stop is already through the current exact quote; FAIL if closer than a declared broker stops level |
| 9 | `duplicate_order` | `duplicate_order` | FAIL if the proposal's idempotency key is among created orders, pending orders or positions |
| 10 | `min_reward_risk` | `min_reward_risk` | Always NOT_CONFIGURED, non-blocking: `reward_risk_method_undecided` (reward:risk is provisional; Phase 1 decision) |
| 11 | `position_sizing` | `position_sizing` | §8 |
| 12 | `max_risk_per_trade` | `max_risk_per_trade` | risk fraction > limit → FAIL |
| 13 | `max_position_volume` | `max_position_size` | volume > per-instrument limit → FAIL |
| 14 | `open_positions` | `max_open_positions` | count ≥ limit → FAIL |
| 15 | `pending_orders` | `max_pending_orders` | count ≥ limit → FAIL |
| 16 | `instrument_exposure` | `max_instrument_exposure` | (open risk in the instrument + new risk) / equity > limit → FAIL |
| 17 | `correlated_exposure` | `correlated_exposure` | same, summed over each configured cluster containing the instrument |
| 18 | `daily_loss` | `max_daily_loss` | loss (realised + unrealised) / start equity ≥ limit → FAIL; **may trip the breaker** |
| 19 | `drawdown` | `max_drawdown` | (peak − equity) / peak ≥ limit → FAIL; **may trip the breaker** |
| 20 | `cooldown` | `cooldown` | an active cooldown for the instrument (or all) → FAIL |
| 21 | `event_restriction` | `news_restriction` | a validated external restriction: restricted → FAIL; unknown → missing input (Foundation §8.1 "calendar unavailable = unknown = reject") |
| 22 | `market_data_present` | `market_data_unavailable` | a verified snapshot is required |
| 23 | `market_data_consistent` | `market_data_invalid` / `look_ahead` | same instrument; nothing after `as_of` |
| 24 | `market_data_source` | `proxy_data` | proxy/derived snapshot → FAIL unless authorised (then analysis only) |
| 25 | `market_data_quality` | `market_data_invalid` | precision loss → REVIEW; calendar-naive flags → NOT_APPLICABLE (§7) |
| 26 | `quote_integrity` | `market_data_invalid` / `look_ahead` / `proxy_data` | same instrument; not after `as_of`; **a proxy quote is never used** (Foundation L2) |
| 27 | `max_spread` | `max_spread` | ask − bid > limit → FAIL; no quote → missing input |
| 28 | `quote_age` | `stale_quote` | quote older than the limit → **REVIEW** (§7) |
| 29 | `slippage_tolerance` | `slippage_tolerance` | a configured tolerance is required (it becomes `OrderIntent.max_slippage`) |

**Missing inputs.** A missing required input yields FAIL (default) or REVIEW, per policy, with a
reason code `missing_<input>`. It is never a pass.

**Boundary conventions** (not thresholds; documented so they are not mistaken for choices of
value):
- risk, volume, exposure and spread fail when **above** the limit;
- loss and drawdown fail when **at or above** it;
- counts fail when **at** the limit, since one more would exceed it.

---

## 5. Decision precedence

```
any blocking FAIL                                → REJECTED
else any blocking REVIEW or blocking NOT_CONFIGURED → REVIEW
else                                             → APPROVED   (needs a computed volume and risk %)
```

- This follows the Phase 1 semantics: REVIEW means no approval plus an owner flag, and never leads
  to an order.
- `decide()` is tested exhaustively over every combination of up to three results of all six
  status/blocking kinds.
- `RiskDecision` and `RiskEvaluation` validators refuse outcomes that do not follow this precedence.

---

## 6. Circuit breaker integration

**Blocking and persistence:**
- **TRIPPED always blocks.** Rule 6 fails; the service also replaces the context's breaker with
  the journal's, so a caller cannot pass in an ARMED breaker.
- **Persistence is the journal.** `BreakerLedger` replays `circuit_breaker.tripped` and
  `circuit_breaker.reset` events. A restart reconstructs the same state, so restarting never
  re-arms the breaker and never implies an owner approval.
- **Trips are sticky.** A tripped breaker keeps its first trip; later trips are not recorded, and
  the engine proposes none.

**Resets:**
- **Only the owner resets.**
  - `stellar.risk` has no reset operation, and a test checks its public API for this.
  - `circuit_breaker.reset` is written only by `stellar.owner` (`python -m stellar.owner
    reset-breaker`).
  - That command requires an interactive terminal, the exact phrase `RESET CIRCUIT BREAKER`, a
    non-empty reason, and a TRIPPED breaker.
  - Every refused attempt is journaled as `circuit_breaker.reset_refused`.
- **The ledger ignores any other reset**, and counts it in `ignored_resets`: a reset from a source
  other than `stellar.owner`, not `by: owner`, without a reason, or while ARMED.
- **Boundary tests:** only `stellar.owner` writes `circuit_breaker.reset`, and nothing outside it
  imports `stellar.owner`.

**Trip policy:**
- **A trade rejection never trips the breaker.** Only the systemic rules named by `TripPolicy` do:
  a daily-loss or drawdown breach (Foundation §8.1 "trip breaker"). They default to on, but can
  only fire once the owner configures those limits.
- **Causes.** The existing trip causes (`risk_rule`, `reconciliation_mismatch`, `data_failure`,
  `budget_exhaustion`, `owner`) are supported by the contract. Only `risk_rule` trips are produced
  in Phase 3; the others belong to later phases (P4 reconciliation, O2 budgets). No calendar-naive
  data signal trips the breaker.

---

## 7. Market-data safety (calendar-naive limitation)

Phase 2 gap detection and freshness are calendar-naive until MD-2 (Phase 2 doc §15.1).
Therefore:

1. **Phase 2 signals never reject and never trip.** `STALE`, `GAP_DETECTED`, `PARTIAL_SERIES` and
   a STALE freshness status never reject a trade and never trip the breaker. Rule 25 records them as
   NOT_APPLICABLE with the reason `calendar_naive_signal_not_risk_evidence`, and a test proves an
   approval with all three flags present.
2. **Quote age gives REVIEW, not FAIL.** The quote-age control (Foundation §8.1 "stale quote") is
   objective elapsed time, but a closed market also ages quotes. A quote older than the configured
   age therefore gives **REVIEW** (`quote_age_exceeds_limit_calendar_naive`). It claims neither
   that the feed is late nor that the market is closed, and it does not trip the breaker.
3. **What is rejected:**
   - missing required data (per policy);
   - a snapshot or quote for another instrument;
   - anything stamped after `as_of` (look-ahead);
   - unauthorised proxy or derived snapshots;
   - any proxy quote.
4. **What is prepared:** the `quote_age` and market-data rules are the place where session-aware
   rules plug in once MD-2 exists.

---

## 8. Spread, slippage and sizing

**Spread:**
- Spread = ask − bid from an exact Phase 2 quote, in price units, against a per-instrument limit.
- No quote means `missing_quote`. A spread is never fabricated, and the check's value is empty.

**Slippage.** A per-instrument tolerance must be configured. It is carried into
`OrderIntent.max_slippage`, and without it no intent can be built. Post-fill slippage checks belong
to Phase 4.

**Sizing (`sizing.py`):**
- **The formula:** risk = volume × stop distance × value-per-price-unit-per-lot, divided by equity.
  Every factor is an explicit input.
- **Where the volume comes from:**
  - `requested_volume` (validated only); or
  - the formula, if the owner sets `size_to_max_risk`: equity × max risk × size factor / (distance
    × value per lot), rounded **down** to the lot step (Foundation §8.1 "by formula"; layer design
    "round down to the lot step; reject below the minimum lot").
- **Checks:**
  - a volume must be a multiple of the lot step;
  - below the minimum volume → FAIL;
  - above the broker maximum → FAIL;
  - an account-currency mismatch → FAIL (no conversion).
- **Entry zones are not sized.** Choosing a reference price inside a zone is an undecided
  methodology question (RK-4), so a zone gives REVIEW `entry_zone_sizing_reference_undecided`.
- **Overweight's size factor (D-9)** stays undecided: REVIEW by default.

---

## 9. Daily loss, drawdown and exposure

- **Daily loss** = max(0, −(realised + unrealised)) / the day's start equity. Unknown unrealised
  P&L with open or unknown positions is a missing input; a known flat book counts it as 0. What
  "the trading day" means is the caller's (RK-6).
- **Drawdown** = (peak − equity) / peak. It needs `peak_equity`.
- **Exposure** = open risk (positions and pending orders with a known `open_risk`) plus the new
  trade's risk, as a fraction of equity. Any unknown `open_risk` is a missing input, never
  estimated.
- **Correlated exposure** uses owner-defined clusters only. An instrument in no cluster is
  NOT_APPLICABLE. Risk is summed without direction netting, which is conservative (RK-7).

---

## 10. Event / news hook

`EventRestrictionState` is the typed hook:
- instrument, `restricted`, an optional window, an event reference, `evaluated_at` and a source.

A later phase's validated calendar fills it.

Behaviour:
- the engine consumes it and does not guess;
- restricted → FAIL;
- missing while enabled → missing input;
- evaluated after `as_of` → look-ahead FAIL.

No news feed, calendar or fake event state exists.

---

## 11. Duplicate and idempotency protection

An approval is valid only for the exact inputs it was computed from. Idempotency is therefore
scoped to the **complete evaluation identity**, not to the proposal.

- **Evaluation fingerprint:**
  - `fingerprint = content_hash({engine_version, policy_hash, context_hash})`, where
    `context_hash` is the canonical hash of the whole normalised `RiskContext`;
  - the context includes the proposal, `as_of`, the breaker state (always the journal's), account
    equity, daily P/L, drawdown inputs, open positions, pending orders, exposure, cooldowns, the
    event restriction, the market snapshot, the quote (so the spread), broker metadata, the
    execution mode, the requested volume and prior idempotency keys;
  - any change in any of these, in the policy (content, so version and hash) or in the engine
    version gives a different fingerprint;
  - the decision id is `dec_` plus the first 40 hex digits of the fingerprint, so two evaluations
    share a decision id exactly when they share every input. The `RiskEvaluation` validator
    refuses a record whose fingerprint or decision id does not match its inputs.
- **Idempotent evaluation** (`RiskService.evaluate`):
  - the context's breaker is replaced by the journal's, then the fingerprint is computed;
  - if the **latest** journaled evaluation of the proposal has the same fingerprint, it is returned
    unchanged: no new events, no second decision, also after a restart;
  - otherwise the proposal is evaluated again and journaled as a **new** evaluation. A changed
    context, a newly tripped breaker or a changed policy therefore always produces a new
    evaluation; it never reuses an old decision;
  - if the context returns to the inputs of an earlier, superseded evaluation, that evaluation is
    journaled again as the latest (it is byte-identical, with the same decision id), so the
    history shows what was current when;
  - the same `proposal_id` with different proposal content raises `ProposalConflictError` and
    records nothing.
- **History:** `evaluations_for(proposal_id)` returns every journaled evaluation, oldest first;
  `latest_evaluation(proposal_id)` returns the current one. Earlier evaluations are never mutated
  or removed; they are superseded. The journal stays append-only and each entry replays exactly.
- **Current authorisation** (`RiskService.authorize_intent(evaluation, current_context, ...)`)
  is the only public way to an `OrderIntent`. It refuses, in this order:
  1. the journaled breaker is TRIPPED → `IntentRefused`, even if the evaluation was APPROVED
     before the trip;
  2. the evaluation is not exactly the journaled latest evaluation of its proposal (never
     journaled, forged, or superseded) → `ReevaluationRequired`;
  3. the fingerprint of the current context (normalised, breaker from the journal) under the
     service's current policy differs from the evaluation's → `ReevaluationRequired`;
  4. the structural checks: APPROVED, PAPER, a configured slippage tolerance, and the Phase 1
     chain validation → `IntentRefused`.

  `ReevaluationRequired` is an `IntentRefused`. The caller evaluates again, then authorises the
  new evaluation. There is **no time-based approval expiry**; `as_of` is simply one of the
  fingerprinted inputs.
- **Order idempotency:**
  - an intent's idempotency key is the Phase 1 hash of the proposal id, whichever of the
    proposal's evaluations authorised it;
  - rule 9 rejects a proposal whose key already exists;
  - intents are validated by the Phase 1 chain.

---

## 12. Events and journal

The service emits, in order, with `correlation_id = proposal_id`, `agent_id = risk_engine` and
`source = stellar.risk`:
- `risk.check.started`: the fingerprint, the checks list, policy version and hash;
- `risk.check.completed`, one per rule: rule, status, reason, passed, blocking, value, limit,
  unit;
- one final event:
  - `risk.approved`: `volume`, `risk_pct_equity`;
  - `risk.rejected`: `reasons`, `shadow_tracked: true`;
  - `risk.review.requested`: `reasons`.

  Each carries `decision_id`, the `fingerprint`, the outcome, the policy and context hashes, and
  the **complete evaluation**.

  Every evaluation of a proposal is a separate, complete set of these events. An idempotent
  repeat of the latest evaluation emits nothing.
- `circuit_breaker.tripped`, when a systemic rule trips the breaker.

Risk events are critical (Phase 1): if one cannot be journaled, the error propagates.

**New canonical name:** `risk.review.requested` (§1).

## 13. Auditing

Every evaluation can be reconstructed from its final event:
- the proposal;
- the policy (content, version, hash);
- the context (every input, `as_of`, breaker state), with its hash;
- every rule's status, reason, measured value, configured limit and unit;
- the decision, with its provenance (produced by `risk_engine`, config hash = policy hash);
- any trip.

Tests show that `RiskEngine(stored.policy).evaluate(stored.context)` reproduces every journaled
evaluation in a proposal's history exactly, and that a tampered record (hash or fingerprint) is
refused. Contexts carry no secrets.

---

## 14. Tests

The full Stellar suite collects **423 tests, all passing**. The Phase 2 baseline at `c986be5`
collects 314:

| Change | Tests |
|---|---|
| `unit/test_rk_policy_contracts.py` (new) | +18 |
| `unit/test_rk_engine_rules.py` (new) | +45 |
| `unit/test_rk_breaker_service.py` (new) | +37 |
| `contract/test_upstream_boundary.py`: 4 new tests plus a 6-case import-order regression | +10 |
| `unit/test_config_and_registry.py`: the parametrized "unimplemented gate is refused" test loses its `risk_engine` case, since that gate is now implemented | −1 |
| **Total** | **314 + 18 + 45 + 37 + 10 − 1 = 423** |

`test_rk_breaker_service.py` has 37 tests: 25 in the first Phase 3 draft, minus the old "decided
once" test, plus 13 for fingerprint-scoped idempotency and current authorisation.

**Coverage by file:**
- **Policy and contracts:**
  - default policy all UNSET; limits exactly when ENABLED; mandatory controls cannot be disabled;
  - test-only policy refused; policy hash;
  - feature gate implemented but no trading;
  - unknown vs empty book; the DEMO gate cannot be opened; state validation;
  - Phase 1 compatibility; NOT_CONFIGURED is never a pass; precedence in `RiskDecision`;
  - the REVIEW event.
- **Engine and rules:**
  - approval under the explicit test policy;
  - the default policy never approves and records NOT_CONFIGURED;
  - disabled controls are non-blocking; reward:risk is never evaluated;
  - malformed input is refused; unsupported instrument; expired and future proposals;
  - LIVE and DEMO; tripped breaker; Overweight/D-9;
  - stop through the market; stops level; duplicates;
  - missing data per policy; proxy snapshot and quote; look-ahead;
  - **calendar-naive flags neither reject nor trip**; precision loss;
  - **spread pass/fail and missing spread**; unconfigured instrument limit; quote age gives REVIEW;
    slippage;
  - **max risk pass/fail**; formula sizing; missing sizing inputs; lot step, min/max, currency;
    zones; position volume;
  - counts; instrument and correlated exposure; **daily loss** (including the trip); **drawdown**
    (including the trip); a plain rejection does not trip;
  - cooldowns; event restrictions;
  - **exhaustive precedence**; FAIL beats REVIEW;
  - **same input + policy = same evaluation**; replay; tamper refusal; **no network**.
- **Breaker and service:**
  - sticky trips; **persistence across restart**; non-owner resets ignored; no reset API;
  - **owner reset** with every safeguard; refusals journaled; armed-breaker refusal; the CLI refuses
    without a TTY;
  - canonical events and payloads; reject and review events;
  - the journal's breaker overrides the context; systemic trip vs plain rejection;
  - **identical evaluation is idempotent** (no duplicate events, also after a restart); a changed
    context is a new evaluation; the fingerprint covers every input and the policy; a forged
    fingerprint is refused; conflict refused;
  - **replay reproduces the whole evaluation history**; **old decisions stay immutable** in the
    journal; returning to an earlier context is journaled again;
  - **current authorisation:** a newly TRIPPED breaker blocks an old approval; changed daily P/L,
    changed quote/spread and a changed policy each require re-evaluation; an unjournaled
    evaluation cannot authorise; no public builder bypasses the service;
  - **intents only from APPROVED PAPER**; slippage required; levels bound to the proposal.
- **Boundaries:**
  - only `stellar.risk` builds `RiskDecision` / `OrderIntent`;
  - only `stellar.owner` writes resets, and nothing imports it;
  - no LLM or network imports in `stellar.risk`;
  - every package imports on its own.

**Test values.** All limits are in the `test_only` `TEST_POLICY`, and all market, account and
metadata values are labelled synthetic test fixtures. None is a default or a recommendation.

---

## 15. Deferred controls

| Control | Status |
|---|---|
| Minimum reward:risk | Not evaluable until a measurement method is decided (Phase 1 decision) |
| Session-aware stale-data and market-open rules | MD-2 |
| Post-fill slippage breach counting (Foundation §8.1) | Phase 4 |
| Reconciliation-mismatch, data-failure and budget-exhaustion trips | Phases 4, 6, 7 (P4, O2) |
| Cooldown production (after a loss, after a close) and event-restriction production | Later phases; hooks exist |
| Real correlation measurement | Deferred; clusters only |
| Margin checks | Needs broker margin data (Phase 8) |

---

## 16. Unresolved decisions

| # | Decision | Safe default until decided |
|---|---|---|
| RK-1 | Put `RiskPolicy` in `StellarConfig` (and wire `trading_permitted()`), or keep it a separate owner file | Separate, validated by `load_risk_policy`; trading still not permitted |
| RK-2 | Every threshold value (Foundation D-12) | All UNSET → REVIEW |
| RK-3 | Default for missing inputs: FAIL or REVIEW | FAIL (Foundation §8.1) |
| RK-4 | Sizing reference for entry zones | Not sized → REVIEW |
| RK-5 | Overweight size factor (D-9) | REVIEW (no trade) |
| RK-6 | Definition of the trading day for daily loss (session or UTC) | Supplied by the caller |
| RK-7 | Direction netting in correlated exposure | None (conservative sum) |
| RK-8 | Whether an old quote should become FAIL once session calendars exist (MD-2) | REVIEW |
| RK-9 | Take-profit on the OrderIntent (none, first target, or an owner rule) | None unless the caller passes one of the proposal's targets |
| RK-10 | Whether default trip-on-breach (daily loss, drawdown) stays on | On (Foundation §8.1); inert until limits exist |
| RK-11 | Where the *current* context for `authorize_intent` comes from (account, P/L, positions, quote). Only the breaker is journal-sourced today | The caller supplies it; the service re-derives the breaker and the fingerprint. The Phase 4 Paper Broker and account state are expected to supply it |
