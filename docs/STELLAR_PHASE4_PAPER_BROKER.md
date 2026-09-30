# Stellar Agents — Foundation Phase 4: Paper Broker

**Status:** implemented, not yet approved. **Base:** Phase 3 at `eb16016`.
**Scope:** internal PAPER execution only. No MT5, no Vantage, no broker API or credentials, no
LIVE or DEMO execution, no strategy, indicator, research, news, macro, LLM or visual code.

Canonical sources: Foundation §4.14–§4.16 and §11 (Phase 4), D-8; layer design §4.3 (events);
Phase 3 §11 (current authorisation).

---

## 1. Architecture

```
TradeProposal → RiskService.evaluate → current APPROVED RiskEvaluation
              → RiskService.authorize_intent → OrderIntent (PAPER)
              → PaperBroker.submit(intent, current RiskContext, as_of, market)
                  ├─ ExecutionChecker (P4): PAPER · not expired · breaker · RiskService.confirm_intent
                  │                          · context matches this book · economics agree
                  ├─ order.created → fill (market) / PENDING (limit)
                  └─ process(Quote | Candle, authorisations): expiry · stop / target · marks
                       · a working order fills ONLY under a current authorisation
                         (ExecutionChecker.check_fill → RiskService.confirm_intent);
                         otherwise it becomes BLOCKED
              → Position → TradeRecord (settlement) → account state (journal fold)
```

- **Deterministic.** Time is always the caller's `as_of`. Prices come only from the `Quote` or
  closed `Candle` passed in. Slippage and spread come only from explicit configuration.
  Nothing reads a clock, a random source, the network or a model; a boundary test forbids
  `random`, `secrets`, network, LLM, MT5 and broker-SDK imports in `stellar.execution`.
- **Journal-backed.** Every transition is an event that carries the complete new record. State
  is reconstructed from the journal on every call. No hidden in-memory state is authoritative.
- **Never an approval.** The broker never builds, widens or refreshes a risk approval. It only
  confirms, through Phase 3, that an intent is still currently authorised. It does so at
  submission and again at the moment a working order would fill (§14).

### Package layout

```
stellar/src/stellar/execution/
  config.py    PaperBrokerConfig (D-8 required), SpreadModel, SlippageModel, IntrabarPolicy,
               InstrumentEconomics
  models.py    PaperOrder, PaperFill, Position, TradeRecord, PnL, ConversionRate,
               PaperAccountState, PaperStats, deterministic id derivation
  pricing.py   input checks, bid/ask per side, synthetic spread, slippage (pure)
  pnl.py       price change → money only with economics (and an explicit rate)
  state.py     Book: the journal fold; load_book (reconstruction)
  views.py     PaperRiskInputs: typed read models for RiskContext
  checker.py   ExecutionChecker (P4): the execution-time gate at submission and at fill time;
               CurrentAuthorisation (input); the only builder of FillAuthorisation
  paper.py     PaperBroker: submit, process, expire_due, cancel, close, read models
  broker.py    Broker protocol (Foundation §4.16)
```

The Foundation plan names `execution/broker.py`, `execution/paper.py`, `execution/checker.py`,
`settlement/` and `review/`. Settlement (the `TradeRecord`) lives in `execution/`, because it is
produced by the same transition that closes a position. `review/` (L1 Post-Trade Reviewer) is
deferred (§19).

### Changes to existing Stellar code (all additive)

| File | Change |
|---|---|
| `ids.py`, `schemas/common.py` | `IdKind.POSITION` (`pos_`); `PositionId` and `TradeId` types |
| `schemas/execution.py` | `ExecutionStatus.CANCELLED` and `EXPIRED` (no-fill statuses for working orders) |
| `telemetry/catalogue.py` | `order.cancelled`, `order.expired`, `account.opened`, with required payload keys (§15) |
| `risk/service.py` | `RiskService.confirm_intent(intent, context)`: the Phase 3 current-authorisation checks at execution time. `authorize_intent` and `confirm_intent` share one private check, so neither is weakened |
| `config/models.py` | `IMPLEMENTED_FEATURES` adds `PAPER_BROKER`. `trading_permitted()` is still always false |

---

## 2. Account model

`PaperBrokerConfig`:
- `account_id`, **`account_currency`** and **`starting_balance`** are required, with no default.
  Foundation D-8 leaves both to the owner; the broker cannot be built without them.
