from decimal import Decimal

import pytest

from ids.infrastructure.adapters.formatters import (
    MINUS,
    format_pct_signed,
    format_pct_unsigned,
    format_pln,
    format_pln_signed,
    format_price,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("16677.64"), "16\u00a0677.64 PLN"),
        (Decimal("0"), "0.00 PLN"),
        (Decimal("-524.80"), f"{MINUS}524.80 PLN"),
    ],
)
def test_format_pln(amount: Decimal, expected: str) -> None:
    assert format_pln(amount) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("100.00"), "+100.00 PLN"),
        (Decimal("-100.00"), f"{MINUS}100.00 PLN"),
    ],
)
def test_format_pln_signed(amount: Decimal, expected: str) -> None:
    assert format_pln_signed(amount) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("25.06"), "25.06 %"),
    ],
)
def test_format_pct_unsigned(amount: Decimal, expected: str) -> None:
    assert format_pct_unsigned(amount) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("12.65"), "+12.65%"),
        (Decimal("-5.43"), f"{MINUS}5.43%"),
    ],
)
def test_format_pct_signed(amount: Decimal, expected: str) -> None:
    assert format_pct_signed(amount) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("118.74"), "118.74"),
        (Decimal("39.995"), "39.995"),
        (Decimal("40.20500"), "40.205"),
        (Decimal("100"), "100.00"),
    ],
)
def test_format_price(amount: Decimal, expected: str) -> None:
    assert format_price(amount) == expected
