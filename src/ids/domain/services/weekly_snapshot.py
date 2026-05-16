"""Weekly snapshot projection service."""

from datetime import datetime
from decimal import Decimal

from ids.domain.models import PortfolioSnapshot
from ids.domain.viewmodels import PositionRow, WeeklySnapshotView

TWO_DP = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100")


def _pct_or_zero(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return ZERO
    return (numerator / denominator * HUNDRED).quantize(TWO_DP)


def build_weekly_snapshot(
    snapshot: PortfolioSnapshot,
    *,
    now: datetime,
) -> WeeklySnapshotView:
    """Project a portfolio snapshot into a weekly report view model."""
    equity_pln = snapshot.account.equity_pln
    cash_pln = snapshot.account.balance_pln
    cash_pct = _pct_or_zero(cash_pln, equity_pln)

    rows: list[PositionRow] = []
    for position in snapshot.positions:
        open_date = position.open_time.date()
        days_held = (snapshot.as_of_date - open_date).days
        pnl_pln = position.gross_pl_pln
        pnl_pct = _pct_or_zero(pnl_pln, position.purchase_value_pln)
        rows.append(
            PositionRow(
                symbol=position.symbol,
                open_date=open_date,
                days_held=days_held,
                open_price=position.open_price,
                market_price=position.market_price,
                pnl_pln=pnl_pln,
                pnl_pct=pnl_pct,
            )
        )

    sorted_rows = tuple(sorted(rows, key=lambda row: (-row.pnl_pct, row.symbol)))
    return WeeklySnapshotView(
        as_of_date=snapshot.as_of_date,
        generated_at=now,
        source_id=snapshot.source_id,
        equity_pln=equity_pln,
        cash_pln=cash_pln,
        cash_pct=cash_pct,
        open_positions_count=len(snapshot.positions),
        rows=sorted_rows,
    )
