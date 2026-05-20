from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from ids.application.viewmodels import PositionRow, WeeklySnapshotView
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.markdown_report_writer import MarkdownReportWriter

pytestmark = pytest.mark.integration


def _view_with_rows(source_id: str = "xtb:fixture.xlsx") -> WeeklySnapshotView:
    return WeeklySnapshotView(
        as_of_date=date(2026, 5, 2),
        generated_at=datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW),
        source_id=source_id,
        equity_pln=Decimal("2000"),
        cash_pln=Decimal("500"),
        cash_pct=Decimal("25.00"),
        open_positions_count=2,
        rows=(
            PositionRow(
                symbol="AAA.PL",
                open_date=date(2026, 1, 1),
                days_held=10,
                open_price=Decimal("100"),
                market_price=Decimal("120"),
                pnl_pln=Decimal("200"),
                pnl_pct=Decimal("20.00"),
            ),
            PositionRow(
                symbol="BBB.PL",
                open_date=date(2026, 1, 2),
                days_held=9,
                open_price=Decimal("100"),
                market_price=Decimal("110"),
                pnl_pln=Decimal("100"),
                pnl_pct=Decimal("10.00"),
            ),
        ),
    )


def _view_empty_rows() -> WeeklySnapshotView:
    return WeeklySnapshotView(
        as_of_date=date(2026, 5, 2),
        generated_at=datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW),
        source_id="xtb:empty.xlsx",
        equity_pln=Decimal("1000"),
        cash_pln=Decimal("500"),
        cash_pct=Decimal("50"),
        open_positions_count=0,
        rows=(),
    )


def _render(tmp_path: Path, view: WeeklySnapshotView) -> str:
    output = tmp_path / "weekly.md"
    MarkdownReportWriter().write_weekly(view, str(output))
    return output.read_text(encoding="utf-8")


def _assert_contains_all(rendered: str, *needles: str) -> None:
    missing = tuple(needle for needle in needles if needle not in rendered)
    assert missing == ()


def test_writes_to_path(tmp_path: Path) -> None:
    writer = MarkdownReportWriter()
    output = tmp_path / "reports" / "weekly.md"

    writer.write_weekly(_view_with_rows(), str(output))

    assert output.is_file()
    assert output.read_text(encoding="utf-8")


def test_renders_summary_section(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_rows())

    _assert_contains_all(rendered, "Equity", "2\u00a0000.00 PLN")


def test_renders_positions_table_when_non_empty(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_rows())

    _assert_contains_all(rendered, "| Symbol", "AAA.PL", "BBB.PL")


def test_renders_no_positions_placeholder_when_empty(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_empty_rows())

    assert "_No open positions._" in rendered
    assert "| Symbol" not in rendered


def test_creates_parent_dir_if_missing(tmp_path: Path) -> None:
    writer = MarkdownReportWriter()
    output = tmp_path / "nested" / "reports" / "weekly.md"

    writer.write_weekly(_view_with_rows(), str(output))

    assert output.parent.is_dir()
    assert output.is_file()


def test_renders_source_id_verbatim(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_rows(source_id="xtb:foo.xlsx"))

    assert "xtb:foo.xlsx" in rendered
