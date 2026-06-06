from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from ids.application.use_cases.generate_weekly_report import generate_weekly_report
from ids.application.viewmodels import WeeklySnapshotView
from ids.domain.models import AccountSummary, PortfolioSnapshot
from ids.domain.timezones import WARSAW

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW)


class _LoaderSpy:
    def __init__(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshot = snapshot
        self.load_latest_calls = 0
        self.loaded_paths: list[Path] = []

    def load_latest(self) -> PortfolioSnapshot:
        self.load_latest_calls += 1
        return self._snapshot

    def load_from_path(self, path: Path) -> PortfolioSnapshot:
        self.loaded_paths.append(path)
        return self._snapshot


class _StoreSpy:
    def __init__(self) -> None:
        self.saved: list[PortfolioSnapshot] = []

    def save(self, snapshot: PortfolioSnapshot) -> None:
        self.saved.append(snapshot)

    def load(self, as_of_date: date) -> PortfolioSnapshot:
        raise AssertionError(f"Unexpected load({as_of_date})")

    def list_all(self) -> tuple[PortfolioSnapshot, ...]:
        return ()


class _WriterSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, WeeklySnapshotView]] = []

    def write_weekly(self, view: WeeklySnapshotView, output_path: str) -> None:
        self.calls.append((output_path, view))


def _snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        as_of_date=date(2026, 5, 2),
        source_id="xtb:fixture.xlsx",
        account=AccountSummary(
            balance_pln=Decimal("1000"),
            equity_pln=Decimal("2000"),
            export_datetime=datetime(2026, 5, 2, 10, 30, tzinfo=WARSAW),
        ),
        positions=(),
    )


def test_uses_load_latest_when_export_is_none() -> None:
    snapshot = _snapshot()
    loader = _LoaderSpy(snapshot)
    store = _StoreSpy()
    writer = _WriterSpy()

    result = generate_weekly_report(
        loader=loader,
        store=store,
        writer=writer,
        now=FIXED_NOW,
        snapshot_dir=Path("outputs/snapshots"),
        report_dir=Path("outputs/reports/weekly"),
        export=None,
    )

    assert loader.load_latest_calls == 1
    assert loader.loaded_paths == []
    assert store.saved == [snapshot]
    assert writer.calls[0][0].endswith("2026-05-02_weekly.md")
    assert result.snapshot_path == Path("outputs/snapshots/2026-05-02.jsonl")
    assert result.report_path == Path("outputs/reports/weekly/2026-05-02_weekly.md")
    assert result.source_file == "fixture.xlsx"


def test_uses_load_from_path_when_export_is_provided() -> None:
    snapshot = _snapshot()
    loader = _LoaderSpy(snapshot)
    store = _StoreSpy()
    writer = _WriterSpy()
    export_path = Path("custom.xlsx")

    generate_weekly_report(
        loader=loader,
        store=store,
        writer=writer,
        now=FIXED_NOW,
        snapshot_dir=Path("outputs/snapshots"),
        report_dir=Path("outputs/reports/weekly"),
        export=export_path,
    )

    assert loader.load_latest_calls == 0
    assert loader.loaded_paths == [export_path]
    assert store.saved == [snapshot]