- `spread` and `slippage` models are required, with no default (§6, §7).
- `economics`: optional owner-declared money value per instrument (§10).
- `intrabar_policy`: `STOP_FIRST` (§9).
- `max_quote_age_seconds`: optional (P4-3).

The first `PaperBroker` for an account journals `account.opened` with the full configuration and
its hash. After a restart the broker reads it back. A different configuration for the same
account raises `AccountConfigConflict`.

`PaperAccountState` (reconstructed) holds:
- the account id, currency and starting balance;
- **balance**, **realised P&L**, **unrealised P&L**, **equity**, **peak equity**, **open risk**;
- open positions, pending orders and closed trades;
- `unsettled_trade_ids` (closed trades whose money P&L is unknown) and `unvalued_position_ids`
  (open positions without a known unrealised P&L);
- `version` (broker events applied), `seq` (last journal sequence), `as_of` and `config_hash`.

**Unknown vs zero:** `None` is always unknown. A fresh account has realised and unrealised P&L of
exactly `0` (known). An account holding a position without economics has `unrealised_pnl = None`
and `equity = None`.

## 3. Order lifecycle

| Status | Meaning | Event | `ExecutionResult.status` |
|---|---|---|---|
| `PREFLIGHT_FAILED` | Refused before acceptance, with a reason. Does **not** use up the proposal | `order.preflight.failed` | `preflight_failed` |
| `PENDING` | Accepted; a limit order waiting for its price | `order.created` | `acknowledged` |
| `BLOCKED` | Accepted and working, but when it became executable no current authorisation passed. It cannot fill until one does (§14) | `order.preflight.failed` (payload `stage: "fill"`) | `preflight_failed` (with the reason) |
| `FILLED` | Filled completely; a position is open | `order.filled` (+ `position.opened`) | `filled` |
| `REJECTED` | Accepted, then the fill was refused (for example slippage above the maximum) | `order.rejected` | `rejected` |
| `CANCELLED` | A working order cancelled on request, or because the breaker was TRIPPED when it became executable | `order.cancelled` | `cancelled` |
| `EXPIRED` | A working order reached `expires_at` | `order.expired` | `expired` |

- **Order types** are those of the Phase 1 `OrderIntent`: `market` and `limit`. There is no stop
  entry order type.
- A **market** order fills from the submission `Quote` or is REJECTED
  (`market_order_needs_quote`, `slippage_exceeds_max`, `stop_through_fill`,
  `target_through_fill`). It never waits.
- A **limit** order stays PENDING until an eligible input reaches its price, it expires, or it
  is cancelled. When an input reaches its price, it fills only under a current authorisation;
  otherwise it becomes BLOCKED.
- **BLOCKED** is working, not final. It fills at a later executable moment if a current
  authorisation is supplied then. It still expires and can be cancelled. The same block reason
  is journaled once, not on every tick.
- **Partial fills are not simulated.** An order fills completely or not at all.
- **Cancellation:**
  - only working (PENDING or BLOCKED) orders can be cancelled;
  - cancelling a CANCELLED order returns the same result and records nothing (idempotent);
  - any other status raises `OrderNotCancellable` and records nothing.
- **Preflight reasons:**
  - `account_mode_not_paper`, `intent_expired`, `context_after_submission`,
    `context_for_another_proposal`;
  - `circuit_breaker_tripped`, `reevaluation_required`, `intent_not_authorised`,
    `invalid_risk_context`;
  - `broker_state_changed`, `account_currency_mismatch`, `economics_mismatch`;
  - `duplicate_order`, `slippage_unavailable`;
  - at fill time also: `authorisation_required`, `authorisation_terms_changed`,
    `authorisation_not_current`, `intent_after_execution_time`.

## 4. Position model

