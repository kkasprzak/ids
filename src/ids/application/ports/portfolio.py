from pathlib import Path
from typing import Protocol

from ids.domain.errors import IDSError
from ids.domain.models import PortfolioSnapshot


class PortfolioLoaderError(IDSError):
    """Base for failures from the PortfolioLoader port."""


class NoPortfolioAvailableError(PortfolioLoaderError):
    """No usable portfolio snapshot can be produced (e.g. no input file found)."""


class PortfolioMalformedError(PortfolioLoaderError):
    """A portfolio source exists but cannot be parsed into a valid snapshot."""


class PortfolioLoader(Protocol):
    """Loads the most recent portfolio snapshot from the configured source."""

    def load_latest(self) -> PortfolioSnapshot: ...

    def load_from_path(self, path: Path) -> PortfolioSnapshot: ...
