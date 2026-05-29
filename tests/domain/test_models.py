from collections.abc import Callable
from decimal import Decimal

import pytest

from ids.domain.enums import AlertKind, PositionType
from ids.domain.models import AccountSummary, Alert, PortfolioSnapshot, Position

pytestmark = pytest.mark.unit


def test_portfolio_snapshot_schema_default_is_1(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot: PortfolioSnapshot = make_snapshot()
    assert snapshot.schema_version == 1


def test_position_type_buy_value() -> None:
    assert PositionType.BUY.value == "BUY"


@pytest.mark.parametrize("equity", [Decimal("0"), Decimal("-1")])
def test_account_summary_requires_positive_equity(
    make_account: Callable[..., AccountSummary],
    equity: Decimal,
) -> None:
    with pytest.raises(ValueError, match=r"AccountSummary\.equity_pln must be positive"):
        make_account(equity=equity)


@pytest.mark.parametrize("open_price", [Decimal("0"), Decimal("-1")])
def test_position_requires_positive_open_price(
    make_position: Callable[..., Position],
    open_price: Decimal,
) -> None:
    with pytest.raises(ValueError, match=r"Position\.open_price must be positive"):
        make_position(open_price=open_price)


@pytest.mark.parametrize("market_price", [Decimal("0"), Decimal("-1")])
def test_position_requires_positive_market_price(
    make_position: Callable[..., Position],
    market_price: Decimal,
) -> None:
    with pytest.raises(ValueError, match=r"Position\.market_price must be positive"):
        make_position(market_price=market_price)


def test_alert_classifies_position_and_portfolio_scope() -> None:
    position_alert = Alert.missing_stop_loss(position_id=42, symbol="PKN.PL")
    portfolio_alert = Alert.cash_reserve_below_minimum(measured_pct=Decimal("9.99"))

    assert position_alert.is_position_alert() is True
    assert position_alert.is_portfolio_alert() is False
    assert portfolio_alert.is_position_alert() is False
    assert portfolio_alert.is_portfolio_alert() is True


def test_alert_factory_methods_define_required_signatures() -> None:
    missing_sl = Alert.missing_stop_loss(position_id=1, symbol="AAA.PL")
    breach = Alert.stop_loss_breach(position_id=2, symbol="BBB.PL", measured_pct=Decimal("-5.25"))
    profit = Alert.profit_take_opportunity(
        position_id=3, symbol="CCC.PL", measured_pct=Decimal("15.00")
    )
    cash = Alert.cash_reserve_below_minimum(measured_pct=Decimal("9.99"))

    assert missing_sl.kind == AlertKind.MISSING_STOP_LOSS
    assert breach.kind == AlertKind.STOP_LOSS_BREACH
    assert profit.kind == AlertKind.PROFIT_TAKE_OPPORTUNITY
    assert cash.kind == AlertKind.CASH_RESERVE_BELOW_MINIMUM
    assert missing_sl.is_position_alert() is True
    assert cash.is_portfolio_alert() is True
