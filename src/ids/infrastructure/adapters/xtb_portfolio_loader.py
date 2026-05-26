import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ids.application.ports.portfolio import (
    NoPortfolioAvailableError,
    PortfolioLoader,
    PortfolioMalformedError,
)
from ids.domain.enums import PositionType
from ids.domain.models import AccountSummary, PortfolioSnapshot, Position
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.xtb_filename import parse_xtb_account_id, parse_xtb_filename

log = logging.getLogger(__name__)

_OPEN_SHEET_PREFIX = "OPEN POSITION "

# Logical field → accepted label aliases. Normalized before matching (strip + casefold).
# All XTB adapter complexity stays here; domain models never see these strings.
_POSITION_COLUMN_SCHEMA: dict[str, frozenset[str]] = {
    "position_id": frozenset({"Position"}),
    "symbol": frozenset({"Symbol"}),
    "type": frozenset({"Type"}),
    "volume": frozenset({"Volume"}),
    "open_time": frozenset({"Open time"}),
    "open_price": frozenset({"Open price"}),
    "market_price": frozenset({"Market price"}),
    "purchase_value": frozenset({"Purchase value"}),
    "sl": frozenset({"SL"}),
    "gross_pl": frozenset({"Gross P/L", "Gross P&L"}),
}
_ACCOUNT_COLUMN_SCHEMA: dict[str, frozenset[str]] = {
    "balance": frozenset({"Balance"}),
    "equity": frozenset({"Equity"}),
}

# Bounded scan caps: high enough to survive XTB layout changes, low enough to
# fail fast on corrupted or unrelated workbooks. Not domain rules.
_EXPORT_DATETIME_SCAN_ROWS = 15
_ACCOUNT_HEADER_SCAN_ROWS = 15
_POSITION_HEADER_SCAN_ROWS = 25


def _normalize_label(label: str) -> str:
    """Strip, collapse internal whitespace, and casefold for alias matching."""
    return " ".join(label.split()).casefold()