`Position` fields:
- **Identity and links:**
  - `position_id`, `order_id`, `intent_id` (the accepted order's intent), `proposal_id` and
    `idempotency_key`;
  - `authorised_intent_id` and `decision_id`: the intent and decision whose current
    authorisation opened the position (the submission intent if still current, otherwise the
    fill-time re-authorisation).
- **Trade terms:** `instrument`, `side`, `volume`, `entry_price`, the approved `stop_loss` and
  `take_profit` copied unchanged from the intent, the intent's `max_slippage`, `entry_fill_id`.
- **Timing:** the entry window (`entry_window_start` / `entry_window_end`: a quote's instant or a
  bar's interval), `opened_at`, `updated_at`.
- **Valuation and state:** `mark_price` / `mark_ts`, `unrealised` (a `PnL`), `status`.
- **Not modelled:** leverage, contract size, pip value, margin, swap and financing. None exists
  unless given explicitly.

**Netting / hedging:** each filled order is its own position. Positions are never netted or
merged, and opposite positions on one instrument may coexist. This is the simplest internal paper
model. It does **not** claim to match MT5 or Vantage account behaviour (P4-13).

## 5. Execution prices and bid/ask

- **Quote:** a BUY executes at the **ask** and a SELL at the **bid**. A mid price is never used.
- **Bar:** a `Candle` is on one side (`price_side`). An execution on that side uses the bar as
  it is (`spread_source = bar_side`). The other side needs the owner's synthetic spread; a `mid`
  or `last` bar needs half of it for each side. Without one, the price is unavailable and nothing
  is invented.
- **Inputs refused** (`InvalidMarketInput`, nothing journaled):
  - proxy prices;
  - quotes stamped after `as_of`, and bars closing after it;
  - open bars;
  - input for another instrument;
  - quotes older than `max_quote_age_seconds` when it is set.
- **Time:** `as_of` never moves backwards (`OutOfOrderInput`). An intent cannot be submitted
  before its `created_at`.

**Every `PaperFill` records** the source price, the level (limit / stop / target), the execution
price, the spread and its source, the slippage and its source, the gap flag, the intrabar
ambiguity and its resolution, the source timestamp, the source and provider symbol, `as_of`, and
provenance (`paper_execution`, config hash, input ids).

| Execution | Price (conservative) |
|---|---|
| Market entry | ask (BUY) / bid (SELL) + adverse slippage |
| Limit entry | the limit price, never better; no slippage |
| Stop-loss | the stop; if the market opened beyond it (gap), that worse open; + adverse slippage |
| Take-profit | the target, never better; no slippage |
| Manual close | the exit-side quote price + adverse slippage |

## 6. Spread

- **`QUOTE_ONLY`:** only real quote spreads and native bar sides.
- **`SYNTHETIC_FIXED`:** an explicit owner value per instrument, labelled
  `spread_source = synthetic_config` on the fill and journaled.
- No spread per market is built in.

## 7. Slippage

- **Models:** `ZERO`, or `FIXED` per instrument. Slippage is always adverse and never random; a
  test runs the same scenario three times and gets identical fills.
- **Market entries:** slippage above the intent's `max_slippage` (Phase 3) **rejects** the fill
  (`slippage_exceeds_max`).
- **Stops and manual closes:** slippage is applied and never rejects the exit, because a
  protective exit must execute. If it exceeds the order's `max_slippage`, the exit fill is
  flagged `slippage_breach = true` and `trade.closed` carries `slippage_breach`.
- **Limit entries and targets:** no slippage.
- **`FIXED` without a value for the instrument:** refused at preflight (`slippage_unavailable`).

**What `OrderIntent.max_slippage` means.** The Phase 1 contract (`OrderIntent`) only says the
field is mandatory. Foundation §8.1 defines the control at two stages:
- *order*: "reject order (max deviation)";
- *post-fill*: "breach after fill → event + breaker count".

So it is an **admission limit** for executing an order, plus a **breach record** after a fill. It
is **not** a universal "refuse to execute" limit:
- **Entry (order admission):** a market fill whose slippage exceeds the maximum is refused
  (`slippage_exceeds_max`). Limit entries have no slippage.
- **Protective exits (post-fill):** a stop or manual close is executed, and a slippage above the
  maximum is recorded as a breach on the fill and in `trade.closed`. Refusing a protective exit
  would leave the position open past its stop, which no contract asks for.
- **Not implemented:**
  - the §8.1 "breaker count": §8.1 gives no count or window for breaches, and none is invented
    (P4-14);
  - a dedicated breach event: the breach is carried in `trade.closed` (P4-14).

## 8. Stop-loss and take-profit

- **Triggers:**
  - a long exits on the bid: stop when bid ≤ stop, target when bid ≥ target;
  - a short exits on the ask: stop when ask ≥ stop, target when ask ≤ target.
- **Take-profit:** only the intent's take-profit (the owner's choice under RK-9); none is
  invented. A position without one has no target.
- **On a hit:** a close execution (`PaperFill`, kind EXIT) → `TradeRecord` → `trade.closed`,
  carrying the trade and the closed position → account update.

## 9. Bar ambiguity policy (no hindsight)

- **Stop and target in one bar:** **STOP_FIRST.** The stop is taken, flagged
  `intrabar_ambiguous = true` and `intrabar_resolution = "stop_first"`. This is the conservative
  assumption named in Foundation §4.15.
- **Entry window:**
  - an input that overlaps the entry window (the bar the limit filled in, or a bar already open
    when a quote-driven entry happened) **can trigger the stop** (pessimistic, flagged
    `stop_counted_in_entry_window`) but **never the target**;
  - inputs that end before the entry are ignored.
- **Pending entries** fill only from inputs that start at or after the order was accepted, and
  end before `expires_at`. The submission quote is the one exception, for the order just
  submitted. A bar straddling acceptance or expiry does not fill: it is not known whether the
  touch happened inside the order's life.
- **Gaps:** a stop gapped through fills at the bar's open. A limit or target gapped through
  still fills only at its level.
- **Not implemented:** an "unresolved" mode that halts a position and asks for lower-timeframe
  data (P4-4).

## 10. P&L semantics and currency conversion

- **Price change:** `price_change` (per unit, signed in the position's favour) is always known.
- **Money:** needs the owner's `InstrumentEconomics` (the value of a 1.0 move per lot, and its
  P&L currency). Without it: `MISSING_ECONOMICS`, amount unknown.
- **Other currency:** if the P&L currency is not the account currency, an explicit
  `ConversionRate` (base = P&L currency, quote = account currency, stamped at or before `as_of`)
  must be passed with the operation. Otherwise: `MISSING_CONVERSION`.
- **Rate rules:**
  - rates are never inverted, chained or defaulted;
  - a rate stamped after `as_of` is look-ahead and refused;
  - two different rates for one pair are refused.
- **The rate used** is stored in the `PnL` (provenance).
- **Rounding:** none is applied (P4-5).

## 11. Balance and equity

- **Balance** = starting balance + the sum of realised money P&L. It changes only when a trade
  settles. If any settled trade's P&L is unknown, balance (and realised P&L) is **unknown**, and
  the trade is listed in `unsettled_trade_ids`.
- **Equity** = balance + unrealised P&L, only when both are known.
- **Peak equity** is the highest known equity after any journaled transition.
- **Open risk** is the loss at every open stop, when every one is calculable without a
  conversion.

## 12. Replay and state reconstruction

- **The fold:** `state.load_book(journal, account_id)` applies broker events in journal order.
  Each event carries the complete new record, so the fold is an upsert:
  - `order.filled` also carries the position it opens;
  - `trade.closed` carries the trade and the closed position;
  - so each transition is whole even if a later event of the same call was never written.
- **Derived output:** `account.snapshot.created` (emitted after each state-changing call) is
  never read back. A test checks that it equals the reconstructed state.
- **Tests:**
  - after a restart (a new process on the same journal file), state and statistics are
    identical;
  - the same journal always gives the same state;
  - earlier events are never changed, and `journal.verify()` passes.
  - a BLOCKED order is still BLOCKED after a restart, with its reason; it still cannot fill
    without a current authorisation, and re-feeding the trigger records nothing.

## 13. Idempotency

- **Same intent:** returns the journaled result and records nothing, also after a restart.
- **Same `intent_id`, different content:** raises `OrderConflictError`.
- **Same proposal (idempotency key), second intent:** `duplicate_order`. One proposal has at most
  one accepted order. A preflight failure does not count, so a fresh authorisation can still be
  submitted.
- **Re-feeding an already processed input:** records nothing. Transitions depend only on the
  reconstructed state and the input.
- **Deterministic ids:** order, position, trade and fill ids are derived from the intent id, so
  replays produce the same ids.

## 14. Risk Engine boundary

- **Intake:** the broker accepts only an intent that `RiskService.confirm_intent` confirms. The
  intent must be **exactly** what `authorize_intent` builds from the **latest** journaled
  evaluation of its proposal, and the fingerprint of the given context under the current policy
  must still match. A superseded or stale approval gives `reevaluation_required`, a hand-made or
  tampered intent `intent_not_authorised`.
- **Breaker:** a TRIPPED breaker refuses at submission. A pending order that would fill while
  the breaker is TRIPPED is cancelled instead. Stops and targets still execute, because closing
  reduces risk.
- **Book match:** the context's account, positions, pending orders and order keys must equal
  this broker's current read models. An approval computed against an older book gives
  `broker_state_changed`, so the owner re-authorises.
- **Economics:** the risk metadata's account currency and value per move must agree with the
  broker's economics.
- **At fill time (working orders):** see below. An accepted order is never a lasting ticket.
- **Read models for Phase 3 (RK-11):**
  - `PaperBroker.risk_inputs(as_of)` returns `AccountRiskState` (None when equity is unknown),
    `PositionState`s, `PendingOrderState`s and the accepted order keys, with
    `source = "paper_broker"`;
  - `stellar.risk` never imports `stellar.execution` (boundary test).

### Fill-time re-authorisation (working orders)

When a PENDING or BLOCKED limit order becomes executable (an eligible input reaches its price),
the broker does, in order:
1. **Breaker TRIPPED** → the order is **CANCELLED** (`circuit_breaker_tripped`). It never fills.
2. **A current authorisation is required.** The caller passes
   `process(..., authorisations=[CurrentAuthorisation(order_id, intent, context)])`, where
   `context` is the caller's *current* `RiskContext` for the proposal. The Execution Checker
   (`check_fill`) refuses unless:
   - an authorisation was offered **for this order** (`authorisation_required`);
   - the intent repeats the order's economic terms exactly (`INTENT_TERMS`: proposal,
     instrument, side, volume, type, price, stop, target, `max_slippage`, idempotency key, mode,
     broker symbol) (`authorisation_terms_changed`);
   - the context is at least as recent as the triggering input (a bar's close, or the quote's
     time), and for a quote trigger it carries that quote or a newer one
     (`authorisation_not_current`). An approval can never predate the data that fills it;
   - all submission checks pass again, including **`RiskService.confirm_intent`**: the intent is
     exactly what Phase 3 builds from the **latest** journaled evaluation of the proposal, and
     the fingerprint of the context under the **current** policy matches
     (`reevaluation_required`);
   - the context's account, positions, pending orders and order keys equal the book the order
     fills into: the current book **without the order itself** (`broker_state_changed`);
   - economics agree.
