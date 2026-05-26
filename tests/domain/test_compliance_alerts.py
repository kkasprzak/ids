from collections.abc import Callable
from decimal import Decimal

import pytest

from ids.domain.compliance_alerts import evaluate_compliance_alerts
from ids.domain.enums import AlertKind, AlertSeverity, PositionType
from ids.domain.models import AccountSummary, Alert, PortfolioSnapshot, Position
from ids.domain.strategy_rules import STOP_LOSS_PCT

pytestmark = pytest.mark.unit


def test_position_with_stop_loss_has_no_missing_stop_loss_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(positions=(make_position(sl=Decimal("95")),))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.MISSING_STOP_LOSS) == ()


def test_position_without_stop_loss_gets_missing_stop_loss_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(id=42, symbol="PKN.PL", sl=None)
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.MISSING_STOP_LOSS) == (
        Alert(
            kind=AlertKind.MISSING_STOP_LOSS,
            severity=AlertSeverity.WARNING,
            position_id=42,
            symbol="PKN.PL",
            recommended_action="Set a protective stop-loss in XTB.",
        ),
    )


def test_loss_greater_than_five_percent_gets_stop_loss_breach_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    position = make_position(
        id=7,
        symbol="LOSS.PL",
        open_price=open_price,
        market_price=_price_after_pct_move(open_price, _pct_just_below(STOP_LOSS_PCT)),
        sl=Decimal("95"),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.STOP_LOSS_BREACH) == (
        Alert(
            kind=AlertKind.STOP_LOSS_BREACH,
            severity=AlertSeverity.ACTION_REQUIRED,
            position_id=7,
            symbol="LOSS.PL",
            measured_pct=_pct_just_below(STOP_LOSS_PCT),
            recommended_action="Close manually or set a protective stop in XTB.",
        ),
    )


@pytest.mark.parametrize("market_price", [Decimal("95"), Decimal("105")])
def test_loss_at_five_percent_or_profit_gets_no_stop_loss_breach_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
    market_price: Decimal,
) -> None:
    position = make_position(open_price=Decimal("100"), market_price=market_price, sl=Decimal("95"))
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.STOP_LOSS_BREACH) == ()


def test_profit_at_fifteen_percent_gets_profit_take_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(
        id=9,
        symbol="WIN.PL",
        open_price=Decimal("100"),
        market_price=Decimal("115"),
        sl=Decimal("95"),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY) == (
        Alert(
            kind=AlertKind.PROFIT_TAKE_OPPORTUNITY,
            severity=AlertSeverity.WARNING,
            position_id=9,
            symbol="WIN.PL",
            measured_pct=Decimal("15.00"),
            recommended_action="Realize 50% of the position.",
        ),
    )


def test_profit_below_fifteen_percent_gets_no_profit_take_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(
        open_price=Decimal("100"),
        market_price=Decimal("114.99"),
        sl=Decimal("95"),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY) == ()


def test_cash_below_ten_percent_gets_cash_reserve_alert(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    account = make_account(balance=Decimal("99.90"), equity=Decimal("1000"))
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM) == (
        Alert(
            kind=AlertKind.CASH_RESERVE_BELOW_MINIMUM,
            severity=AlertSeverity.WARNING,
            measured_pct=Decimal("9.99"),
            recommended_action="Restore cash reserve to at least 10% of portfolio equity.",
        ),
    )


def test_cash_below_ten_percent_is_not_hidden_by_display_rounding(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    account = make_account(balance=Decimal("99.99"), equity=Decimal("1000"))
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM)[0].measured_pct == Decimal(
        "9.99900"
    )


@pytest.mark.parametrize("balance", [Decimal("100"), Decimal("100.01")])
def test_cash_at_or_above_ten_percent_gets_no_cash_reserve_alert(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
    balance: Decimal,
) -> None:
    account = make_account(balance=balance, equity=Decimal("1000"))
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM) == ()


def test_aggregation_returns_all_alerts(
    make_account: Callable[..., AccountSummary],
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    account = make_account(balance=Decimal("50"), equity=Decimal("1000"))
    missing_sl = make_position(id=1, symbol="NO_SL.PL", sl=None)
    loss = make_position(
        id=2,
        symbol="LOSS.PL",
        open_price=Decimal("100"),
        market_price=Decimal("90"),
        sl=Decimal("95"),
    )
    profit = make_position(
        id=3,
        symbol="PROFIT.PL",
        open_price=Decimal("100"),
        market_price=Decimal("120"),
        sl=Decimal("95"),
    )
    snapshot = make_snapshot(account=account, positions=(missing_sl, loss, profit))

    alerts = evaluate_compliance_alerts(snapshot)

    assert [alert.kind for alert in alerts] == [
        AlertKind.MISSING_STOP_LOSS,
        AlertKind.STOP_LOSS_BREACH,
        AlertKind.PROFIT_TAKE_OPPORTUNITY,
        AlertKind.CASH_RESERVE_BELOW_MINIMUM,
    ]


def test_no_rule_violations_returns_no_alerts(
    make_account: Callable[..., AccountSummary],
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    account = make_account(balance=Decimal("100"), equity=Decimal("1000"))
    position = make_position(
        open_price=Decimal("100"), market_price=Decimal("105"), sl=Decimal("95")
    )
    snapshot = make_snapshot(account=account, positions=(position,))

    assert evaluate_compliance_alerts(snapshot) == ()


def test_sell_position_uses_inverse_price_movement_for_threshold_alerts(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(
        type=PositionType.SELL,
        open_price=Decimal("100"),
        market_price=Decimal("84"),
        sl=Decimal("105"),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY)[0].measured_pct == Decimal(
        "16.00"
    )


def test_zero_open_price_skips_price_threshold_alerts(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    position = make_position(open_price=Decimal("0"), market_price=Decimal("200"), sl=Decimal("95"))
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.STOP_LOSS_BREACH) == ()
    assert _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY) == ()


@pytest.mark.parametrize("equity", [Decimal("0"), Decimal("-1")])
def test_non_positive_equity_skips_cash_reserve_alert(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
    equity: Decimal,
) -> None:
    account = make_account(balance=Decimal("0"), equity=equity)
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM) == ()


def _alerts_of_kind(alerts: tuple[Alert, ...], kind: AlertKind) -> tuple[Alert, ...]:
    return tuple(alert for alert in alerts if alert.kind is kind)


def _price_after_pct_move(open_price: Decimal, pct_move: Decimal) -> Decimal:
    return open_price * (Decimal("1") + pct_move / Decimal("100"))


def _pct_just_below(threshold_pct: Decimal) -> Decimal:
    return threshold_pct - Decimal("0.01")
