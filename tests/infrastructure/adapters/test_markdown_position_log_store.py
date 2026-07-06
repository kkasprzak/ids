from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import frontmatter  # pyright: ignore[reportMissingTypeStubs]
import pytest

from ids.application.ports import PositionLogEntry, PositionLogStoreError, UpsertResult
from ids.domain.enums import AlertKind, PositionLogStatus
from ids.domain.position_log_context import ContextAtClose, ContextAtOpen
from ids.domain.value_objects import Price, Symbol
from ids.infrastructure.adapters.markdown_position_log_store import MarkdownPositionLogStore

pytestmark = pytest.mark.integration
EXPECTED_CREATED_COUNT = 2


def _store(tmp_path: Path) -> MarkdownPositionLogStore:
    return MarkdownPositionLogStore(root=tmp_path / "outputs" / "position_logs")


def _path(tmp_path: Path, open_date: date = date(2026, 1, 1), symbol: str = "AAA.PL") -> Path:
    return tmp_path / "outputs" / "position_logs" / f"{open_date.isoformat()}_{symbol}.md"


def _entry(  # noqa: PLR0913
    *,
    id: int = 1,
    open_date: date = date(2026, 1, 1),
    symbol: str = "AAA.PL",
    status: PositionLogStatus = PositionLogStatus.OPEN,
    open_price: Decimal = Decimal("100"),
    close_date: date | None = None,
    close_price: Decimal | None = None,
    gross_pl_pln: Decimal | None = None,
    context_at_open: ContextAtOpen | None = None,
    context_at_close: ContextAtClose | None = None,
) -> PositionLogEntry:
    return PositionLogEntry(
        id=id,
        open_date=open_date,
        symbol=Symbol(symbol),
        status=status,
        open_price=Price(open_price),
        close_date=close_date,
        close_price=Price(close_price) if close_price is not None else None,
        gross_pl_pln=gross_pl_pln,
        context_at_open=context_at_open,
        context_at_close=context_at_close,
    )


def _upsert(tmp_path: Path, entries: Iterable[PositionLogEntry]) -> UpsertResult:
    return _store(tmp_path).upsert_metadata(entries)


def test_new_open_position_creates_file_with_frontmatter_and_scaffolding(tmp_path: Path) -> None:
    entry = _entry()

    result = _upsert(tmp_path, (entry,))

    path = _path(tmp_path)
    post = frontmatter.load(str(path))
    assert result == UpsertResult(created_count=1, refreshed_count=0, status_transitioned_count=0)
    assert path.is_file()
    assert post.metadata["status"] == "open"
    assert post.metadata["symbol"] == "AAA.PL"
    assert post.metadata["open_date"] == date(2026, 1, 1)
    assert "## Open rationale" in post.content
    assert "## Close rationale" in post.content
    assert "## Review history" in post.content


def test_new_closed_position_writes_closed_frontmatter(tmp_path: Path) -> None:
    entry = _entry(
        status=PositionLogStatus.CLOSED,
        close_date=date(2026, 1, 10),
        close_price=Decimal("110"),
        gross_pl_pln=Decimal("100"),
    )

    _upsert(tmp_path, (entry,))

    metadata = frontmatter.load(str(_path(tmp_path))).metadata
    assert metadata["status"] == "closed"
    assert metadata["close_date"] == date(2026, 1, 10)
    assert metadata["close_price"] == "110"
    assert metadata["gross_pl"] == "100"