3. **If it passes** → FILLED. The order stores the `FillAuthorisation` (stage `FILL`, intent id,
   decision id, evaluation fingerprint, context `as_of`, `confirmed_at`), and the position and
   trade reference that decision and fingerprint.
4. **If it fails** → **BLOCKED** with the reason (`order.preflight.failed`, `stage: "fill"`). It
   does not fill.

**Consequences:**
- The submission approval is reused only while **every** fingerprinted input is unchanged,
  including `as_of` and the quote. In practice a later price tick needs a new evaluation.
- **Context changed** (equity, daily P&L, positions, pending orders, exposure, quote or spread,
  metadata, `as_of`): the old approval cannot fill. The caller evaluates again (Phase 3,
  journaled) against `risk_inputs(as_of, excluding_order_id=...)` and the current market data,
  obtains a new intent with the same terms through `authorize_intent`, and offers it.
- **If the re-evaluation sizes differently** (for example equity moved enough to change the
  volume), the terms differ and the order cannot fill (`authorisation_terms_changed`). It stays
  BLOCKED until it expires or is cancelled (P4-8).
- **Policy changed:** the fingerprint under the current policy differs, so
  `reevaluation_required`; only a new evaluation under the new policy can authorise.
- **Nothing is created or mutated:** the broker never creates a proposal, decision or intent.
  Old evaluations and intents stay in the journal unchanged; the fill references the one that
  was current.
