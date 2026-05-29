"""Pure strategy compliance alert evaluation."""

from decimal import Decimal

from ids.domain.enums import PositionType
from ids.domain.models import Alert, PortfolioSnapshot, Position
from ids.domain.strategy_rules import (
    MIN_CASH_RESERVE_PCT,
    PROFIT_TAKE_PCT,
    STOP_LOSS_PCT,
)

HUNDRED = Decimal("100")


def evaluate_compliance_alerts(snapshot: PortfolioSnapshot) -> tuple[Alert, ...]:
    """Return deterministic strategy compliance alerts for a portfolio snapshot."""
    alerts: list[Alert] = []

    for position in snapshot.positions:
        alerts.extend(_position_alerts(position))

    cash_pct = _pct(snapshot.account.balance_pln, snapshot.account.equity_pln)
    if cash_pct < MIN_CASH_RESERVE_PCT:
        alerts.append(Alert.cash_reserve_below_minimum(measured_pct=cash_pct))

    return tuple(alerts)


def _position_alerts(position: Position) -> tuple[Alert, ...]:
    alerts: list[Alert] = []

    if position.sl is None:
        alerts.append(Alert.missing_stop_loss(position_id=position.id, symbol=position.symbol))

    pnl_pct = _position_pnl_pct(position)

    if pnl_pct < STOP_LOSS_PCT:
        alerts.append(
            Alert.stop_loss_breach(
                position_id=position.id,
                symbol=position.symbol,
                measured_pct=pnl_pct,
            )
        )

    if pnl_pct >= PROFIT_TAKE_PCT:
        alerts.append(
            Alert.profit_take_opportunity(
                position_id=position.id,
                symbol=position.symbol,
                measured_pct=pnl_pct,
            )
        )

    return tuple(alerts)


def _position_pnl_pct(position: Position) -> Decimal:
    price_delta = position.market_price - position.open_price
    if position.type is PositionType.SELL:
        price_delta = -price_delta

    return price_delta / position.open_price * HUNDRED


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator * HUNDRED
