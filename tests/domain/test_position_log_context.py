from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

import pytest

from ids.domain.enums import AlertKind, PositionType
from ids.domain.models import AccountSummary, ClosedPosition, PortfolioSnapshot, Position
from ids.domain.position_log_context import context_at_close, context_at_open
from ids.domain.strategy_rules import PROFIT_TAKE_PCT, STOP_LOSS_PCT
from ids.domain.timezones import WARSAW

pytestmark = pytest.mark.unit
EXPECTED_HOLD_DAYS = 10


def _market_price_for_pnl_pct(open_price: Decimal, pnl_pct: Decimal) -> Decimal:
    return open_price * (Decimal("1") + pnl_pct / Decimal("100"))


def test_context_at_open_captures_portfolio_shape(
    make_account: Callable[..., AccountSummary],
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    account = make_account(balance=Decimal("500"), equity=Decimal("2000"))
    position = make_position(purchase_value_pln=Decimal("400"))
    snapshot = make_snapshot(account=account, positions=(position,))

    context = context_at_open(snapshot, position)

    assert context.portfolio_equity_pln == Decimal("2000")
    assert context.cash_reserve_pct == Decimal("25")
    assert context.open_positions_count == 1
    assert context.this_position_pct_of_portfolio == Decimal("20")


def test_context_at_open_compliant_position_satisfies_all_open_rules(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(sl=Decimal("90"))
    snapshot = make_snapshot(positions=(position,))

    context = context_at_open(snapshot, position)

    assert context.strategy_rules_violated == ()
    assert context.strategy_rules_satisfied == (
        AlertKind.MISSING_STOP_LOSS,
        AlertKind.STOP_LOSS_BREACH,
        AlertKind.CASH_RESERVE_BELOW_MINIMUM,
    )


def test_context_at_open_records_violations_deterministically(
    make_account: Callable[..., AccountSummary],
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    breached_market = _market_price_for_pnl_pct(open_price, STOP_LOSS_PCT - Decimal("0.01"))
    account = make_account(balance=Decimal("100"), equity=Decimal("2000"))  # 5% cash
    position = make_position(open_price=open_price, market_price=breached_market, sl=None)
    snapshot = make_snapshot(account=account, positions=(position,))

    context = context_at_open(snapshot, position)

    assert context.strategy_rules_violated == (
        AlertKind.MISSING_STOP_LOSS,
        AlertKind.STOP_LOSS_BREACH,
        AlertKind.CASH_RESERVE_BELOW_MINIMUM,
    )
    assert context.strategy_rules_satisfied == ()


def test_context_at_open_never_reports_profit_take(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    profitable = _market_price_for_pnl_pct(open_price, PROFIT_TAKE_PCT + Decimal("1"))
    position = make_position(open_price=open_price, market_price=profitable, sl=Decimal("90"))
    snapshot = make_snapshot(positions=(position,))

    context = context_at_open(snapshot, position)

    assert AlertKind.PROFIT_TAKE_OPPORTUNITY not in context.strategy_rules_satisfied
    assert AlertKind.PROFIT_TAKE_OPPORTUNITY not in context.strategy_rules_violated


def test_context_at_open_isolates_violations_to_the_target_position(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    healthy = make_position(id=1, symbol="GOOD.PL", sl=Decimal("90"))
    naked = make_position(id=2, symbol="BARE.PL", sl=None)
    snapshot = make_snapshot(positions=(healthy, naked))

    context = context_at_open(snapshot, healthy)

    assert AlertKind.MISSING_STOP_LOSS not in context.strategy_rules_violated


def test_context_at_close_captures_realized_outcome(
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    closed = make_closed_position(
        open_price=Decimal("100"),
        close_price=Decimal("108"),
        open_time=datetime(2026, 1, 1, 9, 0, tzinfo=WARSAW),
        close_time=datetime(2026, 1, 11, 9, 0, tzinfo=WARSAW),
    )
    snapshot = make_snapshot()

    context = context_at_close(snapshot, snapshot, closed)

    assert context.pnl_pct == Decimal("8")
    assert context.hold_duration_days == EXPECTED_HOLD_DAYS
    assert context.strategy_rules_violated == ()
    assert context.strategy_rules_satisfied == (AlertKind.STOP_LOSS_BREACH,)


def test_context_at_close_flags_stop_loss_breach(
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    closed = make_closed_position(open_price=Decimal("100"), close_price=Decimal("90"))
    snapshot = make_snapshot()

    context = context_at_close(snapshot, snapshot, closed)

    assert context.strategy_rules_violated == (AlertKind.STOP_LOSS_BREACH,)
    assert context.strategy_rules_satisfied == ()


def test_context_at_close_marks_reached_profit_take_as_satisfied(
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    closed = make_closed_position(open_price=Decimal("100"), close_price=Decimal("120"))
    snapshot = make_snapshot()

    context = context_at_close(snapshot, snapshot, closed)

    assert context.strategy_rules_satisfied == (
        AlertKind.STOP_LOSS_BREACH,
        AlertKind.PROFIT_TAKE_OPPORTUNITY,
    )
    assert context.strategy_rules_violated == ()


def test_context_at_close_handles_sell_pnl_sign(
    make_closed_position: Callable[..., ClosedPosition],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    closed = make_closed_position(
        type=PositionType.SELL, open_price=Decimal("100"), close_price=Decimal("80")
    )
    snapshot = make_snapshot()

    context = context_at_close(snapshot, snapshot, closed)

    assert context.pnl_pct == Decimal("20")
    assert AlertKind.PROFIT_TAKE_OPPORTUNITY in context.strategy_rules_satisfied
