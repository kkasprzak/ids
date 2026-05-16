from collections.abc import Callable

import pytest

from ids.domain.enums import PositionType
from ids.domain.models import PortfolioSnapshot

pytestmark = pytest.mark.unit


def test_portfolio_snapshot_schema_default_is_1(
    make_snapshot: Callable[..., PortfolioSnapshot],
) -> None:
    snapshot: PortfolioSnapshot = make_snapshot()
    assert snapshot.schema_version == 1


def test_position_type_buy_value() -> None:
    assert PositionType.BUY.value == "BUY"
