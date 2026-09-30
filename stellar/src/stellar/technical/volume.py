"""Volume evidence that keeps real, tick and missing volume apart (Phase 2 semantics).

- The kind comes from the bars (``Candle.volume_kind``): ``real``, ``tick`` or ``none``.
  Tick volume counts price changes; it is never presented as exchange volume.
- If any bar lacks volume, volume is **unavailable**. Nothing is filled with zero.
- Relative volume = latest volume / mean volume of the preceding
  ``relative_volume_lookback`` bars. It is computed only with that many earlier bars, all
  with volume of the same kind, and a non-zero mean.
"""

from __future__ import annotations

from collections.abc import Sequence

from stellar.schemas.market import Candle, VolumeKind
from stellar.technical.models import VolumeEvidence
from stellar.technical.numeric import mean, ratio


def volume_evidence(candles: Sequence[Candle], lookback: int | None) -> VolumeEvidence:
    kinds = {c.volume_kind for c in candles}
    if not candles or VolumeKind.NONE in kinds or any(c.volume is None for c in candles):
        return VolumeEvidence(kind=VolumeKind.NONE, available=False, lookback=lookback)
    if len(kinds) != 1:
        return VolumeEvidence(kind=VolumeKind.NONE, available=False, lookback=lookback)
    kind = kinds.pop()
    latest = candles[-1].volume
    relative = None
    if lookback is not None and len(candles) > lookback:
        relative = ratio(latest, mean([c.volume for c in candles[-1 - lookback:-1]]))
    return VolumeEvidence(kind=kind, available=True, latest=latest, lookback=lookback,
                          relative_volume=relative)
