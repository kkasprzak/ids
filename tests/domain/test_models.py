from collections.abc import Callable
from decimal import Decimal

import pytest

from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position

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
