# Testing Rules

Use these rules for all test suites, fixtures, support modules, and coverage work.

## Layout

- Executable tests belong under `tests/suites/unit/`, `tests/suites/integration/`, or `tests/suites/e2e/`.
- Unit tests must live in a domain subfolder under `tests/suites/unit/<domain>/`.
- Test files use the `test_*.py` naming pattern.
- `tests/support/` is for helpers, canned messages, prompts, websocket payloads, and runners. It must not contain `test_*` functions.
- Keep the only `conftest.py` at `tests/conftest.py`.
- Shared config fixtures belong in `tests/config/`. Shared state builders belong in `tests/state/`.

## Writing Tests

- Ship every behavior change with a test that would fail without the change.
- For bug fixes, add a regression test that captures the old failure.
- Keep tests deterministic. Stub time, network, environment, and filesystem effects when practical.
- Prefer small, explicit helpers over magic fixtures that hide too much setup.
- Production code must never import test helpers.

## Test Support Code

- Use `tests/support/helpers/fmt.py` for CLI-style test output instead of inventing new formatting helpers.
- Keep prompts, persona variants, and large canned payloads in `tests/support/` so they can be reused across suites.
- Keep support modules importable and boring. They should help the tests, not become a second application.

## Coverage

- Coverage is measured against `src/` only.
- If you add runtime behavior in `src/`, either test it directly or explain why it is intentionally uncovered.
- Keep coverage artifacts Sonar-compatible by using the repo coverage command rather than ad hoc local commands when possible.

## Verification

Minimum verification for test or coverage changes:

```bash
python -m pytest -q
bash scripts/coverage.sh
```
