from collections.abc import Callable
from decimal import Decimal

import pytest

from ids.domain.enums import AlertKind, PositionType
from ids.domain.models import AccountSummary, Alert, ClosedPosition, PortfolioSnapshot, Position
from ids.domain.value_objects import Symbol

pytestmark = pytest.mark.unit
SCHEMA_V2 = 2


def test_portfolio_snapshot_schema_default_is_2(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot: PortfolioSnapshot = make_snapshot()
    assert snapshot.schema_version == SCHEMA_V2


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
    with pytest.raises(ValueError, match="Price must be positive"):
        make_position(open_price=open_price)


@pytest.mark.parametrize("market_price", [Decimal("0"), Decimal("-1")])
def test_position_requires_positive_market_price(
    make_position: Callable[..., Position],
    market_price: Decimal,
) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        make_position(market_price=market_price)


@pytest.mark.parametrize("open_price", [Decimal("0"), Decimal("-1")])
def test_closed_position_requires_positive_open_price(
    make_closed_position: Callable[..., ClosedPosition],
    open_price: Decimal,
) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        make_closed_position(open_price=open_price)


@pytest.mark.parametrize("close_price", [Decimal("0"), Decimal("-1")])
def test_closed_position_requires_positive_close_price(
    make_closed_position: Callable[..., ClosedPosition],
    close_price: Decimal,
) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        make_closed_position(close_price=close_price)


@pytest.mark.parametrize(
    ("type_", "market_price", "expected_pct"),
    [
        (PositionType.BUY, Decimal("120"), Decimal("20")),
        (PositionType.BUY, Decimal("94"), Decimal("-6")),
        (PositionType.SELL, Decimal("120"), Decimal("-20")),
        (PositionType.SELL, Decimal("94"), Decimal("6")),
    ],
)
def test_position_pnl_pct_is_signed_relative_to_open_price(
    make_position: Callable[..., Position],
    type_: PositionType,
    market_price: Decimal,
    expected_pct: Decimal,
) -> None:
    position = make_position(type=type_, open_price=Decimal("100"), market_price=market_price)

    assert position.pnl_pct() == expected_pct


@pytest.mark.parametrize(
    ("type_", "close_price", "expected_pct"),
    [
        (PositionType.BUY, Decimal("120"), Decimal("20")),
        (PositionType.BUY, Decimal("94"), Decimal("-6")),
        (PositionType.SELL, Decimal("120"), Decimal("-20")),
        (PositionType.SELL, Decimal("94"), Decimal("6")),
    ],
)
def test_closed_position_pnl_pct_is_signed_relative_to_open_price(
    make_closed_position: Callable[..., ClosedPosition],
    type_: PositionType,
    close_price: Decimal,
    expected_pct: Decimal,
) -> None:
    closed = make_closed_position(type=type_, open_price=Decimal("100"), close_price=close_price)

    assert closed.pnl_pct() == expected_pct


def test_alert_classifies_position_and_portfolio_scope() -> None:
    position_alert = Alert.missing_stop_loss(position_id=42, symbol=Symbol("PKN.PL"))
    portfolio_alert = Alert.cash_reserve_below_minimum(measured_pct=Decimal("9.99"))

    assert position_alert.is_position_alert() is True
    assert position_alert.is_portfolio_alert() is False
    assert portfolio_alert.is_position_alert() is False
    assert portfolio_alert.is_portfolio_alert() is True


def test_alert_factory_methods_define_required_signatures() -> None:
    missing_sl = Alert.missing_stop_loss(position_id=1, symbol=Symbol("AAA.PL"))
    breach = Alert.stop_loss_breach(
        position_id=2, symbol=Symbol("BBB.PL"), measured_pct=Decimal("-5.25")
    )
    profit = Alert.profit_take_opportunity(
        position_id=3, symbol=Symbol("CCC.PL"), measured_pct=Decimal("15.00")
    )
    cash = Alert.cash_reserve_below_minimum(measured_pct=Decimal("9.99"))

    assert missing_sl.kind == AlertKind.MISSING_STOP_LOSS
    assert breach.kind == AlertKind.STOP_LOSS_BREACH
    assert profit.kind == AlertKind.PROFIT_TAKE_OPPORTUNITY
    assert cash.kind == AlertKind.CASH_RESERVE_BELOW_MINIMUM
    assert missing_sl.is_position_alert() is True
    assert cash.is_portfolio_alert() is True
