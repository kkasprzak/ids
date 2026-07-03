"""Domain value objects."""

import re
from dataclasses import dataclass
from decimal import Decimal

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$")


@dataclass(frozen=True)
class Symbol:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not normalized:
            raise ValueError("Symbol cannot be empty")
        if not _SYMBOL_PATTERN.fullmatch(normalized):
            raise ValueError(f"Symbol contains unsupported characters: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Price:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"Price must be positive (got {self.value})")

    def __sub__(self, other: "Price") -> Decimal:
        """Return the signed price change; a delta is not itself a Price."""
        return self.value - other.value

    def __str__(self) -> str:
        return str(self.value)
