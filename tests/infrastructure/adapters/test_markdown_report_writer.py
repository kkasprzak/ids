from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from ids.application.ports import ReportWriterError
from ids.application.viewmodels import AlertView, PositionRow, WeeklySnapshotView
from ids.domain.enums import AlertKind, AlertSeverity
from ids.domain.timezones import WARSAW
from ids.domain.value_objects import Price, Symbol
from ids.infrastructure.adapters.markdown_report_writer import MarkdownReportWriter

pytestmark = pytest.mark.integration
MINUS = "\N{MINUS SIGN}"


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
                symbol=Symbol("AAA.PL"),
                open_date=date(2026, 1, 1),
                days_held=10,
                open_price=Price(Decimal("100")),
                market_price=Price(Decimal("120")),
                pnl_pln=Decimal("200"),
                pnl_pct=Decimal("20.00"),
            ),
            PositionRow(
                symbol=Symbol("BBB.PL"),
                open_date=date(2026, 1, 2),
                days_held=9,
                open_price=Price(Decimal("100")),
                market_price=Price(Decimal("110")),
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


def _view_with_alerts() -> WeeklySnapshotView:
    return WeeklySnapshotView(
        as_of_date=date(2026, 5, 2),
        generated_at=datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW),
        source_id="xtb:fixture.xlsx",
        equity_pln=Decimal("2000"),
        cash_pln=Decimal("120"),
        cash_pct=Decimal("6.00"),
        open_positions_count=2,
        rows=(
            PositionRow(
                symbol=Symbol("AAA.PL"),
                open_date=date(2026, 1, 1),
                days_held=10,
                open_price=Price(Decimal("100")),
                market_price=Price(Decimal("94")),
                pnl_pln=Decimal("-60"),
                pnl_pct=Decimal("-6.00"),
                has_alert=True,
            ),
            PositionRow(
                symbol=Symbol("BBB.PL"),
                open_date=date(2026, 1, 2),
                days_held=9,
                open_price=Price(Decimal("100")),
                market_price=Price(Decimal("116")),
                pnl_pln=Decimal("160"),
                pnl_pct=Decimal("16.00"),
                has_alert=True,
            ),
        ),
        alerts=(
            AlertView(
                kind=AlertKind.MISSING_STOP_LOSS,
                severity=AlertSeverity.WARNING,
                recommended_action="Set a protective stop-loss in XTB.",
                position_id=101,
                symbol=Symbol("AAA.PL"),
            ),
            AlertView(
                kind=AlertKind.STOP_LOSS_BREACH,
                severity=AlertSeverity.ACTION_REQUIRED,
                recommended_action="Close manually or set a protective stop in XTB.",
                position_id=101,
                symbol=Symbol("AAA.PL"),
                measured_pct=Decimal("-6.00"),
            ),
            AlertView(
                kind=AlertKind.PROFIT_TAKE_OPPORTUNITY,
                severity=AlertSeverity.WARNING,
                recommended_action="Realize 50% of the position.",
                position_id=102,
                symbol=Symbol("BBB.PL"),
                measured_pct=Decimal("16.00"),
            ),
            AlertView(
                kind=AlertKind.CASH_RESERVE_BELOW_MINIMUM,
                severity=AlertSeverity.WARNING,
                recommended_action="Restore cash reserve to at least 10% of portfolio equity.",
                measured_pct=Decimal("6.00"),
            ),
        ),
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

    _assert_contains_all(rendered, "| Symbol", "| Alert |", "AAA.PL", "BBB.PL")


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


def test_wraps_template_lookup_errors_in_report_writer_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = MarkdownReportWriter()
    output = tmp_path / "weekly.md"

    def fail_get_template(name: str) -> object:
        raise TemplateNotFound(name)

    monkeypatch.setattr(writer._env, "get_template", fail_get_template)

    with pytest.raises(ReportWriterError, match="Failed to render weekly report"):
        writer.write_weekly(_view_with_rows(), str(output))


def test_wraps_filesystem_write_errors_in_report_writer_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = MarkdownReportWriter()
    output = tmp_path / "nested" / "weekly.md"
    original_write_text = Path.write_text

    def fail_write_text(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if self == output:
            raise PermissionError("blocked")
        return original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(ReportWriterError, match="Failed to write weekly report"):
        writer.write_weekly(_view_with_rows(), str(output))


def test_renders_source_id_verbatim(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_rows(source_id="xtb:foo.xlsx"))

    assert "xtb:foo.xlsx" in rendered


def test_renders_alert_sections_for_each_alert_type(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_alerts())

    breach_line = (
        "[ACTION_REQUIRED] `AAA.PL` (position 101), "
        f"P&L {MINUS}6.00%: Close manually or set a protective stop in XTB."
    )
    _assert_contains_all(
        rendered,
        "## Alerts",
        "### Missing stop-loss",
        "[WARNING] `AAA.PL` (position 101): Set a protective stop-loss in XTB.",
        "### Stop-loss breach (-5% or below)",
        breach_line,
        "### Profit-take opportunity (+15% or above)",
        "[WARNING] `BBB.PL` (position 102), P&L +16.00%: Realize 50% of the position.",
        "### Cash reserve below minimum (10%)",
        "[WARNING] Cash at 6.00 %: Restore cash reserve to at least 10% of portfolio equity.",
    )


def test_renders_no_alerts_placeholder(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_rows())

    assert "_No strategy compliance alerts._" in rendered


def test_marks_rows_with_alert_flag(tmp_path: Path) -> None:
    rendered = _render(tmp_path, _view_with_alerts())

    assert (
        f"| AAA.PL | 2026-01-01 | 10 | 100.00 | 94.00 | {MINUS}60.00 PLN | {MINUS}6.00% | YES |"
        in rendered
    )
    assert "| BBB.PL | 2026-01-02 | 9 | 100.00 | 116.00 | +160.00 PLN | +16.00% | YES |" in rendered
