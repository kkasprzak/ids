from decimal import Decimal

import pytest

from ids.domain.value_objects import Price, Symbol

pytestmark = pytest.mark.unit


def test_symbol_normalizes_to_canonical_form() -> None:
    symbol = Symbol(" aaa.pl ")

    assert symbol.value == "AAA.PL"
    assert str(symbol) == "AAA.PL"


@pytest.mark.parametrize("raw", ["", "   "])
def test_symbol_rejects_empty_values(raw: str) -> None:
    with pytest.raises(ValueError, match="Symbol cannot be empty"):
        Symbol(raw)


@pytest.mark.parametrize("raw", ["AAA PL", "AAA/PL"])
def test_symbol_rejects_unsupported_characters(raw: str) -> None:
    with pytest.raises(ValueError, match="unsupported characters"):
        Symbol(raw)


def test_price_keeps_positive_decimal_value() -> None:
    price = Price(Decimal("39.995"))

    assert price.value == Decimal("39.995")
    assert str(price) == "39.995"


@pytest.mark.parametrize("raw", [Decimal("0"), Decimal("-1")])
def test_price_rejects_non_positive_values(raw: Decimal) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        Price(raw)
