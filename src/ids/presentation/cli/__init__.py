"""Command-line interface for IDS."""

from decimal import ROUND_HALF_UP, getcontext

import typer

from ids.presentation.cli import report


def _configure_decimal() -> None:
    ctx = getcontext()
    ctx.prec = 28
    ctx.rounding = ROUND_HALF_UP


_configure_decimal()

app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(report.app, name="report")


@app.callback()
def main() -> None:
    """Investment Decision System."""
