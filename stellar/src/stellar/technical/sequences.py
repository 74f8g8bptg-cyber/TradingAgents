"""Candle sequences ending at the latest bar. No sequence length is assumed to matter.

- ``consecutive_up`` / ``consecutive_down``: bars in the run of UP (DOWN) bars that ends at
  the latest bar.
- ``alternating``: bars in the longest run ending at the latest bar in which each bar is UP
  or DOWN and differs from the one before (a FLAT bar ends the run; a FLAT latest bar
  gives 0).
- ``shrinking_bodies`` / ``expanding_bodies`` / ``shrinking_ranges`` / ``expanding_ranges`` /
  ``lower_highs`` / ``higher_lows``: consecutive *steps* ending at the latest bar in which
  the value is strictly smaller (larger) than on the previous bar.
- ``upper_rejections`` / ``lower_rejections``: bars in the run of UPPER_REJECTION
  (LOWER_REJECTION) bars ending at the latest bar; None when the rejection threshold is
  unset.

``run_length`` answers the same questions for any predicate and N a caller chooses.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from stellar.technical.models import (
    BarDirection,
    CandleEvidence,
    CandleFeatures,
    CandleLabel,
    SequenceEvidence,
)


def run_length(items: Sequence, predicate: Callable) -> int:
    """Items at the end of ``items`` that all satisfy ``predicate``."""
    count = 0
    for item in reversed(items):
        if not predicate(item):
            break
        count += 1
    return count


def steps(features: Sequence[CandleFeatures], key: Callable, *, smaller: bool) -> int:
    count = 0
    for i in range(len(features) - 1, 0, -1):
        a, b = key(features[i - 1]), key(features[i])
        if not (b < a if smaller else b > a):
            break
        count += 1
    return count


def has_run(items: Sequence, predicate: Callable, n: int) -> bool:
    """True when the last ``n`` items all satisfy ``predicate`` (n chosen by the caller)."""
    return run_length(items, predicate) >= n


def sequences(evidence: Sequence[CandleEvidence], *, rejection_configured: bool) -> SequenceEvidence:
    features = [e.features for e in evidence]
    alternating = 0
    for i in range(len(features) - 1, -1, -1):
        f = features[i]
        if f.direction is BarDirection.FLAT:
            break
        if alternating and f.direction is features[i + 1].direction:
            break
        alternating += 1
    rejections: dict = {"upper_rejections": None, "lower_rejections": None}
    if rejection_configured:
        rejections = {
            "upper_rejections": run_length(evidence,
                                           lambda e: CandleLabel.UPPER_REJECTION in e.labels),
            "lower_rejections": run_length(evidence,
                                           lambda e: CandleLabel.LOWER_REJECTION in e.labels)}
    return SequenceEvidence(
        consecutive_up=run_length(features, lambda f: f.direction is BarDirection.UP),
        consecutive_down=run_length(features, lambda f: f.direction is BarDirection.DOWN),
        alternating=alternating,
        shrinking_bodies=steps(features, lambda f: f.body, smaller=True),
        expanding_bodies=steps(features, lambda f: f.body, smaller=False),
        shrinking_ranges=steps(features, lambda f: f.range, smaller=True),
        expanding_ranges=steps(features, lambda f: f.range, smaller=False),
        lower_highs=steps(features, lambda f: f.high, smaller=True),
        higher_lows=steps(features, lambda f: f.low, smaller=False),
        **rejections)
