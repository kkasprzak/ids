from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path

import frontmatter  # pyright: ignore[reportMissingTypeStubs]
import pytest

from ids.application.ports import PositionLogEntry, PositionLogStoreError, UpsertResult
from ids.infrastructure.adapters.markdown_position_log_store import MarkdownPositionLogStore

pytestmark = pytest.mark.integration
EXPECTED_CREATED_COUNT = 2


def _store(tmp_path: Path) -> MarkdownPositionLogStore:
    return MarkdownPositionLogStore(root=tmp_path / "outputs" / "position_logs")


def _path(tmp_path: Path, open_date: date = date(2026, 1, 1), symbol: str = "AAA.PL") -> Path:
    return tmp_path / "outputs" / "position_logs" / f"{open_date.isoformat()}_{symbol}.md"


def _entry(
    *,
    open_date: date = date(2026, 1, 1),
    symbol: str = "AAA.PL",
    frontmatter: dict[str, object] | None = None,
) -> PositionLogEntry:
    return PositionLogEntry(
        open_date=open_date,
        symbol=symbol,
        frontmatter=frontmatter
        or {
            "status": "open",
            "symbol": symbol,
            "open_date": open_date,
            "open_price": Decimal("100"),
        },
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
        frontmatter={
            "status": "closed",
            "symbol": "AAA.PL",
            "open_date": date(2026, 1, 1),
            "close_date": date(2026, 1, 10),
            "close_price": Decimal("110"),
            "gross_pl": Decimal("100"),
        },
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
    entry = _entry(
        frontmatter={"status": "open", "symbol": "AAA.PL", "open_date": date(2026, 1, 1)}
    )

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
    entry = _entry(
        frontmatter={"status": "closed", "symbol": "AAA.PL", "open_date": date(2026, 1, 1)}
    )

    result = _upsert(tmp_path, (entry,))

    assert result == UpsertResult(created_count=0, refreshed_count=1, status_transitioned_count=1)
    assert frontmatter.load(str(path)).metadata["status"] == "closed"


def test_refresh_with_same_status_is_not_counted_as_transition(tmp_path: Path) -> None:
    _upsert(tmp_path, (_entry(),))

    result = _upsert(tmp_path, (_entry(frontmatter={"status": "open", "symbol": "AAA.PL"}),))

    assert result == UpsertResult(created_count=0, refreshed_count=1, status_transitioned_count=0)


def test_refresh_without_previous_status_is_not_counted_as_transition(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\nsymbol: AAA.PL\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8"
    )

    result = _upsert(tmp_path, (_entry(frontmatter={"status": "open", "symbol": "AAA.PL"}),))

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


def test_frontmatter_key_order_is_deterministic(tmp_path: Path) -> None:
    entry = _entry(
        frontmatter={
            "status": "open",
            "symbol": "AAA.PL",
            "open_date": date(2026, 1, 1),
            "open_price": Decimal("100"),
        },
    )

    _upsert(tmp_path, (entry,))

    rendered = _path(tmp_path).read_text(encoding="utf-8")
    assert rendered.startswith(
        "---\nstatus: open\nsymbol: AAA.PL\nopen_date: 2026-01-01\nopen_price: '100'\n"
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

    def fail_write_text(self: Path, *args: object, **kwargs: object) -> int:
        if self.name == "2026-01-01_AAA.PL.md":
            raise PermissionError("blocked")
        return original_write_text(self, *args, **kwargs)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(PositionLogStoreError, match="Failed to upsert position logs"):
        store.upsert_metadata((_entry(),))


def test_wraps_malformed_frontmatter_in_position_log_store_error(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("---\nstatus: [\n---\n\n## Open rationale\nExisting note\n", encoding="utf-8")

    with pytest.raises(PositionLogStoreError, match="Malformed position log payload"):
        _upsert(tmp_path, (_entry(),))
