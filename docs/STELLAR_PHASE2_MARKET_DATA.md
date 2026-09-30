# Stellar Agents — Foundation Phase 2: Market Data

| | |
|---|---|
| **Status** | Phase 2 market-data foundation implemented; not yet committed |
| **Implements** | `docs/STELLAR_FOUNDATION_PLAN.md` §4.1 (market-data abstraction), §4.2 (symbol normalisation), §4.3–4.6 (instrument records), §4.7 (timeframes), §4.8 (candles) and §11.2 Phase 2, within the scope of the owner's Phase 2 brief |
| **Builds on** | Phase 1 contracts (`docs/STELLAR_PHASE1_IMPLEMENTATION.md`); knowledge audit findings K1–K5, K17 (`docs/STELLAR_TRADING_KNOWLEDGE_AUDIT.md`) |
| **Does not include** | Indicators, candle patterns, price action, strategy, news, macro, risk thresholds, execution, MT5, live feeds or streaming, visual code, Research Lab implementation |

---

## 1. Package layout

```
stellar/src/stellar/marketdata/
  __init__.py            public API
  instruments.py         canonical instrument registry (InstrumentSpec, precision/contract/session placeholders)
  symbols.py             provider symbol mappings (EXACT / PROXY / DERIVED / UNSUPPORTED),
                         SubstitutionPolicy, SymbolMap, TRADINGAGENTS_YAHOO_REFERENCE (data only)
  timeframes.py          durations and parsing
  contracts.py           MarketDataRequest / Response, QuoteResponse, MarketDataSourceInfo,
                         MarketDataQuality, DataIssue, Freshness, MarketDataError, candle_columns
  validation.py          series validation (report, never repair) with explicit policies
  pointintime.py         no-look-ahead helpers
  freshness.py           freshness evaluation and gap detection
  source.py              MarketDataSource protocol + BaseMarketDataSource safety pipeline
  snapshot.py            VerifiedMarketSnapshot + build_verified_snapshot
  providers/
    csv_file.py          local CSV provider (CsvFileSpec, read_csv, CsvFileProvider)
    memory.py            in-memory provider (tests, fixtures, later simulation/research)
stellar/tests/
  md_helpers.py          synthetic test helpers
  fixtures/synthetic_*_h1.csv   four SYNTHETIC fixture files, labelled in their first line
  unit/test_md_*.py      Phase 2 tests
```

### Changes to Phase 1 code (all backward compatible)

| File | Change |
|---|---|
| `schemas/market.py` | `Candle.volume` is now optional; absent volume is `None` with `volume_kind="none"`, never a fake zero. The two must agree. `Candle` gains optional `tick_volume` and `quality_flags`. New `DataQualityFlag` enum. Phase 1 candle records remain valid |
| `schemas/common.py` | `AssetClass` moved here, so market data and config share one enum |
| `config/models.py` | `AssetClass` imported from `schemas.common` (still exported by `stellar.config`). `IMPLEMENTED_FEATURES = {MARKET_DATA}`. New `market_data.max_staleness_intervals` (default `None`, meaning no threshold chosen). Trading is still never permitted |
| `config/__init__.py` | Exports `MarketDataConfig` |
| `tests/unit/test_config_and_registry.py` | The gate test now refuses every gate *except* the implemented one; two new tests cover the market-data gate and the staleness setting |
| `tests/contract/test_upstream_boundary.py` | Import-isolation check extended to `stellar.marketdata`; new contract test pinning upstream's symbol substitutions |

`MarketSnapshot` (Phase 1) is unchanged. It remains the multi-timeframe decision-cycle input that
the Data Validator (T1) will assemble.

---

## 2. Contracts

`Candle`, `Quote`, `CandleSeries` and `Timeframe` are the Phase 1 contracts; Phase 2 does not
duplicate them.

**Candle**
- Carries: instrument, timeframe, `open_time` (the bar timestamp), `close_time`, open/high/low/close
  (Decimal), optional `volume` with its `volume_kind`, optional `tick_volume`, `price_side`,
  `source` (provider id), `provider_symbol`, `proxy`, `is_closed` and `quality_flags`.