- **Guarded by construction:** `FillAuthorisation` is built only in `checker.py` (AST test).
  `PaperBroker._open`, the only place a position is created, refuses anything that is not a
  `FillAuthorisation` confirmed at that moment. A market order fills in the submission call
  under the submission authorisation. The submission authorisation also covers a marketable
  limit only for the submission quote, in the same call.
- **Book timing:** the fill-time book is the journaled book before the triggering input is
  applied; marks from that input are applied after fills in the same step (P4-15).

## 15. Events

| Event | Required keys (catalogue) | Also carries |
|---|---|---|
| `account.opened` **(new)** | `account_id`, `currency`, `starting_balance` | config, config hash |
| `order.preflight.failed` | `order_id`, `reason` | the order record; `stage: "fill"` when a working order is BLOCKED |
| `order.created` | `order_id`, `intent_id`, `idempotency_key`, `mode` | the order record |
| `order.filled` | `order_id`, `fill_price`, `filled_volume` | fill and position records, `authorised_intent_id`, `authorisation_stage` |
| `order.rejected` | `order_id`, `reason` | the order record |
| `order.cancelled` **(new)** | `order_id` | reason, the order record |
| `order.expired` **(new)** | `order_id` | the order record |
| `position.opened` / `position.updated` | — | the position record |
| `trade.closed` | `trade_id` | trade and closed-position records, `slippage_breach` |
| `account.snapshot.created` | — | the derived account state |

