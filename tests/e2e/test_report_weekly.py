import shutil
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook
from typer.testing import CliRunner

import ids.presentation.cli.report as report_cli
from ids.domain.timezones import WARSAW
from ids.presentation.cli import app

pytestmark = pytest.mark.e2e

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_XLSX = _FIXTURES_DIR / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx"
FIXTURE_XLSX_ALERTS = _FIXTURES_DIR / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-09.xlsx"
EXPECTED_WEEKLY = _FIXTURES_DIR / "expected" / "weekly_2026-05-02.md"
EXPECTED_WEEKLY_ALERTS = _FIXTURES_DIR / "expected" / "weekly_2026-05-09.md"
CLI_USAGE_ERROR = 2
FIXED_NOW = datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW)


def _arrange_weekly_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.chdir(tmp_path)
    inputs_dir = tmp_path / "inputs" / "xtb_exports"
    inputs_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_XLSX, inputs_dir / FIXTURE_XLSX.name)
    monkeypatch.setattr(report_cli, "_clock", lambda: FIXED_NOW)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")
    return CliRunner()


def _weekly_report_path(tmp_path: Path) -> Path:
    return tmp_path / "outputs" / "reports" / "weekly" / "2026-05-02_weekly.md"


def _snapshot_path(tmp_path: Path) -> Path:
    return tmp_path / "outputs" / "snapshots" / "2026-05-02.jsonl"


def _assert_weekly_outputs_exist(tmp_path: Path) -> None:
    missing_paths = tuple(
        path
        for path in (_weekly_report_path(tmp_path), _snapshot_path(tmp_path))
        if not path.exists()
    )
    assert missing_paths == ()


def test_weekly_report_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _arrange_weekly_run(tmp_path, monkeypatch)

    result = runner.invoke(app, ["report", "weekly"])

    _assert_weekly_outputs_exist(tmp_path)
    assert result.exit_code == 0
    assert _weekly_report_path(tmp_path).read_text(encoding="utf-8") == EXPECTED_WEEKLY.read_text(
        encoding="utf-8"
    )


def test_weekly_report_renders_compliance_alerts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Action-required alerts present → report still exits 0; golden captures alert section."""
    monkeypatch.chdir(tmp_path)
    inputs_dir = tmp_path / "inputs" / "xtb_exports"
    inputs_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_XLSX_ALERTS, inputs_dir / FIXTURE_XLSX_ALERTS.name)
    monkeypatch.setattr(report_cli, "_clock", lambda: FIXED_NOW)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")

    result = CliRunner().invoke(app, ["report", "weekly"])

    expected_report = tmp_path / "outputs" / "reports" / "weekly" / "2026-05-09_weekly.md"
    expected_snapshot = tmp_path / "outputs" / "snapshots" / "2026-05-09.jsonl"
    assert expected_report.exists()
    assert expected_snapshot.exists()
    assert result.exit_code == 0
    assert expected_report.read_text(encoding="utf-8") == EXPECTED_WEEKLY_ALERTS.read_text(
        encoding="utf-8"
    )


def test_no_export_fails_with_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")

    result = CliRunner().invoke(app, ["report", "weekly"])

    assert result.exit_code == 1
    assert "inputs/xtb_exports" in result.stderr


def test_missing_account_id_fails_with_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IDS_IKZE_ACCOUNT_ID", raising=False)

    result = CliRunner().invoke(app, ["report", "weekly"])

    assert result.exit_code == CLI_USAGE_ERROR
    assert "IDS_IKZE_ACCOUNT_ID" in result.stderr
    assert "--ikze-account-id" in result.stderr


def test_invalid_export_file_fails_with_as_of_derivation_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")
    export_path = tmp_path / "custom.xlsx"
    export_path.touch()

    result = CliRunner().invoke(app, ["report", "weekly", "--export", str(export_path)])

    assert result.exit_code == 1
    assert "Could not derive as_of_date" in result.stderr


def test_malformed_export_fails_with_loader_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")
    export_path = tmp_path / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx"
    workbook = Workbook()
    assert workbook.active is not None
    workbook.active.title = "CLOSED POSITION HISTORY"
    workbook.save(export_path)

    result = CliRunner().invoke(app, ["report", "weekly", "--export", str(export_path)])

    assert result.exit_code == 1
    assert "OPEN POSITION" in result.stderr


def test_idempotency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _arrange_weekly_run(tmp_path, monkeypatch)
    first = runner.invoke(app, ["report", "weekly"])
    assert first.exit_code == 0

    first_report_bytes = _weekly_report_path(tmp_path).read_bytes()
    first_snapshot_bytes = _snapshot_path(tmp_path).read_bytes()

    second = runner.invoke(app, ["report", "weekly"])
    assert second.exit_code == 0
    assert _weekly_report_path(tmp_path).read_bytes() == first_report_bytes
    assert _snapshot_path(tmp_path).read_bytes() == first_snapshot_bytes


def test_weekly_report_export_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    export_path = tmp_path / FIXTURE_XLSX.name
    shutil.copy(FIXTURE_XLSX, export_path)

    monkeypatch.setattr(report_cli, "_clock", lambda: FIXED_NOW)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")

    result = CliRunner().invoke(app, ["report", "weekly", "--export", str(export_path)])

    assert result.exit_code == 0
    _assert_weekly_outputs_exist(tmp_path)


def test_weekly_report_export_override_accepts_custom_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    export_path = tmp_path / "custom.xlsx"
    shutil.copy(FIXTURE_XLSX, export_path)
    monkeypatch.setattr(report_cli, "_clock", lambda: FIXED_NOW)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")

    result = CliRunner().invoke(app, ["report", "weekly", "--export", str(export_path)])

    assert result.exit_code == 0
    _assert_weekly_outputs_exist(tmp_path)
