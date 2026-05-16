import pytest

from ids.domain.errors import IDSError
from ids.domain.ports import (
    NoPortfolioAvailableError,
    PortfolioLoaderError,
    PortfolioMalformedError,
    ReportWriterError,
    SnapshotNotFoundError,
    SnapshotStoreError,
)

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
    ],
)
def test_port_errors_inherit_from_ids_error(error_type: type[Exception]) -> None:
    assert issubclass(error_type, IDSError)
