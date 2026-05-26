# Tech stack

This document lists the languages, libraries, and tools the Investment Decision System depends on. How they fit together is described in `ARCHITECTURE.md`.

## Language and runtime

- **Python** — version 3.12 or newer.

## Dependency and environment management

- **`uv`** — manages Python version, virtual environment, dependencies, and the lockfile (`uv.lock`).

## Runtime libraries

| Concern | Library |
|---------|---------|
| CLI framework | `typer` |
| Tabular analytics | `pandas` |
| XLSX parsing | `openpyxl` (direct dependency) |
| Charts | `matplotlib` |
| YAML parsing | `PyYAML` |
| Frontmatter handling | `python-frontmatter` |
| Markdown templating | `jinja2` |
| User-facing CLI output | `rich` |
| Diagnostic logging | standard library `logging` |

## Developer tooling

| Concern | Tool |
|---------|------|
| Test runner | `pytest` |
| Coverage | `pytest-cov` |
| Parallel testing | `pytest-xdist` |
| Linter and formatter | `ruff` |
| Type checker | `pyright` |
| Pre-commit hooks | `pre-commit` |
| CI | GitHub Actions |

## Out of scope (current MVP)

- `yfinance` and other historical-price providers.
- `money` / `py-moneyed` and other currency-aware money libraries.
- `seaborn`, `plotly`, and alternative chart libraries.
- `mypy`.
- `ruamel.yaml`.
