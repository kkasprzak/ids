# Test Strategy

## Purpose

The test suite serves three goals in priority order:

1. **Design tool** — domain tests are written test-first to drive the shape of domain logic
2. **Regression net** — adapter tests guard the I/O contract against breakage
3. **Living documentation** — e2e tests describe what the CLI does for a reader who doesn't know the code

## What is a Unit Test

From Michael Feathers, _Working Effectively with Legacy Code_: a unit test runs fast and helps localize errors quickly. A test is not a unit test if it talks to a database, communicates across a network, touches the filesystem, or requires environment setup.

This gives three categories:

| Category | Location | Marker | Characteristic |
|---|---|---|---|
| Unit | `tests/domain/` | `pytest.mark.unit` | Pure functions, no I/O, sub-millisecond |
| Integration | `tests/adapters/` | `pytest.mark.integration` | Real filesystem via `tmp_path` |
| System | `tests/e2e/` | `pytest.mark.e2e` | Full CLI invocation, golden file diff |

Markers are applied at the file level:

```python
import pytest
pytestmark = pytest.mark.unit
```

All markers are registered in `pyproject.toml`. Enforcement is by convention — no tooling gate.

## Test Pyramid

- **Domain tests are the primary investment.** Every non-trivial decision branch in `src/ids/domain/` has a test that would fail if that branch were deleted.
- **Adapter tests cover the I/O contract** but do not repeat domain logic.
- **E2E tests are minimal:** one happy path + one key failure per CLI command. No more.

## TDD Workflow

- **Domain logic is written test-first.** Tests drive the API design before the internals exist.
- **Adapters are written implementation-first**, tests second. The I/O contract is tested after the adapter is working.
- **E2E tests are written after the feature is complete.** The golden file is generated from the first correct run and committed as a deliberate human action.

## Fixture Strategy

**Fresh Fixture is a hard rule.** Every test builds its own state from scratch. `scope="module"` and `scope="session"` are banned unless there is a documented performance justification — and even then the fixture must be immutable.

**Object Mother** is the standard factory pattern. Factory functions live in `conftest.py` with keyword-only arguments and round-number defaults:

```python
def make_position(*, symbol: str = "TEST.PL", open_price: Decimal = Decimal("100"), ...) -> Position:
    ...
```

Defaults use round numbers — never realistic-looking values copied from real exports. Realistic numbers imply significance that isn't there and make readers hunt for a pattern that doesn't exist.

**Builder pattern** is used when object graphs become complex (multiple nested objects with non-trivial relationships).

All Object Mother factories are exposed as pytest fixtures via root `conftest.py`.

## Test Data Rules

Two categories of values in tests:

1. **Computed fixtures** — input values must make the expected output derivable by a reader without running the code. If the relationship isn't immediately obvious, add a one-line comment explaining the arithmetic.
2. **Arbitrary fixtures** — use round numbers (`Decimal("100")`, `Decimal("1000")`). Never use realistic-looking values as defaults in Object Mother factories.

## Test Naming

`test_<situation>_<expected_outcome>` — readable as a sentence describing a behavior.

- Good: `test_days_held_uses_as_of_not_now`
- Bad: `test_build_weekly_snapshot_2`

If a test name requires "and" to describe it, split it into two tests.

## One Behavior Per Test

Multiple assertions per test are fine when they collectively verify a single concept. Each test covers exactly one behavior — not one assertion, not one function.

## Test Doubles

**No mocks.** If you feel the urge to mock, it is a signal the design needs to change.

The preference order:
1. **Real implementation** via `tmp_path` (preferred even over fakes for adapter tests)
2. **In-memory fake** that implements a port interface — only when the real adapter has unavoidable side effects or is prohibitively slow
3. **Mocks** — never

## What Not to Test

Do not test:
- **Framework guarantees** — e.g. that `@dataclass(frozen=True)` makes a class frozen
- **Third-party library behavior** — e.g. that `Decimal` arithmetic is correct
- **Anything covered by static analysis** — Pyright handles type correctness; do not replicate it with `isinstance` assertions
- **Internal guards** — `ValueError`/`AssertionError` raised inside private functions
- **Private functions** — test through the public boundary only

## Error Path Testing

Test every port-defined exception at the adapter boundary. Assert both the exception type and a meaningful substring of the message — enough to verify the error is actionable (a file path, a command hint, a field name). Do not assert the full message string.

```python
with pytest.raises(NoPortfolioAvailableError, match="mkdir -p"):
    loader.load_latest()
```

## Golden Files

One golden file per CLI command in `tests/fixtures/expected/`. The file contains full output — partial matching hides regressions in untested sections.

Updating a golden file is always a deliberate human action: regenerate, review the `git diff`, and commit. Updates are never automatic.

## Coverage

Coverage is informational only. It is run in CI as `pytest --cov=ids` but does not gate the build. The real measure is: would a test fail if this decision branch were deleted? That is a code review judgment, not a metric.

## CI Pipeline

Stages run in order, fast-fail:

1. `ruff check . && ruff format --check .`
2. `pyright`
3. `pytest -m unit`
4. `pytest`

**Local workflow:** run `pytest -m unit` during active coding. Run `pytest` before pushing.