- **Common payload:** `account_id` and `as_of`; order events also carry `proposal_id`,
  `intent_id`, `decision_id` and `status`.
- **Envelope:**
  - `source = stellar.paper_broker`, `agent_id = paper_execution`;
  - `correlation_id` is the `proposal_id`, the `instrument` is set, and `ts` is the operation's
    `as_of`;
  - order and trade events are critical domains: a journal failure raises.
- **Why the three new events:**
  - a pending order can now end without a fill, and no canonical event named that;
  - a paper account's starting balance and currency must be journaled for reconstruction, and no
    event recorded an account's creation;
  - the position close uses the existing `trade.closed`; no `position.closed` event was added.
- **No secrets:** events carry no secret keys (Phase 1 envelope check).

## 16. ExecutionResult

Built from the actual order record:
- the status mapping of §3 (BLOCKED maps to `preflight_failed` with its reason: at that moment
  the fill-time preflight failed; the order itself stays working);
- `filled_volume` is the full volume only when a fill exists;
- the fill id, fill price and slippage, and the reason for `preflight_failed` / `rejected`;
- `ts` is the last transition time, and provenance is `paper_execution`.

It is never `filled` without a deterministic fill, and it passes the Phase 1
`validate_execution_result` against its intent.

## 17. Trade history

`TradeRecord` holds:
- the ids: `trade_id`, `position_id`, `proposal_id`, `intent_id`, `order_id`, and the
  `authorised_intent_id`, `decision_id` and `evaluation_fingerprint` of the authorisation the
  entry filled under;
- the terms: instrument, side, volume, stop and take-profit;
- both fills (entry and exit, each fully priced) and `close_reason` (`STOP_LOSS`,
  `TAKE_PROFIT` or `MANUAL`);
- `realised` (a `PnL`, possibly unknown with its reason), `opened_at`, `closed_at` and
  provenance.

**Statistics** (`PaperStats`) are counts only: submitted, preflight-failed, accepted, pending,
blocked, filled, rejected, cancelled, expired, open positions and closed trades. There is no performance
scoring.

---

## 18. Tests

The full Stellar suite collects **537 tests, all passing**. The Phase 3 baseline at `eb16016`
collects 423:

| Change | Tests |
|---|---|
| `unit/test_pb_account_intake.py` (new): configuration, account, intake, idempotency, input checks | +32 |
| `unit/test_pb_execution.py` (new): bid/ask, spread, slippage, limits, expiry, cancel, breaker | +20 |
| `unit/test_pb_positions_pnl.py` (new): positions, SL/TP, gaps, ambiguity, P&L, currencies | +23 |
| `unit/test_pb_replay_boundary.py` (new): restart, replay, immutability, events, Risk boundary | +13 |
| `contract/test_upstream_boundary.py`: 4 new boundary tests + `stellar.execution` import case | +5 |
| `unit/test_pb_pending_reauthorisation.py` (new): fill-time re-authorisation, BLOCKED, `max_slippage` breach | +20 |
| `unit/test_rk_breaker_service.py`: `confirm_intent` | +2 |
| `unit/test_config_and_registry.py`: the "unimplemented gate is refused" case for `paper_broker` is gone (now implemented); the gate test is renamed for Phase 4 | −1 |
| **Total** | **423 + 32 + 20 + 23 + 13 + 20 + 5 + 2 − 1 = 537** |

