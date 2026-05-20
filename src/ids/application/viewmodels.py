"""Render-oriented immutable view models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PositionRow:
    """Pre-computed view of one open position, ready to render in the weekly table."""

    symbol: str
    open_date: date
    days_held: int
    open_price: Decimal
    market_price: Decimal
    pnl_pln: Decimal
    pnl_pct: Decimal


@dataclass(frozen=True)
class WeeklySnapshotView:
    as_of_date: date
    generated_at: datetime
    source_id: str
    equity_pln: Decimal
    cash_pln: Decimal
    cash_pct: Decimal
    open_positions_count: int
    rows: tuple[PositionRow, ...]
