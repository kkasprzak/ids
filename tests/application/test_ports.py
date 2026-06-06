import pytest

from ids.application.ports import (
    NoPortfolioAvailableError,
    PortfolioLoaderError,
    PortfolioMalformedError,
    ReportWriterError,
    SnapshotMalformedError,
    SnapshotNotFoundError,
    SnapshotStoreError,
)
from ids.domain.errors import IDSError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "error_type",
    [
        PortfolioLoaderError,
        NoPortfolioAvailableError,
        PortfolioMalformedError,
        ReportWriterError,
        SnapshotStoreError,
        SnapshotNotFoundError,
        SnapshotMalformedError,
    ],
)
def test_port_errors_inherit_from_ids_error(error_type: type[Exception]) -> None:
    assert issubclass(error_type, IDSError)