With fill-time re-authorisation, 30 existing tests that filled a working order now fill it
through `Desk.fill_with` / `Desk.reauthorise` (`tests/broker_helpers.py`). These helpers run a
real Phase 3 evaluation and `authorize_intent` at the fill time, against the book the order
fills into. The linked-ids test now asserts that the position references the fill-time
decision. `risk_helpers.market` gained an optional `at` time (default unchanged).

**Mutation check.** Each guard was disabled in turn, and at least one test failed every time:
- stop-first on ambiguous bars;
- the maximum-slippage check;
- bid/ask selection (a mid price was substituted);
- the breaker pre-check;
- Phase 3 confirmation;
- the book-match check;
- no target in the entry window;
- the breaker at pending fills;
- no hidden conversion;
- no invented spread;
- submission idempotency;
- fill time:
  - the terms check;
  - context recency (bar trigger);
  - the context carrying the triggering quote;
  - `confirm_intent`;
  - the book match;
  - excluding the order from its own book;
  - an authorisation used only for its own order;
  - the breach flag.

**Fixtures:** all prices, balances, spreads, slippages and economics in `tests/broker_helpers.py`
and the tests are labelled synthetic test fixtures. They are not historical data, defaults or
recommendations.

## 19. Limitations

- No partial fills, partial closes, stop entry orders, trailing stops or multiple targets.
- No swap, commission, financing or margin (Foundation §4.15: configurable costs, off until
  modelled).
- **Exits need a price on their own side.** With `QUOTE_ONLY` and one-sided bars, the other
  side's stop cannot be evaluated, so the position is not protected in the simulation until a
  quote arrives (P4-10). A test covers this.
- A journal call writes several events without a multi-event transaction. Each event is complete
  on its own (§12), but a crash can leave, for example, a fill without its snapshot.
- State is reconstructed by reading the account's events on every call, which is linear in
  history. This is acceptable for Phase 4 volumes.
- **Deferred Phase 4 objectives from the Foundation plan:**
  - the E1 Paper Execution Agent runtime (the broker already records `paper_execution` as the
    producer);
  - the L1 deterministic Post-Trade Reviewer (`review/`);
  - broker reconciliation.

  They are listed here rather than implemented, per this phase's scope.

## 20. Unresolved Phase 4 decisions

| # | Decision | Safe default until decided |
|---|---|---|
| P4-1 | D-8: paper account currency and starting balance | Required config, no default; tests use labelled fixtures |
| P4-2 | Put `PaperBrokerConfig` in `StellarConfig` or keep it a separate owner file (like RK-1) | Separate; validated on construction |
| P4-3 | A maximum quote age for fills | Optional; not checked when unset. The Phase 3 risk rule still checks quote age at evaluation |
| P4-4 | An "unresolved" intrabar mode (halt and require lower-timeframe data) in addition to STOP_FIRST | STOP_FIRST only, flagged on the fill |
| P4-5 | Currency rounding of money figures | No rounding; exact `Decimal` |
| P4-6 | Settling a trade whose P&L was unknown (a late conversion rate) | Balance stays unknown; the trade is listed as unsettled |
| P4-7 | Swap / commission / financing models | Off |
| P4-8 | Whether a proposal whose accepted order was REJECTED, CANCELLED or EXPIRED may be retried | No: one accepted order per proposal (the key is used) |
| P4-9 | *Resolved:* a working order fills only under a current authorisation confirmed by Phase 3 at fill time; otherwise BLOCKED (§14) | — |
| P4-10 | Exit evaluation when the exit side has no price (QUOTE_ONLY with one-sided bars) | Not evaluated; nothing invented |
| P4-11 | A daily P&L read model (`DailyRiskState`), which depends on the trading-day definition (RK-6) | Caller-supplied |
| P4-12 | Multi-event atomicity in the journal | Self-contained events (§12) |
| P4-13 | Netting vs hedging (and later matching the broker's model) | Independent positions; no MT5/Vantage claim |
| P4-14 | Foundation §8.1 post-fill slippage "event + breaker count": the count and window that would trip the breaker, and whether a dedicated event is added | Breach recorded on the exit fill and in `trade.closed`; no counting, no trip |
| P4-15 | Whether the fill-time book should include the triggering input's own marks (equity at that tick) | The journaled book before the input; marks from the input apply after fills |
| P4-16 | Whether a BLOCKED order whose re-evaluation sizes it differently should be replaceable (it cannot be under one accepted order per proposal) | Stays BLOCKED until it expires or is cancelled |
