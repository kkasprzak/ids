"""Shared pytest configuration."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import pytest

from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW


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
        symbol=symbol,
        type=type,
        volume=volume,
        open_time=position_open_time,
        open_price=open_price,
        market_price=market_price,
        purchase_value_pln=purchase_value_pln,
        gross_pl_pln=gross_pl_pln,
        sl=sl,
    )


def make_snapshot(
    *,
    as_of: date = date(2026, 5, 2),
    source_id: str = "test:fixture",
    account: AccountSummary | None = None,
    positions: tuple[Position, ...] = (),
) -> PortfolioSnapshot:
    snapshot_account = account or make_account()
    return PortfolioSnapshot(
        as_of_date=as_of,
        source_id=source_id,
        account=snapshot_account,
        positions=positions,
    )


@pytest.fixture(name="make_account")
def make_account_factory() -> Callable[..., AccountSummary]:
    return make_account


@pytest.fixture(name="make_position")
def make_position_factory() -> Callable[..., Position]:
    return make_position


@pytest.fixture(name="make_snapshot")
def make_snapshot_factory() -> Callable[..., PortfolioSnapshot]:
    return make_snapshot
