# Stellar Phase 6b: Trader, Setup and TradeProposal layer

**Status:** implemented and tested; not committed. Paper-only decision support.
Nothing here trades, approves risk, sizes a position, builds an order intent or calls a broker.
**No profitability claim is made.** Every threshold is unset by default. Tests use labelled
synthetic fixtures.

---

## 1. Scope

Phase 6b turns the Phase 6 research output and the Phase 5 technical evidence into one of three
outcomes:
- **NO_SETUP**;
- a typed **setup candidate**;
- a typed **`TradeProposal`**, which is then handed to the Phase 3 Risk Engine. That hand-off is
  outside this layer.

```
Phase 5 TechnicalAnalysis ─┐
Phase 6 DecisionSupport ───┼─> SetupEvaluator (T6, deterministic) ─> Setup + lifecycle event
(optional MTF analysis) ───┘                        │
                                   selection: owner ids | single option | U4 Trader (LLM)
                                                    │
current VerifiedMarketSnapshot ─> ProposalBuilder (P1, deterministic) ─> TradeProposal | refusal
explicit Approval (rating) ─────┘                   │
                                   journal: trade.proposed; setup ARMED → PROPOSED
                                                    ▼
                                   Phase 3 Risk Engine (NOT called here)
```

**Not implemented** (as instructed):
- risk approval, RiskPolicy changes, OrderIntent, Paper Broker execution;
- position sizing, MT5, Vantage, DEMO, LIVE, credentials;
- Research Lab runtime, the visual world, profitability optimisation, reinforcement learning.

---

## 2. Canonical sources

| Source | Used for |
|---|---|
| Foundation §4.11, §7.2 | the first strategy family: bias → pullback → price action → momentum → entry |
| Foundation §4.12 | the Setup contract and lifecycle states |
| Foundation §4.13, R-1, L8 | setup-first framing, TradeProposal fields, rating = approval strength, Sell ≠ short |
| Foundation §5.1 | roles: T6 `pullback_setup`, T7 `entry_timing`, U4 `trader`, P1 `trade_proposal_builder`, P2 |
| Foundation §7.1 | `setup_validity` (bars), profiles |
| Foundation §11 Phase 5 / 6b | T6, setup lifecycle and P1 (deferred from Phase 5, P5-12); Trader, REVIEW/Hold → no proposal |
| D-9 | Overweight: safe default is no trade |
| Phase 3 RK-4, RK-9 | a zone entry is not sized (REVIEW); take-profit on the order is undecided |
| Audit K51, L4 | the upstream Trader's levels are floats parsed from text: unsafe, advisory only |

---

## 3. Package layout

| Package | Role | May not import |
|---|---|---|
| `stellar/setups/` | `config.py` (SetupConfig, all unset), `models.py` (Setup contract), `evaluate.py` (T6 evaluator), `lifecycle.py` (SetupBook, `setup.state.changed`) | reasoning providers, proposals, trader, proposal schema, risk, execution, owner, config |
| `stellar/proposals/` | `models.py` (Approval, LevelSelection, ProposalOutcome, ProposalFailure), `builder.py` (P1; the only code that constructs a `TradeProposal`) | reasoning, trader, journal, telemetry, risk, execution, owner |
| `stellar/trader/` | `contracts.py` (U4 output schema, prompt, TraderConfig), `desk.py` (TraderDesk: evaluate → select → build → journal) | risk, execution, owner, order / risk / execution schemas, config |

Changes to existing files:
- `tests/contract/test_upstream_boundary.py`: new Phase 6b boundary tests; the list of packages
  allowed to import `stellar.technical`; the import-order list.

No other file changed: no upstream file, no Phase 1–6 source, no schema, no event catalogue
entry and no other doc.

---

## 4. The Setup contract (`stellar.setups.models.Setup`)

