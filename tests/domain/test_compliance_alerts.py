from collections.abc import Callable
from decimal import Decimal

import pytest

from ids.domain.compliance_alerts import evaluate_compliance_alerts
from ids.domain.enums import AlertKind, AlertSeverity, PositionType
from ids.domain.models import AccountSummary, Alert, PortfolioSnapshot, Position
from ids.domain.strategy_rules import MIN_CASH_RESERVE_PCT, PROFIT_TAKE_PCT, STOP_LOSS_PCT

pytestmark = pytest.mark.unit


def _loss_threshold(open_price: Decimal, loss_pct: Decimal) -> Decimal:
    return open_price * (Decimal("1") + loss_pct / Decimal("100"))


def _profit_threshold(open_price: Decimal, profit_pct: Decimal) -> Decimal:
    return open_price * (Decimal("1") + profit_pct / Decimal("100"))


def _cash_balance(equity: Decimal, cash_pct: Decimal) -> Decimal:
    return equity * cash_pct / Decimal("100")


def test_position_with_stop_loss_has_no_missing_stop_loss_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot = make_snapshot(positions=(make_position(sl=Decimal("1")),))

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


def test_loss_beyond_strategy_threshold_gets_stop_loss_breach_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    loss_pct = STOP_LOSS_PCT - Decimal("0.01")
    position = make_position(
        id=7,
        symbol="LOSS.PL",
        open_price=open_price,
        market_price=_loss_threshold(open_price, loss_pct),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.STOP_LOSS_BREACH) == (
        Alert(
            kind=AlertKind.STOP_LOSS_BREACH,
            severity=AlertSeverity.ACTION_REQUIRED,
            position_id=7,
            symbol="LOSS.PL",
            measured_pct=loss_pct,
            recommended_action="Close manually or set a protective stop in XTB.",
        ),
    )


@pytest.mark.parametrize(
    "open_price, market_price",
    [
        (Decimal("100"), _loss_threshold(Decimal("100"), STOP_LOSS_PCT)),
        (Decimal("100"), Decimal("105")),
    ],
)
def test_loss_at_strategy_threshold_or_profit_gets_no_stop_loss_breach_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
    open_price: Decimal,
    market_price: Decimal,
) -> None:
    position = make_position(
        open_price=open_price,
        market_price=market_price,
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.STOP_LOSS_BREACH) == ()


@pytest.mark.parametrize(
    "open_price, market_price",
    [
        (Decimal("100"), _profit_threshold(Decimal("100"), PROFIT_TAKE_PCT)),
        (Decimal("100"), _profit_threshold(Decimal("100"), PROFIT_TAKE_PCT) + Decimal("0.01")),
    ],
)
def test_profit_at_or_beyond_strategy_threshold_gets_profit_take_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
    open_price: Decimal,
    market_price: Decimal,
) -> None:
    position_id = 9
    position = make_position(
        id=position_id,
        open_price=open_price,
        market_price=market_price,
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    profit_take_alerts = _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY)
    assert len(profit_take_alerts) == 1
    assert profit_take_alerts[0].position_id == position_id


def test_profit_below_strategy_threshold_gets_no_profit_take_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    profit_pct = PROFIT_TAKE_PCT - Decimal("0.01")
    position = make_position(
        open_price=open_price,
        market_price=_profit_threshold(open_price, profit_pct),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.PROFIT_TAKE_OPPORTUNITY) == ()


def test_cash_below_strategy_minimum_gets_cash_reserve_alert(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    equity = Decimal("1000")
    cash_pct = MIN_CASH_RESERVE_PCT - Decimal("0.01")
    account = make_account(balance=_cash_balance(equity, cash_pct), equity=equity)
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM) == (
        Alert(
            kind=AlertKind.CASH_RESERVE_BELOW_MINIMUM,
            severity=AlertSeverity.WARNING,
            measured_pct=cash_pct,
            recommended_action="Restore cash reserve to at least 10% of portfolio equity.",
        ),
    )


def test_cash_below_strategy_minimum_is_not_hidden_by_display_rounding(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    equity = Decimal("1000")
    cash_pct = MIN_CASH_RESERVE_PCT - Decimal("0.001")
    account = make_account(balance=_cash_balance(equity, cash_pct), equity=equity)
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM)[0].measured_pct == cash_pct


@pytest.mark.parametrize(
    "cash_pct",
    [MIN_CASH_RESERVE_PCT, MIN_CASH_RESERVE_PCT + Decimal("0.01")],
)
def test_cash_at_or_above_strategy_minimum_gets_no_cash_reserve_alert(
    make_account: Callable[..., AccountSummary],
    make_snapshot: Callable[..., PortfolioSnapshot],
    cash_pct: Decimal,
) -> None:
    equity = Decimal("1000")
    account = make_account(balance=_cash_balance(equity, cash_pct), equity=equity)
    snapshot = make_snapshot(account=account)

    alerts = evaluate_compliance_alerts(snapshot)

    assert _alerts_of_kind(alerts, AlertKind.CASH_RESERVE_BELOW_MINIMUM) == ()


def test_aggregation_returns_all_alerts(
    make_account: Callable[..., AccountSummary],
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    equity = Decimal("1000")
    cash_pct = MIN_CASH_RESERVE_PCT - Decimal("0.01")
    open_price = Decimal("100")
    loss_pct = STOP_LOSS_PCT - Decimal("0.01")
    profit_pct = PROFIT_TAKE_PCT
    account = make_account(balance=_cash_balance(equity, cash_pct), equity=equity)
    missing_sl = make_position(sl=None)
    loss = make_position(
        open_price=open_price,
        market_price=_loss_threshold(open_price, loss_pct),
    )
    profit = make_position(
        open_price=open_price,
        market_price=_profit_threshold(open_price, profit_pct),
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
    equity = Decimal("1000")
    cash_pct = MIN_CASH_RESERVE_PCT + Decimal("0.01")
    open_price = Decimal("100")
    profit_pct = PROFIT_TAKE_PCT - Decimal("0.01")
    account = make_account(balance=_cash_balance(equity, cash_pct), equity=equity)
    position = make_position(
        open_price=open_price,
        market_price=_profit_threshold(open_price, profit_pct),
    )
    snapshot = make_snapshot(account=account, positions=(position,))

    assert evaluate_compliance_alerts(snapshot) == ()


def test_sell_position_price_drop_triggers_profit_take_alert(
    make_position: Callable[..., Position],
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    open_price = Decimal("100")
    position = make_position(
        type=PositionType.SELL,
        open_price=open_price,
        market_price=_loss_threshold(open_price, -PROFIT_TAKE_PCT),
    )
    snapshot = make_snapshot(positions=(position,))

    alerts = evaluate_compliance_alerts(snapshot)

    assert len(alerts) == 1
    assert alerts[0].kind == AlertKind.PROFIT_TAKE_OPPORTUNITY


def _alerts_of_kind(alerts: tuple[Alert, ...], kind: AlertKind) -> tuple[Alert, ...]:
    return tuple(alert for alert in alerts if alert.kind is kind)
