"""Opt-in acceptance checks that run position-log sync on REAL XTB exports.

Real exports carry private portfolio data and live in the gitignored
``inputs/xtb_exports/``; they never enter git or CI. This suite discovers any
that happen to be present locally and exercises the full CLI against them in an
isolated temp workspace (the real ``outputs/`` is never touched). When no export
is present — a clean checkout or CI — every test skips.

Assertions are portable INVARIANTS, not golden bytes: real portfolios change
over time, so we verify structural guarantees that must hold for any export.
"""

import shutil
from datetime import datetime
from pathlib import Path

import frontmatter  # pyright: ignore[reportMissingTypeStubs]
import pytest
from typer.testing import CliRunner

import ids.presentation.cli.position_log as position_log_cli
from ids.bootstrap import app
from ids.domain.timezones import WARSAW
from ids.infrastructure.adapters.xtb_filename import parse_xtb_account_id
from ids.infrastructure.adapters.xtb_portfolio_loader import XTBPortfolioLoader

_REAL_EXPORTS_DIR = Path("inputs/xtb_exports")
FIXED_NOW = datetime(2026, 7, 6, 12, 0, tzinfo=WARSAW)


def _discover_real_exports() -> list[tuple[Path, str]]:
    if not _REAL_EXPORTS_DIR.is_dir():
        return []
    found: list[tuple[Path, str]] = []
    for path in sorted(_REAL_EXPORTS_DIR.glob("account_ikze_*.xlsx")):
        account_id = parse_xtb_account_id(path.name)
        if account_id is not None:
            found.append((path.resolve(), account_id))
    return found


_REAL_EXPORTS = _discover_real_exports()

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not _REAL_EXPORTS,
        reason="no real XTB export in inputs/xtb_exports/ (expected on clean checkout / CI)",
    ),
]

_EXPORT_PARAMS = [
    pytest.param(path, account_id, id=path.name) for path, account_id in _REAL_EXPORTS
]


def _log_dir(tmp_path: Path) -> Path:
    return tmp_path / "outputs" / "position_log"


def _run_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    export_path: Path,
    account_id: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    inputs = tmp_path / "inputs" / "xtb_exports"
    inputs.mkdir(parents=True, exist_ok=True)
    shutil.copy(export_path, inputs / export_path.name)
    monkeypatch.setattr(position_log_cli, "_clock", lambda: FIXED_NOW)
    result = CliRunner().invoke(app, ["position-log", "sync", "--ikze-account-id", account_id])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(("export_path", "account_id"), _EXPORT_PARAMS)
def test_one_log_per_position_with_complete_frontmatter(
    export_path: Path, account_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run_sync(tmp_path, monkeypatch, export_path, account_id)

    snapshot = XTBPortfolioLoader(
        input_dir=tmp_path / "inputs" / "xtb_exports", ikze_account_id=account_id
    ).load_latest()
    logs = sorted(_log_dir(tmp_path).glob("*.md"))

    # No partial-fill collapse: exactly one log per logical position (loader
    # aggregates fills by id). A regression here means positions overwrote each other.
    assert len(logs) == len(snapshot.positions) + len(snapshot.closed_positions)

    for path in logs:
        metadata = frontmatter.load(str(path)).metadata
        for key in ("id", "status", "symbol", "open_date", "open_price"):
            assert key in metadata, f"{path.name} missing {key}"
        if metadata["status"] == "closed":
            for key in ("close_date", "close_price", "gross_pl"):
                assert key in metadata, f"{path.name} (closed) missing {key}"


@pytest.mark.parametrize(("export_path", "account_id"), _EXPORT_PARAMS)
def test_resync_is_byte_identical(
    export_path: Path, account_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run_sync(tmp_path, monkeypatch, export_path, account_id)
    first = {path: path.read_bytes() for path in _log_dir(tmp_path).glob("*.md")}

    _run_sync(tmp_path, monkeypatch, export_path, account_id)
    second = {path: path.read_bytes() for path in _log_dir(tmp_path).glob("*.md")}

    assert second == first


@pytest.mark.parametrize(("export_path", "account_id"), _EXPORT_PARAMS)
def test_user_prose_survives_resync(
    export_path: Path, account_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run_sync(tmp_path, monkeypatch, export_path, account_id)

    target = sorted(_log_dir(tmp_path).glob("*.md"))[0]
    marker = "Bought for the dividend; thesis holds while ROE stays above peers."
    post = frontmatter.load(str(target))
    post.content = post.content.replace("## Open rationale\n", f"## Open rationale\n{marker}\n", 1)
    target.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")

    _run_sync(tmp_path, monkeypatch, export_path, account_id)

    assert marker in target.read_text(encoding="utf-8")
