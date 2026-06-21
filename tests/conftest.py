"""Shared pytest configuration."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import pytest

from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, ClosedPosition, PortfolioSnapshot, Position
from ids.domain.strategy_rules import PROFIT_TAKE_PCT, STOP_LOSS_PCT
from ids.domain.timezones import WARSAW
from ids.domain.value_objects import Price, Symbol


def make_account(
    *,
    balance: Decimal = Decimal("1000"),
    equity: Decimal = Decimal("2000"),
    export_dt: datetime | None = None,
) -> AccountSummary:
    export_datetime = export_dt or datetime(2026, 1, 1, 12, 0, tzinfo=WARSAW)
    return AccountSummary(
        balance_pln=balance,
        equity_pln=equity,
        export_datetime=export_datetime,
    )


def make_position(  # noqa: PLR0913
    *,
    id: int = 1,
    symbol: str = "TEST.PL",
    type: PositionType = PositionType.BUY,
    volume: Decimal = Decimal("10"),
    open_time: datetime | None = None,
    open_price: Decimal = Decimal("100"),
    market_price: Decimal = Decimal("100"),
    purchase_value_pln: Decimal = Decimal("1000"),
    gross_pl_pln: Decimal = Decimal("0"),
    sl: Decimal | None = Decimal("10"),
) -> Position:
    position_open_time = open_time or datetime(2026, 1, 1, 9, 0, tzinfo=WARSAW)
    return Position(
        id=id,
        symbol=Symbol(symbol),
        type=type,
        volume=volume,
        open_time=position_open_time,
        open_price=Price(open_price),
        market_price=Price(market_price),
        purchase_value_pln=purchase_value_pln,
        gross_pl_pln=gross_pl_pln,
        sl=sl,
    )


def make_closed_position(  # noqa: PLR0913
    *,
    id: int = 1001,
    symbol: str = "TEST.PL",
    type: PositionType = PositionType.BUY,
    volume: Decimal = Decimal("10"),
    open_time: datetime | None = None,
    close_time: datetime | None = None,
    open_price: Decimal = Decimal("100"),
    close_price: Decimal = Decimal("110"),
    purchase_value_pln: Decimal = Decimal("1000"),
    gross_pl_pln: Decimal = Decimal("100"),
) -> ClosedPosition:
    position_open_time = open_time or datetime(2026, 1, 1, 9, 0, tzinfo=WARSAW)
    position_close_time = close_time or datetime(2026, 1, 10, 9, 0, tzinfo=WARSAW)
    return ClosedPosition(
        id=id,
        symbol=Symbol(symbol),
        type=type,
        volume=volume,
        open_time=position_open_time,
        close_time=position_close_time,
        open_price=Price(open_price),
        close_price=Price(close_price),
        purchase_value_pln=purchase_value_pln,
        gross_pl_pln=gross_pl_pln,
    )


def make_snapshot(
    *,
    as_of: date = date(2026, 5, 2),
    source_id: str = "test:fixture",
    account: AccountSummary | None = None,
    positions: tuple[Position, ...] = (),
    closed_positions: tuple[ClosedPosition, ...] = (),
) -> PortfolioSnapshot:
    snapshot_account = account or make_account()
    return PortfolioSnapshot(
        as_of_date=as_of,
        source_id=source_id,
        account=snapshot_account,
        positions=positions,
        closed_positions=closed_positions,
    )


def _market_price_for_pnl_pct(open_price: Decimal, pnl_pct: Decimal) -> Decimal:
    return open_price * (Decimal("1") + pnl_pct / Decimal("100"))


def make_position_with_stop_loss_breach(*, id: int, symbol: str) -> Position:
    open_price = Decimal("100")
    breached_pct = STOP_LOSS_PCT - Decimal("0.01")
    return make_position(
        id=id,
        symbol=symbol,
        open_price=open_price,
        market_price=_market_price_for_pnl_pct(open_price, breached_pct),
        sl=Decimal("95"),
    )


def make_position_with_profit_take_opportunity(*, id: int, symbol: str) -> Position:
    open_price = Decimal("100")
    profitable_pct = PROFIT_TAKE_PCT + Decimal("0.01")
    return make_position(
        id=id,
        symbol=symbol,
        open_price=open_price,
        market_price=_market_price_for_pnl_pct(open_price, profitable_pct),
        sl=Decimal("90"),
    )


def make_position_without_position_alerts(*, id: int, symbol: str) -> Position:
    open_price = Decimal("100")
    neutral_pct = Decimal("1")
    return make_position(
        id=id,
        symbol=symbol,
        open_price=open_price,
        market_price=_market_price_for_pnl_pct(open_price, neutral_pct),
        sl=Decimal("90"),
    )


def make_position_without_stop_loss(*, id: int, symbol: str) -> Position:
    return make_position(id=id, symbol=symbol, sl=None)


@pytest.fixture(name="make_account")
def make_account_factory() -> Callable[..., AccountSummary]:
    return make_account


@pytest.fixture(name="make_position")
def make_position_factory() -> Callable[..., Position]:
    return make_position


@pytest.fixture(name="make_closed_position")
def make_closed_position_factory() -> Callable[..., ClosedPosition]:
    return make_closed_position


@pytest.fixture(name="make_snapshot")
def make_snapshot_factory() -> Callable[..., PortfolioSnapshot]:
    return make_snapshot


@pytest.fixture(name="make_position_with_stop_loss_breach")
def make_position_with_stop_loss_breach_factory() -> Callable[..., Position]:
    return make_position_with_stop_loss_breach


@pytest.fixture(name="make_position_with_profit_take_opportunity")
def make_position_with_profit_take_opportunity_factory() -> Callable[..., Position]:
    return make_position_with_profit_take_opportunity


@pytest.fixture(name="make_position_without_position_alerts")
def make_position_without_position_alerts_factory() -> Callable[..., Position]:
    return make_position_without_position_alerts


@pytest.fixture(name="make_position_without_stop_loss")
def make_position_without_stop_loss_factory() -> Callable[..., Position]:
    return make_position_without_stop_loss