**Fields:**
- identity: `setup_id` (stable), `fingerprint` (content hash);
- what it is: `instrument`, `timeframe`, `setup_type`, `direction`;
- where it stands: `status`, `state`, `as_of`, `reasons`, `limitations`, `unevaluated`;
- the leg and its invalidation: `reference_leg_id`, `invalidation_level`,
  `invalidation_evidence_id`;
- validity: `valid_from`, `valid_until`;
- `options` (entry / stop / target);
- `evidence` (the exact inputs), `config_hash`, `produced_by = pullback_setup`.

**Status → canonical state (§4.12).** The brief's statuses are kept. Each maps to exactly one
canonical state:

| Status | State |
|---|---|
| NO_SETUP, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE | NO_SETUP |
| CANDIDATE | WATCHING |
| READY_FOR_PROPOSAL | ARMED |
| INVALIDATED | INVALIDATED |
| EXPIRED | EXPIRED |

- PROPOSED is set only after the builder builds a proposal.
- APPROVED, REJECTED and FILLED belong to Risk and the broker. This layer never sets them.
- The model rejects inconsistent records. For example:
  - NO_SETUP with a direction;
  - READY without entry, stop and target options, an invalidation level and `valid_until`;
  - evidence dated after `as_of`.

**Direction** is `LONG` / `SHORT` / `NONE`. There is no Buy / Sell anywhere in the layer.

**Setup types.** Only `PULLBACK_CONTINUATION` is defined, because it is the only canonically
described family (§4.11, §7.2). Breakout / retest, range and reversal setups have no canonical
definition, so none is classified. §7.4 describes adding a family as another pluggable
detector that produces the same `Setup` type.

---

## 5. Evaluation rules (`evaluate_setup`, deterministic, no model)

### Inputs (refused with `SetupInputError`)

The inputs are checked before anything is evaluated. Each failure has its own code:

| Code | Refused when |
|---|---|
| `technical_hash_mismatch` | the technical analysis fails Phase 5 `verify` |
| `instrument_mismatch` | the inputs are for different instruments |
| `future_technical` | the analysis (or the MTF analysis) is dated after `as_of` |
| `future_research` | the decision support is dated after `as_of` |
| `technical_not_reviewed` | the decision support did not review this exact analysis (id and hash) |

### Rules, in order (the first that applies decides the status)

1. **Structure state:**
   - INSUFFICIENT → INSUFFICIENT_EVIDENCE;
   - RANGE or MIXED → NO_SETUP;
   - UP → LONG; DOWN → SHORT.
2. **The last completed leg** must be a WITH_STRUCTURE leg in the setup direction, between
   CONFIRMED pivots, with a pullback against it (depth > 0). Otherwise → NO_SETUP.
3. **Invalidation.** Either of these → INVALIDATED:
   - `break_against_state` (a close beyond the last swing);
   - the pullback's extreme trades beyond the leg's start swing (the invalidation level).
4. **Expiry.** `as_of ≥ valid_until` → EXPIRED. Here
   `valid_until = leg.confirmed_at + setup_validity_bars × timeframe`, only when configured.
5. **Research cannot support the setup** → INSUFFICIENT_EVIDENCE, when any of these holds:
   - the run FAILED;
   - the evidence grade is INSUFFICIENT;
   - the stance is INSUFFICIENT_EVIDENCE.
6. **Disagreement** → CONFLICTING_EVIDENCE. The disagreement is kept as reasons, never
   averaged. It is any of:
   - stance MIXED, or opposite to the direction;
   - a TECHNICAL_MACRO_DISAGREEMENT finding;
   - multi-timeframe alignment DISAGREE, or agreeing the other way.
7. **Otherwise CANDIDATE.** It becomes READY_FOR_PROPOSAL only if all of these hold:
   - the stance supports the direction;
   - the grade ∈ `ready_evidence_grades`;
   - validity is configured;
   - the optional retracement bounds hold;
   - there is at least one entry, one stop and one target option.

   Every unmet condition is a reason.

### Pullback

- The only inputs are the Phase 5 leg, the pullback extreme and depth, and the optional
  retracement ratio bounds.
