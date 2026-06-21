from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from ids.application.ports.snapshot_store import (
    SnapshotMalformedError,
    SnapshotNotFoundError,
    SnapshotStore,
    SnapshotStoreError,
)
from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, ClosedPosition, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW
from ids.domain.value_objects import Price, Symbol


class JSONLSnapshotStore(SnapshotStore):
    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, snapshot: PortfolioSnapshot) -> None:
        path = self._path_for(snapshot.as_of_date)
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            line = _snapshot_to_dto(snapshot).model_dump_json()
            path.write_text(f"{line}\n", encoding="utf-8")
        except SnapshotMalformedError:
            raise
        except (ValidationError, TypeError, ValueError) as exc:
            raise SnapshotMalformedError(f"Malformed snapshot payload: {exc}") from exc
        except OSError as exc:
            raise SnapshotStoreError(f"Failed to save snapshot to `{path}`: {exc}") from exc

    def load(self, as_of_date: date) -> PortfolioSnapshot:
        path = self._path_for(as_of_date)
        try:
            if not path.is_file():
                raise SnapshotNotFoundError(
                    f"No snapshot for {as_of_date.isoformat()} in {self._root}/",
                )
            return self._load_file(path)
        except SnapshotNotFoundError:
            raise
        except SnapshotMalformedError:
            raise
        except OSError as exc:
            raise SnapshotStoreError(f"Failed to load snapshot from `{path}`: {exc}") from exc

    def list_all(self) -> tuple[PortfolioSnapshot, ...]:
        try:
            if not self._root.is_dir():
                return ()
            files = sorted(self._root.glob("*.jsonl"))
            return tuple(self._load_file(path) for path in files)
        except SnapshotMalformedError:
            raise
        except OSError as exc:
            raise SnapshotStoreError(f"Failed to list snapshots in `{self._root}`: {exc}") from exc

    def _path_for(self, as_of_date: date) -> Path:
        return self._root / f"{as_of_date.isoformat()}.jsonl"

    def _load_file(self, path: Path) -> PortfolioSnapshot:
        with path.open(encoding="utf-8") as file:
            first_line = file.readline()
        return _dto_to_snapshot(_parse_snapshot_dto(first_line))


class _StrictDTO(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)


class _AccountDTO(_StrictDTO):
    balance_pln: Decimal
    equity_pln: Decimal
    export_datetime: datetime


class _PositionDTO(_StrictDTO):
    id: int
    symbol: str
    type: PositionType
    volume: Decimal
    open_time: datetime
    open_price: Decimal
    market_price: Decimal
    purchase_value_pln: Decimal
    gross_pl_pln: Decimal
    sl: Decimal | None


class _ClosedPositionDTO(_StrictDTO):
    id: int
    symbol: str
    type: PositionType
    volume: Decimal
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    close_price: Decimal
    purchase_value_pln: Decimal
    gross_pl_pln: Decimal


class _SnapshotV1DTO(_StrictDTO):
    schema_version: Literal[1]
    as_of_date: date
    source_id: str
    account: _AccountDTO
    positions: list[_PositionDTO]


class _SnapshotV2DTO(_StrictDTO):
    schema_version: Literal[2]
    as_of_date: date
    source_id: str
    account: _AccountDTO
    positions: list[_PositionDTO]
    closed_positions: list[_ClosedPositionDTO]


type _SnapshotDTO = _SnapshotV1DTO | _SnapshotV2DTO

_SNAPSHOT_DTO_ADAPTER: TypeAdapter[_SnapshotDTO] = TypeAdapter(_SnapshotDTO)


def _snapshot_to_dto(snapshot: PortfolioSnapshot) -> _SnapshotV2DTO:
    try:
        return _SnapshotV2DTO(
            schema_version=2,
            as_of_date=snapshot.as_of_date,
            source_id=snapshot.source_id,
            account=_AccountDTO(
                balance_pln=snapshot.account.balance_pln,
                equity_pln=snapshot.account.equity_pln,
                export_datetime=_to_utc(snapshot.account.export_datetime),
            ),
            positions=[_position_to_dto(position) for position in snapshot.positions],
            closed_positions=[
                _closed_position_to_dto(position) for position in snapshot.closed_positions
            ],
        )
    except ValidationError as exc:
        raise SnapshotMalformedError(f"Malformed snapshot payload: {exc}") from exc