- Rejected at construction:
  - high below open/close, or low above them;
  - NaN or infinity;
  - booleans or floats used as numbers;
  - negative volume;
  - naive timestamps;
  - a close time not after the open time.

**New contracts (`marketdata/contracts.py`):**

| Contract | Purpose |
|---|---|
| `MarketDataRequest` | instrument, timeframe, **`as_of` (required)**, optional `start` / `end` (`open_time` window), `substitution` (default: exact only), `max_staleness_intervals` |
| `MarketDataResponse` | request, source info, the mapping actually used, `series` (a `CandleSeries` or `None`), quality, freshness, `retrieved_at`. **Its validator refuses** bars after `as_of`, unclosed bars, bars outside the window, other instruments or timeframes, a proxy/derived mapping the request did not allow, a missing `PROXY_SOURCE` / `DERIVED_SOURCE` flag, bars not labelled with the provider and symbol actually used, and any data carrying validation errors |
| `QuoteResponse` | one point-in-time quote with its source and mapping; same labelling rules |
| `MarketDataSourceInfo` | provider id, name, kind (`LOCAL_FILE`, `IN_MEMORY`, `HISTORICAL_API`, `BROKER`), price side, volume kind, declared precision, timestamp convention, daily-bar boundary, quote support, limitations, and `synthetic` |
| `MarketDataQuality` | sorted, unique `DataQualityFlag`s; typed `DataIssue`s (code, severity, message, file line, open time); bar count; gap count; observed and declared price decimals |
| `MarketDataError` | exception with a typed `ErrorCode` (`UNKNOWN_INSTRUMENT`, `UNSUPPORTED_INSTRUMENT`, `UNSUPPORTED_TIMEFRAME`, `UNSUPPORTED_OPERATION`, `PROXY_NOT_ALLOWED`, `DERIVED_NOT_ALLOWED`, `NO_DATA`, `VALIDATION_FAILED`, `SOURCE_UNAVAILABLE`, `MALFORMED_SOURCE`), the detail, and every `DataIssue`; `to_record()` for journaling |
| `candle_columns()` | column view for research code; returns the original `datetime` / `Decimal` objects, unconverted |

---

## 3. Instrument model

`INSTRUMENTS` holds one `InstrumentSpec` per canonical id:

| Id | Display | Asset class | Base / quote |
|---|---|---|---|
| `XAUUSD` | XAU/USD | metal | XAU / USD |
| `EURUSD` | EUR/USD | fx | EUR / USD |
| `USDJPY` | USD/JPY | fx | USD / JPY |
| `NAS100` | NAS100 | index_cfd | — / USD |

- **Precision, contract and session are placeholders.** `PrecisionSpec(price_decimals=None,
  source="unset")`, `ContractSpec` and `SessionSpec` stay unset until the broker, provider or owner
  declares them (Foundation §6: execution values come from the broker). `with_runtime_metadata()`
  applies declared values without touching identity.
- **Only canonical ids are accepted.** `get_instrument` refuses display names and provider symbols
  (`"XAU/USD"`, `"GC=F"`, `"^NDX"`).
- **The registry agrees with the Phase 1 config defaults**, and a test enforces it.

---

## 4. Provider abstraction

`MarketDataSource` (a protocol) offers:
- `info()`, `instruments()`, `timeframes(instrument)`, `mapping(instrument)`,
  `metadata(instrument)`;
- `candles(request)` and `quote(instrument, as_of, substitution)`.

Foundation §4.1's `candles(instrument, timeframe, start, end, as_of)` arguments travel in
`MarketDataRequest`.

`BaseMarketDataSource` gives **every** provider the same pipeline:

1. **Resolve the mapping:**
   - UNSUPPORTED → `UNSUPPORTED_INSTRUMENT`;
   - PROXY / DERIVED → `PROXY_NOT_ALLOWED` / `DERIVED_NOT_ALLOWED`, unless explicitly allowed.
