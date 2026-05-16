from pathlib import Path
from typing import Protocol

from ids.domain.errors import IDSError
from ids.domain.viewmodels import WeeklySnapshotView


class ReportWriterError(IDSError):
    """Base for failures from the ReportWriter port."""


class ReportWriter(Protocol):
    """Renders a view-model into a report file at the given path."""

    def write_weekly(self, view: WeeklySnapshotView, output_path: Path) -> None: ...
