"""Pure strategy compliance alert evaluation."""

from decimal import Decimal

from ids.domain.enums import PositionType
from ids.domain.models import Alert, PortfolioSnapshot, Position
from ids.domain.strategy_rules import (
    MIN_CASH_RESERVE_PCT,
    PROFIT_TAKE_PCT,
    STOP_LOSS_PCT,
)
from ids.domain.value_objects import Price

HUNDRED = Decimal("100")


def position_pnl_pct(
    open_price: Price, current_price: Price, position_type: PositionType
) -> Decimal:
    """Signed profit/loss percentage of a position relative to its open price."""
    price_delta = current_price.value - open_price.value
    if position_type is PositionType.SELL:
        price_delta = -price_delta

    return price_delta / open_price.value * HUNDRED


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
    return position_pnl_pct(position.open_price, position.market_price, position.type)


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator * HUNDRED
