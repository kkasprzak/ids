from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal

import pytest

from ids.application.ports.position_log_store import PositionLogEntry, UpsertResult
from ids.application.use_cases.sync_position_logs import sync_position_logs
from ids.domain.enums import PositionLogStatus
from ids.domain.models import ClosedPosition, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW
from ids.domain.value_objects import Price, Symbol

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW)


class _LoaderSpy:
    def __init__(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshot = snapshot
        self.load_latest_calls = 0

    def load_latest(self) -> PortfolioSnapshot:
        self.load_latest_calls += 1
        return self._snapshot

    def load_from_path(self, path: object) -> PortfolioSnapshot:
        raise AssertionError(f"Unexpected load_from_path({path})")


class _LogStoreSpy:
    def __init__(self, result: UpsertResult) -> None:
        self._result = result
        self.received: list[PositionLogEntry] = []

    def upsert_metadata(self, entries: Iterable[PositionLogEntry]) -> UpsertResult:
        self.received.extend(entries)
        return self._result


def _no_op_result() -> UpsertResult:
    return UpsertResult(created_count=0, refreshed_count=0, status_transitioned_count=0)


def test_load_latest_is_the_single_source(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    loader = _LoaderSpy(make_snapshot())
    log_store = _LogStoreSpy(_no_op_result())

    sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    assert loader.load_latest_calls == 1


def test_open_positions_project_to_open_entries(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(
        symbol="PKN.PL",
        open_price=Decimal("100"),
    )
    loader = _LoaderSpy(make_snapshot(positions=(position,)))
    log_store = _LogStoreSpy(_no_op_result())

    sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    assert log_store.received == [
        PositionLogEntry(
            open_date=position.open_time.date(),
            symbol=Symbol("PKN.PL"),
            status=PositionLogStatus.OPEN,
            open_price=Price(Decimal("100")),
        )
    ]


def test_closed_positions_project_to_closed_entries(
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    closed = make_closed_position(
        symbol="CDR.PL",
        open_price=Decimal("100"),
        close_price=Decimal("110"),
        gross_pl_pln=Decimal("100"),
    )
    loader = _LoaderSpy(make_snapshot(closed_positions=(closed,)))
    log_store = _LogStoreSpy(_no_op_result())

    sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    assert log_store.received == [
        PositionLogEntry(
            open_date=closed.open_time.date(),
            symbol=Symbol("CDR.PL"),
            status=PositionLogStatus.CLOSED,
            open_price=Price(Decimal("100")),
            close_date=closed.close_time.date(),
            close_price=Price(Decimal("110")),
            gross_pl_pln=Decimal("100"),
        )
    ]


def test_open_and_closed_positions_are_both_projected(
    make_position: Callable[..., Position],
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    loader = _LoaderSpy(
        make_snapshot(
            positions=(make_position(symbol="AAA.PL"),),
            closed_positions=(make_closed_position(symbol="BBB.PL"),),
        )
    )
    log_store = _LogStoreSpy(_no_op_result())

    sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    statuses = [(entry.symbol, entry.status) for entry in log_store.received]
    assert statuses == [
        (Symbol("AAA.PL"), PositionLogStatus.OPEN),
        (Symbol("BBB.PL"), PositionLogStatus.CLOSED),
    ]


def test_empty_snapshot_upserts_no_entries(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    loader = _LoaderSpy(make_snapshot())
    log_store = _LogStoreSpy(_no_op_result())

    sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    assert log_store.received == []


def test_result_propagates_store_counts_and_sync_metadata(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    loader = _LoaderSpy(make_snapshot(source_id="xtb:statement.xlsx", positions=(make_position(),)))
    counts = UpsertResult(created_count=3, refreshed_count=2, status_transitioned_count=1)
    log_store = _LogStoreSpy(counts)

    result = sync_position_logs(loader=loader, log_store=log_store, now=FIXED_NOW)

    assert result.synced_at == FIXED_NOW
    assert result.source_file == "statement.xlsx"
    assert result.created_count == counts.created_count
    assert result.refreshed_count == counts.refreshed_count
    assert result.status_transitioned_count == counts.status_transitioned_count
