# Stellar Agents — Foundation Phase 5: Deterministic Technical / Candle / Price-Action Engine

**Status:** implemented, not yet approved. **Base:** Phase 4 at `fed33bd`.

**Scope:** descriptive technical evidence from validated Phase 2 bars. There is:
- no trading decision, no TradeProposal and no Setup;
- no order, no Risk or Paper Broker change;
- no LLM, news, macro, Research Lab runtime, MT5 or visual code.

**Canonical sources:** Foundation §4.9 (indicator pipeline), §4.10 (candle / price action),
§4.11 (structure / pullback), §3 (ARIA concepts: "no ARIA formula, threshold or code is carried
over"), the TradingAgents knowledge audit §5 (upstream indicator defects), and Phase 2 (market
data).

**Scope versus the Foundation plan.** Foundation §11 Phase 5 also lists T6 Pullback / Setup,
T7 Entry Timing, the Setup lifecycle and the P1 deterministic proposal builder. This phase
implements only the evidence layer that those components will consume (T3, T4 and T5
calculations), as the owner scoped it. T6, T7, the Setup lifecycle, P1 and profiles are deferred
(§17, P5-12).

---

## 1. Architecture

```
Phase 2 MarketDataResponse (validated closed bars, source, mapping, quality, freshness)
      │  as_of (explicit), TechnicalConfig (every threshold UNSET by default)
      ▼
stellar.technical.analyse ── bars with close_time <= as_of only
      ├─ candles.py      measurements + rule-based descriptors
      ├─ pivots.py       swings: CONFIRMED (right window closed) / CANDIDATE
      ├─ structure.py    HH/HL/LH/LL/EQH/EQL, state, STRUCTURE_BREAK_UP/DOWN
      ├─ legs.py         impulse legs, current pullback, consolidation
      ├─ sequences.py    run lengths ending at the latest bar
      ├─ volatility.py   TR, ATR (Wilder), range statistics
      ├─ indicators.py   SMA, EMA, RSI, MACD, Bollinger
      ├─ volume.py       real / tick / missing, relative volume
      └─ levels.py       zones from swing clusters, break / retest observations
      ▼
TechnicalAnalysis (typed, hashed, point-in-time)  ──  mtf.analyse_mtf (same as_of, per timeframe)
      ▼
publish.py → analysis.created × 3 (structure / momentum / price_action AnalysisReports)
```

**Package** `stellar/src/stellar/technical/`:
- `config.py`, `models.py`, `numeric.py`;
- `candles.py`, `pivots.py`, `structure.py`, `legs.py`, `sequences.py`, `volatility.py`,
  `indicators.py`, `volume.py`, `levels.py`;
- `engine.py`, `mtf.py`, `publish.py`.

The Foundation plan names `analysis/structure/`, `analysis/indicators/` and
`analysis/price_action/`. One `technical/` package keeps the shared engine and contracts
together. The three facets are still published as the three canonical analysis kinds (§14).

**Changes to existing Stellar code (additive):**
- `config/models.py`: `IMPLEMENTED_FEATURES` adds `TECHNICAL_ANALYSIS`. `trading_permitted()`
  is still always false.

No shared contract changed: `AnalysisReport`, `AnalysisKind` and the `analysis.created` event
are reused as they are.

## 2. Contracts

`TechnicalAnalysis`:
- **Identity:** `engine_version`, `analysis_id` (`an_` + hash), `content_hash`, `instrument`,
  `timeframe`, `as_of`.
- **`source` (`SourceRef`):**
  - provider, provider symbol, mapping kind, price side and volume kind, synthetic flag;
  - the response's `as_of` and series hash, the hash of the bars actually used, the bar count
    and the first / last bar times.
