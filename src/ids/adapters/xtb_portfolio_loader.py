import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ids.adapters.xtb_filename import parse_xtb_filename
from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position
from ids.domain.ports.portfolio import (
    NoPortfolioAvailableError,
    PortfolioLoader,
    PortfolioMalformedError,
)
from ids.domain.timezones import WARSAW

log = logging.getLogger(__name__)

_OPEN_SHEET_PREFIX = "OPEN POSITION "
_REQUIRED_COLUMNS = (
    "Position",
    "Symbol",
    "Type",
    "Volume",
    "Open time",
    "Open price",
    "Market price",
    "Purchase value",
    "SL",
    "Gross P/L",
)


class XTBPortfolioLoader(PortfolioLoader):
    def __init__(self, input_dir: Path, ikze_account_id: str) -> None:
        self._input_dir = input_dir
        self._account_id = ikze_account_id

    def load_latest(self) -> PortfolioSnapshot:
        if not self._input_dir.is_dir():
            raise NoPortfolioAvailableError(
                f"Directory `{self._input_dir}/` not found.\n"
                f"  Create it and place an XTB XLSX export there:\n"
                f"    mkdir -p {self._input_dir}/\n"
                f"    cp ~/Downloads/account_ikze_{self._account_id}_*.xlsx {self._input_dir}/"
            )

        xlsx_files = sorted(self._input_dir.glob("*.xlsx"))
        candidates = [
            (parse_xtb_filename(path.name, expected_account_id=self._account_id), path)
            for path in xlsx_files
        ]
        matching = [(as_of, path) for as_of, path in candidates if as_of is not None]
        if not matching:
            found = [path.name for path in xlsx_files]
            raise NoPortfolioAvailableError(
                f"No IKZE export matching pattern in `{self._input_dir}/`:\n"
                f"    account_ikze_{self._account_id}_pl_xlsx_<YYYY-MM-DD>_<YYYY-MM-DD>.xlsx\n"
                f"  Found: {found if found else '(empty)'}"
            )

        for as_of, path in candidates:
            if as_of is None:
                log.debug("Skipped %s (does not match IKZE pattern)", path.name)

        matching.sort(key=lambda item: item[0])
        as_of_date, latest_file = matching[-1]
        return self._parse(latest_file, as_of_date)

    def load_from_path(self, path: Path) -> PortfolioSnapshot:
        as_of = parse_xtb_filename(path.name, expected_account_id=self._account_id)
        if as_of is None:
            raise PortfolioMalformedError(
                f"File `{path.name}` does not match expected pattern; cannot derive as_of_date."
            )
        return self._parse(path, as_of)

    def _parse(self, path: Path, as_of_date: date) -> PortfolioSnapshot:
        try:
            workbook = load_workbook(path, data_only=True, read_only=True)
            sheet = self._find_open_position_sheet(workbook)
            account = self._parse_account_summary(sheet)
            positions = self._parse_positions(sheet)
        except PortfolioMalformedError:
            raise
        except Exception as exc:
            raise PortfolioMalformedError(f"Failed to parse {path.name}: {exc}") from exc

        return PortfolioSnapshot(
            as_of_date=as_of_date,
            source_id=f"xtb:{path.name}",
            account=account,
            positions=tuple(positions),
        )

    def _find_open_position_sheet(self, workbook: Workbook) -> Worksheet:
        for name in workbook.sheetnames:
            if name.startswith(_OPEN_SHEET_PREFIX):
                return workbook[name]
        raise PortfolioMalformedError(
            f"No sheet starting with `{_OPEN_SHEET_PREFIX}` found in workbook. "
            f"Sheets: {workbook.sheetnames}"
        )

    def _parse_account_summary(self, sheet: Worksheet) -> AccountSummary:
        label_row_idx, label_columns = self._find_labelled_row(
            sheet, required={"Balance", "Equity"}, max_scan_rows=10
        )
        value_row = next(
            sheet.iter_rows(
                min_row=label_row_idx + 1,
                max_row=label_row_idx + 1,
                values_only=True,
            )
        )
        balance = self._cell_to_decimal(value_row[label_columns["Balance"]])
        equity = self._cell_to_decimal(value_row[label_columns["Equity"]])
        export_dt = self._find_export_datetime(sheet)
        return AccountSummary(balance_pln=balance, equity_pln=equity, export_datetime=export_dt)

    def _parse_positions(self, sheet: Worksheet) -> list[Position]:
        header_row_idx, columns = self._find_labelled_row(
            sheet, required=set(_REQUIRED_COLUMNS), max_scan_rows=20
        )

        positions: list[Position] = []
        for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
            first = row[columns["Position"]] if columns["Position"] < len(row) else None
            if first is None:
                continue
            if first == "Total":
                break
            positions.append(self._row_to_position(row, columns))
        return positions

    def _row_to_position(self, row: tuple[Any, ...], columns: dict[str, int]) -> Position:
        sl_raw = row[columns["SL"]]
        sl = None if sl_raw in (None, 0, 0.0) else self._cell_to_decimal(sl_raw)
        return Position(
            id=int(row[columns["Position"]]),
            symbol=str(row[columns["Symbol"]]),
            type=PositionType(row[columns["Type"]]),
            volume=self._cell_to_decimal(row[columns["Volume"]]),
            open_time=self._naive_dt_to_warsaw(row[columns["Open time"]]),
            open_price=self._cell_to_decimal(row[columns["Open price"]]),
            market_price=self._cell_to_decimal(row[columns["Market price"]]),
            purchase_value_pln=self._cell_to_decimal(row[columns["Purchase value"]]),
            gross_pl_pln=self._cell_to_decimal(row[columns["Gross P/L"]]),
            sl=sl,
        )

    @staticmethod
    def _find_labelled_row(
        sheet: Worksheet, *, required: set[str], max_scan_rows: int
    ) -> tuple[int, dict[str, int]]:
        for row_idx, row in enumerate(
            sheet.iter_rows(min_row=1, max_row=max_scan_rows, values_only=True), start=1
        ):
            present = {str(cell): idx for idx, cell in enumerate(row) if isinstance(cell, str)}
            if required.issubset(present):
                return row_idx, present
        raise PortfolioMalformedError(
            f"Could not find row containing labels {required} in first {max_scan_rows} rows."
        )

    @staticmethod
    def _cell_to_decimal(value: Any) -> Decimal:
        if value is None:
            raise PortfolioMalformedError("Expected number, got None")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _naive_dt_to_warsaw(value: Any) -> datetime:
        if not isinstance(value, datetime):
            raise PortfolioMalformedError(f"Expected datetime, got {type(value).__name__}")
        return value.replace(tzinfo=WARSAW) if value.tzinfo is None else value.astimezone(WARSAW)

    @staticmethod
    def _find_export_datetime(sheet: Worksheet) -> datetime:
        for row in sheet.iter_rows(min_row=1, max_row=6, values_only=True):
            for cell in row:
                if isinstance(cell, datetime):
                    return (
                        cell.replace(tzinfo=WARSAW)
                        if cell.tzinfo is None
                        else cell.astimezone(WARSAW)
                    )
        raise PortfolioMalformedError("Could not find export datetime in sheet header.")
