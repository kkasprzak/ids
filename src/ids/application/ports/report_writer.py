from typing import Protocol

from ids.application.viewmodels import WeeklySnapshotView
from ids.domain.errors import IDSError


class ReportWriterError(IDSError):
    """Base for failures from the ReportWriter port."""


class ReportWriter(Protocol):
    """Renders a view-model into a report file at the given path."""

    def write_weekly(self, view: WeeklySnapshotView, output_path: str) -> None: ...