- **`config` + `config_hash`:** every parameter used.
- **Evidence:**
  - `candles` (`CandleEvidence`: `CandleFeatures` + labels + unevaluated);
  - `pivots` (`Pivot`), `structure` (`MarketStructure`: `SwingPoint`s, state, `StructureEvent`s);
  - `legs` (`StructureLeg`), `pullback` (`Pullback`), `consolidation` (`Consolidation`),
    `sequences` (`SequenceEvidence`);
  - `volatility` (`Volatility`), `indicators` (`IndicatorValue`), `ma_ordering`;
  - `volume` (`VolumeEvidence`), `zones` (`PriceZone` with `ZoneEvent`s).
- **Quality:** `limitations` (§12) and `unevaluated` (what was not computed and why).
- **`provenance`:** `technical_engine`, the config hash and the snapshot id if given.

**Its validator refuses** any evidence dated after `as_of`: candle close times, pivot
confirmations, structure events, zone times and leg confirmations.

**Measurements versus labels.** Measurements are facts: prices, differences, ratios, counts
and times. Labels are named observations with an explicit rule (`INSIDE_BAR`, `HH`,
`STRUCTURE_BREAK_UP`, `RETEST_HELD`). There is no buy, sell, bias, entry, stop, target, signal,
probability or profitability field. A test walks the whole contract and fails on that
vocabulary; the only exception is MACD's standard "signal line" period.

## 3. Numbers and precision

- **All arithmetic is `Decimal`,** under one explicit context (`numeric.CALC_CONTEXT`): 34
  significant digits, ROUND_HALF_EVEN. It is applied by every public entry point, so the
  caller's ambient decimal context cannot change a result (tested with precision 6).
- **Prices are never quantised.** Differences and sums of prices are exact; only division and
  square root round, at 34 digits. The source bars' Decimal values are kept unchanged in
  `CandleFeatures`, and EUR/USD five-decimal values survive (tested).
- **No float** is used in any calculation (a boundary test forbids `float` calls in the
  package). Multi-timeframe interval counts use integer microseconds.
- **No upstream code:** `stockstats`, `pandas`, `yfinance` and TradingAgents are not imported
  (boundary test). None of the audit's defects is reproduced: 2-decimal rounding,
  `min_periods=1` partial averages, `adjust=True` EMAs, a first RSI of 50 and `ffill().bfill()`.

## 4. Candle measurements and descriptors

**Measurements (always):**
- open, high, low, close; direction (UP / DOWN / FLAT);
- range, body, signed body, upper and lower wick;
- body / upper-wick / lower-wick ratios to the range, and close location ((close − low) /
  range);
- gap from the previous close;
- true range (high − low for the first bar, flagged);
- relative range (range / mean range of the preceding `relative_range_lookback` bars).

**Zero-range bars:** ratios and close location are `None`, never 0 or an error.

**Descriptors without thresholds (definitions):**
- BULLISH / BEARISH / NEUTRAL (close vs open);
- INSIDE_BAR and OUTSIDE_BAR (strict comparisons; an equal extreme is neither);
- BULLISH_ENGULFING: previous bar bearish, this bar bullish, this body contains the previous
  body and is larger. BEARISH_ENGULFING is the mirror.

**Descriptors with thresholds** (evaluated only when configured):

| Descriptor | Rule |
|---|---|
| DOJI_LIKE | body ratio ≤ `doji_max_body_ratio` |
| SMALL_BODY | body ratio ≤ `small_body_max_ratio` |
| LARGE_BODY | body ratio ≥ `large_body_min_ratio` |
| UPPER_REJECTION / LOWER_REJECTION | wick ratio ≥ `rejection_wick_min_ratio` |
| EXPANSION_BAR / CONTRACTION_BAR | relative range ≥ `expansion_min_relative_range` / ≤ `contraction_max_relative_range` |

**Unset thresholds** are listed as `unevaluated` with reason `threshold_unset`, the analysis
carries `THRESHOLD_UNSET`, and the raw ratios are still reported.

A descriptor observes geometry. None states that a candle predicts anything.

## 5. Pivots (swings) and confirmation

