"""Render-oriented immutable view models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ids.domain.enums import AlertKind, AlertSeverity
from ids.domain.models import Alert
from ids.domain.value_objects import Price, Symbol


@dataclass(frozen=True)
class PositionRow:
    """Pre-computed view of one open position, ready to render in the weekly table."""

    symbol: Symbol
    open_date: date
    days_held: int
    open_price: Price
    market_price: Price
    pnl_pln: Decimal
    pnl_pct: Decimal
    has_alert: bool = False


@dataclass(frozen=True)
class AlertView:
    kind: AlertKind
    severity: AlertSeverity
    recommended_action: str
    position_id: int | None = None
    symbol: Symbol | None = None
    measured_pct: Decimal | None = None

    @classmethod
    def from_domain_alert(cls, alert: Alert) -> "AlertView":
        return cls(
            kind=alert.kind,
            severity=alert.severity,
            recommended_action=alert.recommended_action,
            position_id=alert.position_id,
            symbol=alert.symbol,
            measured_pct=alert.measured_pct,
        )


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
    alerts: tuple[AlertView, ...] = ()
