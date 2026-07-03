from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import pytest

from ids.application.viewmodels import PositionRow, WeeklySnapshotView
from ids.application.weekly_snapshot import build_weekly_snapshot
from ids.domain.enums import AlertKind, AlertSeverity
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW)


def _weekly_view(snapshot: PortfolioSnapshot) -> WeeklySnapshotView:
    return build_weekly_snapshot(snapshot, now=FIXED_NOW)


def _first_row(view: WeeklySnapshotView) -> PositionRow:
    return view.rows[0]


def test_empty_portfolio_returns_zero_count_and_empty_rows(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(positions=())

    view = _weekly_view(snapshot)

    assert view.open_positions_count == 0
    assert view.rows == ()
    assert view.alerts == ()


def test_single_position_basic_fields_propagated(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    position = make_position(symbol="PKN.PL", open_price=Decimal("99"), market_price=Decimal("111"))
    snapshot = make_snapshot(source_id="src:one", positions=(position,))

    view = _weekly_view(snapshot)

    assert view.as_of_date == snapshot.as_of_date
    assert view.generated_at == FIXED_NOW
    assert view.source_id == "src:one"
    assert view.equity_pln == snapshot.account.equity_pln
    assert view.cash_pln == snapshot.account.balance_pln
    assert view.open_positions_count == 1
    assert _first_row(view).symbol == position.symbol
    assert _first_row(view).open_price == position.open_price
    assert _first_row(view).market_price == position.market_price
    assert _first_row(view).open_date == position.open_time.date()


def test_days_held_uses_as_of_not_now(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    as_of = date(2026, 5, 2)
    open_date = date(2026, 4, 1)
    position = make_position(open_time=datetime(2026, 4, 1, 9, 15, tzinfo=WARSAW))
    snapshot = make_snapshot(as_of=as_of, positions=(position,))

    view = _weekly_view(snapshot)

    assert _first_row(view).days_held == (as_of - open_date).days


def test_pnl_pct_computation_with_quantize_to_two_places(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    position = make_position(purchase_value_pln=Decimal("3"), gross_pl_pln=Decimal("1"))
    snapshot = make_snapshot(positions=(position,))

    view = _weekly_view(snapshot)

    assert _first_row(view).pnl_pct == Decimal("33.33")


def test_cash_pct_computation(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_account: Callable[..., AccountSummary],
) -> None:
    account = make_account(balance=Decimal("250"), equity=Decimal("1000"))
    snapshot = make_snapshot(account=account)

    view = _weekly_view(snapshot)

    assert view.cash_pct == Decimal("25.00")


def test_position_purchase_value_zero_pnl_pct_returns_zero(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    position = make_position(purchase_value_pln=Decimal("0"), gross_pl_pln=Decimal("100"))
    snapshot = make_snapshot(
        positions=(position,),
    )

    view = _weekly_view(snapshot)

    assert _first_row(view).pnl_pct == Decimal("0.00")


def test_rows_sorted_by_pnl_pct_descending(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    low = make_position(
        symbol="LOW.PL", purchase_value_pln=Decimal("100"), gross_pl_pln=Decimal("-5")
    )
    high = make_position(
        symbol="HIGH.PL", purchase_value_pln=Decimal("100"), gross_pl_pln=Decimal("12")
    )
    mid = make_position(
        symbol="MID.PL", purchase_value_pln=Decimal("100"), gross_pl_pln=Decimal("3")
    )
    snapshot = make_snapshot(positions=(low, high, mid))

    view = _weekly_view(snapshot)

    assert tuple(str(row.symbol) for row in view.rows) == ("HIGH.PL", "MID.PL", "LOW.PL")


def test_sort_tie_broken_by_symbol_alpha(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    zzz = make_position(
        symbol="ZZZ.PL", purchase_value_pln=Decimal("100"), gross_pl_pln=Decimal("5")
    )
    aaa = make_position(
        symbol="AAA.PL", purchase_value_pln=Decimal("100"), gross_pl_pln=Decimal("5")
    )
    snapshot = make_snapshot(positions=(zzz, aaa))

    view = _weekly_view(snapshot)

    assert tuple(str(row.symbol) for row in view.rows) == ("AAA.PL", "ZZZ.PL")


def test_source_id_propagated_to_view(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(source_id="xtb:2026-05-12")

    view = _weekly_view(snapshot)

    assert view.source_id == "xtb:2026-05-12"


def test_generated_at_equals_now_argument(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot()

    view = _weekly_view(snapshot)

    assert view.generated_at == FIXED_NOW


def test_same_day_open_has_zero_days_held(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_position: Callable[..., Position],
) -> None:
    open_time = datetime(2026, 5, 2, 8, 0, tzinfo=WARSAW)
    position = make_position(open_time=open_time)
    snapshot = make_snapshot(as_of=date(2026, 5, 2), positions=(position,))

    view = build_weekly_snapshot(snapshot, now=datetime(2026, 5, 1, 12, 0, tzinfo=WARSAW))

    assert _first_row(view).days_held == 0


def test_alerts_are_included_in_view_model(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_account: Callable[..., AccountSummary],
    make_position_with_stop_loss_breach: Callable[..., Position],
    make_position_with_profit_take_opportunity: Callable[..., Position],
    make_position_without_stop_loss: Callable[..., Position],
) -> None:
    account = make_account(balance=Decimal("50"), equity=Decimal("1000"))
    breach = make_position_with_stop_loss_breach(id=7, symbol="BREACH.PL")
    no_sl = make_position_without_stop_loss(id=8, symbol="NOSL.PL")
    take_profit = make_position_with_profit_take_opportunity(id=9, symbol="TAKE.PL")
    snapshot = make_snapshot(account=account, positions=(breach, no_sl, take_profit))

    view = _weekly_view(snapshot)

    assert tuple(alert.kind for alert in view.alerts) == (
        AlertKind.STOP_LOSS_BREACH,
        AlertKind.MISSING_STOP_LOSS,
        AlertKind.PROFIT_TAKE_OPPORTUNITY,
        AlertKind.CASH_RESERVE_BELOW_MINIMUM,
    )
    assert tuple(alert.severity for alert in view.alerts) == (
        AlertSeverity.ACTION_REQUIRED,
        AlertSeverity.WARNING,
        AlertSeverity.WARNING,
        AlertSeverity.WARNING,
    )


def test_rows_flagged_only_for_positions_with_position_alerts(
    make_snapshot: Callable[..., PortfolioSnapshot],
    make_account: Callable[..., AccountSummary],
    make_position_with_stop_loss_breach: Callable[..., Position],
    make_position_without_position_alerts: Callable[..., Position],
) -> None:
    account = make_account(balance=Decimal("50"), equity=Decimal("1000"))
    flagged = make_position_with_stop_loss_breach(id=101, symbol="FLAGGED.PL")
    unflagged = make_position_without_position_alerts(id=102, symbol="OK.PL")
    snapshot = make_snapshot(account=account, positions=(flagged, unflagged))

    view = _weekly_view(snapshot)

    row_flags = {str(row.symbol): row.has_alert for row in view.rows}
    assert row_flags["FLAGGED.PL"] is True
    assert row_flags["OK.PL"] is False