- Candle counts are never a rule. `counter_direction_bars`, sequence runs and body totals are
  not read at all: a boundary test checks the evaluator's source.
- A test shows that two red bars in a counter-structure context stay NO_SETUP.

### No recomputation

The evaluator reads Phase 5 records as given. The only arithmetic is:
- `level ± buffer`;
- `multiple × ATR`.

Both run in Phase 5's Decimal context.

---

## 6. Level options: entries, stops, targets

Every option:
- is a typed `LevelOption` with a deterministic `option_id`;
- carries its `sources` (`PHASE5_PIVOT`, `PHASE5_ZONE`, `PHASE5_ATR`, `MARKET_QUOTE`,
  `SETUP_CONFIG`; there is no LLM source);
- carries the Phase 5 `evidence_ids` it came from;
- carries a `basis` label, which becomes the proposal's `PriceLevel.basis`.

### Entries (a typed entry model)

| Kind | Enabled by | Order type | Price |
|---|---|---|---|
| MARKET_AT_QUOTE | `entry_models` | `market` | read at build time from the quote: ask (LONG), bid (SHORT); no quote → NO_QUOTE |
| LIMIT_AT_ZONE | `entry_models` | `limit` | a Phase 5 zone (SUPPORT/MIXED for LONG, RESISTANCE/MIXED for SHORT) strictly between the invalidation level and the leg's end swing |

- A limit zone is kept as `zone_low` / `zone_high` and is never collapsed to a midpoint. A
  zero-width zone becomes a single limit price.
- The builder refuses a limit already marketable against the current reference (the quote
  side, or the last close when there is no quote): LIMIT_WOULD_BE_MARKETABLE.

### Stops (mandatory; from explicit evidence)

- **STRUCTURE_STOP:** the leg's start swing ± `stop_buffer`.
  - With no buffer set, the stop sits exactly on the level. Its basis says `_no_buffer`, and
    no percent or pip distance is assumed.
- **ATR_STOP:** only when `atr_stop_multiple` is set and the Phase 5 ATR is ready. The distance
  is resolved at build time from the chosen entry's far edge.

### Targets (evidence-derived)

- **PRIOR_SWING_TARGET:** the leg's end swing.
- **ZONE_TARGET:** the near edge of each opposing zone beyond it.
- **RK-9 is unresolved,** so all target options are kept. The proposal's `take_profits` holds
  exactly the targets explicitly selected (owner or Trader), sorted nearest first. Several
  targets are never reduced to one silently.

### Geometry (builder)

- LONG: stop < every entry price < every target.
- SHORT: the reverse.
- Zones are checked on both edges.
- A failure refuses the build (INVALID_STOP_GEOMETRY / INVALID_TARGET_GEOMETRY) before the
  schema is reached. The `TradeProposal` validator checks the geometry again.

---

## 7. U4 Trader (LLM): interpretation and selection only

- **Role:** the registered U4 `trader` (source UPSTREAM; the concept is reused, the upstream
  code is not). It runs only when:
  - a setup is READY; and
  - more than one option exists for some role; and
  - its LLM is enabled with an explicit budget and model (`TraderConfig`, D-11).
- **Output:** `TraderSelectionOutput` is a closed schema with **no numeric field** (a boundary
  test checks the type annotations). It holds:
  - `decision` SELECT / DECLINE;
  - option ids for the entry, the stop and the targets;
  - cited evidence ids;
  - `direction` (LONG / SHORT / NONE);
  - narrative `rationale` / `risks`.
- **Rejected answers.** The answer is rejected, and the step is FAILED with a typed reason,
  when:
  - it is not JSON (`not_json`). Prose such as "FINAL TRANSACTION PROPOSAL: **BUY** at …" is
    rejected;
  - it has an unknown field, such as a price (`schema_mismatch`);
  - its direction is not LONG / SHORT / NONE, such as "BUY" (`schema_mismatch`);
  - it cites an id that was not offered (`unknown_evidence_id`);
  - it names another setup (`wrong_setup`) or the other direction (`direction_mismatch`);
  - it puts an option in the wrong role (`option_role_mismatch`).
