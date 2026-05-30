# Fully synthetic fixture — no real brokerage data.
# Designed to trigger every compliance alert kind in the weekly report:
# missing stop-loss, stop-loss breach, profit-take opportunity, and cash
# reserve below minimum. Regenerate by running this script and committing the
# result after reviewing the diff.
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tests.infrastructure.adapters.conftest import make_xlsx

FIXTURE_PATH = Path(__file__).parent / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-09.xlsx"


if __name__ == "__main__":
    make_xlsx(
        FIXTURE_PATH,
        balance=Decimal("1000.00"),
        equity=Decimal("20000.00"),
        export_dt=datetime(2026, 5, 9, 10, 30),
        positions=[
            {
                "Position": 1000000003,
                "Symbol": "SYM_A",
                "Open time": datetime(2026, 4, 25, 9, 0),
                "Open price": Decimal("100.00"),
                "Market price": Decimal("105.00"),
                "Purchase value": Decimal("1000.00"),
                "Gross P/L": Decimal("50.00"),
                "SL": 0,
            },
            {
                "Position": 1000000004,
                "Symbol": "SYM_B",
                "Open time": datetime(2026, 4, 15, 9, 0),
                "Open price": Decimal("100.00"),
                "Market price": Decimal("90.00"),
                "Purchase value": Decimal("1000.00"),
                "Gross P/L": Decimal("-100.00"),
                "SL": Decimal("85.00"),
            },
            {
                "Position": 1000000005,
                "Symbol": "SYM_C",
                "Open time": datetime(2026, 4, 10, 9, 0),
                "Open price": Decimal("100.00"),
                "Market price": Decimal("120.00"),
                "Purchase value": Decimal("1000.00"),
                "Gross P/L": Decimal("200.00"),
                "SL": Decimal("95.00"),
            },
        ],
    )
