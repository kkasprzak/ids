"""Core immutable domain models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ids.domain.enums import AlertKind, AlertSeverity, PositionType


@dataclass(frozen=True)
class AccountSummary:
    balance_pln: Decimal
    equity_pln: Decimal
    export_datetime: datetime


@dataclass(frozen=True)
class Position:
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


@dataclass(frozen=True)
class PortfolioSnapshot:
    as_of_date: date
    source_id: str
    account: AccountSummary
    positions: tuple[Position, ...]
    schema_version: int = 1


@dataclass(frozen=True)
class Alert:
    kind: AlertKind
    severity: AlertSeverity
    recommended_action: str
    position_id: int | None = None
    symbol: str | None = None
    measured_pct: Decimal | None = None
