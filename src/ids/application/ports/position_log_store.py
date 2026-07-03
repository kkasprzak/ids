from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from ids.domain.enums import PositionLogStatus
from ids.domain.errors import IDSError
from ids.domain.position_log_context import ContextAtClose, ContextAtOpen
from ids.domain.value_objects import Price, Symbol


@dataclass(frozen=True)
class PositionLogEntry:
    """A position-log record expressed in domain terms.

    The adapter owns the translation from these typed fields to the Markdown
    frontmatter serialization; the application layer never shapes YAML.
    """

    open_date: date
    symbol: Symbol
    status: PositionLogStatus
    open_price: Price
    close_date: date | None = None
    close_price: Price | None = None
    gross_pl_pln: Decimal | None = None
    context_at_open: ContextAtOpen | None = None
    context_at_close: ContextAtClose | None = None


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