class XTBPortfolioLoader(PortfolioLoader):
    def __init__(self, input_dir: Path, ikze_account_id: str) -> None:
        self._input_dir = input_dir
        self._account_id = ikze_account_id

    def load_latest(self) -> PortfolioSnapshot:
        latest_file, as_of_date = self._select_latest_export()
        return self._parse(latest_file, as_of_date)

    def load_from_path(self, path: Path) -> PortfolioSnapshot:
        as_of_date = self._as_of_date_for_path(path)
        return self._parse(path, as_of_date)

    def _select_latest_export(self) -> tuple[Path, date]:
        xlsx_files = self._list_xlsx_files()

        strict_match = self._latest_strict_filename_match(xlsx_files)
        if strict_match is not None:
            return strict_match

        fallback_candidates, excluded_other_accounts = self._eligible_fallback_candidates(
            xlsx_files
        )
        if not fallback_candidates:
            self._raise_no_available_export(xlsx_files, excluded_other_accounts)

        latest_file = max(fallback_candidates, key=lambda path: path.stat().st_mtime)
        as_of_date = self._as_of_date_from_export_datetime(latest_file)
        log.info(
            "No strict IKZE filename matches; selected latest XLSX by mtime: %s "
            "(as_of_date from workbook export datetime: %s)",
            latest_file.name,
            as_of_date.isoformat(),
        )
        return latest_file, as_of_date

    def _list_xlsx_files(self) -> list[Path]:
        if not self._input_dir.is_dir():
            raise NoPortfolioAvailableError(
                f"Directory `{self._input_dir}/` not found.\n"
                f"  Create it and place an XTB XLSX export there:\n"
                f"    mkdir -p {self._input_dir}/\n"
                f"    cp ~/Downloads/account_ikze_{self._account_id}_*.xlsx {self._input_dir}/"
            )
        return sorted(self._input_dir.glob("*.xlsx"))

    def _latest_strict_filename_match(self, xlsx_files: list[Path]) -> tuple[Path, date] | None:
        candidates = [
            (parse_xtb_filename(path.name, expected_account_id=self._account_id), path)
            for path in xlsx_files
        ]
        matching = [(as_of, path) for as_of, path in candidates if as_of is not None]
        if not matching:
            return None

        for as_of, path in candidates:
            if as_of is None:
                log.debug("Skipped %s (does not match IKZE pattern)", path.name)
        as_of_date, latest_file = max(matching, key=lambda item: item[0])
        return latest_file, as_of_date

    def _eligible_fallback_candidates(self, xlsx_files: list[Path]) -> tuple[list[Path], list[str]]:
        fallback_candidates: list[Path] = []
        excluded_other_accounts: list[str] = []
        for path in xlsx_files:
            declared_account_id = parse_xtb_account_id(path.name)
            if declared_account_id is not None and declared_account_id != self._account_id:
                excluded_other_accounts.append(path.name)
                continue
            fallback_candidates.append(path)
        return fallback_candidates, excluded_other_accounts

    def _raise_no_available_export(
        self, xlsx_files: list[Path], excluded_other_accounts: list[str]
    ) -> NoReturn:
        found = [path.name for path in xlsx_files]
        excluded = excluded_other_accounts if excluded_other_accounts else "(none)"
        raise NoPortfolioAvailableError(
            f"No IKZE export matching pattern in `{self._input_dir}/` "
            f"and no eligible fallback XLSX files.\n"
            f"  Expected pattern:\n"
            f"    account_ikze_{self._account_id}_pl_xlsx_<YYYY-MM-DD>_<YYYY-MM-DD>.xlsx\n"
            f"  Found: {found if found else '(empty)'}\n"
            f"  Excluded as other account IDs: {excluded}"
        )

    def _as_of_date_for_path(self, path: Path) -> date:
        as_of = parse_xtb_filename(path.name, expected_account_id=self._account_id)
        if as_of is not None:
            return as_of

        declared_account_id = parse_xtb_account_id(path.name)
        if declared_account_id is not None and declared_account_id != self._account_id:
            raise PortfolioMalformedError(
                f"File `{path.name}` clearly belongs to IKZE account `{declared_account_id}`, "
                f"expected `{self._account_id}`."
            )
        as_of_from_workbook = self._as_of_date_from_export_datetime(path)
        log.info(
            "File %s does not match strict IKZE filename pattern; "
            "using workbook export datetime for as_of_date: %s",
            path.name,
            as_of_from_workbook.isoformat(),
        )
        return as_of_from_workbook

    def _parse(self, path: Path, as_of_date: date) -> PortfolioSnapshot:
        try:
            sheet = self._load_open_position_sheet(path)
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

    def _load_open_position_sheet(self, path: Path) -> Worksheet:
        workbook = load_workbook(path, data_only=True, read_only=True)
        return self._find_open_position_sheet(workbook)

    def _find_open_position_sheet(self, workbook: Workbook) -> Worksheet:
        prefix_matches = [n for n in workbook.sheetnames if n.startswith(_OPEN_SHEET_PREFIX)]
        if prefix_matches:
            return workbook[prefix_matches[0]]

        semantic_matches = [
            n for n in workbook.sheetnames if _sheet_has_position_table(workbook[n])
        ]
        if len(semantic_matches) == 1:
            log.info(
                "No sheet matching prefix %r; using semantic fallback: %r",
                _OPEN_SHEET_PREFIX,
                semantic_matches[0],
            )
            return workbook[semantic_matches[0]]
        if len(semantic_matches) > 1:
            raise PortfolioMalformedError(
                f"Multiple sheets contain the open-position table columns; cannot choose "
                f"automatically. Ambiguous sheets: {semantic_matches}. "
                f"All sheets: {workbook.sheetnames}"
            )
        required_fields = sorted(_POSITION_COLUMN_SCHEMA.keys())
        raise PortfolioMalformedError(
            f"No sheet starting with `{_OPEN_SHEET_PREFIX}` found and no sheet contains "
            f"the required open-position fields {required_fields}. "
            f"Sheets: {workbook.sheetnames}"
        )

    def _parse_account_summary(self, sheet: Worksheet) -> AccountSummary:
        label_row_idx, label_columns = _find_labelled_row(
            sheet, schema=_ACCOUNT_COLUMN_SCHEMA, max_scan_rows=_ACCOUNT_HEADER_SCAN_ROWS
        )
        value_row = next(
            sheet.iter_rows(
                min_row=label_row_idx + 1,
                max_row=label_row_idx + 1,
                values_only=True,
            )
        )
        balance = _cell_to_decimal(value_row[label_columns["balance"]])
        equity = _cell_to_decimal(value_row[label_columns["equity"]])
        export_dt = _find_export_datetime(sheet)
        return AccountSummary(balance_pln=balance, equity_pln=equity, export_datetime=export_dt)

    def _parse_positions(self, sheet: Worksheet) -> list[Position]:
        header_row_idx, columns = _find_labelled_row(
            sheet, schema=_POSITION_COLUMN_SCHEMA, max_scan_rows=_POSITION_HEADER_SCAN_ROWS
        )

        # Footer detection: any non-numeric value in the position_id cell ends the table.
        # This covers "Total", "TOTAL", localized variants, and future XTB footer changes
        # without requiring a hardcoded alias list. Empty cells (None) are spacer rows.
        # Numeric rows that have bad values in other fields still raise PortfolioMalformedError.
        positions: list[Position] = []
        for row_idx, row in enumerate(
            sheet.iter_rows(min_row=header_row_idx + 1, values_only=True),
            start=header_row_idx + 1,
        ):
            first = row[columns["position_id"]] if columns["position_id"] < len(row) else None
            if first is None:
                continue
            if not isinstance(first, int | float):
                break
            positions.append(self._row_to_position(row, columns, row_idx))
        return positions

    def _row_to_position(
        self, row: tuple[Any, ...], columns: dict[str, int], row_idx: int
    ) -> Position:
        position_id_raw = self._row_cell(row, columns, row_idx, "position_id")
        symbol_raw = self._row_cell(row, columns, row_idx, "symbol")
        type_raw = self._row_cell(row, columns, row_idx, "type")
        volume_raw = self._row_cell(row, columns, row_idx, "volume")
        open_time_raw = self._row_cell(row, columns, row_idx, "open_time")
        open_price_raw = self._row_cell(row, columns, row_idx, "open_price")
        market_price_raw = self._row_cell(row, columns, row_idx, "market_price")
        purchase_value_raw = self._row_cell(row, columns, row_idx, "purchase_value")
        gross_pl_raw = self._row_cell(row, columns, row_idx, "gross_pl")
        sl_raw = self._row_cell(row, columns, row_idx, "sl")

        try:
            position_type = PositionType(type_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "type", type_raw, exc) from exc
        try:
            volume = _cell_to_decimal(volume_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "volume", volume_raw, exc) from exc
        try:
            open_time = _naive_dt_to_warsaw(open_time_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "open_time", open_time_raw, exc) from exc
        try:
            open_price = _cell_to_decimal(open_price_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "open_price", open_price_raw, exc) from exc
        try:
            market_price = _cell_to_decimal(market_price_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "market_price", market_price_raw, exc) from exc
        try:
            purchase_value = _cell_to_decimal(purchase_value_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "purchase_value", purchase_value_raw, exc) from exc
        try:
            gross_pl = _cell_to_decimal(gross_pl_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "gross_pl", gross_pl_raw, exc) from exc

        try:
            sl = _normalize_stop_loss(sl_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "sl", sl_raw, exc) from exc

        try:
            position_id = int(position_id_raw)
        except Exception as exc:
            raise _position_row_error(row_idx, "position_id", position_id_raw, exc) from exc

        return Position(
            id=position_id,
            symbol=str(symbol_raw),
            type=position_type,
            volume=volume,
            open_time=open_time,
            open_price=open_price,
            market_price=market_price,
            purchase_value_pln=purchase_value,
            gross_pl_pln=gross_pl,
            sl=sl,
        )

    def _row_cell(
        self, row: tuple[Any, ...], columns: dict[str, int], row_idx: int, logical_field: str
    ) -> Any:
        col_idx = columns[logical_field]
        if col_idx >= len(row):
            raise PortfolioMalformedError(
                f"Malformed open-position row {row_idx}: missing field `{logical_field}` "
                f"at expected column index {col_idx}."
            )
        return row[col_idx]

    def _as_of_date_from_export_datetime(self, path: Path) -> date:
        message_prefix = (
            f"Could not derive as_of_date for `{path.name}` from workbook export datetime"
        )
        try:
            sheet = self._load_open_position_sheet(path)
            return _find_export_datetime(sheet).date()
        except PortfolioMalformedError as exc:
            raise PortfolioMalformedError(f"{message_prefix}: {exc}") from exc
        except Exception as exc:
            raise PortfolioMalformedError(f"{message_prefix}: {exc}") from exc


