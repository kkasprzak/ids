from decimal import Decimal

import pytest

from ids.application.viewmodels import AlertView
from ids.domain.models import Alert

pytestmark = pytest.mark.unit

POSITION_ID = 123


def test_alert_view_factory_maps_domain_alert_fields() -> None:
    alert = Alert.stop_loss_breach(
        position_id=POSITION_ID,
        symbol="PKN.PL",
        measured_pct=Decimal("-6.50"),
    )

    view = AlertView.from_domain_alert(alert)

    assert view.kind == alert.kind
    assert view.severity == alert.severity
    assert view.recommended_action == alert.recommended_action
    assert view.position_id == POSITION_ID
    assert view.symbol == "PKN.PL"
    assert view.measured_pct == Decimal("-6.50")
