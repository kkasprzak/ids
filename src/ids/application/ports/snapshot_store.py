from datetime import date
from typing import Protocol

from ids.domain.errors import IDSError
from ids.domain.models import PortfolioSnapshot


class SnapshotStoreError(IDSError):
    """Base for failures from the SnapshotStore port."""


class SnapshotNotFoundError(SnapshotStoreError):
    """No snapshot exists for the requested date."""


class SnapshotMalformedError(SnapshotStoreError):
    """A snapshot source exists but cannot be parsed into a valid snapshot."""


class SnapshotStore(Protocol):
    """Persists and retrieves PortfolioSnapshot history.

    A snapshot per as_of_date. Idempotent: save(s) followed by save(s) yields the same
    on-disk state. Designed for git-versioned storage where every snapshot is a
    diffable artifact.
    """

    def save(self, snapshot: PortfolioSnapshot) -> None: ...

    def load(self, as_of_date: date) -> PortfolioSnapshot: ...

    def list_all(self) -> tuple[PortfolioSnapshot, ...]:
        """Return all snapshots ordered by as_of_date ascending. Empty tuple if none."""
        ...