2. **Unsupported timeframe** → `UNSUPPORTED_TIMEFRAME`.
3. **Check source labels:** each bar must carry the provider id, the mapped symbol and the matching
   `proxy` label, or the error is `MALFORMED_SOURCE`.
4. **Validate the whole series.** Any ERROR raises `VALIDATION_FAILED` with every issue listed.
5. **Keep only bars with `close_time <= as_of`**, then apply the window.
6. **Derive quality flags** for the returned slice: gaps, missing volume, partial coverage, proxy or
   derived, stale. Source-level warnings (sorting, dropped duplicates, precision loss) carry over.
7. **Evaluate freshness** and set `retrieved_at` from an injectable clock, so tests are
   deterministic.

**Instruments with no data at `as_of`.** A response with `series=None`, `bar_count=0` and freshness
`NO_DATA`, not an error. The snapshot builder refuses such a response.

---

## 5. Local file provider

`CsvFileProvider(provider_id, name, files=[CsvFileSpec…], price_side, volume_kind, synthetic,
limitations, clock, duplicate_policy, order_policy)`.

**Spec.** Each `CsvFileSpec` declares:
- the path, instrument, timeframe and provider symbol;
- the mapping kind (EXACT by default; PROXY and DERIVED need a description);
- an optional `naive_timezone` (IANA) and `declared_price_decimals`.

The instrument is **never inferred from the file name**. A test uses a file named `XAUUSD_H1.csv`
declared as EUR/USD.

**Format:**
- **Comment lines.** Optional leading `#` lines, kept as notes (the fixtures start with
  "SYNTHETIC TEST DATA").
- **Columns.** A header with required `timestamp, open, high, low, close` and optional
  `close_time, volume, tick_volume`. Unknown or repeated columns are errors: an `adj_close` column
  would mean adjusted, not raw, prices.
- **`timestamp`** is the bar open time in ISO 8601:
  - with an offset, it is converted to UTC;
  - without one, it needs the spec's `naive_timezone`;
  - ambiguous and non-existent daylight-saving wall times are errors.
- **`close_time`** defaults to `timestamp` plus the timeframe duration.
- **Numbers** are parsed as `Decimal` from the text as written.
  - Empty required values, non-numbers, `NaN`, `inf` and `true` are errors.
  - An empty optional `volume` means **no volume** (`None`), not zero.
- **Every problem is reported with its file line.** The file is rejected, never patched.

**Explicit policies (defaults reject):**
- `OrderPolicy.SORT` sorts an out-of-order file and flags `OUT_OF_ORDER`.
- `DuplicatePolicy.DROP_IDENTICAL` drops exact duplicates and flags `DUPLICATE_BAR`.
- Conflicting duplicates are always rejected.

`read(instrument, timeframe)` returns the raw parse (`CsvImport`: candles, file lines, issues,
notes) for inspection, with no point-in-time cut.

`InMemoryMarketDataSource` serves pre-built `Candle` and `Quote` objects through the same pipeline,
and is the only Phase 2 provider with quotes.

---

## 6. Precision rules

1. **No rounding anywhere.** Values are `Decimal` parsed from the source text. Floats are refused at
   the contract.
2. **Serialization keeps the written digits.** Pydantic JSON writes `Decimal` as its string:
   `1.08537` stays `"1.08537"`, and `1.08510` keeps its trailing zero.
3. **`observed_price_decimals`** is reported per response.
4. **A source may declare its precision.** Prices with more decimals than declared are an error
   (`PRECISION_EXCEEDS_DECLARED`). If the instrument's precision is known and the source declares
   fewer decimals, the data is kept and flagged `SOURCE_PRECISION_LOSS`.

Tests prove exact round trips for EUR/USD `1.08537` (5 dp), USD/JPY `149.872` (3 dp), XAU/USD
`2386.35` (2 dp), NAS100 `18477.00` (2 dp, trailing zero kept) and a 5-dp USD/JPY value
`149.87215`.

---

## 7. Proxy rules

