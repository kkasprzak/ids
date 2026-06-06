from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Protocol

import typer
from rich.console import Console

from ids.application.use_cases.generate_weekly_report import GenerateWeeklyReportResult
from ids.domain.errors import IDSError
from ids.domain.timezones import WARSAW
from ids.presentation.cli.constants import (
    IKZE_ACCOUNT_ID_ENV,
)

console = Console()
err_console = Console(stderr=True)


class WeeklyReportCommand(Protocol):
    def __call__(
        self,
        *,
        export: Path | None,
        ikze_account_id: str,
        now: datetime,
    ) -> GenerateWeeklyReportResult: ...


def _now_warsaw() -> datetime:
    return datetime.now(WARSAW)


# Stable test seam for deterministic CLI runs; keep tests off private clock helpers.
_clock: Callable[[], datetime] = _now_warsaw


def create_app(
    *,
    run_weekly_report: WeeklyReportCommand,
    clock: Callable[[], datetime] | None = None,
) -> typer.Typer:
    app = typer.Typer(no_args_is_help=True, add_completion=False)

    @app.command("weekly")
    def weekly(  # pyright: ignore[reportUnusedFunction]
        export: Annotated[
            Path | None,
            typer.Option("--export", help="Override auto-discovery: load this specific XLSX."),
        ] = None,
        ikze_account_id: Annotated[
            str | None,
            typer.Option(
                "--ikze-account-id",
                envvar=IKZE_ACCOUNT_ID_ENV,
                help=(
                    "XTB IKZE account ID matching your export filenames. "
                    f"Falls back to the {IKZE_ACCOUNT_ID_ENV} environment variable."
                ),
            ),
        ] = None,
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
            result = run_weekly_report(
                export=export,
                ikze_account_id=ikze_account_id,
                now=(clock or _clock)(),
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

    return app
