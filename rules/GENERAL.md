# General Engineering Guidelines

Shared engineering expectations for all work in this codebase. Use these rules as the default approach for new logic and refactors.

## Planning and implementation
- Draft a plan before coding, share it, and get approval before changes.
- Iterate on the plan when constraints or questions arise; proceed only after clear agreement.
- Run project linters/tests from the CLI after implementation so the tree stays clean.
- Whenever you rename or move a file/module, audit the codebase for imports and update them immediately so nothing keeps referring to the old path.
- Before adding a new module, directory, or helper, document which existing files you evaluated and why extending them was rejected.

## Module layout
- Prefer one class per file; split if a second class is needed.
- Start each Python file with a module-level docstring describing its purpose and behavior; for shell scripts, add a header comment block after the shebang.
- Place internal helpers before public exports so plumbing appears first.
- Keep `__init__.py` files as import/re-export hubs; keep executable logic in dedicated modules.
- Export each public symbol from a single place and avoid unused exports.
- When you need explicit exports via `__all__`, define it only at the very bottom of the module after every class, function, and constant.
- Avoid creating singletons or global instances in the defining module; instantiate them in entry-point scripts, factory functions, or dependency-injection setups instead.
- Do not add module-level free functions that merely wrap a module-level singleton instance (e.g., `get_engine()` calling `_singleton.get()`). If a class manages state, the public API is the class itself—do not hide it behind free functions in the same file. This pattern creates hidden global state, complicates testing, and makes debugging harder because callers don't realize they're touching shared mutable state.
- Do not trigger work at import time; expose callable entry points instead.
- Keep files at or under 350 lines; split when approaching the limit. Data-heavy fixtures may exceed this when splitting would hurt clarity.
- Use section dividers in this exact format when needed:
  ```
  # ============================================================================
  # CLI
  # ============================================================================
  ```

## Imports, data structures, and constants
- Define local dataclasses, typed dictionaries, and custom errors directly under imports.
- Keep module-level constants and lookup tables near the top so they precede executable code.
- Avoid magic values inline; surface configuration knobs explicitly instead of hiding them in logic.

## Documentation
- Documentation tiers:
  - README: core concepts, required env vars, primary workflows (deploy, run, stop), and minimum examples that are validated.
  - ADVANCED (or similarly named deep-dives): engine/quantization details, operational playbooks (restart, health, logs), tuning flags, and troubleshooting.
  - Feature/area-specific docs: only when scope is too deep for README; link from README or ADVANCED to avoid orphaned content.
- Required structure for Markdown docs: short purpose statement, concise contents list near the top, prerequisites/env vars, step-by-step flows (setup, run, stop/restart), testing/validation notes, and links to canonical knobs/flags instead of duplicating tables.
- Script and flag coverage: every host script must list all supported flags/env vars with descriptions, defaults, required/optional status, and interactions. When new flags or behaviors ship, update the canonical table (README for core flows, ADVANCED for deep tuning) and link rather than re-state.
- Deduplication and layout: pick one canonical location for each table or process; other docs link back. Keep section ordering consistent with current README/ADVANCED patterns (features → quickstart → deployment → quantization → operations/restart/health/logs → tests/tools) unless there is a strong reason to diverge.
- Style: professional tone, no emojis. Prefer prose descriptions of architecture over ASCII directory trees—use trees sparingly and only for small, specific subsets. Keep commands copy/pasteable, validated, and tied to current scripts/flags; note expected outputs or health checks when relevant.
- Currency and ownership: update docs with every behavior change; when altering flags or defaults, the same PR must update the canonical doc. Avoid silent drift—flag gaps as follow-ups if unknown.
- Validation: runnable examples must reflect current scripts and flags; if an example is unverified, mark it and add a follow-up task with owner. State any assumptions or prerequisites explicitly.

