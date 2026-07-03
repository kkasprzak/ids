from decimal import ROUND_HALF_UP, getcontext

import pytest
import typer

import ids.presentation.cli

EXPECTED_DECIMAL_PRECISION = 28

pytestmark = pytest.mark.unit


def test_cli_import_configures_decimal_context() -> None:
    assert (
        ids.presentation.cli.create_app(report_app=typer.Typer(), position_log_app=typer.Typer())
        is not None
    )
    assert getcontext().prec == EXPECTED_DECIMAL_PRECISION
    assert getcontext().rounding == ROUND_HALF_UP