1. **Mapping kinds.** A provider symbol never redefines an instrument; each mapping is EXACT, PROXY,
   DERIVED or UNSUPPORTED.
2. **Opt-in only.**
   - `SubstitutionPolicy()` accepts exact data only.
   - A proxy needs `allow_proxy=True`; derived data needs `allow_derived=True`, separately.
3. **A permitted proxy is labelled everywhere:**
   - the canonical instrument stays the requested one;
   - `mapping.provider_symbol` records what was actually used;
   - every bar has `proxy=True` and that provider symbol;
   - the response carries `PROXY_SOURCE` (or `DERIVED_SOURCE`).
4. **Upstream reference.** `TRADINGAGENTS_YAHOO_REFERENCE` records how upstream TradingAgents
   resolves the four instruments, classified by Stellar:
   - `XAUUSD → GC=F` and `NAS100 → ^NDX` are **PROXY**;
   - the FX `=X` symbols are EXACT.

   A contract test reads upstream's alias table (without importing upstream) and fails if upstream
   changes, forcing a re-classification.

---

## 8. Freshness

`Freshness` records:
- `as_of` and `retrieved_at`;
- `source_timestamp` (newest bar close, or quote time);
- the expected interval;
- `intervals_behind` and `max_staleness_intervals`;
- `status` and `stale_reason`.

| Status | When |
|---|---|
| `NO_DATA` | no bar at or before `as_of` |
| `UNKNOWN` | no threshold configured (the default): no staleness is claimed |
| `FRESH` / `STALE` | whole intervals from the newest close to `as_of` ≤ / > the threshold |

- A source timestamp after `as_of` is refused.
- The threshold comes from the request, which a caller can fill from
  `config.market_data.max_staleness_intervals`.
- There is no market-hours logic, because session calendars are not implemented. A weekend
  therefore reads as intervals behind, and the threshold must be chosen with that in mind.
- **Freshness is calendar-naive.** See §15.1 for what that means and how its results may be used.

---

## 9. Quality flags

`DataQualityFlag`:

| Flag | Meaning |
|---|---|
| `MISSING_VOLUME` | at least one bar has no volume |
| `DUPLICATE_BAR` | identical duplicates were dropped by explicit policy |
| `GAP_DETECTED` | missing intervals between bars; reported with `Gap` records, never filled |
| `STALE` | older than the configured threshold |
| `PROXY_SOURCE` | data is from a proxy instrument |
| `DERIVED_SOURCE` | data is derived |
| `OUT_OF_ORDER` | bars were sorted by explicit policy |
| `INVALID_PRICE_RELATION` | reserved for bar-level reporting; such bars are rejected, with issue code `INVALID_PRICE_RELATION` |
| `SOURCE_PRECISION_LOSS` | the source declares fewer decimals than the instrument |
| `PARTIAL_SERIES` | the returned bars do not cover the requested `start` / `end` window |

**Issue severities.**
- **ERROR** rejects the data.
- **WARNING** keeps it and flags it.

Codes and severities are typed. Messages are for humans only.

---

## 10. Look-ahead safety

- A bar is known only once it has closed: `close_time <= as_of`.
  - A bar that opened before `as_of` but is still forming is excluded.
  - A request with `as_of = T` never returns a bar that closes after T.
  - A bar closing exactly at T is included.
- Quotes are known when `ts <= as_of`.
- **Enforced three times:**
  1. by the base pipeline (`known_at`);
  2. by the `MarketDataResponse` / `QuoteResponse` validators (a hand-built response with a later
     bar cannot exist);
  3. by `Freshness` (no source timestamp after `as_of`).
- **Helpers:** `known_at`, `in_window`, `assert_no_look_ahead` (raises `LookAheadError`),
  `latest_quote_at`.

---

## 11. Verified market snapshot

`build_verified_snapshot(response, snapshot_id, created_at, config_hash, quote=None)` is adapted
from TradingAgents' verified snapshot (knowledge audit K17), without its 2-dp formatting, proxying
or indicators.

