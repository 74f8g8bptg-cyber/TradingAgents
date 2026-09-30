# Stellar Agents — Foundation Phase 1 Implementation Note

| | |
|---|---|
| **Status** | Phase 1 technical foundation implemented; not yet committed |
| **Implements** | `docs/STELLAR_FOUNDATION_PLAN.md` §11.2 Phase 1 (contracts, config, telemetry core, journal, registry, circuit-breaker state object), within the scope set by the owner's Phase 1 brief |
| **Does not include** | Market data, research collectors, LLM calls, strategy logic, risk thresholds, risk engine, broker, MT5, live trading, API, renderer or StarNet-derived code |

---

## 1. Package layout

Stellar is a **separate installable project** beside upstream (layer design §1.4). No upstream
file was changed. Install with `pip install -e . -e ./stellar`; test with `pytest` inside
`stellar/`.

```
stellar/
  pyproject.toml              # project "stellar-agents"; depends on tradingagents + pydantic
  src/stellar/
    __init__.py               # __version__
    ids.py                    # ULID event ids; prefixed record ids (prop_, dec_, int_, ...)
    serialization.py          # canonical JSON, SHA-256
    schemas/                  # typed contracts
      common.py               # base model, Decimal/UTC/id/label types, instruments, Provenance
      market.py               # Timeframe, Candle, Quote, CandleSeries, MarketSnapshot
      research.py             # Claim, ResearchItem, ClaimValidation, ResearchRole
      analysis.py             # AnalysisKind, Coverage, AnalysisReport
      proposal.py             # Rating, EntrySpec, PriceLevel, TradeProposal
      risk.py                 # RiskOutcome, RiskRule, RiskCheck, RiskDecision
      order.py                # AccountMode, OrderType, OrderIntent, idempotency key
      execution.py            # ExecutionStatus, ExecutionResult
    telemetry/
      catalogue.py            # canonical event names, critical domains, required payload keys
      events.py               # StellarEvent envelope, new_event()
      bus.py                  # in-process EventBus (journal first, then subscribers)
    journal/store.py          # StellarJournal: SQLite, append-only, ordered
    risk/breaker.py           # CircuitBreakerState (state only; no thresholds, no reset operation)
    config/                   # StellarConfig models and TOML loader
    agents/                   # AgentIdentity, AgentRegistry, the architectural roster
    validation/chain.py       # proposal → decision → intent → result cross-checks
  tests/
    factories.py              # valid example records (illustrative test values only)
    unit/                     # contracts, trade rules, chain, events, journal, bus, config, registry,
                              # circuit-breaker state
    contract/                 # upstream boundary tests
```

## 2. Implemented contracts

All contracts share one base: **closed** (unknown fields rejected), **immutable**, **versioned**
(`schema_version` 1.x; other majors rejected; later fields are added as optional), **UTC**
timestamps (naive rejected), **prefixed ids** (for example a `dec_` id in a `proposal_id` field
is rejected), and **Decimal** numbers. Floats, booleans, NaN and infinity are rejected.

