from collections.abc import Iterable
from pathlib import Path

import frontmatter  # pyright: ignore[reportMissingTypeStubs]
import yaml
from frontmatter import Post  # pyright: ignore[reportMissingTypeStubs]
from frontmatter.default_handlers import YAMLHandler  # pyright: ignore[reportMissingTypeStubs]

from ids.application.ports.position_log_store import (
    PositionLogEntry,
    PositionLogStore,
    PositionLogStoreError,
    UpsertResult,
)
from ids.domain.position_log_context import ContextAtClose, ContextAtOpen

_SCAFFOLDING_SECTIONS = (
    "## Open rationale",
    "## Close rationale",
    "## Review history",
)

# Moment-of-decision context structs are written once and then frozen. The
# adapter refuses to overwrite them on refresh: whatever value already lives in
# the file wins over any incoming value for these keys.
_IMMUTABLE_FRONTMATTER_KEYS = (
    "context_at_open",
    "context_at_close",
)


class _StableYAMLHandler(YAMLHandler):
    def export(self, metadata: dict[str, object], **kwargs: object) -> str:
        kwargs.setdefault("sort_keys", False)
        return super().export(metadata, **kwargs)


class MarkdownPositionLogStore(PositionLogStore):
    def __init__(self, root: Path) -> None:
        self._root = root
        self._handler = _StableYAMLHandler()

    def upsert_metadata(self, entries: Iterable[PositionLogEntry]) -> UpsertResult:
        created_count = 0
        refreshed_count = 0
        status_transitioned_count = 0
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                path = self._path_for(entry)
                if path.exists():
                    previous_status = self._refresh_existing(path, entry)
                    refreshed_count += 1
                    if previous_status is not None and previous_status != entry.status.value:
                        status_transitioned_count += 1
                else:
                    self._write_new(path, entry)
                    created_count += 1
            return UpsertResult(
                created_count=created_count,
                refreshed_count=refreshed_count,
                status_transitioned_count=status_transitioned_count,
            )
        except PositionLogStoreError:
            raise
        except (TypeError, ValueError, yaml.YAMLError) as exc:
            raise PositionLogStoreError(f"Malformed position log payload: {exc}") from exc
        except OSError as exc:
            raise PositionLogStoreError(
                f"Failed to upsert position logs in `{self._root}`: {exc}"
            ) from exc

    def _path_for(self, entry: PositionLogEntry) -> Path:
        return self._root / f"{entry.open_date.isoformat()}_{entry.symbol}.md"

    def _write_new(self, path: Path, entry: PositionLogEntry) -> None:
        post = Post(_new_content(), self._handler, **_frontmatter(entry))
        path.write_text(frontmatter.dumps(post, handler=self._handler) + "\n", encoding="utf-8")

    def _refresh_existing(self, path: Path, entry: PositionLogEntry) -> object:
        post = frontmatter.load(str(path), handler=self._handler)
        previous_status = post.metadata.get("status")
        post.metadata = _refreshed_metadata(entry, post.metadata)
        post.content = _with_missing_sections(post.content)
        path.write_text(frontmatter.dumps(post, handler=self._handler) + "\n", encoding="utf-8")
        return previous_status


def _refreshed_metadata(entry: PositionLogEntry, existing: dict[str, object]) -> dict[str, object]:
    metadata = _frontmatter(entry)
    for key in _IMMUTABLE_FRONTMATTER_KEYS:
        if key in existing:
            metadata[key] = existing[key]
    return metadata


def _frontmatter(entry: PositionLogEntry) -> dict[str, object]:
    """Translate a typed entry into deterministically ordered YAML frontmatter."""
    metadata: dict[str, object] = {
        "status": entry.status.value,
        "symbol": str(entry.symbol),
        "open_date": entry.open_date,
        "open_price": str(entry.open_price),
    }
    if entry.close_date is not None:
        metadata["close_date"] = entry.close_date
    if entry.close_price is not None:
        metadata["close_price"] = str(entry.close_price)
    if entry.gross_pl_pln is not None:
        metadata["gross_pl"] = str(entry.gross_pl_pln)
    if entry.context_at_open is not None:
        metadata["context_at_open"] = _context_at_open_frontmatter(entry.context_at_open)
    if entry.context_at_close is not None:
        metadata["context_at_close"] = _context_at_close_frontmatter(entry.context_at_close)
    return metadata


def _context_at_open_frontmatter(context: ContextAtOpen) -> dict[str, object]:
    return {
        "portfolio_equity_pln": str(context.portfolio_equity_pln),
        "cash_reserve_pct": str(context.cash_reserve_pct),
        "open_positions_count": context.open_positions_count,
        "this_position_pct_of_portfolio": str(context.this_position_pct_of_portfolio),
        "strategy_rules_satisfied": [rule.value for rule in context.strategy_rules_satisfied],
        "strategy_rules_violated": [rule.value for rule in context.strategy_rules_violated],
    }


def _context_at_close_frontmatter(context: ContextAtClose) -> dict[str, object]:
    return {
        "hold_duration_days": context.hold_duration_days,
        "pnl_pct": str(context.pnl_pct),
        "strategy_rules_satisfied": [rule.value for rule in context.strategy_rules_satisfied],
        "strategy_rules_violated": [rule.value for rule in context.strategy_rules_violated],
    }


def _new_content() -> str:
    return "\n\n".join(_SCAFFOLDING_SECTIONS)


def _with_missing_sections(content: str) -> str:
    updated = content
    for section in _SCAFFOLDING_SECTIONS:
        if section not in updated:
            updated = _append_section(updated, section)
    return updated


def _append_section(content: str, section: str) -> str:
    if not content:
        return section
    return f"{content.rstrip()}\n\n{section}"