**Fields:**
- instrument, timeframe, `as_of`, `created_at`;
- **`latest_bar`** (the validated bar object itself);
- an optional **`latest_quote`**, with its source and mapping;
- `bar_count`, first open and last close times, and the series hash;
- source info, mapping, quality, freshness;
- provenance (`produced_by="data_validator"` and the config hash).

**Rules:**
- Every price in it was present in the validated input, with its original precision. The only
  derived values are counts, timestamps taken from the bars, and the hash.
- No indicator is computed.
- Proxy labels carry through.
- An empty response or a later-dated quote is refused.
- A snapshot with a bar or quote after `as_of` cannot be constructed.

---

## 12. Research Lab compatibility

The contracts give the future Research Lab what it needs:
- **historical ranges:** `start` / `end` / `as_of`;
- **stable UTC timestamps**;
- **normalized access:** `candle_columns`;
- **deterministic serialization:** canonical JSON and the series `content_hash`;
- **provenance:** provider, symbol, mapping kind, synthetic flag;
- **explicit `as_of` boundaries with no look-ahead.**

The Research Lab itself is not implemented.

---

## 13. Tests

The full Stellar suite collects **314 tests, all passing**. The Phase 1 baseline at `b151851`
collects 199. The difference is +115:

| Change | Tests |
|---|---|
| Four new market-data test files | +113 |
| `unit/test_config_and_registry.py`: the parametrized "unimplemented gate is refused" test no longer has a `market_data` case, because that gate is now implemented | −1 |
| `unit/test_config_and_registry.py`: two new tests | +2 |
| `contract/test_upstream_boundary.py`: one new test | +1 |
| **Total** | **199 + 113 − 1 + 2 + 1 = 314** |

No test was changed to make these numbers match.

| File | Tests | Covers |
|---|---|---|
| `unit/test_md_instruments_timeframes.py` | 28 | registry; config agreement; canonical-id-only lookup; runtime metadata; mapping rules; unsupported default; substitution policy; upstream reference classification; durations; timeframe parsing and rejection |
| `unit/test_md_validation.py` | 23 | bar-level rejection (OHLC, NaN, infinity, bool, float, negative volume, naive time); optional volume; Phase 1 candle compatibility; series rules (mismatch, unclosed, duration, order, duplicates, conflicts, overlaps, gaps, missing volume, declared precision, precision loss); freshness |
| `unit/test_md_csv_provider.py` | 35 | synthetic labels; protocol and capabilities; no filename inference; **precision for all four instruments and EUR/USD 1.08537 round trip**; UTC normalisation; naive, ambiguous and non-existent times; 11 malformed-input cases; file line numbers; empty and absent volume; order and duplicate policies; gaps; declared precision; duplicate registration; unreadable file |
| `unit/test_md_safety_and_snapshot.py` | 27 | **proxy refused by default (XAU/USD→GC=F, NAS100→^NDX, in memory and from CSV)**; explicit opt-in labelled everywhere; derived opt-in; mislabelled sources; unknown/unsupported instruments; **point in time** (as_of at an open, mid-bar, at a close, before all data, windows, CSV, helpers, quotes); response validators refuse look-ahead and unlabelled or disallowed proxies; freshness and STALE; partial series; slice gaps; deterministic serialization; columns; **snapshot** (only input values, quote, proxy labels, refusals) |
| `unit/test_config_and_registry.py` | +2 new, −1 parametrized case | market-data gate implemented; staleness setting; every unimplemented gate still refused |
| `contract/test_upstream_boundary.py` | +1 | upstream `XAUUSD→GC=F`, `NAS100→^NDX` aliases pinned as PROXY; marketdata import isolation |

**Fixtures.** The four `tests/fixtures/synthetic_*_h1.csv` files are hand-written synthetic
values dated 2030 and labelled "SYNTHETIC TEST DATA — NOT MARKET HISTORY" in their first line; a
test enforces the label. They are not market evidence.

---

## 14. Deferred providers

