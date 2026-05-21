from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from ids.application.use_cases import generate_weekly_report
from ids.domain.errors import IDSError
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.jsonl_snapshot_store import JSONLSnapshotStore
from ids.infrastructure.adapters.markdown_report_writer import MarkdownReportWriter
from ids.infrastructure.adapters.xtb_portfolio_loader import XTBPortfolioLoader
from ids.presentation.cli.constants import (
    DEFAULT_REPORTS_DIR,
    DEFAULT_SNAPSHOTS_DIR,
    DEFAULT_XTB_INPUT_DIR,
    IKZE_ACCOUNT_ID_ENV,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)
EXPORT_OPTION = typer.Option(
    None,
    "--export",
    help="Override auto-discovery: load this specific XLSX.",
)
IKZE_ACCOUNT_ID_OPTION = typer.Option(
    None,
    "--ikze-account-id",
    envvar=IKZE_ACCOUNT_ID_ENV,
    help=(
        "XTB IKZE account ID matching your export filenames. "
        f"Falls back to the {IKZE_ACCOUNT_ID_ENV} environment variable."
    ),
)


def _now_warsaw() -> datetime:
    return datetime.now(WARSAW)


# Stable test seam for deterministic CLI runs; keep tests off private clock helpers.
_clock: Callable[[], datetime] = _now_warsaw


@app.command("weekly")
def weekly(
    export: Path | None = EXPORT_OPTION,
    ikze_account_id: str | None = IKZE_ACCOUNT_ID_OPTION,
) -> None:
    """Generate the weekly portfolio snapshot from the latest XTB IKZE export."""
    if not ikze_account_id:
        err_console.print(
            f"[red]✗[/red] IKZE account ID is required. "
            f"Set the {IKZE_ACCOUNT_ID_ENV} environment variable "
            f"or pass --ikze-account-id."
        )
        raise typer.Exit(code=2)
    try:
        loader = XTBPortfolioLoader(
            input_dir=DEFAULT_XTB_INPUT_DIR,
            ikze_account_id=ikze_account_id,
        )
        store = JSONLSnapshotStore(DEFAULT_SNAPSHOTS_DIR)
        writer = MarkdownReportWriter()

        result = generate_weekly_report(
            loader=loader,
            store=store,
            writer=writer,
            now=_clock(),
            snapshot_dir=DEFAULT_SNAPSHOTS_DIR,
            report_dir=DEFAULT_REPORTS_DIR,
            export=export,
        )
        snapshot = result.snapshot

        source_file = result.source_file
        console.print(f"[green]✓[/green] Loaded {source_file}")
        console.print(
            f"  Equity {snapshot.account.equity_pln} PLN · "
            f"{len(snapshot.positions)} open positions · "
            f"as of {snapshot.as_of_date.isoformat()}"
        )
        console.print(f"[green]✓[/green] Wrote {result.snapshot_path}")
        console.print(f"[green]✓[/green] Wrote {result.report_path}")

    except IDSError as error:
        err_console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(code=1) from error
