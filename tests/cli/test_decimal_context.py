from decimal import ROUND_HALF_UP, getcontext

import pytest

import ids.cli

EXPECTED_DECIMAL_PRECISION = 28

pytestmark = pytest.mark.unit


def test_cli_import_configures_decimal_context() -> None:
    assert ids.cli.app is not None
    assert getcontext().prec == EXPECTED_DECIMAL_PRECISION
    assert getcontext().rounding == ROUND_HALF_UP
