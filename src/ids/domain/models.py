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

    def __post_init__(self) -> None:
        _require_positive_decimal("AccountSummary", "equity_pln", self.equity_pln)


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

    def __post_init__(self) -> None:
        _require_positive_decimal("Position", "open_price", self.open_price)
        _require_positive_decimal("Position", "market_price", self.market_price)


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

    @classmethod
    def missing_stop_loss(cls, *, position_id: int, symbol: str) -> "Alert":
        return cls(
            kind=AlertKind.MISSING_STOP_LOSS,
            severity=AlertSeverity.WARNING,
            recommended_action="Set a protective stop-loss in XTB.",
            position_id=position_id,
            symbol=symbol,
        )

    @classmethod
    def stop_loss_breach(cls, *, position_id: int, symbol: str, measured_pct: Decimal) -> "Alert":
        return cls(
            kind=AlertKind.STOP_LOSS_BREACH,
            severity=AlertSeverity.ACTION_REQUIRED,
            recommended_action="Close manually or set a protective stop in XTB.",
            position_id=position_id,
            symbol=symbol,
            measured_pct=measured_pct,
        )

    @classmethod
    def profit_take_opportunity(
        cls, *, position_id: int, symbol: str, measured_pct: Decimal
    ) -> "Alert":
        return cls(
            kind=AlertKind.PROFIT_TAKE_OPPORTUNITY,
            severity=AlertSeverity.WARNING,
            recommended_action="Realize 50% of the position.",
            position_id=position_id,
            symbol=symbol,
            measured_pct=measured_pct,
        )

    @classmethod
    def cash_reserve_below_minimum(cls, *, measured_pct: Decimal) -> "Alert":
        return cls(
            kind=AlertKind.CASH_RESERVE_BELOW_MINIMUM,
            severity=AlertSeverity.WARNING,
            recommended_action="Restore cash reserve to at least 10% of portfolio equity.",
            measured_pct=measured_pct,
        )

    def is_position_alert(self) -> bool:
        return self.position_id is not None

    def is_portfolio_alert(self) -> bool:
        return self.position_id is None


def _require_positive_decimal(model_name: str, field_name: str, value: Decimal) -> None:
    if value <= 0:
        raise ValueError(f"{model_name}.{field_name} must be positive")
