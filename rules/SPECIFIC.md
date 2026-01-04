# Repo-Specific Guidelines

Expectations tailored to this repository’s layout and inference workflows. Use these rules when placing code or assets within this project.

## Configuration and parameters
- Avoid inline magic values; store configuration knobs in the `config/` directory. Reuse an existing module when possible before adding new ones.
- For feature flags that enable behavior when set, treat absence as “off.” Don’t introduce redundant “disable” flags—only the enabling flag should be needed.
- Keep each configuration value defined exactly once: if only Python code consumes it, define it in `src/config/`; if only shell scripts consume it, keep it under `scripts/` and expose it to Python via environment variables or CLI arguments instead of duplicating constants.

## Directories and code reuse
- Keep code DRY; prefer reusing existing helpers over duplicating logic.
- Reserve `helpers/` for utilities that make sense across execution engines and other subdirectories.
- Keep execution- or engine-specific logic inside `execution/` and `engines/` respectively. Handler and CLI modules must not import internal submodules from these directories—use the public APIs exposed via `__init__.py` or factory abstractions.
- Route all inbound and outbound transport concerns through `handlers/`; everything else must call `handlers` via typed methods rather than touching sockets or HTTP objects directly.
- Keep conversational transforms (parsing user messages, formatting responses, structuring tool calls) inside `messages/` and reuse its validators whenever shaping chat or tool payloads.
- Place all token-related utilities and tokenizer interactions under `tokens/`—do not replicate token math elsewhere.
- Avoid subdirectories that contain a single file unless further splits are imminent. Otherwise, move logic into a better-suited location and remove the extra folder.
- When refactoring large files into related modules, group them under a shared subdirectory to keep organization clear.
- Before adding a new module, extend the closest existing peer module when feasible; new files must include a short justification in the PR/CL description that lists the modules considered and rejected.

## Errors and diagnostics
- Define every runtime or domain-specific exception inside `src/errors/`, organized by feature (e.g., `src/errors/websocket.py`, `src/errors/tool.py`); import from there instead of declaring ad-hoc classes.
- Re-export each public exception via `src/errors/__init__.py` so call sites can rely on `from src.errors import ToolDrainError`-style imports.
- Tests that need runtime exceptions import them from `src/errors/`; test-only harness failures belong under `tests/helpers/errors/` and nowhere else.
- Log formatting helpers or structured error payload builders also live next to their corresponding error classes inside `src/errors/` to keep context centralized.

## State and data models
- Store canonical dataclasses and TypedDicts that describe runtime state under `src/state/` with one module per concern (e.g., `session.py`, `tool.py`, `websocket.py`). Create the directory if it does not yet exist before adding state.
- Treat the definitions in `src/state/` as the single source of truth; every layer (handlers, execution, engines) must import from there rather than redefining shapes.
- Provide builders/factories for common state snapshots inside `tests/helpers/state/` so tests can compose consistent data without re-specifying every field.
- When a new state concept appears, add it to `src/state/`, update `__all__`, and extend the matching helper builders before using it anywhere else.
- Give each dataclass or TypedDict a docstring noting the owning component (handlers/execution/engine) and the lifecycle stage it represents.
- When state objects grow optional fields or flags, document the default semantics in the class docstring and add validation helpers under `src/state/validation.py`.

## Dependency boundaries
- Imports may only flow downward: `handlers` can import from `execution` and `engines`, `execution` can import from `engines`, but the reverse direction is forbidden.
- `src/scripts/` may invoke handlers or execution entry points but must not import engines directly; use the factory abstractions in `engines/`.
- Tests may import production code freely but production modules must never import from `tests/`.

## Scripts
- Place Python helpers that power CLI scripts under `src/scripts`, organized by category directories when useful.
- Keep Docker-related Python logic inside the relevant `docker/` subdirectory for each image rather than under `src/scripts`.
- Centralize heavyweight orchestration tasks (e.g., building TensorRT engines) in a single script and have all other scripts invoke it; do not fork divergent copies of the same workflow.
- Keep shell scripts focused on orchestration and call into shared functions/helpers for reusable steps so each script has one responsibility.

## Docker
- Keep Python logic used by Docker assets inside clearly named directories under `docker/` so it stays separate from shell drivers.
- Factor out logic shared by multiple Docker images (e.g., TRT and VLLM) into a common subdirectory; keep image-specific scripts and helpers inside that image’s folder.
- Each Docker image directory must include its own README explaining how to build and run it; the root `docker/README.md` should cover overall layout and entry points.
- Keep Dockerfiles focused on setup steps; move non-trivial logic into scripts or Python files and invoke them from the Dockerfile.

## Testing layout
- Every behavioral change must land with a focused test under the mirrored path in `tests/` (e.g., `src/tokens/source.py` → `tests/logic/tokens/test_source.py`); integration tests live under the closest matching feature directory.
- Mirror the structure of `src/` under `tests/logic/` by feature area (handlers → `tests/logic/handlers`, tokens → `tests/logic/tokens`, etc.) so ownership is obvious.
- Shared fixtures, websocket tooling, and regression harnesses belong under `tests/helpers/`; avoid importing test helpers from production code or vice versa.
- When adding a new top-level directory in `src/`, immediately create the matching tree in `tests/` (even if empty) so future contributors know where tests should live.