| Provider | Status | Reason |
|---|---|---|
| **TradingAgents / Yahoo adapter** | **Deferred** | Upstream's path would need a network call. It is daily-only, adjusted (`auto_adjust=True`) and gap-filled (`ffill().bfill()`) by default, it caches in the user's home directory, it rounds its text output to 2 dp, and it substitutes `GC=F` / `^NDX`. A safe adapter would have to call upstream internals (`load_ohlcv(fill_gaps=False)`), re-validate everything and classify proxies. The classification is ready (`TRADINGAGENTS_YAHOO_REFERENCE`); the adapter is not built, and no upstream file is touched |
| Historical market-data provider (intraday, bid/ask) | Deferred | Foundation D-1 open |
| MT5 as a data source | Phase 8 | Windows host (D-17) |
| Live / streaming quotes | Not in scope | — |

---

## 15. Known limitations

1. **No session calendars** (Foundation §11.2 lists the Market Session Agent T2 and per-instrument
   calendars in Phase 2; the owner's brief excludes market-open logic). Weekend and holiday gaps are
   flagged like any gap, and freshness counts them as intervals behind. See §15.1.
2. **No bar-alignment check.** H4/D1/W1 boundaries depend on provider or broker server time. Only
   M1–H4 durations are checked; D1/W1 durations are not.
3. **Precision is known only when declared.** Instruments carry no default precision; a source
   declares its own, and the instrument's comes from the broker later.
4. **No gap filling, resampling or cross-timeframe building.** A higher timeframe is never built
   from a lower one here.
5. **The CSV provider parses the file on every request.** This is simple and deterministic; caching
   can come later.
6. **Quotes** come only from the in-memory provider.
7. **The Data Validator (T1) as an agent** (events, journal records) is not wired. The snapshot
   builder records `produced_by="data_validator"`.

---

### 15.1 Calendar-naive gaps and freshness (until MD-2)

Until market and session calendars are implemented under MD-2, **gap detection and freshness are
calendar-naive**. They compare timestamps with fixed timeframe durations and know nothing about
when a market is open.

- **Weekends, holidays and other market closures may appear** as `GAP_DETECTED` gaps (with
  missing-interval counts), and as elapsed intervals in `Freshness.intervals_behind`. This can
  produce `STALE` when a threshold is configured.
- **A reported gap does not say whether data is missing** or the market was closed. Likewise, an
  "intervals behind" count or a `STALE` status does not say whether data is late or the market is
  shut.
- **These results are descriptive data-quality signals only.** They must **not** later be treated
  as deterministic trading or risk evidence without session-aware validation: for example, a Risk
  Engine stale-data rule, an Execution Checker market-open check, or a breaker trip on data failure
  must not rely on them.
- Session-aware validation is to be added under MD-2. That work must not invent session schedules;
  they come from an approved calendar source.
- Phase 2 implements no market calendar and assumes no session schedule.

## 16. Unresolved decisions

| # | Decision | Safe default until decided |
|---|---|---|
| MD-1 | Historical data source for intraday and bid/ask history (Foundation D-1) | Owner-supplied CSV files |
| MD-2 | Session calendars and market hours per instrument (T2), and how freshness should treat closed markets | Gaps reported; freshness in raw intervals; both calendar-naive and not usable as trading or risk evidence (§15.1) |
| MD-3 | Staleness threshold (`max_staleness_intervals`) per timeframe | Unset → freshness UNKNOWN |
| MD-4 | Declared precision per source and instrument (broker digits) | Unset; only declared values are enforced |
| MD-5 | Bar-alignment conventions (H4/D1/W1 boundaries, server time) per source | Not enforced |
| MD-6 | Whether and how to build the TradingAgents/Yahoo adapter (analysis-only proxy data) | Deferred |
| MD-7 | Whether the CSV provider should support quotes / bid-ask files | Not supported |
| MD-8 | Journaling of market-data responses and snapshots (`snapshot.created` / `snapshot.rejected` events) and T1 wiring | Deferred to the phase that runs decision cycles |
| MD-9 | Default duplicate and order policies per source | Reject (safest) |