| Contract (brief name) | Class | Source of fields | Key structural rules |
|---|---|---|---|
| ResearchFinding | `ResearchItem` (alias `ResearchFinding`) | Foundation §4.29.1 | canonical `affected` symbols; retrieved ≥ published; unique claim ids |
| ValidatedFact | `ClaimValidation` (alias `ValidatedFact`) | Foundation §4.29.2 | one check per validator; ACCEPTED only if every check accepts and a label exists; a non-accepting check gives a reason; `is_validated_fact` = accepted and FACT |
| MarketSnapshot | `MarketSnapshot` (+ `Candle`, `Quote`, `CandleSeries`) | Foundation §4.7, §4.8, §9.1 | OHLC consistency; strictly ordered series with verified content hash; **no candle or quote after `as_of`**; one instrument |
| AnalysisReport | `AnalysisReport` (+ `Coverage`) | `analysis.created` payload (Foundation §10.1, layer design §4.3) | links required by kind (instrument, market snapshot, research snapshot, coverage); excerpt/chars/sha256 together; **no levels or sizes** |
| TradeProposal | `TradeProposal` (+ `EntrySpec`, `PriceLevel`, `AdvisoryLevels`) | Foundation §4.13 | only Buy/Overweight ratings; Buy at size factor 1; entry = price **or** zone; stop and targets on the correct side; targets distinct and ordered nearest first (a representation order only); `reward_risk` is **provisional** (see below); built only by `trade_proposal_builder` |
| RiskDecision | `RiskDecision` (+ `RiskCheck`) | Foundation §8.1–8.2 | APPROVED / REJECTED / REVIEW; approval needs checks, volume and risk %, no failed checks; REJECTED/REVIEW need reason codes and carry no volume; every failed check is a reason; made only by `risk_engine` |
| OrderIntent | `OrderIntent` | Foundation §4.14 | PAPER or DEMO only (LIVE cannot be expressed); stop-loss and `max_slippage` mandatory; idempotency key = SHA-256(`proposal_id`); level sides checked; built only by `risk_engine` |
| ExecutionResult | `ExecutionResult` | order events, layer design §4.3 | explicit lifecycle status; fills need price and fill id; partial < requested; failures need a reason; only execution agents; the MT5 agent is DEMO only |
| StellarEvent | `StellarEvent` | layer design §4.2 | see §3 |

**Reward:risk is provisional and non-canonical.** How to measure it (which take-profit, which
entry price for a zone) is a trading-methodology decision that has not been made, so the contract
does **not** compute or check it. `TradeProposal.reward_risk` is optional. When present it must be
a typed, finite, positive `Decimal`, but it is kept exactly as the builder stated it. No rule may
use it until the method is decided. The level geometry checks (stop and targets on the correct
side of the whole entry price or zone) do not depend on any reward:risk formula. D-9 remains open.

**Cross-record validation** (`stellar.validation`) reports deterministic problem codes:
- **Decision vs proposal:** same proposal, instrument and run, decided after the proposal.
- **Intent vs proposal and decision:**
  - the decision is APPROVED, and the ids match;
  - the side follows the direction;
  - volume equals the decision's volume;
  - stop, target, order type and price match the proposal;
  - the intent expires no later than the proposal and is created after the decision.
- **Result vs intent:** same ids, instrument, side, mode and volume, and time order.

## 3. Event model

- **Envelope** (layer design §4.2): `event_id` (ULID), `schema_version`, `type`, `ts` (UTC), `seq`,
  `run_id`, `station_id`, `source`, `agent_id`, `room`, `instrument`, `correlation_id`
  (a record id), `payload`.
- **Canonical names only.** The catalogue is the layer design §4.3 set; it includes all 29
  Foundation §10.1 minimum V1 events. Legacy v0.3 names and unknown names are rejected.
- **Payload rules.**
  - Payloads must be JSON.
  - Non-finite numbers are rejected.
  - Secret-bearing keys (`api_key`, `password`, `backend_url`, …) are rejected at any depth.
  - Decision-critical events must carry the payload keys the layer design names (for example
    `risk.approved` needs `proposal_id` and `decision_id`).
- **Deterministic serialization:** canonical JSON (sorted keys, no whitespace, no NaN).
  `content_key()` hashes the event without `seq`.
- **Replay-friendly:** `seq` is empty until the journal assigns it; stored events carry it. JSON
  round-trips exactly. `new_event()` accepts an injected time and random source, so events are
  reproducible in tests.
- **Bus:** `EventBus.publish` writes to the journal first, then delivers the stored event once to
  subscribers. A duplicate `event_id` is not delivered again. A failing subscriber is logged and
  skipped. A journal **write** failure re-raises for `trade.*`, `risk.*`, `order.*` and
  `circuit_breaker.*` events (execution must halt), and is logged for other events.
  Malformed events and id conflicts always raise.