def test_existing_user_prose_remains_present_when_metadata_is_refreshed(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    user_prose = "I opened this because revenue growth accelerated."
    path.write_text(
        "---\nstatus: open\nsymbol: AAA.PL\n---\n\n"
        f"## Open rationale\n{user_prose}\n\n## Review history\n- first note\n",
        encoding="utf-8",
    )
    entry = _entry(status=PositionLogStatus.OPEN)

    _upsert(tmp_path, (entry,))

    content = frontmatter.load(str(path)).content
    assert user_prose in content
    assert "- first note" in content


def test_status_transition_from_open_to_closed_is_counted(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\nstatus: open\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8"
    )
    entry = _entry(status=PositionLogStatus.CLOSED)

    result = _upsert(tmp_path, (entry,))

    assert result == UpsertResult(created_count=0, refreshed_count=1, status_transitioned_count=1)
    assert frontmatter.load(str(path)).metadata["status"] == "closed"


def test_refresh_with_same_status_is_not_counted_as_transition(tmp_path: Path) -> None:
    _upsert(tmp_path, (_entry(),))

    result = _upsert(tmp_path, (_entry(status=PositionLogStatus.OPEN),))

    assert result == UpsertResult(created_count=0, refreshed_count=1, status_transitioned_count=0)


def test_refresh_without_previous_status_is_not_counted_as_transition(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\nsymbol: AAA.PL\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8"
    )

    result = _upsert(tmp_path, (_entry(status=PositionLogStatus.OPEN),))

    assert result == UpsertResult(created_count=0, refreshed_count=1, status_transitioned_count=0)


def test_multiple_positions_same_symbol_different_dates_create_multiple_files(
    tmp_path: Path,
) -> None:
    entries = (
        _entry(open_date=date(2026, 1, 1), symbol="AAA.PL"),
        _entry(open_date=date(2026, 1, 2), symbol="AAA.PL"),
    )

    result = _upsert(tmp_path, entries)

    assert result.created_count == EXPECTED_CREATED_COUNT
    assert _path(tmp_path, date(2026, 1, 1), "AAA.PL").is_file()
    assert _path(tmp_path, date(2026, 1, 2), "AAA.PL").is_file()


def test_frontmatter_records_xtb_position_id(tmp_path: Path) -> None:
    position_id = 2498119260
    _upsert(tmp_path, (_entry(id=position_id),))

    post = frontmatter.load(str(_path(tmp_path)))
    assert post.metadata["id"] == position_id


def test_cross_id_collision_on_same_open_date_and_symbol_keeps_both_logs(tmp_path: Path) -> None:
    # Two distinct positions bought the same day on the same symbol must not
    # overwrite each other; the later one is disambiguated by position id.
    entries = (
        _entry(id=111, open_date=date(2026, 1, 1), symbol="AAA.PL"),
        _entry(id=222, open_date=date(2026, 1, 1), symbol="AAA.PL"),
    )

    result = _upsert(tmp_path, entries)

    root = tmp_path / "outputs" / "position_logs"
    assert result.created_count == EXPECTED_CREATED_COUNT
    assert (root / "2026-01-01_AAA.PL.md").is_file()
    assert (root / "2026-01-01_AAA.PL_222.md").is_file()


def test_frontmatter_key_order_is_deterministic(tmp_path: Path) -> None:
    entry = _entry(open_price=Decimal("100"))

    _upsert(tmp_path, (entry,))

    rendered = _path(tmp_path).read_text(encoding="utf-8")
    assert rendered.startswith(
        "---\nid: 1\nstatus: open\nsymbol: AAA.PL\nopen_date: 2026-01-01\nopen_price: '100'\n"
    )


def test_missing_sections_are_appended_without_duplicating_existing_sections(
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\nstatus: open\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8"
    )

    _upsert(tmp_path, (_entry(),))

    content = frontmatter.load(str(path)).content
    assert content.count("## Open rationale") == 1
    assert content.count("## Close rationale") == 1
    assert content.count("## Review history") == 1


def test_wraps_filesystem_write_errors_in_position_log_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    original_write_text = Path.write_text

    def fail_write_text(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if self.name == "2026-01-01_AAA.PL.md":
            raise PermissionError("blocked")
        return original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(PositionLogStoreError, match="Failed to upsert position logs"):
        store.upsert_metadata((_entry(),))


def _context_at_open(*, equity: str) -> ContextAtOpen:
    return ContextAtOpen(
        portfolio_equity_pln=Decimal(equity),
        cash_reserve_pct=Decimal("25"),
        open_positions_count=3,
        this_position_pct_of_portfolio=Decimal("12.5"),
        strategy_rules_satisfied=(AlertKind.MISSING_STOP_LOSS, AlertKind.STOP_LOSS_BREACH),
        strategy_rules_violated=(AlertKind.CASH_RESERVE_BELOW_MINIMUM,),
    )


def _context_block(rendered: str) -> str:
    start = rendered.index("context_at_open:")
    end = rendered.index("\n---", start)
    return rendered[start:end]


def test_enum_rule_ids_serialize_as_plain_strings(tmp_path: Path) -> None:
    entry = _entry(context_at_open=_context_at_open(equity="2000"))

    _upsert(tmp_path, (entry,))

    rendered = _path(tmp_path).read_text(encoding="utf-8")
    assert "!!python" not in rendered
    metadata = frontmatter.load(str(_path(tmp_path))).metadata
    context = cast("dict[str, object]", metadata["context_at_open"])
    assert context["strategy_rules_satisfied"] == ["MISSING_STOP_LOSS", "STOP_LOSS_BREACH"]
    assert context["strategy_rules_violated"] == ["CASH_RESERVE_BELOW_MINIMUM"]


def test_context_at_open_is_immutable_across_refresh_with_different_state(tmp_path: Path) -> None:
    original = _entry(context_at_open=_context_at_open(equity="2000"))
    _upsert(tmp_path, (original,))
    original_block = _context_block(_path(tmp_path).read_text(encoding="utf-8"))

    refreshed = _entry(context_at_open=_context_at_open(equity="9999"))
    _upsert(tmp_path, (refreshed,))

    rendered = _path(tmp_path).read_text(encoding="utf-8")
    assert _context_block(rendered) == original_block
    assert "9999" not in rendered


def test_context_at_close_is_written_once_when_absent_then_frozen(tmp_path: Path) -> None:
    _upsert(tmp_path, (_entry(),))

    first_close = ContextAtClose(
        hold_duration_days=9,
        pnl_pct=Decimal("10"),
        strategy_rules_satisfied=(),
        strategy_rules_violated=(),
    )
    _upsert(
        tmp_path,
        (_entry(status=PositionLogStatus.CLOSED, context_at_close=first_close),),
    )
    after_first = frontmatter.load(str(_path(tmp_path))).metadata["context_at_close"]

    second_close = ContextAtClose(
        hold_duration_days=99,
        pnl_pct=Decimal("-50"),
        strategy_rules_satisfied=(),
        strategy_rules_violated=(),
    )
    _upsert(
        tmp_path,
        (_entry(status=PositionLogStatus.CLOSED, context_at_close=second_close),),
    )
    after_second = frontmatter.load(str(_path(tmp_path))).metadata["context_at_close"]

    assert after_first == {
        "hold_duration_days": 9,
        "pnl_pct": "10",
        "strategy_rules_satisfied": [],
        "strategy_rules_violated": [],
    }
    assert after_second == after_first


def test_wraps_malformed_frontmatter_in_position_log_store_error(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("---\nstatus: [\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8")

    with pytest.raises(PositionLogStoreError, match="Malformed position log payload"):
        _upsert(tmp_path, (_entry(),))
