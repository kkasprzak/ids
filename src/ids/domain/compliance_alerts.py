"""Pure strategy compliance alert evaluation."""

from decimal import Decimal

from ids.domain.enums import AlertKind, AlertSeverity, PositionType
from ids.domain.models import Alert, PortfolioSnapshot, Position
from ids.domain.strategy_rules import (
    MIN_CASH_RESERVE_PCT,
    PROFIT_TAKE_PCT,
    STOP_LOSS_PCT,
)

HUNDRED = Decimal("100")

_MISSING_STOP_LOSS_ACTION = "Set a protective stop-loss in XTB."
_STOP_LOSS_BREACH_ACTION = "Close manually or set a protective stop in XTB."
_PROFIT_TAKE_ACTION = "Realize 50% of the position."
_CASH_RESERVE_ACTION = "Restore cash reserve to at least 10% of portfolio equity."


def evaluate_compliance_alerts(snapshot: PortfolioSnapshot) -> tuple[Alert, ...]:
    """Return deterministic strategy compliance alerts for a portfolio snapshot."""
    alerts: list[Alert] = []

    for position in snapshot.positions:
        alerts.extend(_position_alerts(position))

    cash_pct = _pct_or_none(snapshot.account.balance_pln, snapshot.account.equity_pln)
    if cash_pct is not None and cash_pct < MIN_CASH_RESERVE_PCT:
        alerts.append(
            Alert(
                kind=AlertKind.CASH_RESERVE_BELOW_MINIMUM,
                severity=AlertSeverity.WARNING,
                measured_pct=cash_pct,
                recommended_action=_CASH_RESERVE_ACTION,
            )
        )

    return tuple(alerts)


def _position_alerts(position: Position) -> tuple[Alert, ...]:
    alerts: list[Alert] = []

    if position.sl is None:
        alerts.append(
            Alert(
                kind=AlertKind.MISSING_STOP_LOSS,
                severity=AlertSeverity.WARNING,
                position_id=position.id,
                symbol=position.symbol,
                recommended_action=_MISSING_STOP_LOSS_ACTION,
            )
        )

    pnl_pct = _position_pnl_pct(position)
    if pnl_pct is None:
        return tuple(alerts)

    if pnl_pct < STOP_LOSS_PCT:
        alerts.append(
            Alert(
                kind=AlertKind.STOP_LOSS_BREACH,
                severity=AlertSeverity.ACTION_REQUIRED,
                position_id=position.id,
                symbol=position.symbol,
                measured_pct=pnl_pct,
                recommended_action=_STOP_LOSS_BREACH_ACTION,
            )
        )

    if pnl_pct >= PROFIT_TAKE_PCT:
        alerts.append(
            Alert(
                kind=AlertKind.PROFIT_TAKE_OPPORTUNITY,
                severity=AlertSeverity.WARNING,
                position_id=position.id,
                symbol=position.symbol,
                measured_pct=pnl_pct,
                recommended_action=_PROFIT_TAKE_ACTION,
            )
        )

    return tuple(alerts)


def _position_pnl_pct(position: Position) -> Decimal | None:
    if position.open_price == 0:
        return None

    price_delta = position.market_price - position.open_price
    if position.type is PositionType.SELL:
        price_delta = -price_delta

    return price_delta / position.open_price * HUNDRED


def _pct_or_none(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator <= 0:
        return None
    return numerator / denominator * HUNDRED