## 4. Journal behaviour

`StellarJournal(path)` is a local SQLite store; `":memory:"` is used for tests.

- **Append-only:** triggers abort any UPDATE or DELETE of events and of the journal metadata.
- **Ordered:** `seq` = previous + 1, assigned inside one `BEGIN IMMEDIATE` transaction, so the
  sequence is contiguous from 1. Journal order is append order, not timestamp order.
- **Validated:** only `StellarEvent`s are accepted, and they are re-validated from data, so a
  `model_construct` bypass is caught. JSON input is parsed and validated first. Caller-supplied
  `seq` is refused.
- **Duplicate-safe:** the same `event_id` with the same content returns the stored copy and writes
  nothing. The same id with different content raises `DuplicateEventConflict`.
- **Integrity:** every read checks the stored body hash and `seq`. `verify()` also checks
  contiguity. A foreign database is refused (format marker).
- **Reads:**
  - `read(since_seq, run_id=, types=, limit=)`, `replay()`, `get(event_id)`, `last_seq()`.
- **Separate from upstream memory:** the journal never reads or writes `TradingMemoryLog`, and its
  default location is `~/.stellar/journal.sqlite3`.

## 4a. Circuit-breaker state (`stellar.risk`)

`CircuitBreakerState` is a **state contract only** (Foundation §4.27, §8.3). It holds no
threshold, evaluates no rule and has **no reset operation**.

| Part | Design |
|---|---|
| `status` | `ARMED` (default) or `TRIPPED`. `trading_blocked` is true when tripped |
| `trip: BreakerTrip` | `cause`: `risk_rule`, `reconciliation_mismatch`, `data_failure`, `budget_exhaustion` or `owner`. Also: `rule` (a `RiskRule`, required for `risk_rule`), `value` / `limit` (Decimal, as observed; no limits defined here), `tripped_by` (technical agent id, or `owner` for a manual trip and only then), `tripped_at`, and the optional `event_id` |
| `last_reset: OwnerReset` | A **record** of a reset: `by` must be the literal `owner`, plus a non-empty `reason`, `reset_at` and the optional `event_id`. Any other value of `by` is rejected |
| `updated_at` | When the state last changed |
| `tripped(trip)` | Pure transition ARMED → TRIPPED. **Sticky:** tripping a tripped breaker returns it unchanged, keeping the first trip |

Rules enforced by validation:
- a TRIPPED state records its trip, and an ARMED state carries no active trip;
- an active trip cannot predate the last reset, and times are ordered.

**Owner-only reset.**
- There is no `reset`, `arm` or `clear` method, and no automatic re-arming on a timer or on
  restart. A test checks the public API for this.
- The owner command that performs a reset, with typed confirmation and a reason, and emits
  `circuit_breaker.reset`, is Phase 3. This contract can only record its result.

**Event compatibility.**
- `BreakerTrip.to_event_payload()` produces a valid `circuit_breaker.tripped` payload: `rule`
  (the rule id, or the cause for non-rule trips), `cause`, `value`, `limit` and `tripped_by`.
- `BreakerTrip.from_event()` rebuilds the trip from such an event for replay.
- Persistence of the state across restarts is Phase 3.

## 5. Configuration model

`StellarConfig` is immutable, loaded once from TOML (`load_config`), and has explicit defaults.

| Section | Phase 1 content |
|---|---|
| `environment` | `development` (default) / `test` / `production` |
| `station_id` | `stellar-01` |
| `execution.mode` | `PAPER` (default). **LIVE is always refused**: it does not exist in V1 and needs a future implementation and explicit owner approval. **DEMO is refused** until the Phase 8 demo gate exists |
| `instruments` | XAU/USD (`XAUUSD`, metal), EUR/USD (`EURUSD`, fx), USD/JPY (`USDJPY`, fx), NAS100 (`NAS100`, index_cfd), each with its display name, currencies, an optional session calendar and flags. There are no broker values |
| `features` | Gates for market data, risk engine, paper broker, technical analysis, research pipeline, LLM agents, MT5 demo bridge, visual API and visual station. All default off, and **a gate for an unimplemented subsystem cannot be enabled** |
| `journal.path` | `~/.stellar/journal.sqlite3` |

