from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from ids.adapters.formatters import (
    format_pct_signed,
    format_pct_unsigned,
    format_pln,
    format_pln_signed,
    format_price,
)
from ids.domain.ports.report_writer import ReportWriter
from ids.domain.viewmodels import WeeklySnapshotView


class MarkdownReportWriter(ReportWriter):
    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("ids.adapters", "templates"),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        filters = cast(
            dict[str, Any],
            self._env.filters,  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        )
        filters["pln"] = format_pln
        filters["pln_signed"] = format_pln_signed
        filters["pct"] = format_pct_unsigned
        filters["pct_signed"] = format_pct_signed
        filters["price"] = format_price

    def write_weekly(self, view: WeeklySnapshotView, output_path: str) -> None:
        template = self._env.get_template("weekly_report.md.j2")
        rendered = template.render(view=view)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
