"""Local CSV file provider (Foundation §4.1: file importer first).

Each file is registered with an explicit ``CsvFileSpec``: instrument, timeframe,
provider symbol and mapping kind are declared, never inferred from the file name.

File format:
- optional leading comment lines starting with ``#`` (kept as notes, for example
  a "SYNTHETIC TEST DATA" label);
- a header row with exactly these column names (lower case):
  required ``timestamp``, ``open``, ``high``, ``low``, ``close``;
  optional ``close_time``, ``volume``, ``tick_volume``. Any other column is an
  error (an "adj_close" column would mean the data is not raw prices);
- ``timestamp`` is the bar's open time in ISO 8601. With an offset (``Z``,
  ``+00:00``, ``-05:00``) it is converted to UTC. Without one, the spec must name
  an IANA ``naive_timezone``; ambiguous or non-existent local times (daylight
  saving changes) are errors;
- ``close_time`` defaults to ``timestamp`` + the timeframe duration;
- prices and volumes are parsed as ``Decimal`` from the text as written, so no
  digit is added or lost (``1.08537`` stays ``1.08537``).

Every problem is reported with its line number; the file is rejected, never
patched.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, ValidationError, field_validator, model_validator

from stellar.marketdata.contracts import (
    DataIssue,
    ErrorCode,
    IssueCode,
    IssueSeverity,
    MarketDataError,
    MarketDataSourceInfo,
)
from stellar.marketdata.instruments import InstrumentSpec
from stellar.marketdata.source import BaseMarketDataSource, Clock
from stellar.marketdata.symbols import MappingKind, ProviderSymbolMapping, SymbolMap
from stellar.marketdata.timeframes import duration
from stellar.marketdata.validation import DuplicatePolicy, OrderPolicy
from stellar.schemas.common import InstrumentId, ShortText, StellarModel
from stellar.schemas.market import Candle, Timeframe, VolumeKind

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close")
OPTIONAL_COLUMNS = ("close_time", "volume", "tick_volume")


class CsvFileSpec(StellarModel):
    path: Path
    instrument: InstrumentId
    timeframe: Timeframe
    provider_symbol: ShortText
    mapping_kind: MappingKind = MappingKind.EXACT
    mapping_description: ShortText | None = None
    naive_timezone: ShortText | None = None
    declared_price_decimals: int | None = Field(default=None, ge=0, le=12)
    delimiter: str = Field(default=",", min_length=1, max_length=1)

    @field_validator("naive_timezone")
    @classmethod
    def _known_zone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError(f"unknown IANA timezone {value!r}") from exc
        return value

    @model_validator(mode="after")
    def _supported(self) -> CsvFileSpec:
        if self.mapping_kind is MappingKind.UNSUPPORTED:
            raise ValueError("a registered file cannot be an UNSUPPORTED mapping")
        return self


class CsvImport(StellarModel):
    """Result of parsing one file: bars, their line numbers, issues and comment notes."""

    candles: tuple[Candle, ...] = ()
    rows: tuple[int, ...] = ()
    issues: tuple[DataIssue, ...] = ()
    notes: tuple[str, ...] = ()


def _error(code: IssueCode, message: str, row: int | None = None) -> DataIssue:
    return DataIssue(code=code, severity=IssueSeverity.ERROR, message=message[:500], row=row)


def _parse_time(text: str, zone: ZoneInfo | None, row: int) -> tuple[datetime | None, DataIssue | None]:
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return None, _error(IssueCode.INVALID_TIMESTAMP, f"not an ISO 8601 time: {text!r}", row)
    if value.tzinfo is not None:
        return value, None
    if zone is None:
        return None, _error(IssueCode.NAIVE_TIMESTAMP,
                            f"{text!r} has no UTC offset and the file declares no timezone", row)
    early, late = value.replace(tzinfo=zone, fold=0), value.replace(tzinfo=zone, fold=1)
    # A wall time skipped by a clock change does not survive a round trip through UTC.
    round_trip = early.astimezone(ZoneInfo("UTC")).astimezone(zone).replace(tzinfo=None)
    if round_trip != value:
        return None, _error(IssueCode.NONEXISTENT_LOCAL_TIME,
                            f"{text!r} does not exist in {zone.key} (clock change)", row)
    # A wall time repeated by a clock change has two different UTC offsets.
    if early.utcoffset() != late.utcoffset():
        return None, _error(IssueCode.AMBIGUOUS_LOCAL_TIME,
                            f"{text!r} is ambiguous in {zone.key} (clock change)", row)
    return early, None


def _parse_decimal(text: str, column: str, row: int, required: bool
                   ) -> tuple[Decimal | None, DataIssue | None]:
    text = text.strip()
    if text == "":
        if required:
            return None, _error(IssueCode.INVALID_NUMBER, f"{column} is empty", row)
        return None, None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, _error(IssueCode.INVALID_NUMBER, f"{column} is not a number: {text!r}", row)
    if not value.is_finite():
        return None, _error(IssueCode.INVALID_NUMBER, f"{column} is not finite: {text!r}", row)
    return value, None


def read_csv(spec: CsvFileSpec, provider_id: str, volume_kind: VolumeKind, price_side) -> CsvImport:
    """Parse ``spec.path`` into candles. Never raises for data problems; reports them."""
    try:
        lines = spec.path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise MarketDataError(ErrorCode.SOURCE_UNAVAILABLE, f"cannot read {spec.path}: {exc}") from exc

    notes, start = [], 0
    while start < len(lines) and lines[start].lstrip().startswith("#"):
        notes.append(lines[start].lstrip()[1:].strip())
        start += 1
    if start >= len(lines):
        return CsvImport(notes=tuple(notes),
                         issues=(_error(IssueCode.MISSING_COLUMN, "the file has no header row"),))

    reader = csv.reader(lines[start:], delimiter=spec.delimiter)
    header = [h.strip() for h in next(reader)]
    header_line = start + 1
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    unknown = [c for c in header if c not in REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    duplicated = sorted({c for c in header if header.count(c) > 1})
    issues: list[DataIssue] = []
    if missing:
        issues.append(_error(IssueCode.MISSING_COLUMN, f"missing column(s) {missing}", header_line))
    if unknown or duplicated:
        issues.append(_error(IssueCode.MALFORMED_ROW,
                             f"unexpected or repeated column(s) {unknown + duplicated}", header_line))
    if issues:
        return CsvImport(notes=tuple(notes), issues=tuple(issues))

    zone = ZoneInfo(spec.naive_timezone) if spec.naive_timezone else None
    step: timedelta = duration(spec.timeframe)
    proxy = spec.mapping_kind is not MappingKind.EXACT
    candles, rows = [], []
    for offset, values in enumerate(reader):
        row = header_line + 1 + offset
        if not values or all(not v.strip() for v in values):
            issues.append(_error(IssueCode.MALFORMED_ROW, "empty row", row))
            continue
        if len(values) != len(header):
            issues.append(_error(IssueCode.MALFORMED_ROW,
                                 f"{len(values)} fields, header has {len(header)}", row))
            continue
        record = dict(zip(header, (v.strip() for v in values), strict=True))
        row_issues: list[DataIssue] = []
        open_time, issue = _parse_time(record["timestamp"], zone, row)
        if issue:
            row_issues.append(issue)
        close_time = open_time + step if open_time is not None else None
        if record.get("close_time"):
            close_time, issue = _parse_time(record["close_time"], zone, row)
            if issue:
                row_issues.append(issue)
        numbers = {}
        for column in ("open", "high", "low", "close", "volume", "tick_volume"):
            if column in record:
                numbers[column], issue = _parse_decimal(record[column], column, row,
                                                        required=column in REQUIRED_COLUMNS)
                if issue:
                    row_issues.append(issue)
        if row_issues:
            issues.extend(row_issues)
            continue
        volume = numbers.get("volume")
        try:
            candle = Candle(
                instrument=spec.instrument, timeframe=spec.timeframe,
                open_time=open_time, close_time=close_time,
                open=numbers["open"], high=numbers["high"], low=numbers["low"],
                close=numbers["close"],
                volume=volume, volume_kind=volume_kind if volume is not None else VolumeKind.NONE,
                tick_volume=numbers.get("tick_volume"),
                price_side=price_side, source=provider_id, provider_symbol=spec.provider_symbol,
                proxy=proxy, is_closed=True,
            )
        except ValidationError as exc:
            text = str(exc)
            code = (IssueCode.INVALID_PRICE_RELATION
                    if ("high must" in text or "low must" in text) else IssueCode.MALFORMED_ROW)
            issues.append(_error(code, text.splitlines()[-1] if code is IssueCode.MALFORMED_ROW
                                 else text, row))
            continue
        candles.append(candle)
        rows.append(row)
    return CsvImport(candles=tuple(candles), rows=tuple(rows), issues=tuple(issues),
                     notes=tuple(notes))


class CsvFileProvider(BaseMarketDataSource):
    """Deterministic provider over explicitly registered local CSV files."""

    def __init__(
        self,
        *,
        provider_id: str,
        name: str,
        files: Sequence[CsvFileSpec],
        price_side,
        volume_kind: VolumeKind,
        synthetic: bool = False,
        limitations: Iterable[str] = (),
        clock: Clock | None = None,
        duplicate_policy: DuplicatePolicy = DuplicatePolicy.REJECT,
        order_policy: OrderPolicy = OrderPolicy.REJECT,
        instrument_specs: dict[InstrumentId, InstrumentSpec] | None = None,
    ) -> None:
        self._files: dict[tuple[InstrumentId, Timeframe], CsvFileSpec] = {}
        mappings: dict[InstrumentId, ProviderSymbolMapping] = {}
        for spec in files:
            key = (spec.instrument, spec.timeframe)
            if key in self._files:
                raise ValueError(f"two files registered for {spec.instrument} {spec.timeframe}")
            self._files[key] = spec
            mapping = ProviderSymbolMapping(
                provider_id=provider_id, instrument=spec.instrument, kind=spec.mapping_kind,
                provider_symbol=spec.provider_symbol, description=spec.mapping_description)
            if spec.instrument in mappings and mappings[spec.instrument] != mapping:
                raise ValueError(f"files for {spec.instrument} declare different symbol mappings")
            mappings[spec.instrument] = mapping
        info = MarketDataSourceInfo(
            provider_id=provider_id, name=name, kind="LOCAL_FILE", price_side=price_side,
            volume_kind=volume_kind, synthetic=synthetic, limitations=tuple(limitations),
            timestamp_convention="bar open time; ISO 8601 with offset, or the file's declared "
                                 "timezone, converted to UTC",
        )
        super().__init__(info, SymbolMap(provider_id, mappings.values()), clock=clock,
                         duplicate_policy=duplicate_policy, order_policy=order_policy,
                         instrument_specs=instrument_specs)

    def _available(self) -> dict[InstrumentId, tuple[Timeframe, ...]]:
        available: dict[InstrumentId, list[Timeframe]] = {}
        for instrument, timeframe in self._files:
            available.setdefault(instrument, []).append(timeframe)
        order = list(Timeframe)
        return {i: tuple(sorted(tfs, key=order.index)) for i, tfs in available.items()}

    def _declared_price_decimals(self, instrument: InstrumentId, timeframe: Timeframe) -> int | None:
        return self._files[(instrument, timeframe)].declared_price_decimals

    def _load_candles(self, instrument: InstrumentId, timeframe: Timeframe):
        result = self.read(instrument, timeframe)
        return result.candles, result.rows, result.issues

    def read(self, instrument: InstrumentId, timeframe: Timeframe) -> CsvImport:
        """The raw parse of one registered file, with every issue (no point-in-time cut)."""
        spec = self._files[(InstrumentId(instrument), timeframe)]
        info = self.info()
        return read_csv(spec, info.provider_id, info.volume_kind, info.price_side)
