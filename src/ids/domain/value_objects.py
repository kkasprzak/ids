"""Domain value objects."""

import re
from dataclasses import dataclass

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