- **Swing high:** the high is strictly greater than the highs of the `left` bars before and
  the `right` bars after it. A swing low is the mirror. Ties are not pivots.
- **CONFIRMED** only when the `right`-th bar after the swing has closed. `confirmed_at` is that
  bar's close time, and `right_bars_seen == right`.
- **CANDIDATE:** it beats its left window and every right-window bar that has closed so far,
  but the window is incomplete at `as_of`. It is reported with `right_bars_seen`, adds the
  `UNCONFIRMED_PIVOT` limitation, and is **never** used by structure, legs or zones.
- **No window configured:** no pivots, and `PIVOT_WINDOW_UNSET`.
- **Evidence:** pivot bar times, price, left/right window, confirmation time and status.

## 6. Market structure

- **Swing labels:** each confirmed swing is compared with the previous confirmed swing of its
  kind, within tolerance t:
  - highs: HH (higher by more than t), LH (lower by more than t), otherwise EQH;
  - lows: HL, LL, otherwise EQL.
- **Tolerance t:**
  - exact (0) when unset, or a price amount;
  - or `atr_multiple` × the ATR **at that swing's confirmation bar** (never today's ATR);
  - if that ATR is not ready, the swing stays unlabelled.
- **State,** from the latest labelled high and low:
  - UP (HH + HL), DOWN (LH + LL), RANGE (EQH + EQL), MIXED (any other combination);
  - INSUFFICIENT (either missing).

  It describes the swing sequence. It is not a bias, and no rule calls anything a reversal.
