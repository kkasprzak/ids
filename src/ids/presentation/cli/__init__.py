"""Command-line interface for IDS."""

from decimal import ROUND_HALF_UP, getcontext

import typer


def _configure_decimal() -> None:
    ctx = getcontext()
    ctx.prec = 28
    ctx.rounding = ROUND_HALF_UP


_configure_decimal()


def create_app(*, report_app: typer.Typer, position_log_app: typer.Typer) -> typer.Typer:
    app = typer.Typer(no_args_is_help=True, add_completion=False)
    app.add_typer(report_app, name="report")
    app.add_typer(position_log_app, name="position-log")

    @app.callback()
    def main() -> None:  # pyright: ignore[reportUnusedFunction]
        """Investment Decision System."""

    return app
