# Stellar Agents — Research Lab Plan

| | |
|---|---|
| **Status** | v0.1 — design only, for owner review. No code, dependency, roadmap or registry change |
| **Date** | 2026-09-30 |
| **Revision at writing** | `06578ea` |
| **Builds on** | `docs/STELLAR_FOUNDATION_PLAN.md` (v0.3, canonical), `docs/STELLAR_LAYER_DESIGN.md`, `docs/STELLAR_MASTER_ROADMAP.md`, `docs/STELLAR_VISUAL_WORLD_PLAN.md`, `docs/STELLAR_PHASE1_IMPLEMENTATION.md`, `docs/STELLAR_TRADING_KNOWLEDGE_AUDIT.md` |
| **Scope** | A dedicated, experimental subsystem with two evolutionary research agents that study chart analysis itself (price mechanics, candles, shapes, structure, statistics, new metrics and representations), independent of any one market |
| **Hard rule** | The Research Lab **produces evidence, never decisions**. It cannot trade, rate, size, approve, change risk limits, or change another agent's behaviour on its own |

---

## Naming: "Research Lab" is not the "research chain"

The Foundation Plan already uses **research** for the macro/news chain: collectors R1–R6,
validators V1–V4, the Causal/Macro Analyst M1, the market specialists S1–S4, and the
`research.*` events.

The Research Lab is a **different subsystem** that studies *analysis methods*, not the world.

| Term | Meaning |
|---|---|
| **Research chain** | Foundation §4.29: news, central banks and macro, turned into assessments for a decision cycle |
| **Research Lab** (this document) | Chart and price-mechanics science: hypotheses, experiments, metrics and validated findings about how price behaves |
| **Research Manager** | The upstream debate judge (U3). Unrelated to both |

Every Research Lab name uses the `lab` prefix (events `lab.*`, component `ResearchLab`), so the
three are never confused.

---

## Contents