- `config_hash()` hashes the canonical form.
- `trading_permitted()` always returns `False` with reasons in Phase 1: no risk configuration or
  risk engine exists, so it fails closed (Foundation §4.26).
- There is no environment-variable overlay. Secrets are never part of the config.

## 6. Agent registry

- **`AgentIdentity` fields:**
  - `code`, `technical_id`, `role`, `group`, `responsibilities`;
  - `kind` (deterministic / llm / hybrid), `source` (STELLAR / UPSTREAM), `llm_tier`;
  - `roster_status` (minimum V1 / deferred / demo gate), `enabled`;
  - `upstream_node` (U1–U8 only), and an optional `display_name`.
- **The roster** is the whole Foundation §5.1 architectural roster: **41 agents**, R1–R6, V1–V4,
  M1, S1–S4, T1–T8, U1–U8, P1–P4, E1–E2, L1–L2 and O1–O2.
- **Enabled flags:**
  - The 36 minimum-V1 roles are enabled; this marks roster membership only, since no runtime
    exists.
  - R3–R6 are deferred and E2 is held for the demo gate. None of these five can be enabled.
- **Rules:**
  - Risk and execution agents must be deterministic.
  - Codes, ids, upstream nodes and display names must be unique, and a display name cannot reuse a
    technical id.
- **Personas:** display personas are not in the repository. `with_display_names()` applies them
  from outside, for example from the owner's local override (visual plan §5).

## 7. Tests

`stellar/tests` has 199 tests, all passing.

| File | Covers |
|---|---|
| `unit/test_core_contracts.py` | valid construction and JSON round trip of every contract; aliases; immutability; unknown fields; schema major version; UTC; canonical instruments; id prefixes; candle, series and snapshot rules (look-ahead); research, validation and analysis rules; number strictness; exact Decimal round trip |
| `unit/test_trade_contracts.py` | proposal ratings, size factor, level geometry, zone edges, provisional (never recomputed) reward:risk, builder identity, advisory levels; decision outcomes and reason codes; intent references, modes, idempotency key, levels; execution lifecycle |
| `unit/test_chain_validation.py` | no intent without an APPROVED decision; every intent / proposal / decision mismatch; result vs intent |
| `unit/test_events_and_journal.py` | ULID reproducibility; catalogue canonicality; legacy names rejected; envelope rules; required payload keys; secret keys; deterministic serialization; journal order, filters, duplicates, conflicts, malformed input, append-only triggers, persistence, tamper detection; bus delivery, duplicate suppression, subscriber isolation, critical-write halt |
| `unit/test_config_and_registry.py` | safe defaults; LIVE and DEMO refused; invalid modes; feature gates; unknown keys; instrument validation; TOML load and stable hash; immutability; roster size, status, lookups, deterministic risk/execution, persona separation, duplicates |
| `unit/test_no_prose_execution_values.py` | every price, volume and ratio field is Decimal; every text field of the proposal, decision, order and result contracts is on an allowlist; no notes field; levels given as prose are rejected |
| `unit/test_circuit_breaker_state.py` | armed default; sticky trips; every documented cause; trip and state consistency; no reset/arm/clear operation; recorded resets are the owner's only; trip ↔ `circuit_breaker.tripped` event round trip; serialization |
| `contract/test_upstream_boundary.py` | upstream (`tradingagents`, `cli`, `tests`, `main.py`) never imports Stellar; the root `pyproject.toml` does not mention Stellar; Phase 1 Stellar code imports no upstream module (checked statically and in a subprocess); Stellar declares its dependency on tradingagents; the registry's upstream node names exist in `graph/setup.py`; the `Rating` enum equals upstream's `RATINGS_5_TIER` + `RATING_REVIEW` |

