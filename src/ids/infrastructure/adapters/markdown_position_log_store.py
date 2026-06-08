from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

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

_SCAFFOLDING_SECTIONS = (
    "## Open rationale",
    "## Close rationale",
    "## Review history",
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
                    new_status = entry.frontmatter.get("status")
                    if (
                        previous_status is not None
                        and new_status is not None
                        and previous_status != new_status
                    ):
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
        post = Post(_new_content(), self._handler, **_normalized_frontmatter(entry.frontmatter))
        path.write_text(frontmatter.dumps(post, handler=self._handler) + "\n", encoding="utf-8")

    def _refresh_existing(self, path: Path, entry: PositionLogEntry) -> object:
        post = frontmatter.load(str(path), handler=self._handler)
        previous_status = _metadata_value(post.metadata, "status")
        post.metadata = _normalized_frontmatter(entry.frontmatter)
        post.content = _with_missing_sections(post.content)
        path.write_text(frontmatter.dumps(post, handler=self._handler) + "\n", encoding="utf-8")
        return previous_status


def _metadata_value(metadata: dict[str, object], key: str) -> object:
    return metadata.get(key)


def _normalized_frontmatter(frontmatter: dict[str, object]) -> dict[str, object]:
    return {key: _normalized_value(value) for key, value in frontmatter.items()}


def _normalized_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _normalized_value(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple):
        items = cast(Iterable[object], value)
        return [_normalized_value(item) for item in items]
    if isinstance(value, str | int | float | bool | date | datetime) or value is None:
        return value
    return str(value)


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
