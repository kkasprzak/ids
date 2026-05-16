# Fully synthetic fixture — no real brokerage data.
# Account 99999999, position IDs 1000000001/2, and all monetary values are
# invented. Regenerate by running this script and committing the result after
# reviewing the diff. Never replace with a real XTB export.
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tests.adapters.conftest import make_xlsx

FIXTURE_PATH = Path(__file__).parent / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx"


if __name__ == "__main__":
    make_xlsx(
        FIXTURE_PATH,
        balance=Decimal("3000.00"),
        equity=Decimal("15000.00"),
        export_dt=datetime(2026, 5, 2, 10, 30),
        positions=[
            {
                "Position": 1000000001,
                "Symbol": "VWCE.DE",
                "Open time": datetime(2026, 4, 20, 9, 0),
                "Open price": Decimal("100.00"),
                "Market price": Decimal("110.00"),
                "Purchase value": Decimal("1000.00"),
                "Gross P/L": Decimal("100.00"),
                "SL": Decimal("90.00"),
            },
            {
                "Position": 1000000002,
                "Symbol": "CNDX.UK",
                "Open time": datetime(2026, 4, 30, 9, 0),
                "Open price": Decimal("200.00"),
                "Market price": Decimal("190.00"),
                "Purchase value": Decimal("2000.00"),
                "Gross P/L": Decimal("-100.00"),
                "SL": Decimal("180.00"),
            },
        ],
    )
