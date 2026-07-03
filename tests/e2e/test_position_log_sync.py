import shutil
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import ids.presentation.cli.position_log as position_log_cli
from ids.bootstrap import app
from ids.domain.timezones import WARSAW

pytestmark = pytest.mark.e2e

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_XLSX = _FIXTURES_DIR / "account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx"
CLI_USAGE_ERROR = 2
FIXED_NOW = datetime(2026, 5, 12, 18, 30, tzinfo=WARSAW)


def _arrange_sync_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.chdir(tmp_path)
    inputs_dir = tmp_path / "inputs" / "xtb_exports"
    inputs_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_XLSX, inputs_dir / FIXTURE_XLSX.name)
    monkeypatch.setattr(position_log_cli, "_clock", lambda: FIXED_NOW)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")
    return CliRunner()


def _position_log_dir(tmp_path: Path) -> Path:
    return tmp_path / "outputs" / "position_log"


def test_position_log_sync_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _arrange_sync_run(tmp_path, monkeypatch)

    result = runner.invoke(app, ["position-log", "sync"])

    assert result.exit_code == 0
    logs = tuple(_position_log_dir(tmp_path).glob("*.md"))
    assert len(logs) >= 1


def test_missing_account_id_fails_with_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IDS_IKZE_ACCOUNT_ID", raising=False)

    result = CliRunner().invoke(app, ["position-log", "sync"])

    assert result.exit_code == CLI_USAGE_ERROR
    assert "IDS_IKZE_ACCOUNT_ID" in result.stderr
    assert "--ikze-account-id" in result.stderr


def test_no_export_fails_with_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IDS_IKZE_ACCOUNT_ID", "99999999")

    result = CliRunner().invoke(app, ["position-log", "sync"])

    assert result.exit_code == 1
    assert "inputs/xtb_exports" in result.stderr


def test_sync_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _arrange_sync_run(tmp_path, monkeypatch)
    first = runner.invoke(app, ["position-log", "sync"])
    assert first.exit_code == 0

    first_bytes = {path: path.read_bytes() for path in _position_log_dir(tmp_path).glob("*.md")}

    second = runner.invoke(app, ["position-log", "sync"])
    assert second.exit_code == 0

    second_bytes = {path: path.read_bytes() for path in _position_log_dir(tmp_path).glob("*.md")}
    assert second_bytes == first_bytes
