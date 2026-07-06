"""Reconcile the position-log directory against the latest portfolio snapshot."""

from dataclasses import dataclass
from datetime import datetime

from ids.application.ports.portfolio import PortfolioLoader
from ids.application.ports.position_log_store import PositionLogEntry, PositionLogStore
from ids.domain.enums import PositionLogStatus
from ids.domain.models import ClosedPosition, Position


@dataclass(frozen=True)
class SyncPositionLogsResult:
    synced_at: datetime
    source_file: str
    created_count: int
    refreshed_count: int
    status_transitioned_count: int


def sync_position_logs(
    *,
    loader: PortfolioLoader,
    log_store: PositionLogStore,
    now: datetime,
) -> SyncPositionLogsResult:
    """Project the latest snapshot's positions into position-log entries and upsert them."""
    snapshot = loader.load_latest()

    entries = [
        *(_open_entry(position) for position in snapshot.positions),
        *(_closed_entry(position) for position in snapshot.closed_positions),
    ]
    upsert = log_store.upsert_metadata(entries)

    return SyncPositionLogsResult(
        synced_at=now,
        source_file=snapshot.source_id.removeprefix("xtb:"),
        created_count=upsert.created_count,
        refreshed_count=upsert.refreshed_count,
        status_transitioned_count=upsert.status_transitioned_count,
    )


def _open_entry(position: Position) -> PositionLogEntry:
    return PositionLogEntry(
        id=position.id,
        open_date=position.open_time.date(),
        symbol=position.symbol,
        status=PositionLogStatus.OPEN,
        open_price=position.open_price,
    )


def _closed_entry(position: ClosedPosition) -> PositionLogEntry:
    return PositionLogEntry(
        id=position.id,
        open_date=position.open_time.date(),
        symbol=position.symbol,
        status=PositionLogStatus.CLOSED,
        open_price=position.open_price,
        close_date=position.close_time.date(),
        close_price=position.close_price,
        gross_pl_pln=position.gross_pl_pln,
    )