The upstream suite still passes unchanged: 1139 passed, 1 skipped (a missing optional
`langchain_aws`). `ruff check .` over the whole repository passes.

## 8. Deferred work

- **Foundation Phase 1 items not in this brief:**
  - `.github/workflows/stellar.yml`;
  - the full upstream contract-test set (U1, U2, U4–U12, U15, U16, U22, U29); only node names and
    the rating vocabulary are pinned now;
  - the breaker's tripping rules, its persistence across restarts, and the owner reset command
    (Phase 3);
  - the reward:risk measurement method, if one is adopted, and D-9;
  - journal tables for decision records (the journal stores events only).
- **Contracts for later phases:**
  - `Setup` and its lifecycle, `SessionContext`, `MacroAssessment`, `MarketAssessment`,
    `StructureAssessment`, `MomentumAssessment` and `PriceActionAssessment`;
  - research snapshots, `TradeRecord`, `TradeReview` and settlement.
- **Restricting `OrderIntent` construction to the Risk Engine by module boundary**
  (Foundation §8.4). Today the contract checks `produced_by = risk_engine`, and the chain check
  requires an APPROVED decision.
- **Later-phase items:**
  - market data (Phase 2);
  - risk engine and thresholds (Phase 3);
  - Paper Broker (Phase 4);
  - technical agents (Phase 5);
  - research and LLM integration (Phase 6);
  - MT5 (Phase 8);
  - visual API and renderer (Phases 9–10).

## 9. Deviations from the approved documents

1. **Brief names versus documented names.**
   - `ResearchFinding` and `ValidatedFact` are aliases of the documented `ResearchItem` and of
     `ClaimValidation`. `ClaimValidation` is a new name for the V1–V4 per-claim result, which the
     docs describe without naming.
   - `AnalysisReport` is the common record behind `analysis.created`.
2. **Provenance.** Records carry `provenance` (`produced_by`, `config_hash`, `input_ids`). The
   proposal's documented `config_hash` field is `provenance.config_hash`.
3. **RiskDecision REVIEW.** The brief asked for a REVIEW outcome; it means no approval plus an
   owner flag, and never leads to an order. Reason codes are one per Foundation §8.1 control, plus
   `owner_review_required` and `missing_input`.
4. **OrderIntent fields.** `instrument` and `created_at` are added to the §4.14 field list, for
   chain validation. The `order.created` event already carries the instrument.
5. **Fields defined here, because the docs give none:** `ExecutionResult` (from the order events),
   the `Quote` shape, and `OrderSide` values `BUY` / `SELL`.
6. **Reward:risk is not computed.** Foundation §4.13 lists `reward_risk` as "(computed)", but the
   method is an undecided trading-methodology choice. The field is optional, typed and provisional,
   and no formula is defined.
7. **Execution mode.** It includes `LIVE` as a reserved value that is always refused. Foundation
   §8.1 says LIVE "does not exist in V1"; the brief allowed a disabled placeholder.
8. **Record id prefixes.** The docs name `prop_`, `ord_`, `trade_` and `run_`. The remaining
   prefixes are Phase 1 choices: `ri_`, `clm_`, `val_`, `rsnap_`, `snap_`, `setup_`, `an_`,
   `dec_`, `int_`, `fill_`, `rev_` and `stl_`.
9. **Registry.**
   - `home_room` is not in the technical registry. Rooms belong to the station layer, and VX-1 and
     VX-2 (VW-1) are pending.
   - Technical ids use the visual plan §5.3 proposals (VW-5).
   - LLM tiers for U1, U2 and U4–U7 follow upstream's quick-thinking model.

No visual-world document needed changes: no implementation contradiction was found.
