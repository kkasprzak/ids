import re
from datetime import date

_PATTERN = re.compile(
    r"^account_ikze_(?P<account_id>\d+)_pl_xlsx_"
    r"(?P<from_date>\d{4}-\d{2}-\d{2})_"
    r"(?P<as_of_date>\d{4}-\d{2}-\d{2})\.xlsx$"
)
_ACCOUNT_PATTERN = re.compile(r"^account_ikze_(?P<account_id>\d+)_pl_xlsx_.*\.xlsx$")


def parse_xtb_filename(name: str, *, expected_account_id: str) -> date | None:
    """Return XTB export as_of_date or None when filename is out of scope."""
    match = _PATTERN.match(name)
    if match is None:
        return None
    if match["account_id"] != expected_account_id:
        return None
    try:
        return date.fromisoformat(match["as_of_date"])
    except ValueError:
        return None


def parse_xtb_account_id(name: str) -> str | None:
    """Return account id when filename clearly declares IKZE account provenance."""
    match = _ACCOUNT_PATTERN.match(name)
    if match is None:
        return None
    return match["account_id"]
