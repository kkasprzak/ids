from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import typer

from ids.application.use_cases import generate_weekly_report
from ids.application.use_cases.generate_weekly_report import GenerateWeeklyReportResult
from ids.infrastructure.adapters.jsonl_snapshot_store import JSONLSnapshotStore
from ids.infrastructure.adapters.markdown_report_writer import MarkdownReportWriter
from ids.infrastructure.adapters.xtb_portfolio_loader import XTBPortfolioLoader
from ids.presentation.cli import create_app as create_cli_app
from ids.presentation.cli.constants import (
    DEFAULT_REPORTS_DIR,
    DEFAULT_SNAPSHOTS_DIR,
    DEFAULT_XTB_INPUT_DIR,
)
from ids.presentation.cli.report import create_app as create_report_app


def run_weekly_report(
    *,
    export: Path | None,
    ikze_account_id: str,
    now: datetime,
) -> GenerateWeeklyReportResult:
    loader = XTBPortfolioLoader(
        input_dir=DEFAULT_XTB_INPUT_DIR,
        ikze_account_id=ikze_account_id,
    )
    store = JSONLSnapshotStore(DEFAULT_SNAPSHOTS_DIR)
    writer = MarkdownReportWriter()

    return generate_weekly_report(
        loader=loader,
        store=store,
        writer=writer,
        now=now,
        snapshot_dir=DEFAULT_SNAPSHOTS_DIR,
        report_dir=DEFAULT_REPORTS_DIR,
        export=export,
    )


def create_app(clock: Callable[[], datetime] | None = None) -> typer.Typer:
    report_app = create_report_app(run_weekly_report=run_weekly_report, clock=clock)
    return create_cli_app(report_app=report_app)


app = create_app()
