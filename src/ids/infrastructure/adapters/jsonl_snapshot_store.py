import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ids.application.ports.snapshot_store import SnapshotNotFoundError, SnapshotStore
from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW


class JSONLSnapshotStore(SnapshotStore):
    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, snapshot: PortfolioSnapshot) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(snapshot.as_of_date)
        line = json.dumps(
            _snapshot_to_dict(snapshot),
            separators=(",", ":"),
            ensure_ascii=False,
        )
        path.write_text(f"{line}\n", encoding="utf-8")

    def load(self, as_of_date: date) -> PortfolioSnapshot:
        path = self._path_for(as_of_date)
        if not path.is_file():
            raise SnapshotNotFoundError(
                f"No snapshot for {as_of_date.isoformat()} in {self._root}/",
            )
        return self._load_file(path)

    def list_all(self) -> tuple[PortfolioSnapshot, ...]:
        if not self._root.is_dir():
            return ()
        files = sorted(self._root.glob("*.jsonl"))
        return tuple(self._load_file(path) for path in files)

    def _path_for(self, as_of_date: date) -> Path:
        return self._root / f"{as_of_date.isoformat()}.jsonl"

    def _load_file(self, path: Path) -> PortfolioSnapshot:
        with path.open(encoding="utf-8") as file:
            first_line = file.readline()
        return _dict_to_snapshot(json.loads(first_line))


def _snapshot_to_dict(snapshot: PortfolioSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "as_of_date": snapshot.as_of_date.isoformat(),
        "source_id": snapshot.source_id,
        "account": {
            "balance_pln": str(snapshot.account.balance_pln),
            "equity_pln": str(snapshot.account.equity_pln),
            "export_datetime": snapshot.account.export_datetime.isoformat(),
        },
        "positions": [_position_to_dict(position) for position in snapshot.positions],
    }


def _position_to_dict(position: Position) -> dict[str, Any]:
    return {
        "id": position.id,
        "symbol": position.symbol,
        "type": position.type.value,
        "volume": str(position.volume),
        "open_time": position.open_time.isoformat(),
        "open_price": str(position.open_price),
        "market_price": str(position.market_price),
        "purchase_value_pln": str(position.purchase_value_pln),
        "gross_pl_pln": str(position.gross_pl_pln),
        "sl": str(position.sl) if position.sl is not None else None,
    }


def _dict_to_snapshot(data: dict[str, Any]) -> PortfolioSnapshot:
    if data.get("schema_version") != 1:
        raise SnapshotNotFoundError(
            f"Unsupported snapshot schema_version: {data.get('schema_version')}",
        )
    return PortfolioSnapshot(
        as_of_date=date.fromisoformat(data["as_of_date"]),
        source_id=data["source_id"],
        account=AccountSummary(
            balance_pln=Decimal(data["account"]["balance_pln"]),
            equity_pln=Decimal(data["account"]["equity_pln"]),
            export_datetime=_parse_datetime(data["account"]["export_datetime"]),
        ),
        positions=tuple(_dict_to_position(position) for position in data["positions"]),
        schema_version=data["schema_version"],
    )


def _dict_to_position(data: dict[str, Any]) -> Position:
    return Position(
        id=data["id"],
        symbol=data["symbol"],
        type=PositionType(data["type"]),
        volume=Decimal(data["volume"]),
        open_time=_parse_datetime(data["open_time"]),
        open_price=Decimal(data["open_price"]),
        market_price=Decimal(data["market_price"]),
        purchase_value_pln=Decimal(data["purchase_value_pln"]),
        gross_pl_pln=Decimal(data["gross_pl_pln"]),
        sl=Decimal(data["sl"]) if data["sl"] is not None else None,
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(WARSAW)