def _position_to_dto(position: Position) -> _PositionDTO:
    return _PositionDTO(
        id=position.id,
        symbol=str(position.symbol),
        type=position.type,
        volume=position.volume,
        open_time=_to_utc(position.open_time),
        open_price=position.open_price.value,
        market_price=position.market_price.value,
        purchase_value_pln=position.purchase_value_pln,
        gross_pl_pln=position.gross_pl_pln,
        sl=position.sl,
    )


def _closed_position_to_dto(position: ClosedPosition) -> _ClosedPositionDTO:
    return _ClosedPositionDTO(
        id=position.id,
        symbol=str(position.symbol),
        type=position.type,
        volume=position.volume,
        open_time=_to_utc(position.open_time),
        close_time=_to_utc(position.close_time),
        open_price=position.open_price.value,
        close_price=position.close_price.value,
        purchase_value_pln=position.purchase_value_pln,
        gross_pl_pln=position.gross_pl_pln,
    )


def _parse_snapshot_dto(payload: str) -> _SnapshotDTO:
    try:
        return _SNAPSHOT_DTO_ADAPTER.validate_json(payload)
    except ValidationError as exc:
        raise SnapshotMalformedError(f"Malformed snapshot JSON: {exc}") from exc


def _dto_to_snapshot(dto: _SnapshotDTO) -> PortfolioSnapshot:
    try:
        closed_positions = (
            ()
            if isinstance(dto, _SnapshotV1DTO)
            else tuple(_dto_to_closed_position(position) for position in dto.closed_positions)
        )
        return PortfolioSnapshot(
            as_of_date=dto.as_of_date,
            source_id=dto.source_id,
            account=AccountSummary(
                balance_pln=dto.account.balance_pln,
                equity_pln=dto.account.equity_pln,
                export_datetime=_to_warsaw(dto.account.export_datetime),
            ),
            positions=tuple(_dto_to_position(position) for position in dto.positions),
            closed_positions=closed_positions,
            schema_version=dto.schema_version,
        )
    except (TypeError, ValueError) as exc:
        raise SnapshotMalformedError(f"Malformed snapshot payload: {exc}") from exc


def _dto_to_position(dto: _PositionDTO) -> Position:
    return Position(
        id=dto.id,
        symbol=Symbol(dto.symbol),
        type=dto.type,
        volume=dto.volume,
        open_time=_to_warsaw(dto.open_time),
        open_price=_dto_price("open_price", dto.open_price),
        market_price=_dto_price("market_price", dto.market_price),
        purchase_value_pln=dto.purchase_value_pln,
        gross_pl_pln=dto.gross_pl_pln,
        sl=dto.sl,
    )


def _dto_to_closed_position(dto: _ClosedPositionDTO) -> ClosedPosition:
    return ClosedPosition(
        id=dto.id,
        symbol=Symbol(dto.symbol),
        type=dto.type,
        volume=dto.volume,
        open_time=_to_warsaw(dto.open_time),
        close_time=_to_warsaw(dto.close_time),
        open_price=_dto_price("open_price", dto.open_price),
        close_price=_dto_price("close_price", dto.close_price),
        purchase_value_pln=dto.purchase_value_pln,
        gross_pl_pln=dto.gross_pl_pln,
    )


def _dto_price(field_name: str, value: Decimal) -> Price:
    try:
        return Price(value)
    except ValueError as exc:
        raise ValueError(f"{field_name}: {exc}") from exc


def _to_warsaw(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise SnapshotMalformedError("Snapshot datetime values must be timezone-aware")
    return value.astimezone(WARSAW)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise SnapshotMalformedError("Snapshot datetime values must be timezone-aware")
    return value.astimezone(UTC)
