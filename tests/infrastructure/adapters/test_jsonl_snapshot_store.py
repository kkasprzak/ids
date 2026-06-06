import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from ids.application.ports import SnapshotMalformedError, SnapshotNotFoundError, SnapshotStoreError
from ids.domain.models import ClosedPosition, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.jsonl_snapshot_store import JSONLSnapshotStore

pytestmark = pytest.mark.integration
SCHEMA_V1 = 1
SCHEMA_V2 = 2
DEFAULT_AS_OF_DATE = date(2026, 5, 2)

type JSONValue = str | int | bool | None | list[JSONValue] | dict[str, JSONValue]
type JSONPayload = dict[str, JSONValue]


def _store(tmp_path: Path) -> JSONLSnapshotStore:
    return JSONLSnapshotStore(root=tmp_path / "outputs" / "snapshots")


def _snapshot_path(tmp_path: Path, as_of: date = DEFAULT_AS_OF_DATE) -> Path:
    return tmp_path / "outputs" / "snapshots" / f"{as_of.isoformat()}.jsonl"


def _utc_json(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _account_payload(**overrides: JSONValue) -> JSONPayload:
    payload: JSONPayload = {
        "balance_pln": "1",
        "equity_pln": "2",
        "export_datetime": "2026-05-02T10:00:00+02:00",
    }
    payload.update(overrides)
    return payload


def _position_payload(**overrides: JSONValue) -> JSONPayload:
    payload: JSONPayload = {
        "id": 1,
        "symbol": "AAA.PL",
        "type": "BUY",
        "volume": "1",
        "open_time": "2026-05-01T10:00:00+02:00",
        "open_price": "100",
        "market_price": "110",
        "purchase_value_pln": "100",
        "gross_pl_pln": "10",
        "sl": None,
    }
    payload.update(overrides)
    return payload


def _closed_position_payload(**overrides: JSONValue) -> JSONPayload:
    payload: JSONPayload = {
        "id": 123,
        "symbol": "AAA.PL",
        "type": "BUY",
        "volume": "1",
        "open_time": "2026-05-01T10:00:00+02:00",
        "close_time": "2026-05-08T10:00:00+02:00",
        "open_price": "100",
        "close_price": "110",
        "purchase_value_pln": "100",
        "gross_pl_pln": "10",
    }
    payload.update(overrides)
    return payload


def _snapshot_payload_v2(**overrides: JSONValue) -> JSONPayload:
    payload: JSONPayload = {
        "schema_version": SCHEMA_V2,
        "as_of_date": DEFAULT_AS_OF_DATE.isoformat(),
        "source_id": "x",
        "account": _account_payload(),
        "positions": [],
        "closed_positions": [],
    }
    payload.update(overrides)
    return payload


def _snapshot_payload_v1(**overrides: JSONValue) -> JSONPayload:
    payload = _without(_snapshot_payload_v2(schema_version=SCHEMA_V1), "closed_positions")
    payload.update(overrides)
    return payload


def _without(payload: JSONPayload, key: str) -> JSONPayload:
    copied = dict(payload)
    copied.pop(key)
    return copied


def _write_snapshot_payload(path: Path, payload: JSONPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


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


def test_save_writes_stable_schema_v2_json_shape(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position_id = 7
    closed_position_id = 1007
    snapshot = make_snapshot(
        positions=(
            make_position(
                id=position_id,
                open_price=Decimal("39.995"),
                market_price=Decimal("40.005"),
                sl=None,
            ),
        ),
        closed_positions=(make_closed_position(id=closed_position_id),),
    )
    store = _store(tmp_path)

    store.save(snapshot)

    raw_line = _snapshot_path(tmp_path).read_text(encoding="utf-8")
    raw_payload: object = json.loads(raw_line)  # pyright: ignore[reportAny]
    assert isinstance(raw_payload, dict)
    payload = raw_payload
    positions = payload["positions"]
    closed_positions = payload["closed_positions"]
    assert isinstance(positions, list)
    assert isinstance(closed_positions, list)
    position = positions[0]
    closed_position = closed_positions[0]
    assert isinstance(position, dict)
    assert isinstance(closed_position, dict)

    assert payload["schema_version"] == SCHEMA_V2
    assert payload["as_of_date"] == snapshot.as_of_date.isoformat()
    assert payload["source_id"] == snapshot.source_id
    assert payload["account"]["balance_pln"] == str(snapshot.account.balance_pln)
    assert payload["account"]["equity_pln"] == str(snapshot.account.equity_pln)
    assert payload["account"]["export_datetime"] == _utc_json(snapshot.account.export_datetime)
    assert position["id"] == position_id
    assert position["open_time"] == _utc_json(snapshot.positions[0].open_time)
    assert position["open_price"] == "39.995"
    assert position["market_price"] == "40.005"
    assert position["sl"] is None
    assert closed_position["id"] == closed_position_id
    assert closed_position["open_time"] == _utc_json(snapshot.closed_positions[0].open_time)
    assert closed_position["close_time"] == _utc_json(snapshot.closed_positions[0].close_time)


def test_save_rejects_naive_datetimes(
    tmp_path: Path,
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(open_time=datetime(2026, 5, 2, 10, 0))
    snapshot = make_snapshot(positions=(position,))
    store = _store(tmp_path)

    with pytest.raises(SnapshotMalformedError, match="timezone-aware"):
        store.save(snapshot)


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


def test_load_missing_raises_snapshot_not_found(tmp_path: Path) -> None:
    store = _store(tmp_path)

    with pytest.raises(SnapshotNotFoundError):
        store.load(DEFAULT_AS_OF_DATE)


def test_save_wraps_filesystem_errors_in_snapshot_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_snapshot: Callable[..., PortfolioSnapshot]
) -> None:
    store = _store(tmp_path)
    snapshot = make_snapshot()
    original_write_text = Path.write_text

    def fail_write_text(self: Path, *args: object, **kwargs: object) -> int:
        if self == _snapshot_path(tmp_path):
            raise PermissionError("blocked")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(SnapshotStoreError, match="Failed to save snapshot"):
        store.save(snapshot)


def test_load_wraps_filesystem_errors_in_snapshot_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_snapshot: Callable[..., PortfolioSnapshot]
) -> None:
    store = _store(tmp_path)
    snapshot = make_snapshot()
    store.save(snapshot)
    original_open = Path.open

    def fail_open(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if self == _snapshot_path(tmp_path):
            raise PermissionError("blocked")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_open)

    with pytest.raises(SnapshotStoreError, match="Failed to load snapshot"):
        store.load(snapshot.as_of_date)


def test_list_all_wraps_filesystem_errors_in_snapshot_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    root = tmp_path / "outputs" / "snapshots"
    root.mkdir(parents=True, exist_ok=True)
    original_is_dir = Path.is_dir

    def fail_is_dir(self: Path) -> bool:
        if self == root:
            raise PermissionError("blocked")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", fail_is_dir)

    with pytest.raises(SnapshotStoreError, match="Failed to list snapshots"):
        store.list_all()


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


def test_unsupported_schema_version_raises_snapshot_malformed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(path, _snapshot_payload_v2(schema_version=3))

    with pytest.raises(SnapshotMalformedError):
        store.load(DEFAULT_AS_OF_DATE)


def test_invalid_json_payload_raises_snapshot_malformed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json}\n", encoding="utf-8")

    with pytest.raises(SnapshotMalformedError, match="JSON"):
        store.load(DEFAULT_AS_OF_DATE)


def test_load_schema_v1_maps_missing_closed_positions_to_empty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(path, _snapshot_payload_v1())

    loaded = store.load(DEFAULT_AS_OF_DATE)

    assert loaded.schema_version == 1
    assert loaded.closed_positions == ()


def test_load_rejects_domain_invalid_payload_as_snapshot_malformed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(
        path,
        _snapshot_payload_v2(positions=[_position_payload(open_price="0")]),
    )

    with pytest.raises(SnapshotMalformedError, match="open_price"):
        store.load(DEFAULT_AS_OF_DATE)


def test_load_rejects_naive_datetimes_as_snapshot_malformed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(
        path,
        _snapshot_payload_v2(
            account=_account_payload(export_datetime="2026-05-02T10:00:00"),
        ),
    )

    with pytest.raises(SnapshotMalformedError, match="timezone-aware"):
        store.load(DEFAULT_AS_OF_DATE)


def test_save_upgrades_loaded_v1_snapshot_to_v2(tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(path, _snapshot_payload_v1())

    loaded_v1 = store.load(DEFAULT_AS_OF_DATE)
    assert loaded_v1.schema_version == SCHEMA_V1

    store.save(loaded_v1)

    raw_payload: object = json.loads(path.read_text(encoding="utf-8"))  # pyright: ignore[reportAny]
    assert isinstance(raw_payload, dict)
    assert raw_payload["schema_version"] == SCHEMA_V2
    assert raw_payload["closed_positions"] == []
    assert store.load(DEFAULT_AS_OF_DATE).schema_version == SCHEMA_V2


def test_list_all_supports_mixed_schema_v1_v2_ordered_by_as_of(tmp_path: Path) -> None:
    store = _store(tmp_path)
    root = tmp_path / "outputs" / "snapshots"
    _write_snapshot_payload(
        root / f"{DEFAULT_AS_OF_DATE.isoformat()}.jsonl",
        _snapshot_payload_v1(source_id="v1"),
    )
    _write_snapshot_payload(
        root / "2026-05-09.jsonl",
        _snapshot_payload_v2(
            as_of_date="2026-05-09",
            source_id="v2",
            account=_account_payload(
                balance_pln="3",
                equity_pln="4",
                export_datetime="2026-05-09T10:00:00+02:00",
            ),
            closed_positions=[_closed_position_payload()],
        ),
    )

    listed = store.list_all()

    assert tuple(snapshot.as_of_date for snapshot in listed) == (
        DEFAULT_AS_OF_DATE,
        date(2026, 5, 9),
    )
    assert listed[0].schema_version == SCHEMA_V1
    assert listed[0].closed_positions == ()
    assert listed[1].schema_version == SCHEMA_V2
    assert len(listed[1].closed_positions) == 1


@pytest.mark.parametrize(
    ("payload", "error_match"),
    (
        (
            _without(_snapshot_payload_v2(), "closed_positions"),
            "closed_positions",
        ),
        (
            _snapshot_payload_v2(positions={}),
            "positions",
        ),
        (
            _snapshot_payload_v2(closed_positions={}),
            "closed_positions",
        ),
        (
            _snapshot_payload_v2(positions=[123]),
            "positions",
        ),
        (
            _snapshot_payload_v2(closed_positions=[123]),
            "closed_positions",
        ),
        (
            _snapshot_payload_v2(schema_version=True),
            "schema_version",
        ),
        (
            _snapshot_payload_v2(schema_version="2"),
            "schema_version",
        ),
        (
            _snapshot_payload_v2(account=_account_payload(balance_pln={})),
            "balance_pln",
        ),
        (
            _snapshot_payload_v2(positions=[_position_payload(id="bad")]),
            "id",
        ),
        (
            _snapshot_payload_v2(positions=[_position_payload(volume="not-a-decimal")]),
            "volume",
        ),
        (
            _snapshot_payload_v2(as_of_date="not-a-date"),
            "as_of_date",
        ),
        (
            _snapshot_payload_v2(account=_account_payload(export_datetime="not-a-datetime")),
            "export_datetime",
        ),
        (
            _snapshot_payload_v2(positions=[_position_payload(type="NOPE")]),
            "type",
        ),
    ),
)
def test_malformed_snapshot_payload_raises_snapshot_malformed(
    tmp_path: Path,
    payload: JSONPayload,
    error_match: str,
) -> None:
    store = _store(tmp_path)
    path = _snapshot_path(tmp_path)
    _write_snapshot_payload(path, payload)

    with pytest.raises(SnapshotMalformedError, match=error_match):
        store.load(DEFAULT_AS_OF_DATE)