- **Events:** the first bar that **closes** beyond the latest confirmed swing high / low
  (after that swing's confirmation) is STRUCTURE_BREAK_UP / STRUCTURE_BREAK_DOWN. Wicks do not
  count.
- **`break_against_state`** marks the latest event when it is opposite to the state (a
  "possible structural shift" observation).

## 7. Impulse, pullback, consolidation

**Legs** (impulse measurements):
- *Construction:* between consecutive alternating confirmed swings. Consecutive same-kind swings
  are reduced to the more extreme one (the earlier on a tie).
- *Per leg:* direction, start / end swing and time, bars, net move, path length (sum of
  |close change|), efficiency (|net| / path), cumulative signed body, mean range, range
  expansion vs the preceding bars, and net move / ATR at the end bar. A leg is known from its
  end swing's confirmation.
- *Role:* WITH_STRUCTURE / COUNTER_STRUCTURE relative to the state at `as_of`, otherwise
  UNCLASSIFIED.

**Pullback,** from the end of the last completed leg to `as_of`:
- bars, maximum adverse price, depth, and retracement ratio (depth / |leg net move|; above 1
  means beyond the leg's start);
- the current retracement ratio;
- counts and body totals of bars moving against and with the leg, and the mean close
  location.

**No rule** turns a count of counter-direction candles into a signal: "two or three red candles"
is only a number in this record (tested).

**Consolidation** (the last `consolidation.lookback` bars):
- measurements: high, low, range, net displacement, path, efficiency, overlap ratio
  (consecutive bars whose ranges overlap), mean range, and range / ATR;
- `is_consolidation` is set only when `max_range_atr` and `min_overlap_ratio` are configured and
  ATR is ready. Otherwise it is `None` (unevaluated).

## 8. Sequences

Run lengths ending at the latest bar, with no assumed N:
- consecutive up / down bars and the alternating run;
- shrinking / expanding bodies and ranges, lower highs and higher lows (consecutive strict
  steps);
- upper / lower rejections (`None` when the rejection threshold is unset).

`run_length` and `has_run(predicate, n)` let a caller choose N.

## 9. Support / resistance zones; breakout and retest

- **Tolerance:** `zone_tolerance.price`, or `atr_multiple` × the ATR at `as_of`. Without it, no
  zones (`tolerance_unset`).
- **Clustering:** confirmed swings, in the order they became known, join the first zone whose
  members widened by the tolerance contain them; otherwise they start a new zone.
- **Zone bounds:** [lowest member − t, highest member + t]. A zone always has width, so no
  single exact level is presented.
- **Recorded per zone:**
  - kind: SUPPORT (lows), RESISTANCE (highs) or MIXED;
  - derivation (`confirmed_pivot_cluster`), tolerance and method, source swing ids;
  - `first_known_at` (the first member's confirmation);
  - `interactions` (bars closed after `first_known_at` whose range overlaps the zone) and
    `last_tested_at`.
- **Events and state** (`inside`, `above`, `below`, `above_after_break`, `below_after_break`),
  from the side where the confirming bar closed:
  - CLOSE_ABOVE / CLOSE_BELOW: a close crosses outside the zone (a break);
  - WICK_ABOVE / WICK_BELOW: a bar inside the zone trades beyond it but closes back inside;
  - after a break, RETEST_ATTEMPT (a bar trades back into the zone), then RETEST_HELD (it
    closes outside again on the break side) or RETEST_FAILED.
- **No future touches:** only bars up to `as_of` exist in an analysis, so a later touch cannot
  strengthen an earlier query (tested: 2 interactions early, more later).

## 10. Volatility and indicators

No period is a default: each indicator exists only when configured. Values before the warm-up
are `None`, the indicator is `ready = false`, and `INSUFFICIENT_HISTORY` is set.

| Indicator | Formula | Warm-up |
|---|---|---|
| True range | max(H−L, \|H−C₋₁\|, \|L−C₋₁\|); H−L for the first bar | 1 |
| ATR(n) | Wilder: mean of TR₀..TRₙ₋₁, then (ATR·(n−1)+TR)/n | n |
| SMA(n) | mean of the last n closes | n |
| EMA(n) | seeded with SMA(n); EMA += 2/(n+1)·(close − EMA) | n |
| RSI(n) | Wilder averages of gains and losses (seeded with the mean of the first n changes); 100 − 100/(1+RS); 100 if no losses; **None if no movement** (no invented 50) | n+1 |
| MACD(f,s,g) | EMA(f) − EMA(s); signal = EMA(g) of the line; histogram = line − signal | s+g−1 |
| Bollinger(n,k) | SMA(n) ± k·**population** SD; bandwidth; %B | n |

- **Every value** carries its parameters, warm-up, bars available, readiness, value, previous
  value and slope.
- **Labels are comparisons:** `close_above` / `close_below`, `macd_above_signal`,
  `close_inside_bands`, and `rsi_above_upper` / `rsi_below_lower` only when RSI levels are
  configured. `ma_ordering` lists the moving averages by value once all are ready.
- **Hand-computed fixture values are pinned by tests,** for example on closes 1, 2, 3, 4, 5, 4,
  3: EMA(3) 3.5, MACD(2,3,2) −1/9, signal 1/54, histogram −7/54.
- **Common periods** (9 / 21 / 50 / 200, 14, 12-26-9, 20-2) are not defaults (Foundation §3:
  "periods: RESEARCH / VALIDATE").

## 11. Volume

- **The kind comes from the bars:** `real`, `tick` or `none`. Tick volume is never presented as
  exchange volume; it adds `TICK_VOLUME_ONLY`.
- **Missing volume:** any bar without volume makes volume unavailable (`MISSING_VOLUME`).
  Nothing is filled with zero.
- **Relative volume** = latest / mean of the preceding `relative_volume_lookback` bars. It needs
  that history and a non-zero mean.

## 12. Quality and limitations

| Limitation | When |
|---|---|
| `calendar_naive_context` | Always (no session calendar yet; Phase 2 MD-2) |
| `insufficient_history` | A configured calculation (ATR, indicator, consolidation, ATR-based zone tolerance, structure with a pivot window) lacks history |
| `unconfirmed_pivot` | Candidates exist |
| `pivot_window_unset` / `threshold_unset` | Configuration not given |
| `missing_volume` / `tick_volume_only` | §11 |
| `proxy_source` / `derived_source` | Substitute series (refused unless `allow_substitute_data`) |
| `partial_series` / `gap_detected` / `stale_source` | From the Phase 2 response (calendar-naive; not risk evidence) |
| `synthetic_source` | Synthetic or test data |
| `missing_timeframe` | Multi-timeframe only |

`unevaluated` lists each item not computed and the reason. Nothing degrades silently.

## 13. Multi-timeframe evidence

- **Same `as_of` everywhere:** `analyse_mtf` analyses each timeframe independently with the same
  `as_of`. A higher-timeframe bar still forming at `as_of` is **excluded** (tested with an H4 bar
  closing three hours after `as_of`). No timeframe is resampled from another, and no missing
  bar is synthesised.
- **Per timeframe:** available or not (with the reason), analysis id and hash, last closed bar,
  intervals since it (a calendar-naive number), and structure state.
- **Alignment:**
  - AGREE_UP / AGREE_DOWN / AGREE_RANGE when all comparable states agree;
  - DISAGREE otherwise;
  - INSUFFICIENT with fewer than two comparable timeframes.

  Missing timeframes are listed and add `MISSING_TIMEFRAME`. Readings are ordered from the
  longest timeframe to the shortest.
- **Not a strategy:** agreement is evidence. No timeframe is assigned a strategy role here
  (profiles, D-7, are later work).

## 14. Events

`publish_technical_analysis` uses the **existing** `analysis.created` event; no event name was
added. One analysis becomes three Phase 1 `AnalysisReport`s linked to the Phase 2
`VerifiedMarketSnapshot` of the same series:

| Kind | Agent | Facet |
|---|---|---|
| `structure` | `market_structure` (T3) | swings, structure, legs, pullback, zones |
| `momentum` | `technical_indicator` (T4) | indicators, volatility |
| `price_action` | `price_action` (T5) | candles, sequences, consolidation |

- **Payload:** the technical analysis id and content hash, engine version, timeframe, `as_of`,
  snapshot id, structure state, limitations and the report.
- **Correlation:** `correlation_id` is the technical analysis id.
- **Snapshot check:** a snapshot of another series is refused (`SnapshotMismatch`).
- **Not journaled:** the full evidence. It is reproducible from the same bars, config and engine
  version, and `verify()` checks it (P5-10).

## 15. Point-in-time guarantees

For `as_of = T`:
- no bar closing after T and no unclosed bar is used;
- `as_of` after the response's `as_of` is refused;
- no pivot is confirmed by a bar that had not closed;
- no zone interaction or structure event after T;
- no indicator value from later bars;
- structure tolerances use the ATR at each swing's own confirmation.

**Dedicated test:** for every prefix of a series, the analysis at that point is identical
whether or not later bars exist in the input. **Structural guard:** the contract validator
refuses any evidence dated after `as_of`.

## 16. Determinism and hashing

- **Pure inputs:** no clock, randomness, network or model. A boundary test forbids `random`,
  `secrets`, `time`, network, LLM and broker imports.
- **Hash:** `content_hash` is the canonical SHA-256 of the analysis except its id and hash;
  `analysis_id` is `an_` + its first 40 hex digits.
- **Same result:** the same bars, config, `as_of` and engine version give the same bytes (tested,
  also under a different ambient decimal context). A config change changes the hash, and
  `verify()` detects tampering.

## 17. Research Lab compatibility

The Research Lab (not built here) can consume analyses as data:
- raw measurements, timestamps, `as_of`, parameters (`config`, `config_hash`), deterministic
  evidence ids (`piv_…`, `leg_…`, `zone_…`), source ranges and hashes, engine version, and
  canonical serialisation.
- It is validated logic only: no experimental hypothesis, "research" feature flag or
  profitability claim is in this package. ARIA-inspired *strategy* features belong to the T6 /
  T7 / Research Lab phases and must be off by default there (Foundation §11).

## 18. Tests

The full Stellar suite collects **608 tests, all passing**. The Phase 4 baseline at `fed33bd`
collects 537:

| Change | Tests |
|---|---|
| `unit/test_ta_candles.py` (new): measurements, zero range, precision, descriptors, thresholds, sequences | +15 |
| `unit/test_ta_structure.py` (new): pivots and confirmation, structure, legs, pullback (both directions), consolidation, zones, break / retest, no future touches | +20 |
| `unit/test_ta_indicators.py` (new): TR, ATR, SMA, EMA, RSI, MACD, Bollinger (hand-computed), warm-up, precision, volume | +16 |
| `unit/test_ta_engine_mtf.py` (new): point-in-time, determinism, limitations, proxy, MTF, publishing, no trading vocabulary | +16 |
| `contract/test_upstream_boundary.py`: 4 technical boundary tests + import case | +5 |
| `unit/test_config_and_registry.py`: the unimplemented-gate case for `technical_analysis` is gone | −1 |
| **Total** | **537 + 15 + 20 + 16 + 16 + 5 − 1 = 608** |

**Mutation check.** Each guard was disabled in turn; each time at least one test failed:
- early pivot confirmation;
- using bars after `as_of`;
- a wick counting as a structure break;
- touches before a zone was known;
- a partial SMA warm-up;
- RSI inventing 50;
- early ATR values;
- ties as pivots;
- the pullback depth side;
- non-strict inside bars;
- ignoring missing volume;
- using a forming higher-timeframe bar.

**Fixtures:** `tests/technical_helpers.py` builds labelled synthetic bars through the Phase 2
in-memory source. They are constructed shapes, not market history, and the test configuration
is `test_only`.

## 19. Limitations

- **Calendar-naive:** no session or holiday awareness (weekend gaps are just gaps; MD-2).
- **No resampling:** a timeframe the source does not serve is missing.
- **Recomputation cost:** each analysis recomputes from all bars given (linear in bars; fine
  for Phase 5 volumes).
- **Roles are relative to `as_of`:** leg roles use the structure state at `as_of`. That is
  point-in-time correct, but earlier legs are described relative to today's state.
- **Clustering is order-dependent** (deterministic, documented). Zones are not merged after
  creation.
- **Structure breaks** are reported for the latest confirmed swing high and low only.
- **Not implemented:** pin-bar and "acceptance at a level" descriptors (Foundation §4.10 lists
  pin bars). With the wick ratios and zones they are expressible, but their rules are left to
  the owner (P5-4).

## 20. Unresolved Phase 5 decisions

| # | Decision | Safe default until decided |
|---|---|---|
| P5-1 | Pivot window (left / right) per timeframe | UNSET: no pivots, no structure |
| P5-2 | Candle thresholds (doji, small / large body, rejection wick, expansion / contraction) | UNSET: raw ratios only |
| P5-3 | Equal-swing and zone tolerances (price or ATR multiple) | Exact equality; no zones |
| P5-4 | Pin-bar and level-acceptance definitions | Not defined |
| P5-5 | ATR, MA, RSI (and levels), MACD and Bollinger parameters | UNSET: not computed |
| P5-6 | Consolidation window and classification thresholds | UNSET |
| P5-7 | Relative-range and relative-volume lookbacks | UNSET |
| P5-8 | Ties at pivots (strict), population vs sample SD, EMA seeding, RSI with no movement | Documented choices above; revisit with evidence |
| P5-9 | Which timeframes form each profile (D-7) and their MTF roles | Not assigned |
| P5-10 | Journal the full evidence, or only ids + hashes (current) | Ids + hashes; recompute to verify |
| P5-11 | Session-aware gaps and daily boundaries (MD-2) | Calendar-naive, labelled |
| P5-12 | T6 Pullback / Setup, T7 Entry Timing, the Setup lifecycle, the P1 deterministic proposal builder and profiles (Foundation §11 Phase 5) | Deferred; this phase supplies their evidence only |