- **Numbers.** Nothing reads a number from the rationale.
- **Calls.** Calls go through the Phase 6 `call_structured` path:
  - fingerprinted and journal-checkpointed (the same question is not paid for twice);
  - retries only for retryable failures;
  - `agent.task.*` / `agent.llm_call.*` events;
  - `decision.trader_plan.created` with the selected ids.
- **Selection order.** The desk selects in this order:
  1. the owner's `LevelSelection`;
  2. the single option per role, if there is only one (no LLM);
  3. the Trader;
  4. otherwise SELECTION_REQUIRED.
- **Upstream reuse (audit K51 / L4).**
  - Upstream's `TraderProposal` renders float levels into markdown. Stellar parses **no** level
    from text, so `llm_levels_advisory` stays empty.
  - The Foundation's "Trader layout parser" for advisory levels is therefore not built. See §14.

---

## 8. Proposal Builder (P1)

`build_proposal(setup, selection, approval, market, config, created_at)` is pure. It uses no
model, journal, Risk Engine or broker.

### Refusals, in order (`ProposalFailure`)

1. The setup is not ready, or the selection belongs to other evidence:
   - `setup_not_ready`;
   - `selection_required`;
   - `selection_for_other_evidence`.
2. The approval does not allow a proposal:
   - `approval_required`;
   - `approval_for_other_setup` (the approval names another `setup_id`);
   - `approval_direction_mismatch` (the approval names the other direction);
   - `overweight_d9_unresolved` (D-9 safe default: no trade);
   - `rating_does_not_approve`, for Hold, Underweight, Sell and REVIEW. Sell is never read as
     "go short".
3. The configuration or timing does not allow one:
   - `profile_not_configured`;
   - `config_mismatch`;
   - `created_before_setup`;
   - `expiry_not_configured`;
   - `setup_expired`.
4. The market data is unusable:
   - `market_data_mismatch`;
   - `future_market_data`;
   - `market_data_older_than_evidence`;
   - `market_data_stale` (STALE or NO_DATA). UNKNOWN freshness (no staleness threshold
     configured, MD) is not treated as stale and is visible on the snapshot.
5. The selection does not fit the setup's options:
   - `unknown_option`;
   - `option_role_mismatch`;
   - `missing_target`.
6. The entry cannot be resolved:
   - `no_quote`;
   - `entry_unresolved`;
   - `limit_would_be_marketable`.
7. The geometry is wrong:
   - `invalid_stop_geometry`;
   - `invalid_target_geometry`.
8. The schema refuses the record: `proposal_schema_rejected` (defence in depth).

### The built proposal

The existing Phase 1 `TradeProposal` is reused unchanged. No field was added: everything
§4.13 asks for fits the existing contract.

| Field | Value |
|---|---|
| `proposal_id` | `prop_` + a hash of: setup fingerprint, selection, approval, market snapshot id, series hash and quote, config hash, `created_at` |
| `run_id` | the Phase 6 run |
| `snapshot_id` | the market snapshot |
| `setup_id` | the setup |
| `profile` | from config |
| `direction` | from the setup |
| `source_rating` | Buy |
| `size_factor` | 1: the schema's value for Buy; a rating strength, not a size |
| `entry` | typed |
| `stop_loss` | typed |
| `take_profits` | typed |
| `reward_risk` | **None**: the measurement method is undecided; no minimum is invented |
| `valid_until` | the setup's |
| `llm_levels_advisory` | None |
| `contradictions` | the Phase 6 challenge kinds |
| `report_hashes` | the decision outputs hash, the technical content hash, the setup fingerprint, and the MTF hash if any |
| `provenance` | `trade_proposal_builder`, the config hash, and the input record ids |

- `ProposalOutcome.proposal_hash` is the proposal fingerprint.
- Proposals are frozen records.
- `load_proposal` only re-validates a journaled proposal.

---

### LONG / SHORT semantics (exact)

