from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from ids.application.ports import SnapshotNotFoundError
from ids.domain.models import ClosedPosition, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.jsonl_snapshot_store import JSONLSnapshotStore

pytestmark = pytest.mark.integration
SCHEMA_V1 = 1
SCHEMA_V2 = 2


def _store(tmp_path: Path) -> JSONLSnapshotStore:
    return JSONLSnapshotStore(root=tmp_path / "outputs" / "snapshots")


def _snapshot_path(tmp_path: Path, as_of: date = date(2026, 5, 2)) -> Path:
    return tmp_path / "outputs" / "snapshots" / f"{as_of.isoformat()}.jsonl"


def test_save_creates_file(tmp_path: Path, make_snapshot: Callable[..., PortfolioSnapshot]) -> None:
    snapshot = make_snapshot()
    store = _store(tmp_path)

    store.save(snapshot)

    assert _snapshot_path(tmp_path).is_file()


def test_round_trip(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(
        positions=(make_position(id=7), make_position(id=8)),
        closed_positions=(make_closed_position(id=1007),),
    )
    store = _store(tmp_path)
    store.save(snapshot)

    loaded = store.load(snapshot.as_of_date)

    assert loaded == snapshot


def test_decimal_precision_preserved(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    precise = Decimal("39.995")
    snapshot = make_snapshot(
        positions=(make_position(open_price=precise, market_price=precise),),
    )
    store = _store(tmp_path)
    store.save(snapshot)

    loaded = store.load(snapshot.as_of_date)

    assert loaded.positions[0].open_price == precise
    assert loaded.positions[0].market_price == precise


def test_datetime_warsaw_aware_round_trip(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_time = datetime(2026, 4, 21, 9, 15, tzinfo=WARSAW)
    snapshot = make_snapshot(positions=(make_position(open_time=open_time),))
    store = _store(tmp_path)
    store.save(snapshot)

    loaded = store.load(snapshot.as_of_date)

    assert loaded.positions[0].open_time.tzinfo == WARSAW


def test_sl_none_round_trip(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(positions=(make_position(sl=None),))
    store = _store(tmp_path)
    store.save(snapshot)

    loaded = store.load(snapshot.as_of_date)

    assert loaded.positions[0].sl is None


def test_sl_decimal_round_trip(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(positions=(make_position(sl=Decimal("101.23")),))
    store = _store(tmp_path)
    store.save(snapshot)

    loaded = store.load(snapshot.as_of_date)

    assert loaded.positions[0].sl == Decimal("101.23")


def test_save_idempotent(tmp_path: Path, make_snapshot: Callable[..., PortfolioSnapshot]) -> None:
    snapshot = make_snapshot()
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)

    store.save(snapshot)
    first = path.read_bytes()
    store.save(snapshot)
    second = path.read_bytes()

    assert first == second


def test_save_overwrites_same_as_of_date(
    tmp_path: Path,
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    store = _store(tmp_path)
    first = make_snapshot(source_id="source:first")
    second = make_snapshot(source_id="source:second", positions=(make_position(id=5),))

    store.save(first)
    store.save(second)

    loaded = store.load(first.as_of_date)
    assert loaded == second


def test_load_missing_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)

    with pytest.raises(SnapshotNotFoundError):
        store.load(date(2026, 5, 2))


def test_list_all_orders_by_as_of_ascending(
    tmp_path: Path,
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    store = _store(tmp_path)
    may_16 = make_snapshot(as_of=date(2026, 5, 16), source_id="s3")
    may_2 = make_snapshot(as_of=date(2026, 5, 2), source_id="s1")
    may_9 = make_snapshot(as_of=date(2026, 5, 9), source_id="s2")
    store.save(may_16)
    store.save(may_2)
    store.save(may_9)

    listed = store.list_all()

    assert tuple(snapshot.as_of_date for snapshot in listed) == (
        date(2026, 5, 2),
        date(2026, 5, 9),
        date(2026, 5, 16),
    )


def test_list_all_returns_empty_when_directory_missing(tmp_path: Path) -> None:
    store = _store(tmp_path)

    assert store.list_all() == ()


def test_unsupported_schema_version_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"schema_version":3,"as_of_date":"2026-05-02","source_id":"x","account":{"balance_pln":"1","equity_pln":"1","export_datetime":"2026-05-02T10:00:00+02:00"},"positions":[]}\n',
        encoding="utf-8",
    )

    with pytest.raises(SnapshotNotFoundError):
        store.load(date(2026, 5, 2))


def test_load_schema_v1_maps_missing_closed_positions_to_empty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"schema_version":1,"as_of_date":"2026-05-02","source_id":"x","account":{"balance_pln":"1","equity_pln":"2","export_datetime":"2026-05-02T10:00:00+02:00"},"positions":[]}\n',
        encoding="utf-8",
    )

    loaded = store.load(date(2026, 5, 2))

    assert loaded.schema_version == 1
    assert loaded.closed_positions == ()


def test_list_all_supports_mixed_schema_v1_v2_ordered_by_as_of(tmp_path: Path) -> None:
    store = _store(tmp_path)
    root = tmp_path / "outputs" / "snapshots"
    root.mkdir(parents=True, exist_ok=True)
    (root / "2026-05-02.jsonl").write_text(
        '{"schema_version":1,"as_of_date":"2026-05-02","source_id":"v1","account":{"balance_pln":"1","equity_pln":"2","export_datetime":"2026-05-02T10:00:00+02:00"},"positions":[]}\n',
        encoding="utf-8",
    )
    (root / "2026-05-09.jsonl").write_text(
        '{"schema_version":2,"as_of_date":"2026-05-09","source_id":"v2","account":{"balance_pln":"3","equity_pln":"4","export_datetime":"2026-05-09T10:00:00+02:00"},"positions":[],"closed_positions":[{"id":123,"symbol":"AAA.PL","type":"BUY","volume":"1","open_time":"2026-05-01T10:00:00+02:00","close_time":"2026-05-08T10:00:00+02:00","open_price":"100","close_price":"110","purchase_value_pln":"100","gross_pl_pln":"10"}]}\n',
        encoding="utf-8",
    )

    listed = store.list_all()

    assert tuple(snapshot.as_of_date for snapshot in listed) == (date(2026, 5, 2), date(2026, 5, 9))
    assert listed[0].schema_version == SCHEMA_V1
    assert listed[0].closed_positions == ()
    assert listed[1].schema_version == SCHEMA_V2
    assert len(listed[1].closed_positions) == 1