def _sheet_has_position_table(
    sheet: Worksheet, max_scan_rows: int = _POSITION_HEADER_SCAN_ROWS
) -> bool:
    required_count = len(_POSITION_COLUMN_SCHEMA)
    for row in sheet.iter_rows(min_row=1, max_row=max_scan_rows, values_only=True):
        present = {_normalize_label(str(cell)) for cell in row if isinstance(cell, str)}
        # Count distinct logical fields covered (each field matches if any alias is present)
        covered = sum(
            1
            for aliases in _POSITION_COLUMN_SCHEMA.values()
            if any(_normalize_label(a) in present for a in aliases)
        )
        if covered == required_count:
            return True
    return False


def _find_labelled_row(
    sheet: Worksheet,
    *,
    schema: dict[str, frozenset[str]],
    max_scan_rows: int,
) -> tuple[int, dict[str, int]]:
    normalized_schema = {
        logical: {_normalize_label(a) for a in aliases} for logical, aliases in schema.items()
    }
    for row_idx, row in enumerate(
        sheet.iter_rows(min_row=1, max_row=max_scan_rows, values_only=True), start=1
    ):
        norm_row = {
            _normalize_label(str(cell)): idx
            for idx, cell in enumerate(row)
            if isinstance(cell, str)
        }
        columns: dict[str, int] = {}
        for logical, norm_aliases in normalized_schema.items():
            for alias in norm_aliases:
                if alias in norm_row:
                    columns[logical] = norm_row[alias]
                    break
        if len(columns) == len(schema):
            return row_idx, columns
    required_desc = [
        f"{logical} (accepts: {', '.join(sorted(aliases))})" for logical, aliases in schema.items()
    ]
    raise PortfolioMalformedError(
        f"Could not find row with all required columns in first {max_scan_rows} rows. "
        f"Required: {'; '.join(required_desc)}"
    )