A READY_FOR_PROPOSAL SHORT setup **does** produce a `TradeProposal`. The canonical
architecture supports it explicitly: setup-first framing (§4.13, R-1) exists so that direction
comes from the deterministic setup and the rating only approves it. The Phase 1 contract
already carries `direction: LONG | SHORT` next to `source_rating`, so no contract change was
needed.

| | LONG setup | SHORT setup |
|---|---|---|
| Field that opens the position | `direction = LONG` | `direction = SHORT` |
| `source_rating` | `Buy` | `Buy` |
| What `Buy` means | "take this LONG setup" | "take this SHORT setup" |
| Market entry reference | ask | bid |
| Geometry | stop < entry < targets | stop > entry > targets |
| Phase 3 intent side (`SIDE_FOR_DIRECTION[direction]`) | `OrderSide.BUY` | `OrderSide.SELL` |

**Why this is unambiguous:**
- `direction` is copied only from the setup.
- The Risk Engine derives the order side only from `direction` (`risk/intents.py`); it never
  reads a side from `source_rating`. `OrderSide.SELL` is Stellar's order-side enum, not the
  upstream "Sell" rating.
- `source_rating` can only be Buy or Overweight (Phase 1 schema, R-1), and the builder builds
  only on Buy. Overweight is refused under D-9.
- The upstream **Sell** rating ("exit or avoid the position", L8) never approves a proposal in
  either direction. No code in `setups` / `proposals` / `trader` names `Rating.SELL`,
  `Rating.UNDERWEIGHT`, `Rating.HOLD`, `OrderSide` or `SIDE_FOR_DIRECTION`, and no mapping
  keyed by rating exists. A test checks the source.

**The typed approval is bound, not a synonym for LONG.** `Approval` carries `setup_id` and
`direction` as well as the rating. The builder refuses:
- an approval for another setup (`approval_for_other_setup`);
- an approval whose direction differs from the setup (`approval_direction_mismatch`).

So a Buy approval of a SHORT setup states "SHORT" explicitly. A LONG approval can never turn a
SHORT setup into a LONG proposal, and a SHORT approval can never turn a LONG setup into a SHORT
proposal.

---

## 9. Configuration (`SetupConfig`; every threshold UNSET)

| Setting | Unset means |
|---|---|
| `setup_validity_bars` | no `valid_until`: the setup cannot become READY (no forever-valid proposal) |
| `ready_evidence_grades` | READY is not reachable |
| `min_retracement_ratio` / `max_retracement_ratio` | not evaluated (reported in `unevaluated`) |
| `entry_models` | no entry option |
| `stop_buffer` (price or ATR multiple) | no buffer (stop on the level, labelled) |
| `atr_stop_multiple` | no ATR stop |
| `profile` | the builder refuses |

- `SetupConfig` is versioned, carries a `test_only` label and has a `config_hash`.
- `TraderConfig` is off by default. Enabling it needs a budget and a model.
- **Not configurable at all** (not decided):
  - minimum reward:risk;
  - position size (no 0.01 default);
  - an expiry default;
  - percent or pip stops.

---

## 10. Evidence quality

- Readiness uses the typed Phase 6 `EvidenceQuality.grade` plus the configured set of allowed
  grades.
- `self_reported_confidence` from any model is never read.

---

## 11. Point in time, identity and idempotency

**Point in time:**
- inputs dated after `as_of` are refused;
- only CONFIRMED pivots (confirmed by `as_of`) reach a level. A test checks that the latest
  pullback low, still a CANDIDATE pivot, is never used;
- market data after `created_at` is refused.

**Identity:**
- `setup_id` hashes the instrument, timeframe, type, direction, reference leg id **and leg
  prices**, and the config hash. Phase 5 pivot ids name bar times and windows, not prices, so
  the prices are bound in explicitly.
- `fingerprint` hashes the whole record.

**Changes and repeats:**
- The same evidence gives an identical `Setup`, an identical proposal id, and no new journal
  event.
