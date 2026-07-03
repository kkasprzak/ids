"""Moment-of-decision portfolio context and strategy-compliance snapshots.

These structs are written once into position-log frontmatter — on open and on
close — and then frozen. They encode the learning-loop primitive: what the
portfolio looked like and which strategy rules were satisfied/violated at the
instant a position was opened or closed. The strategy-rule vocabulary reuses the
existing :class:`AlertKind` identifiers and the IDS02 compliance evaluator; no
new rule logic is introduced here, only invoked at new moments in time.
"""

from dataclasses import dataclass
from decimal import Decimal

from ids.domain.compliance_alerts import evaluate_compliance_alerts
from ids.domain.enums import AlertKind
from ids.domain.models import ClosedPosition, PortfolioSnapshot, Position
from ids.domain.strategy_rules import PROFIT_TAKE_PCT, STOP_LOSS_PCT

HUNDRED = Decimal("100")

# Rules evaluated at the moment a position is opened. PROFIT_TAKE_OPPORTUNITY is
# deliberately excluded — it is an opportunity signal, not a discipline rule a
# freshly opened position can satisfy or violate.
_OPEN_RULES: tuple[AlertKind, ...] = (
    AlertKind.MISSING_STOP_LOSS,
    AlertKind.STOP_LOSS_BREACH,
    AlertKind.CASH_RESERVE_BELOW_MINIMUM,
)


@dataclass(frozen=True)
class ContextAtOpen:
    portfolio_equity_pln: Decimal
    cash_reserve_pct: Decimal
    open_positions_count: int
    this_position_pct_of_portfolio: Decimal
    strategy_rules_satisfied: tuple[AlertKind, ...]
    strategy_rules_violated: tuple[AlertKind, ...]


@dataclass(frozen=True)
class ContextAtClose:
    hold_duration_days: int
    pnl_pct: Decimal
    strategy_rules_satisfied: tuple[AlertKind, ...]
    strategy_rules_violated: tuple[AlertKind, ...]


def context_at_open(snapshot: PortfolioSnapshot, position: Position) -> ContextAtOpen:
    """Capture portfolio context and strategy compliance at the moment of opening."""
    equity = snapshot.account.equity_pln
    cash_reserve_pct = snapshot.account.balance_pln / equity * HUNDRED
    position_pct = position.purchase_value_pln / equity * HUNDRED
    satisfied, violated = _open_rule_compliance(snapshot, position)
    return ContextAtOpen(
        portfolio_equity_pln=equity,
        cash_reserve_pct=cash_reserve_pct,
        open_positions_count=len(snapshot.positions),
        this_position_pct_of_portfolio=position_pct,
        strategy_rules_satisfied=satisfied,
        strategy_rules_violated=violated,
    )


def context_at_close(
    open_snapshot: PortfolioSnapshot,
    close_snapshot: PortfolioSnapshot,
    closed_position: ClosedPosition,
) -> ContextAtClose:
    """Capture realized outcome and strategy compliance at the moment of closing.

    ``open_snapshot`` and ``close_snapshot`` bracket the holding period; rule
    compliance is judged against the realized P&L of the closed position itself,
    not against either snapshot's open positions.
    """
    pnl_pct = closed_position.pnl_pct()
    hold_duration_days = (closed_position.close_time - closed_position.open_time).days
    satisfied, violated = _close_rule_compliance(pnl_pct)
    return ContextAtClose(
        hold_duration_days=hold_duration_days,
        pnl_pct=pnl_pct,
        strategy_rules_satisfied=satisfied,
        strategy_rules_violated=violated,
    )


def _open_rule_compliance(
    snapshot: PortfolioSnapshot, position: Position
) -> tuple[tuple[AlertKind, ...], tuple[AlertKind, ...]]:
    fired = {
        alert.kind
        for alert in evaluate_compliance_alerts(snapshot)
        if alert.kind in _OPEN_RULES
        and (alert.is_portfolio_alert() or alert.position_id == position.id)
    }
    return _split(_OPEN_RULES, fired)


def _close_rule_compliance(
    pnl_pct: Decimal,
) -> tuple[tuple[AlertKind, ...], tuple[AlertKind, ...]]:
    satisfied: list[AlertKind] = []
    violated: list[AlertKind] = []

    if pnl_pct < STOP_LOSS_PCT:
        violated.append(AlertKind.STOP_LOSS_BREACH)
    else:
        satisfied.append(AlertKind.STOP_LOSS_BREACH)

    # A reached profit-take target is a satisfied opportunity; falling short is
    # not a violation, so PROFIT_TAKE_OPPORTUNITY never appears in `violated`.
    if pnl_pct >= PROFIT_TAKE_PCT:
        satisfied.append(AlertKind.PROFIT_TAKE_OPPORTUNITY)

    return tuple(satisfied), tuple(violated)


def _split(
    applicable: tuple[AlertKind, ...], violated: set[AlertKind]
) -> tuple[tuple[AlertKind, ...], tuple[AlertKind, ...]]:
    satisfied = tuple(rule for rule in applicable if rule not in violated)
    violated_ordered = tuple(rule for rule in applicable if rule in violated)
    return satisfied, violated_ordered