1. [Core principle](#1-core-principle)
2. [Scientist A — Explorer](#2-scientist-a--explorer)
3. [Scientist B — Validator / Skeptic](#3-scientist-b--validator--skeptic)
4. [Evolutionary research loop](#4-evolutionary-research-loop)
5. [Scientific Memory](#5-scientific-memory)
6. [Knowledge types and statuses](#6-knowledge-types-and-statuses)
7. [Chart-shape research](#7-chart-shape-research)
8. [Alternative price representations](#8-alternative-price-representations)
9. [Seasonality, calendar and probability research](#9-seasonality-calendar-and-probability-research)
10. [Statistical safety](#10-statistical-safety)
11. [Market independence](#11-market-independence)
12. [Support mode (Research Support Desk)](#12-support-mode-research-support-desk)
13. [Knowledge sharing and promotion](#13-knowledge-sharing-and-promotion)
14. [Stellar Weekly Research Council](#14-stellar-weekly-research-council)
15. [Learning and growth](#15-learning-and-growth)
16. [Tooling (future)](#16-tooling-future)
17. [AI-Newton inspiration](#17-ai-newton-inspiration)
18. [Architecture](#18-architecture)
19. [Relation to Stellar phases](#19-relation-to-stellar-phases)
20. [Visual world: Quant / Chart Research Laboratory](#20-visual-world-quant--chart-research-laboratory)
21. [Safety boundaries (summary)](#21-safety-boundaries-summary)
22. [Unresolved decisions](#22-unresolved-decisions)

---

## 1. Core principle

The Research Lab is an **experimental scientific subsystem**. Its job is to **discover, test,
challenge, refine, remember and share** knowledge about chart analysis.

| It does | It never does |
|---|---|
| Form hypotheses about price behaviour | Execute, propose or size trades |
| Define candidate metrics, patterns and representations | Produce BUY / SELL, a rating or an approval |
| Run deterministic experiments on historical data | Bypass, relax or tune the Risk Engine |
| Try to disprove its own findings | Change any hard risk threshold (Foundation D-12 stays owner-only) |
| Keep every result, including failures | Promote a discovery directly into live trading logic |
| Answer evidence questions from other agents | Rewrite another agent's prompt, config or code |
| Publish validated, versioned findings with their limits | Present a finding as universal truth |

**Position in the architecture.**
- The Lab sits **beside** the decision pipeline, not in it.
- It reads market data through the same Stellar `MarketDataSource` (Phase 2), with the same
  point-in-time rules.
- It writes only to its own Scientific Memory and to the event journal.
- Its outputs reach the decision pipeline only as **cited, advisory evidence** (§12) or through an
  **owner-approved, versioned code change** after promotion (§13).
- The Risk Engine never reads Lab output.

**Determinism.** Language models may *propose* hypotheses, variants and explanations. Every number
the Lab reports comes from **deterministic experiment code** with a recorded specification, dataset
and seed. A model never computes, estimates or rounds a result. This is the same rule as the
verified market snapshot and Foundation §8.4, applied to research.

---

## 2. Scientist A — Explorer

| | |
|---|---|
| **Proposed technical id** | `lab_explorer` (code and group: RL-1) |
| **Kind** | Hybrid: LLM for idea generation and write-ups; deterministic experiment runner for every result |
| **Mission** | Invent hypotheses, search for new patterns, create new metrics and indicators, combine existing tools in new ways, test new representations of price, study recurring chart shapes, and look for useful relationships humans may not have named |

**Research domains:**
- candle body/wick relationships and sequences of candles;
- impulse versus consolidation, and rejection;
- compression and expansion;
- slope, acceleration/deceleration and curvature;
- symmetry;
- channels, triangles and ranges;
- pivot geometry, and support/resistance geometry;
- multi-timeframe relationships;
- volatility-normalised patterns and momentum transitions;
- breakout and retest mechanics.

**How the Explorer works:**
1. **Starts from something concrete:**
   - an observation, such as a Council question, a support request or an anomaly in data;
   - a gap in memory, i.e. a concept never tested in some context;
   - a mutation of an existing candidate (§4).
2. **Writes a hypothesis as a typed specification, not prose.** The specification names:
   - the representation (§8);
   - the feature or metric definition (versioned);
   - the event or condition, and the outcome measure (forward return, direction, range, time to
     target);
   - the horizon;
   - the instruments and timeframes;
   - the dataset window;
   - the baseline it must beat;
   - the success criteria, **declared before looking at test data** (§10).
3. **Checks Scientific Memory first:**
   - Has this exact experiment already run?
   - Has a near-duplicate failed?
   - Is there a counterexample on record?

   The Explorer does not repeat a failed experiment unless something material has changed
   (§5.4).
4. **Runs exploration on training data only.** It may try many variants there, and every variant
   is counted (§10.3).
5. **Submits its best candidates to the Validator.** A candidate carries the full record of what
   was tried, including discarded variants.

**Exploration versus exploitation.** The Explorer keeps a budget split between:
- **exploitation:** refining candidates that already show evidence;
- **exploration:** untested concepts, representations and contexts.

The split, the LLM budget and the compute budget are configuration (RL-6). A concept family that
keeps failing is deprioritised automatically, by recorded failure history, not by forgetting it.

**The Explorer may not:**
- touch the locked test data;
- mark anything validated;
- publish;
- contact the decision pipeline except through the Support Desk (§12).

---

## 3. Scientist B — Validator / Skeptic

| | |
|---|---|
| **Proposed technical id** | `lab_validator` |
| **Kind** | Mostly deterministic (statistical test battery); LLM for counterexample search ideas and the written verdict |
| **Mission** | Challenge the Explorer: reproduce, attack, and validate only robust findings |

**The Validator's duties.** It actively tries to **disprove**. For every candidate it:

1. **Reproduces** the Explorer's result from the stored specification and seed. A result that does
   not reproduce is rejected as `NOT_REPRODUCIBLE`.
2. **Tests out-of-sample:**
   - on the locked test partition, once (§10.2);
   - with walk-forward windows where the hypothesis is time-dependent.
3. **Tests across periods:** early, middle and late thirds of history, plus named stress periods
   when configured.
4. **Tests across volatility regimes:** results are segmented by regime labels (§10.5).
5. **Tests across instruments and timeframes:**
   - generality is scored, but not required;
   - a finding that holds on one instrument only is recorded as **context-specific**, not
     rejected.
6. **Tests chance:**
   - comparison with null models: shuffled or block-bootstrapped series, random-entry baselines,
     and matched random events;
   - reports the probability that such a result appears by chance, *after* adjusting for the
     number of variants tried.
7. **Searches for counterexamples:** the cases where the pattern fired and the outcome was
   opposite, grouped by context, and stored as `COUNTEREXAMPLE` records.
8. **Runs sensitivity analysis.** It perturbs every parameter; a result that collapses under a
   small change is flagged `FRAGILE`.
9. **Compares versions.** A new version must beat its parent on the declared criteria out of
   sample, not only in training.
10. **Checks redundancy.** A candidate metric that is near-identical to an existing metric (by
    correlation of values or by identical event sets) is flagged `DUPLICATE_OF` that metric.
11. **Issues a verdict:**
    - `VALIDATED` (with contexts);
    - `REJECTED` (with reason codes);
    - `NEEDS_MORE_EVIDENCE` (with what is missing);
    - `CONTEXT_SPECIFIC` (validated only where stated).

**Independence.** The Validator:
- works from the stored specification, not from the Explorer's narrative;
- has its own seed and its own resampling;
- cannot be overruled by the Explorer.

Only the promotion pipeline (§13), and ultimately the owner, can overrule a verdict.

---

## 4. Evolutionary research loop

The loop is inspired by AI-Newton's concept-driven discovery (§17), adapted to noisy financial data.

```
Observation ─> Hypothesis ─> Experiment (train) ─> Result
                    ^                                 │
                    │                  ┌──────────────┴───────────────┐
                    │                  v                              v
                    └──── Mutation / Variant  <──  promising     discard (recorded as FAILED)
                                       │
                                       v
                          Re-test (train, counted) ─> Candidate
                                                        │
                        Validator: Reproduce ─> Out-of-sample ─> Counter-test ─> Robustness
                                                        │
                                                   Replication
                                                        │
              ┌─────────────────────┬───────────────────┼───────────────────────┐
              v                     v                   v                       v
          VALIDATED           CONTEXT_SPECIFIC   NEEDS_MORE_EVIDENCE        REJECTED
              │                     │                   │                       │
              └──────── Candidate knowledge ─> Promotion pipeline (§13)   kept forever, with
                                                                           reasons (§5)
```

**Mutations.** A variant is derived from a parent by one recorded operation:
- **parameter:** change a window or threshold;
- **representation:** for example raw → ATR-normalised;
- **condition:** add or remove a filter;
- **combination:** combine two concepts;
- **simplification:** remove a term;
- **generalisation:** widen the context;
- **specialisation:** narrow it.

**Versioned concepts.** Every metric, pattern or rule is a versioned concept, for example:

```
WickExhaustionMetric_V1   (parent: none)
WickExhaustionMetric_V2   (parent: V1; mutation: representation raw → ATR-normalised)
WickExhaustionMetric_V3   (parent: V2; mutation: condition + "only at 20-bar extremes")
```

Each version stores:
- its **parent version**;
- the **reason for the mutation**;
- the **changed parameters** as a structured diff;
- its **experiment results**;
- **whether it improved**, on which criteria, and out of sample or not;
- its **limitations** and known counterexamples;
- its complexity (§17.6).

A version is never edited after it has results: a change creates a new version.

**Loop termination.** A lineage stops being mutated when any of these holds:
- it is validated and stable across two successive re-tests;
- its failure count passes a configured limit (RL-6);
- no mutation has improved it for a configured number of generations.

The Council may reopen it (§14).

---

## 5. Scientific Memory

### 5.1 Purpose and properties

Scientific Memory is the Lab's persistent, **append-only** knowledge store:
- It is separate from the trading records, but uses the Phase 1 disciplines: typed contracts,
  immutable records, prefixed ids, provenance, canonical JSON with hashes, and schema versioning.
- **Nothing is deleted.** Failed and rejected research is kept.
- **Status changes are new records** that reference the old one, so the history of every idea is
  reconstructable.

**Storage** is a local SQLite database. It could be the Stellar Journal database with separate
tables, or a separate file (RL-4). Every write also emits a `lab.*` event into the Stellar Journal,
so the Lab's activity is replayable and visible to the station.

### 5.2 Record types and common fields

All records carry:
- `record_id` (prefixed, RL-3), `kind` (§6), `schema_version`;
- `created_at` (UTC), `created_by` (technical agent id or `owner`);
- `derived_from` (list of record ids) and `supersedes` (optional);
- `status` (§6.2), `evidence_level` (§6.3);
- `provenance`: data source ids, dataset hash, code version, config hash, random seed;
- `limitations` (text plus structured tags);
- `content_hash`.

| Stored item | Record kind(s) | Key content |
|---|---|---|
| Observations | `OBSERVATION` | What was seen, where (instrument, timeframe, window), by whom, and a link to the data slice |
| Hypotheses | `HYPOTHESIS` | Typed specification (§2 step 2), declared success criteria, baseline |
| Experiments and parameters | `EXPERIMENT` | Hypothesis id, concept version, full parameter set, partition used, seed, code version |
| Datasets and time ranges | inside `EXPERIMENT` and the dataset registry | Instruments, timeframes, date ranges, provider, dataset hash, as-of cut |
| Results | `RESULT` (attached to an experiment) | Sample size, effect size, confidence interval, baseline comparison, adjusted chance probability, per-segment tables |
| Failed experiments | `RESULT` with status `FAILED` | Same as results; never deleted |
| Counterexamples | `COUNTEREXAMPLE` | Concrete cases (instrument, time, context) that contradict a candidate |
| Rejected ideas | `REJECTED_FINDING` | Reason codes, verdict, the experiments that decided it |
| Candidate knowledge | `CANDIDATE_METRIC`, `CANDIDATE_PATTERN`, `CANDIDATE_RULE` | Definition, version lineage, evidence so far |
| Validated knowledge | `VALIDATED_FINDING` | Contexts where it holds, evidence, limitations, version |
| Exceptions | `EXCEPTION` | Documented contexts where a validated finding does not hold |
| Limitations | `LIMITATION` | Known constraints (data depth, regimes not covered, costs ignored) |
| Replication history | `REPLICATION_RESULT` | Each re-test or reproduction, linked to the finding it tests |
| Version history | concept version chain | parent, mutation, diff, improvement flag |

### 5.3 Confidence and evidence status

Confidence is **not a single number chosen by a model**. It is derived from recorded evidence:
- sample size;
- out-of-sample outcome;
- the number of contexts it held in;
- replication count;
- the adjusted chance probability;
- counterexample share.

It is summarised as an `evidence_level` (§6.3). The derivation rules are versioned, so a change of
rule does not silently re-grade old findings.

### 5.4 Avoiding repeated failures

- Every experiment has an **experiment fingerprint**: a hash of the concept version, canonical
  parameters, representation, dataset specification and partition.
- Before running, the registry is checked. An **identical** fingerprint is not re-run.
- A **near-identical** fingerprint (same concept family, parameters within a recorded tolerance,
  same data) is re-run only with a stated reason. Valid reasons:
  - new data (a longer history, a new instrument);
  - a changed representation;
  - a replication request from the Validator or the Council;
  - a bug fix in experiment code, recorded by code version.
- Every such re-run is recorded as a `REPLICATION_RESULT` or a new experiment, never as an
  overwrite.

---

## 6. Knowledge types and statuses

### 6.1 Kinds

| Kind | Meaning | Universal? |
|---|---|---|
| `OBSERVATION` | Something noticed; no claim | No |
| `HYPOTHESIS` | A testable claim with declared criteria | No |
| `EXPERIMENT` | One run of a test with full specification | — |
| `CANDIDATE_METRIC` | A proposed measurement of price behaviour (a formula over a representation) | No |
| `CANDIDATE_PATTERN` | A proposed recognisable configuration (shape, sequence, geometry) | No |
| `CANDIDATE_RULE` | A proposed conditional relationship ("when X in context C, Y tends to follow within H") | No |
| `VALIDATED_FINDING` | A candidate that passed validation **in stated contexts** | **Only within its stated contexts** |
| `REJECTED_FINDING` | A candidate that failed, with reasons | — |
| `COUNTEREXAMPLE` | Concrete contradicting cases | — |
| `LIMITATION` | A known constraint on a finding or on the Lab | — |
| `EXCEPTION` | A context where a validated finding does not hold | — |
| `REPLICATION_RESULT` | Outcome of reproducing or re-testing | — |

**No record is universal truth.** Even a validated finding carries its contexts, its evidence date
and its data range, and it can be demoted by later evidence (§13.4).

### 6.2 Statuses

`DRAFT → UNDER_TEST → CANDIDATE → UNDER_VALIDATION →`
{`VALIDATED`, `CONTEXT_SPECIFIC`, `NEEDS_MORE_EVIDENCE`, `REJECTED`, `NOT_REPRODUCIBLE`,
`FRAGILE`, `DUPLICATE`}, then optionally `PUBLISHED` (§13) and later `DEMOTED` or `SUPERSEDED`.

### 6.3 Evidence levels

| Level | Meaning |
|---|---|
| E0 | Idea only; no experiment |
| E1 | In-sample evidence only |
| E2 | Out-of-sample on one instrument/timeframe |
| E3 | Out-of-sample on several contexts, with replication |
| E4 | E3 plus stable across periods and regimes, and survived Council challenge |

The numeric criteria behind each level (minimum samples, adjusted significance, replication count)
are configuration approved by the owner (RL-5). This document does not choose them.

---

## 7. Chart-shape research

The scientists study graphical shapes and geometry **as numbers**. Shapes are computed objects, not
pictures a model looks at. A rendered chart is for humans and the Council only.

| Shape family | Computable description (examples) |
|---|---|
| Triangles, wedges | Two fitted boundary lines over pivots; converging slopes; apex distance; touches per side |
| Rectangles, ranges | Horizontal boundary pair; width relative to ATR; duration; touches |
| Channels | Parallel fitted lines; slope; width; containment ratio |
| Compression / expansion | Sequence of shrinking or growing ranges (bar range, ATR, Bollinger width) |
| Curves | Polynomial or spline fit of normalised price; curvature sign and magnitude |
| Slopes, angles | Regression slope in a scale-free representation (per ATR per bar), since raw chart angles depend on axis scaling |
| Distances | Price distance in ATR units; time distance in bars |
| Symmetry | Mirror similarity of the left and right legs around a pivot, after normalisation |
| Wick/body ratios | Upper wick, lower wick and body as fractions of range; vectors over sequences |
| Pivot spacing | Bars between swing points; regularity measures |
| Repeated sequences | Symbolic encodings of candles or pivots (§8) and recurring substrings |
| Breakout shapes | Pre-break compression plus break-bar characteristics |
| Reversal shapes | Pivot sequences with specific geometry (for example lower high after a failed higher high) |

**Method:**
1. Extract a window of bars ending at an event.
2. Transform it to a chosen representation (§8).
3. Normalise it (price and time).
4. Compute the shape descriptors.
5. Compare against a **large historical library** of windows, using a similarity measure
   (Euclidean on normalised vectors, dynamic time warping, or shape-descriptor distance). Which
   measures to use is an experiment choice, recorded per experiment.
6. Measure what followed the nearest neighbours versus a baseline.

**Guard.** Pivot and swing detection must be **causal**: a pivot is known only when its confirming
bars have closed. Every descriptor is computed with the data available at the event's time. A
repainting pivot would make every shape look predictive.

---

## 8. Alternative price representations

| Representation | Notes |
|---|---|
| Raw price | Baseline; not comparable across instruments or decades |
| Percentage returns | Scale-free per bar |
| Log price / log returns | Additive over time; better for long spans |
| Normalised price | Window rescaled (for example min–max or z-score within the window) |
| ATR-normalised movement | Moves in units of recent volatility; comparable across instruments |
| Volatility-adjusted series | Returns divided by rolling volatility |
| Pivot sequences | Only swing points (price and time), a compressed skeleton of structure |
| Scale-independent shapes | Price and time both normalised to a unit box |
| Candle body/wick vectors | Each bar as (body, upper wick, lower wick, direction) relative to range or ATR |
| Time-normalised sequences | Windows resampled to a fixed length so shapes of different duration compare |
| Symbolic encodings | Bars or pivots mapped to a small alphabet (for example "strong up body, long lower wick") for sequence mining |

**Representation experiments.** The same hypothesis can run under several representations. The
Lab reports which representation reveals the effect best **out of sample**. A representation that
wins only in training is not preferred. Representation is part of the concept version and of the
experiment fingerprint.

---

## 9. Seasonality, calendar and probability research

**Supported calendar keys:**
- same calendar date across years;
- week of year, month, quarter;
- day of week, hour, trading session;
- beginning and end of month or quarter;
- before and after recurring events, such as scheduled releases (once a calendar source exists,
  Foundation D-2/D-4).

**Measures:**
- Absolute prices are **never** compared across years or decades.
- Allowed measures:
  - return %, log return and direction;
  - normalised range and ATR-relative movement;
  - volatility, drawdown and maximum favourable/adverse excursion;
  - forward returns at stated horizons;
  - duration (bars to a move of a given size).

**Rules:**
- **Sample sizes are always reported:** the number of years or occurrences per bucket, and per
  instrument. A bucket below the configured minimum (RL-5) is shown as "insufficient sample", not
  as a result.
- **Bucket count is a multiple-testing burden.** Twelve months times five weekdays times four
  instruments is 240 tests. The adjustment (§10.3) counts all of them.
- **Time zone and session definitions** are explicit and versioned. An "hour" result means
  nothing without the time zone and the provider's bar convention (Foundation §4.7).
- **Regime drift:** calendar effects are tested per era (for example by decade, or before and after
  structural changes) and reported with their stability.
- **Data depth** is a dependency. Seasonality needs long history, which depends on the historical
  data source (Foundation D-1).

**Probability outputs.** The Lab reports:
- empirical frequencies with confidence intervals;
- effect sizes against a baseline;
- the adjusted chance probability.

It does not report a bare "70% win rate" without its sample, interval, baseline and context.

---

## 10. Statistical safety

A visually attractive pattern is not evidence.

| # | Safeguard | Rule |
|---|---|---|
| 10.1 | Point-in-time data | All features use only data available at the event time. This covers causal pivots, closed bars only, and provider bar conventions. It is the same `as_of` rule as Foundation §4.1 and the knowledge audit's point-in-time patterns |
| 10.2 | Train / validation / test separation | Each dataset is split by time into training (Explorer), validation (Validator's iterative checks) and a **locked test** partition. The test partition of a dataset is used **once per candidate version**; every access is logged, and a second look is recorded as such |
| 10.3 | Multiple-hypothesis accounting | Every variant tried in a family is counted, including discarded ones. Reported significance is adjusted for that count; the method is RL-5 (for example false-discovery-rate control). The number of trials is shown next to every result |
| 10.4 | Walk-forward validation | For time-dependent hypotheses: rolling fit and test windows; the result is the aggregate of out-of-sample windows only |
| 10.5 | Regime segmentation | Results are reported per volatility regime (for example ATR percentile bands), per trend state and per session. A finding whose effect lives in one regime is `CONTEXT_SPECIFIC` |
| 10.6 | Robustness | Block bootstrap confidence intervals; results on each instrument and timeframe separately; results with the highest-impact periods removed |
| 10.7 | Sensitivity analysis | Parameter perturbation grid; a result that holds only at one setting is `FRAGILE` |
| 10.8 | Null models and baselines | Shuffled or block-bootstrapped series; random-entry and matched-random-event baselines; "always the same direction" baseline |
| 10.9 | Sample-size reporting | Every result states n; buckets below the minimum are not interpreted |
| 10.10 | False-positive tracking | The Lab tracks how many of its promoted findings later failed replication or were demoted. This rate is a Lab health metric shown at the Council |
| 10.11 | Overfitting warnings | Automatic warnings for: many parameters relative to events, a large train–test gap, many variants for one family, tiny effect with huge n, dependence on a few outliers |
| 10.12 | Complexity penalty | Simpler concepts are preferred at equal evidence (§17.6) |
| 10.13 | Costs awareness | Findings intended for trading are also reported net of a configured spread and slippage model. A gross-only edge is labelled as such |
| 10.14 | Pre-declaration | Success criteria and the primary metric are declared in the hypothesis before validation. Changing them after seeing results creates a new hypothesis version |

---

## 11. Market independence

- The scientists study **general analysis mechanisms**: candles, structure, volatility, momentum,
  shape and statistics.
- They are **not** XAU/USD, EUR/USD, USD/JPY or NAS100 specialists, and have no market focus.
- They test discoveries on those instruments, and on others when data exists, **to evaluate
  generality**:
  - a finding that holds broadly is general;
  - a finding that holds on one instrument is recorded as context-specific, with that context.
- They produce no market view. They do not say "gold looks bearish".
- Market-specific interpretation belongs to the Market Specialists (S1–S4). Macro interpretation
  belongs to M1.
- A Lab finding may be used by a specialist, which states it as evidence with its citation (§12).

---

## 12. Support mode (Research Support Desk)

Other agents can ask the Lab evidence questions.

**Example.** The XAU/USD Specialist writes: "I have a bearish hypothesis, but I'm unsure whether this
pattern is historically meaningful." The Lab:
1. retrieves comparable historical cases (similarity search, §7);
2. tests the relevant pattern;
3. returns the sample size, the supporting evidence and the counterexamples;
4. states the uncertainty.

It does **not** return a trade instruction.

**Request contract (proposed `ResearchQuery`):**
- requester (technical id);
- question (short text);
- pattern or concept reference or specification;
- instruments and timeframes;
- `as_of` (UTC);
- routing: Explorer, Validator, or Explorer then Validator;
- time budget.

**Answer contract (proposed `ResearchEvidence`):**
- query id;
- `as_of`;
- the concepts and versions used;
- sample size;
- effect with confidence interval, and baseline;
- adjusted chance probability;
- counterexamples, as a count plus examples;
- regime breakdown;
- evidence level;
- limitations;
- a statement of what the answer does **not** show.

The answer has **no** direction, action, level or size field, by construction, like the Phase 1
"no prose execution values" rule.

**Rules:**
- **Point-in-time.** A query made during a decision cycle is answered with data up to its `as_of`
  only, and from findings that existed at that time.
- **Advisory and cited.** A consumer that uses an answer cites its id, so the Contradiction Checker
  (P2) and the journal can trace it.
- **Latency.** A live decision cycle never waits indefinitely:
  - an answer that misses its time budget is returned as "unavailable";
  - it is never guessed;
  - whether support queries are allowed inside live cycles at all is RL-8.
- **Routing modes:**
  - **Explorer only:** quick exploratory look, labelled E1 at best.
  - **Validator only:** check of an existing finding.
  - **Explorer → Validator:** full question.
- **Evidence status of an answer:**
  - **Explorer-only answers** are labelled **EXPLORATORY / NOT VALIDATED** in the response itself
    (an evidence-status field), not only in the text. They may prompt further investigation or
    seed new hypotheses. They must **not** be presented to another Stellar agent as validated
    research evidence, and a consumer may not cite them as such.
  - **Validated supporting evidence.** An answer meant to be used as validated evidence must pass
    through the Validator, either directly (Validator only) or through Explorer → Validator. Only
    then does it carry the Validator's verdict and evidence level.
  - **Provenance is preserved in every answer:**
    - which scientist(s) produced it;
    - the concepts, versions and experiment ids used;
    - the data range and `as_of`;
    - the evidence status: EXPLORATORY / NOT VALIDATED, or the Validator's verdict and evidence
      level.

---

## 13. Knowledge sharing and promotion

### 13.1 Pipeline

```
Discovery ─> Validation ─> Promotion review ─> Publication ─> Consumers notified
 (Explorer)   (Validator)   (Curator + owner)   (versioned)    (subscribed agents)
```

| Step | Owner | Output |
|---|---|---|
| Discovery | Explorer | `CANDIDATE_*` record |
| Validation | Validator | verdict record with contexts and evidence level |
| Promotion review | Knowledge Curator (a Lab role run by the Supervisor, RL-9), plus **owner approval** for anything that could change behaviour | promotion decision record |
| Publication | ResearchLab | a `PublishedFinding` (immutable, versioned) and a `lab.finding.published` event |
| Notification | ResearchLab | consumers subscribed to a topic receive the finding id; nothing in them changes automatically |

### 13.2 Two publication levels

1. **Evidence publication.** A validated finding becomes available as **context** that agents may
   read and cite: specialists, T8, the debate and the Council. It changes no code and no threshold.
2. **Method adoption.** A finding becomes part of deterministic logic, such as a new metric in the
   technical agents (T3–T7) or a new Setup condition. This **always** goes through:
   - an owner-approved, versioned code change with tests;
   - then simulation (Foundation Phase 7) and paper validation, like any strategy change.

   The Lab never edits another agent's code, prompt or configuration.

### 13.3 What consumers see

Every published finding carries:
- source: concept, version and lineage;
- evidence: experiments and replications;
- evidence level and confidence derivation;
- limitations and exceptions;
- applicable contexts: instruments, timeframes, regimes, sessions;
- data range and `as_of` of the evidence;
- version, and what it supersedes.

### 13.4 Demotion

- A published finding is re-tested on a schedule (RL-10) and whenever new data arrives.
- A finding that fails replication is **demoted**. A `lab.finding.demoted` event notifies its
  consumers.
- Anything adopted into code is flagged for owner review. It is not removed automatically.

---

## 14. Stellar Weekly Research Council

A recurring meeting that produces **real records and events**, not just animation.

| Aspect | Design |
|---|---|
| Schedule | Weekly; day and time in config (RL-11); convened by the Supervisor (O1) |
| Participants | Explorer, Validator, Knowledge Curator; invited as relevant: technical agents (T3–T8), Market Specialists (S1–S4), Causal/Macro Analyst (M1), Performance/Attribution (L2); the owner may attend (read the minutes, add questions) |
| Agenda (built from memory) | New discoveries; rejected hypotheses and why; experiments still running; updated metrics and versions; important counterexamples; knowledge revisions (promotions, demotions); Lab health (false-positive rate, budget use) |
| Challenges | Any participant may challenge a finding with a typed challenge: a counter-hypothesis, a context to test, or a suspected leak or bias. Each challenge becomes an `OBSERVATION` or a queued experiment |
| Questions | Specialists and technical agents may raise research questions; each becomes a queued `HYPOTHESIS` draft with its requester |
| Outputs | `CouncilSession` record (participants, agenda, minutes); challenge records; new experiment queue entries; promotion recommendations for the owner. Events: `lab.council.started`, `lab.council.challenge.raised`, `lab.council.completed` |
| Limits | LLM budget per session; a fixed time box; no decision is taken about trading, and no threshold changes |

The minutes are generated from the records. The narrative is written by an LLM, but every number in
it comes from Scientific Memory.

---

## 15. Learning and growth

The scientists become more knowledgeable **through stored knowledge, not self-modification**.

| Source of growth | Mechanism |
|---|---|
| Accumulated experiments | A larger library of results and neighbours for similarity search |
| Validated findings | Reusable building blocks for new hypotheses (combination mutations) |
| Rejected findings and failures | Deprioritised families; duplicate checks; "known dead ends" given to the Explorer's context |
| Better search strategies | Recorded success rates per mutation operator and per representation guide what to try next (a bandit over strategies, with its statistics stored) |
| Versioned metrics | Lineages that record which changes helped |
| Improved hypothesis generation | The Explorer's prompt context is assembled from memory: relevant findings, failures and open questions. Prompts themselves change only through versioned, reviewed code changes |

There is no weight training, no automatic code generation into production, and no silent
behaviour change. A custom metric formula lives in the experiment sandbox (§16) until promoted by
§13.2.

---

## 16. Tooling (future)

Planned tools; none is implemented here.

| Tool | Purpose | Notes |
|---|---|---|
| OHLCV access | Historical and point-in-time bars | Stellar `MarketDataSource` (Phase 2) |
| Indicator calculations | Standard indicators | Stellar indicator layer (Phase 5); knowledge audit: `stockstats` formulas as a pinned reference |
| Pivots and swing points | Causal swing detection | Shared with T3 once built |
| Trend lines, channels, support/resistance tools | Fit and describe lines and zones | Deterministic geometry |
| Custom formula sandbox | Define candidate metrics safely | A restricted expression language over bar arrays, or sandboxed code, is RL-7; no network, no file access, bounded CPU, deterministic |
| Statistics | Tests, intervals, bootstrap, multiple-testing control | Library choice is a later dependency decision |
| Pattern matching and similarity search | Nearest historical windows | Indexed library of normalised windows |
| Historical replay | Point-in-time walk-through of past markets | Shared with Phase 7 simulation |
| Multi-timeframe overlays | Aligned higher/lower timeframe views | Uses Foundation §4.7 alignment rules |
| Chart drawing and annotations | Human-readable evidence boards | For the owner, the Council and the station; never an input to results |
| Experiment notebook | Per-experiment record view | Rendered from Scientific Memory |
| Visual comparison boards | Side-by-side shape and outcome comparisons | Station screens (§20) |

---

## 17. AI-Newton inspiration

AI-Newton (a concept-driven system for discovering physical laws from experimental data) is used
**as architectural inspiration only**. This plan does not rely on its code. Whether any of its code
could be reused must wait for a future reuse audit of its licence and coupling (RL-12). Its
physics-specific machinery (symbolic regression over physical quantities, conservation laws) is not
copied.

| Concept | Stellar adaptation |
|---|---|
| 17.1 Specific vs general knowledge | A finding validated in one context stays `CONTEXT_SPECIFIC`; generalisation is a separate, tested step |
| 17.2 Candidate rules before promotion | All knowledge starts as `CANDIDATE_*`; only validation and review promote it |
| 17.3 Provenance / `derived_from` | Every record links to its parents; lineages are reconstructable |
| 17.4 Validation across contexts | Instruments, timeframes, periods and regimes (§3, §10) |
| 17.5 Memory of failures | Failures stored and fingerprinted; dead ends inform search (§5.4, §15) |
| 17.6 Complexity control | Each concept has a complexity score (terms, parameters, conditions); simpler wins at equal evidence; complexity growth must buy out-of-sample improvement |
| 17.7 Redundancy / duplicate control | Near-duplicate metrics and patterns are detected and linked, not re-discovered |
| 17.8 Exploration vs exploitation | Budgeted split between refining promising lineages and testing new concepts (§2) |
| 17.9 Generalisation only after evidence | Widening a context is a mutation that must be re-validated |

**Differences from physics.** Markets are noisy, non-stationary and adaptive, so a "law" is at best
a context-bound statistical tendency. This is why the Lab adds what physics discovery does not
need:
- out-of-sample locking;
- multiple-testing accounting;
- regime segmentation;
- demotion.

---

## 18. Architecture

Proposed components, all under a future `stellar/src/stellar/lab/` package (not created now):

| Component | Responsibility | Boundaries |
|---|---|---|
| **ResearchLab** | Facade and scheduler: runs research cycles within budgets, routes requests, emits `lab.*` events | No access to risk, execution, broker or decision state |
| **ExplorerScientist** (`lab_explorer`) | Hypothesis and variant generation; exploration on training partitions | Cannot read locked test data; cannot set verdicts; cannot publish |
| **ValidatorScientist** (`lab_validator`) | Reproduction, out-of-sample tests, counter-testing, robustness; verdicts | Cannot create hypotheses except counter-hypotheses; cannot publish |
| **ExperimentRegistry** | Experiment specifications, fingerprints, partitions, test-set access log, execution queue; runs experiments deterministically in a sandbox | The only component that computes results |
| **ScientificMemory** | Append-only typed store of all §6 records and lineages | No updates or deletes; status changes are new records |
| **KnowledgePromotionPipeline** | Promotion review, owner approval requests, publication, demotion | Cannot modify another agent; publishes immutable findings only |
| **ResearchSupportDesk** | `ResearchQuery` → `ResearchEvidence` for other agents; enforces `as_of` and time budgets | Answers carry no action, direction, level or size |
| **ResearchCouncil** | Weekly session orchestration, agenda, challenges, minutes | Produces records and queued experiments only |

**Data flow.**

```
MarketDataSource (Phase 2) ──> ExperimentRegistry (sandbox) ──> ScientificMemory ──> lab.* events ──> Journal / Station
        ^                               ^        ^                       │
        │                    ExplorerScientist  ValidatorScientist       ├──> KnowledgePromotionPipeline ──> PublishedFinding
        │                                                                │            (owner approval)
   as_of cut                                                             └──> ResearchSupportDesk <──> Specialists / T* / Council
```

**Proposed event names** (canonical convention R-3; additive to the catalogue when implemented):

| Event | Emitted by |
|---|---|
| `lab.observation.recorded` | ResearchLab / Council |
| `lab.hypothesis.created` | Explorer |
| `lab.experiment.started` | ExperimentRegistry |
| `lab.experiment.completed` | ExperimentRegistry |
| `lab.experiment.failed` | ExperimentRegistry |
| `lab.candidate.created` | Explorer |
| `lab.validation.completed` | Validator |
| `lab.finding.validated` | Validator |
| `lab.finding.rejected` | Validator |
| `lab.finding.published` | KnowledgePromotionPipeline |
| `lab.finding.demoted` | KnowledgePromotionPipeline |
| `lab.support.requested` | ResearchSupportDesk |
| `lab.support.answered` | ResearchSupportDesk |
| `lab.council.started` | ResearchCouncil |
| `lab.council.challenge.raised` | ResearchCouncil |
| `lab.council.completed` | ResearchCouncil |

**Budgets and safety:**
- The Lab runs under the Operational Wellbeing Monitor's budgets (O2), with its own LLM and
  compute budget lines.
- Lab work never delays a decision cycle.
- A Lab failure never affects trading.

---

## 19. Relation to Stellar phases

The canonical roadmap (Foundation §11) is **not changed** here. The Lab depends on, and fits after,
existing phases:

| Phase | What the Lab needs from it |
|---|---|
| Phase 1 (done) | Contract, event, journal, registry and provenance patterns; the Lab will add a registry group and id kinds (RL-1, RL-3) |
| Phase 2 — Market data | Point-in-time OHLCV for the four instruments; timeframes; candle validation; deep history for seasonality (depends on D-1) |
| Phase 5 — Technical foundation | Shared deterministic building blocks: pivots, structure, candle features, indicators. The Lab studies and extends them; it must not fork them |
| Phase 6 — Research and LLM integration | LLM tiers and budgets (D-11); the specialists that will query the Support Desk |
| Phase 7 — Simulation | Historical replay and cost models for evaluating trading-relevant findings |
| Proposed **Research Lab phase** | Implementation of §18. Proposed placement: **after Phase 7** (needs data, the technical building blocks and simulation), with a possible early read-only subset (Scientific Memory schema and offline experiments on Phase 2 data) after Phase 5. This is a proposal for owner decision (RL-2), not a roadmap change |
| Phases 9–10 — Station | The laboratory room and Council visuals (§20) |

**Documented proposals needing later reconciliation (not applied):**
- a new agent group (the Research Lab) and two roster entries;
- new id prefixes;
- the `lab.*` event family;
- a new station room.

---

## 20. Visual world: Quant / Chart Research Laboratory

Design only. This proposes a room extension to the Visual World Plan (not applied; it would be a
later VX item).

| Aspect | Concept |
|---|---|
| Room | **Quant / Chart Research Laboratory**, on the analysis deck next to the Technical Deck (placement decided with the visual plan) |
| Residents | Explorer and Validator, with original personas from the persona registry; no franchise names in the repository |
| Chart walls | Large screens showing current experiments: normalised shape overlays, nearest-neighbour historical windows, outcome distributions |
| Shape comparison table | A holographic bench where candidate shapes are laid over historical matches |
| Experiment board | Columns by status (drafted, running, under validation, validated, rejected) with sample sizes and evidence levels |
| Metric version rack | Lineages like `WickExhaustionMetric_V1 → V2 → V3`, each with improved / not improved markers |
| Failed-experiment archive | A visible archive wall: failures are kept and shown, not hidden |
| Hypothesis status lights | Per-hypothesis badges driven by `lab.*` events |
| Support Desk | A window where other agents' requests queue; answers carry an "evidence, not advice" stamp |
| Weekly Research Council | Held in the lab or the Debate Chamber: scientists present at the wall, other agents challenge, minutes appear on screen; driven by `lab.council.*` events |
| Visual states | Explorer: `THINKING` (hypothesis), `CHECKING` (experiment running); Validator: `CHECKING`; both `REPORTING` at the Council. All derived from runtime events, as in the visual plan |

The room shows only recorded research. It never shows a trade signal.

---

## 21. Safety boundaries (summary)

1. **No trading authority.** No execution, no ratings, no proposals, no sizing, no approvals.
2. **No risk authority.** It cannot read, change or tune risk configuration or thresholds, and the
   Risk Engine never reads Lab output.
3. **No self-promotion.** Candidates must pass validation; behaviour-affecting adoption needs owner
   approval, a versioned code change with tests, and then simulation and paper validation.
4. **No silent influence.** Consumers receive published, cited findings. Nothing rewrites another
   agent.
5. **Deterministic numbers only.** LLMs propose and explain; code computes.
6. **Point-in-time everywhere.** Experiments and support answers use only data available at their
   `as_of`.
7. **Failures are permanent records.**
8. **Statistical safeguards are mandatory** for any status above E1 (§10).
9. **Budgets and isolation.** The Lab cannot delay or break the trading pipeline.
10. **Market-neutral.** No market views, and no specialist role.

---

## 22. Unresolved decisions

| # | Decision | Options | Safe default until decided |
|---|---|---|---|
| RL-1 | Roster codes and group for the scientists | New group `research_lab` with new codes (the Phase 1 code pattern allows R, V, M, S, T, U, P, E, L, O only, so a new letter or a scheme change is needed); or use existing letters | Not in the registry until the Lab phase |
| RL-2 | Implementation placement | After Phase 7 (proposed); an early read-only subset after Phase 5; later | No implementation |
| RL-3 | Record id prefixes (for example `obs_`, `hyp_`, `exp_`, `res_`, `cand_`, `find_`, `cex_`, `rep_`, `cncl_`) | Adopt, rename | Not added to `IdKind` yet |
| RL-4 | Scientific Memory storage | Tables in the Stellar Journal database; a separate SQLite file | Separate file (isolation) |
| RL-5 | Statistical thresholds | Minimum sample sizes; significance and multiple-testing method; evidence-level criteria; partition sizes | Owner-approved config; none chosen here |
| RL-6 | Budgets | LLM and compute per cycle; exploration/exploitation split; failure limits per lineage | Small fixed budget, configurable |
| RL-7 | Custom formula sandbox | Restricted expression language; sandboxed Python; both | Restricted expression language |
| RL-8 | Support queries inside live decision cycles | Allowed with a time budget; offline only (pre-computed evidence) | Offline only |
| RL-9 | Knowledge Curator | A role of the Supervisor (O1); a separate agent; owner only | Supervisor role, owner approval required |
| RL-10 | Re-test cadence for published findings | Weekly (with the Council); on new data; both | Both |
| RL-11 | Council schedule and attendance | Day and time; mandatory vs invited participants | Weekly, off-market hours, invited participants |
| RL-12 | AI-Newton code reuse | Reuse audit (licence, coupling) before any use; inspiration only | Inspiration only |
| RL-13 | Costs in research | Spread/slippage model per instrument for trading-relevant findings | Gross and net both reported once a cost model exists |
| RL-14 | Visual room placement and Council venue | Lab room vs Debate Chamber | Decided with the visual plan |
| RL-15 | Data depth for seasonality and long-horizon studies | Depends on the historical source (D-1) | Studies limited to available history, with the depth reported |
