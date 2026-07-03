from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Protocol

import typer
from rich.console import Console

from ids.application.use_cases.sync_position_logs import SyncPositionLogsResult
from ids.domain.errors import IDSError
from ids.domain.timezones import WARSAW
from ids.presentation.cli.constants import IKZE_ACCOUNT_ID_ENV

console = Console()
err_console = Console(stderr=True)


class SyncPositionLogsCommand(Protocol):
    def __call__(
        self,
        *,
        ikze_account_id: str,
        now: datetime,
    ) -> SyncPositionLogsResult: ...


def _now_warsaw() -> datetime:
    return datetime.now(WARSAW)


# Stable test seam for deterministic CLI runs; keep tests off private clock helpers.
_clock: Callable[[], datetime] = _now_warsaw


def create_app(
    *,
    run_sync_position_logs: SyncPositionLogsCommand,
    clock: Callable[[], datetime] | None = None,
) -> typer.Typer:
    app = typer.Typer(no_args_is_help=True, add_completion=False)

    @app.command("sync")
    def sync(  # pyright: ignore[reportUnusedFunction]
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
        """Reconcile per-position Markdown logs with the latest XTB IKZE export."""
        if not ikze_account_id:
            err_console.print(
                f"[red]✗[/red] IKZE account ID is required. "
                f"Set the {IKZE_ACCOUNT_ID_ENV} environment variable "
                f"or pass --ikze-account-id."
            )
            raise typer.Exit(code=2)
        try:
            result = run_sync_position_logs(
                ikze_account_id=ikze_account_id,
                now=(clock or _clock)(),
            )
            console.print(f"[green]✓[/green] Loaded {result.source_file}")
            console.print(
                f"  {result.created_count} created · "
                f"{result.refreshed_count} refreshed · "
                f"{result.status_transitioned_count} status-transitioned"
            )
        except IDSError as error:
            err_console.print(f"[red]✗[/red] {error}")
            raise typer.Exit(code=1) from error

    return app