## Readability and style
- Use clear, descriptive names for functions, variables, classes, files, and modules. Avoid vague identifiers like `data`, `info`, `temp`, `result`, `handle`, or `process`—prefer names that convey purpose, such as `user_session`, `parse_token_stream`, or `ConnectionState`.
- Follow naming conventions consistently: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants, and positive boolean predicates such as `is_ready` or `should_retry`.
- Do not embed file or directory names in function or variable names; if a function lives in `model_detect.sh`, name it `classify_prequant`, not `model_detect_classify_prequant`. The file path already provides context—repeating it creates noise and clutters call sites.
- Keep functions shallow—avoid more than two or three levels of nesting. When conditionals or loops push deeper, extract the inner logic into helper functions.
- Give each function a single, well-defined responsibility; extract unrelated work into helpers or new modules.
- Limit side effects and keep inputs/outputs narrowly scoped; document any unavoidable shared state or exceptions.
- Avoid 'maybe' in function or variable names—it conflates existence with optionality. Use `is_*`, `has_*`, or `can_*` predicates for booleans, and return `Optional[T]` with a clear noun for nullable values.
- Remove deprecated or unused logic rather than leaving shims.
- Delete unused parameters promptly so signatures match active behavior.
- Avoid lazy-loading or lazy-instantiation in all files.
- Mark code smells or risky patterns with a `# TODO(cleanup):` or `# WARNING:` comment explaining the concern so they can be tracked and addressed.
- Keep control flow straightforward: prefer early returns over deep nesting, avoid multiple exit points from loops, simplify compound boolean expressions, and limit each function to one main path with clear exception handling.

## Comments
- Keep comments concise and focused on current behavior, NOT on past actions we took or refactors.
- Prefer intent (“why”) over line-by-line narration, especially for non-obvious control flow.
- Do not remove useful comments just to reduce length; reorganize instead when needed.

## Function contracts and typing
- Annotate every function and method with explicit type hints (no implicit `Any`); introduce Protocols or TypedDicts when structural typing is needed.
- Give each public function, class, and module a docstring that states its purpose, key parameters, return value, and noteworthy side effects.
- Validate inputs at the top of the function and fail fast with domain-specific errors or `ValueError`—never mutate caller data to “make it fit.”
- Accept required data first, optional overrides second, and injected dependencies last; favor keyword-only parameters for behavioral toggles.

## Error handling and logging
- Define a module-level `logger = logging.getLogger(__name__)` and route all diagnostic output through it; never use `print` for runtime logging.
- Raise purpose-built exceptions so callers can branch on intent; centralize exception classes per repo instead of inventing ad-hoc classes inline.
- Wrap external I/O (network, subprocess, filesystem) in try/except blocks that attach enough context (IDs, payload sizes) before re-raising.
- Do not swallow exceptions—either convert them to a typed error that propagates, or log and re-raise so upstream handlers can react.

## Testing
- Ship every behavioral change with a matching automated test (unit, integration, or system) that would fail without the change.
- Keep tests deterministic by stubbing clocks, network calls, randomness, and filesystem writes; centralize shared fixtures so they can be reused.
- Add a regression test for each bug fix that previously failed to prevent repeats; reference the failure scenario in the test’s docstring or comments.
- Name test modules `test_*.py`, fixtures `fixture_*`, and doubles `fake_*`/`stub_*` so intent stays obvious.
- Limit test modules to the smallest practical scope; extract reusable builders into helper modules or fixtures instead of duplicating factories inline.

## State and concurrency
- Model shared runtime state with frozen dataclasses or TypedDicts and keep their definitions in an obvious, centralized module so structure stays discoverable.
- Treat state objects as immutable snapshots; when an update is required, construct a new instance instead of mutating one that other callers might hold.
- Pass state explicitly through function parameters instead of stashing it in globals or module-level caches.
- Keep singleton instances in a dedicated registry or container module (`registry.py`, `container.py`) rather than scattering them across factory modules. Entry-point code (servers, CLI scripts) should be the only code that instantiates or retrieves singletons; everything else receives dependencies as parameters.
- When multiple async tasks or threads might touch the same resource, guard access with `asyncio.Lock`, `contextlib.AsyncExitStack`, or threading locks rather than relying on timing.

## Shell and CLI scripts
- Start every shell script with `#!/usr/bin/env bash` and `set -euo pipefail`; enable `IFS=$'\n\t'` when splitting on lines.
- Declare read-only configuration with `readonly VAR=value` and prefer functions over inline command sequences for reuse.
- Keep script function names in `snake_case` and log via a shared helper (`log_info`, `log_error`) rather than ad-hoc `echo` prefixes.
- Before writing a new script, confirm whether the behavior belongs in an existing script under `scripts/` or `src/scripts/` and explain the decision in the change description.
