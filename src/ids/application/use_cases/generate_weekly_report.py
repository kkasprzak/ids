from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ids.application.ports.portfolio import PortfolioLoader
from ids.application.ports.report_writer import ReportWriter
from ids.application.ports.snapshot_store import SnapshotStore
from ids.application.weekly_snapshot import build_weekly_snapshot
from ids.domain.models import PortfolioSnapshot


@dataclass(frozen=True)
class GenerateWeeklyReportResult:
    snapshot: PortfolioSnapshot
    snapshot_path: Path
    report_path: Path
    source_file: str


def generate_weekly_report(  # noqa: PLR0913
    *,
    loader: PortfolioLoader,
    store: SnapshotStore,
    writer: ReportWriter,
    now: datetime,
    snapshot_dir: Path,
    report_dir: Path,
    export: Path | None = None,
) -> GenerateWeeklyReportResult:
    snapshot = loader.load_from_path(export) if export else loader.load_latest()
    store.save(snapshot)

    snapshot_path = snapshot_dir / f"{snapshot.as_of_date.isoformat()}.jsonl"
    report_path = report_dir / f"{snapshot.as_of_date.isoformat()}_weekly.md"

    view = build_weekly_snapshot(snapshot, now=now)
    writer.write_weekly(view, str(report_path))

    return GenerateWeeklyReportResult(
        snapshot=snapshot,
        snapshot_path=snapshot_path,
        report_path=report_path,
        source_file=snapshot.source_id.removeprefix("xtb:"),
    )
