from datetime import date

import pytest

from ids.adapters.xtb_filename import parse_xtb_account_id, parse_xtb_filename

pytestmark = pytest.mark.integration


def test_parse_xtb_filename_success() -> None:
    result = parse_xtb_filename(
        "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx",
        expected_account_id="99999999",
    )
    assert result == date(2026, 5, 2)


def test_parse_xtb_filename_wrong_account_returns_none() -> None:
    result = parse_xtb_filename(
        "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx",
        expected_account_id="88888888",
    )
    assert result is None


@pytest.mark.parametrize(
    "filename",
    [
        "account_88888888_pl_xlsx_2024-12-31_2026-05-02.xlsx",
        "foo.xlsx",
        "account_ikze_99999999_pl_csv_2024-12-31_2026-05-02.xlsx",
    ],
)
def test_parse_xtb_filename_wrong_patterns_return_none(filename: str) -> None:
    assert parse_xtb_filename(filename, expected_account_id="99999999") is None


def test_parse_xtb_filename_invalid_date_returns_none() -> None:
    result = parse_xtb_filename(
        "account_ikze_99999999_pl_xlsx_2024-12-31_2026-13-02.xlsx",
        expected_account_id="99999999",
    )
    assert result is None


def test_parse_xtb_account_id_success() -> None:
    result = parse_xtb_account_id("account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx")
    assert result == "99999999"


@pytest.mark.parametrize("filename", ["custom.xlsx", "account_ikze_x_pl_xlsx_foo.xlsx"])
def test_parse_xtb_account_id_non_matching_returns_none(filename: str) -> None:
    assert parse_xtb_account_id(filename) is None
