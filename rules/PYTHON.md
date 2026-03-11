# Python Rules

Use these rules for production Python, Python-based lint tooling, and Docker-side Python helpers.

## Module Design

- Start each module with a short docstring that says what the module owns.
- Keep files below the repo policy limits. Split before a file approaches 300 lines or a function approaches 60 lines.
- Prefer one stateful class per file. If a second class appears, confirm the file still has a single responsibility.
- Keep constants, dataclasses, TypedDicts, and error imports near the top of the module.
- Define `__all__` only when it adds value, and keep it at the bottom of the file.

## Imports and Boundaries

- Do not import from `tests` in production code.
- Keep imports acyclic. If a new import creates a cycle, extract a shared type or helper into the correct lower layer.
- `src/scripts` must compose through public APIs and must not import `src.engines` directly.
- `src/engines` must not import `src.handlers`.
- `src/config` must stay pure and must not reach into runtime orchestration packages.
- `src/runtime` and `src.handlers.session` have extra isolation rules. Respect them instead of routing around them.

If you are tempted to cross one of these boundaries, the ownership is probably wrong.

## Config, State, and Errors

- `src/config` exports constants, dataclasses, and resolved values only. No I/O, no environment mutation, no hidden runtime work.
- Put shared runtime shapes in `src/state`. Reuse them instead of redefining dictionaries ad hoc.
- Put runtime exceptions in `src/errors` and re-export public ones from `src/errors/__init__.py`.
- Keep state construction explicit. When a snapshot changes, build a new value instead of mutating a widely shared object in place.

## Runtime Safety

- Do not perform work at import time.
- Do not use lazy singleton patterns, module-level instance caches, or wrapper functions that hide shared global state.
- Do not use `print` for runtime diagnostics. Use a module logger.
- Do not use `subprocess` with `shell=True`.
- Do not silence exceptions with empty `except` blocks. Either add context and re-raise or convert to a typed error.
- Keep external I/O boundaries explicit and well-logged.

## Naming and Structure

- Use descriptive names. Generic names like `helpers`, `utils`, `misc`, `temp`, `helper`, or `process_data` are rejected outside allowlisted paths.
- Keep public APIs narrow. Avoid wrapper functions that add no value.
- Remove dead parameters, dead branches, and old compatibility shims instead of leaving them behind.
- Prefer explicit dependency injection over reaching into module globals.

## Verification

Minimum verification for Python changes:

```bash
bash scripts/lint.sh --only code
python -m pytest -q
```

Run `bash scripts/coverage.sh` when the change affects behavior or test coverage expectations.