def _cell_to_decimal(value: Any) -> Decimal:
    if value is None:
        raise PortfolioMalformedError("Expected number, got None")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _naive_dt_to_warsaw(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise PortfolioMalformedError(f"Expected datetime, got {type(value).__name__}")
    return value.replace(tzinfo=WARSAW) if value.tzinfo is None else value.astimezone(WARSAW)


def _find_export_datetime(sheet: Worksheet) -> datetime:
    for row in sheet.iter_rows(min_row=1, max_row=_EXPORT_DATETIME_SCAN_ROWS, values_only=True):
        for cell in row:
            if isinstance(cell, datetime):
                return (
                    cell.replace(tzinfo=WARSAW) if cell.tzinfo is None else cell.astimezone(WARSAW)
                )
    raise PortfolioMalformedError(
        f"Could not find export datetime in first {_EXPORT_DATETIME_SCAN_ROWS} rows."
    )


def _position_row_error(
    row_idx: int, field_name: str, value: Any, exc: Exception
) -> PortfolioMalformedError:
    return PortfolioMalformedError(
        f"Malformed open-position row {row_idx}, field `{field_name}` "
        f"(value={value!r}, type={type(value).__name__}): {exc}"
    )


def _normalize_stop_loss(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        value = stripped
    decimal_value = _cell_to_decimal(value)
    return None if decimal_value == 0 else decimal_value