- Changed research or technical evidence gives a new fingerprint and a new proposal id.
- A new leg or a new config gives a new `setup_id`.
- A setup that is already PROPOSED gets no second proposal (`setup_already_proposed`). The same
  evidence returns the journaled proposal.
- If a crash happens after `trade.proposed` but before the lifecycle event, the retry does not
  journal a second `trade.proposed`.

---

## 12. Lifecycle and events (existing catalogue names only)

| Event | When | Payload (main keys) |
|---|---|---|
| `setup.state.changed` | a new state, or new evidence in the same state (`evidence_changed`) | setup_id, from, to, rule, status, direction, fingerprint, as_of, setup |
| `agent.task.started/completed/failed`, `agent.llm_call.started/completed` | U4 call | role, fingerprint, call record, output |
| `decision.trader_plan.created` | Trader answer accepted | decision, direction, option ids, fingerprint (no numbers) |
| `trade.proposed` | proposal built (once per proposal id) | proposal_id, setup_id, instrument, direction (required), proposal, proposal_hash, selection, approval |

**Transitions.**
- Allowed: from (none) / NO_SETUP / WATCHING / ARMED to any evaluated state.
- ARMED → PROPOSED only through `mark_proposed`, for the armed fingerprint.
- PROPOSED → INVALIDATED / EXPIRED (APPROVED / REJECTED are Risk's).
- INVALIDATED, EXPIRED, REJECTED and FILLED are terminal: reopening is refused and nothing is
  journaled.
- A PROPOSED setup is not moved back by later evaluations.

**Correlation.** Events carry the Phase 6 `run_id` as `correlation_id`.

**Critical events.** No risk, order, breaker, account or position event is emitted (a boundary
test checks this). `trade.proposed` is in the critical `trade` domain, so a journal failure
propagates and nothing continues.

---

## 13. Boundaries (enforced by tests)

The setups, proposals and trader packages:
- **never import:**
  - `stellar.risk`, `stellar.execution`, `stellar.owner`, `stellar.config`;
  - the order / risk / execution schemas;
  - vendor SDKs, network, `os`, `subprocess`, `random`, `secrets`, `tradingagents`;
- **never call:**
  - OrderIntent, RiskDecision, PaperBroker, RiskService, RiskPolicy, ExecutionResult,
    ExecutionChecker, FillAuthorisation;
  - `authorize_intent`, `confirm_intent`, `owner_reset_breaker`, BreakerLedger;
- have no LIVE / DEMO string and no `float`.

Further rules:
- Only `proposals/builder.py` builds a `TradeProposal` (Risk's `rules.py` only re-validates).
- `setups` calls no model.
- `proposals` uses no model, journal or telemetry.
- The Trader schema has no numeric field.
- Research Lab: not wired. Phase 6b records (setup fingerprint, option ids, proposal hash) are
  replayable inputs for it later.

---

## 14. Canonical conflicts and interpretations (flagged, not silently resolved)

| # | Topic | Canonical text | What Phase 6b does |
|---|---|---|---|
| C-1 | Status names | §4.12: WATCHING / ARMED; the brief: CANDIDATE / READY_FOR_PROPOSAL / INSUFFICIENT_EVIDENCE / CONFLICTING_EVIDENCE | both kept, with a fixed status → state map (§4) |
| C-2 | ARMED meaning | §4.11a: ARMED waits for the T7 entry trigger | READY = ARMED here; T7 entry timing is not built (the market entry is at the quote now) |
| C-3 | Approval source | §4.13: the PM (U10) rating approves; U10 is not in 6b (U1–U8) | the builder needs an explicit typed `Approval` (PM or owner) bound to one `setup_id` and direction; without it, no proposal |
| C-4 | Trader advisory levels | §4.13 / U8: parse the Trader's rendered entry and stop as advisory | the brief forbids textual numeric parsing, so no parser; `llm_levels_advisory` is None |
| C-5 | `reward_risk` | §4.13 lists it as "computed" | the Phase 1 decision stands: not computed (method undecided) |
| C-6 | Order of chains | §5.1: setup first, then the LLM chain judges it | Phase 6 already ran; the evaluator reads its output for the same technical analysis |
| C-7 | MTF roles | profiles (D-7, P5-9) unassigned | any DISAGREE alignment counts as conflict (conservative) |

---

## 15. Unresolved decisions (safe defaults in force)

| # | Decision | Safe default |
|---|---|---|
| TS-1 | Setup validity per profile (§7.1) | UNSET → never READY |
| TS-2 | Which evidence grades may reach READY | UNSET → never READY |
| TS-3 | Retracement bounds | not evaluated |
| TS-4 | Stop buffer (price / ATR), ATR stop multiple | no buffer; no ATR stop |
| TS-5 | Entry models allowed per profile | none |
| TS-6 | Target on a zone: near edge (current) vs far edge | near edge, labelled `opposing_zone_near_edge` |
| TS-7 | Profile id (D-7) | UNSET → no proposal |
| TS-8 | Minimum reward:risk and its measurement (Phase 1) | not computed, not checked |
| TS-9 | D-9 Overweight size factor | no trade |
| TS-10 | RK-9 take-profit on the order | all selected targets kept on the proposal; the order's take-profit stays the caller's choice (Phase 3) |
| TS-11 | RK-4 sizing of a zone entry | the Risk Engine returns REVIEW for zones |
| TS-12 | Additional setup families (breakout, range) | not classified |
| TS-13 | Market freshness threshold (MD) | UNKNOWN is accepted and visible; STALE / NO_DATA refused |
| TS-14 | T7 entry timing on the entry timeframe | not built |
| TS-15 | Whether a PM (U10) or the owner supplies approvals in production | explicit input only |

---

## 16. Tests

All fixtures are synthetic.

| File | What it covers |
|---|---|
| `tests/trader_helpers.py` | constructed LONG / SHORT / RANGE / breach paths; quote-bearing snapshots; a scripted Trader; real Phase 6 pipeline runs; labelled one-field variants |
| `tests/unit/test_tr_setups.py` (35) | clean LONG / SHORT; NO_SETUP; insufficient; technical / macro conflict (real pipeline); MTF conflict; neutral; unset config; retracement bounds; ATR buffer and stop; invalidation (close and wick); expiry; identity; idempotency; immutability; no look-ahead; candidate pivot excluded; tamper and mismatch refusals; lifecycle |
| `tests/unit/test_tr_proposals.py` (32) | clean LONG / SHORT / zone; ATR stop; ids; immutability; stop / target geometry; marketable limit; no quote; missing target; unknown / misused options; approvals (none, Overweight, Hold / Underweight / Sell / REVIEW); profile; config; expiry; stale / future / old / other-instrument data; ordering |
| `tests/unit/test_tr_direction_semantics.py` (27) | exact LONG and SHORT semantics (direction, rating, entry side, geometry, Phase 3 side); every rating × both directions (only Buy builds; the direction is always the setup's); Sell / Underweight never open a short; no rating-to-direction or rating-to-side code; approvals for the other direction or another setup are refused; the schema rejects a flipped direction; SHORT end to end through the desk |
| `tests/unit/test_tr_trader.py` (29) | desk end to end; events; idempotency and checkpoint reuse; one proposal per setup; single-option and owner modes; selection required; no-setup and conflict paths; LLM invents a price / option / evidence id; BUY word; free-text BUY; wrong direction or setup; role misuse; decline; provider failure; crash retry; future research |
| `tests/contract/test_upstream_boundary.py` (+11: 8 tests, 3 import-order cases) | the boundaries in §13 |

Mutation checks were run on the evaluator, builder, desk, lifecycle and boundary tests. Every
non-equivalent mutant is killed. The equivalent survivors are defensive checks that a verified
Phase 5 analysis always satisfies:
- zone pivots are confirmed;
- depth > 0 once a leg's end pivot is confirmed;
- an UP leg in an UP state is WITH_STRUCTURE.
