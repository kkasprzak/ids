import pytest

from ids.domain.value_objects import Symbol

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
