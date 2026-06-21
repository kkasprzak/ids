from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ids.domain.errors import IDSError
from ids.domain.value_objects import Symbol


@dataclass(frozen=True)
class PositionLogEntry:
    open_date: date
    symbol: Symbol
    frontmatter: dict[str, object]


@dataclass(frozen=True)
class UpsertResult:
    created_count: int
    refreshed_count: int
    status_transitioned_count: int


class PositionLogStoreError(IDSError):
    """Base for failures from the PositionLogStore port."""


class PositionLogStore(Protocol):
    """Persists per-position Markdown logs with system-owned frontmatter."""

    def upsert_metadata(self, entries: Iterable[PositionLogEntry]) -> UpsertResult: ...
