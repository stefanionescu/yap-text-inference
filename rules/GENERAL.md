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
- Start each file with a brief description of its purpose and behavior.
- Place internal helpers before public exports so plumbing appears first.
- Keep `__init__.py` files as import/re-export hubs; keep executable logic in dedicated modules.
- Export each public symbol from a single place and avoid unused exports.
- When you need explicit exports via `__all__`, define it only at the very bottom of the module after every class, function, and constant.
- Avoid creating singletons or global instances in the defining module; instantiate them at assembly points.
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
- Keep the primary README focused on essential concepts and required knowledge.
- Use ADVANCED-style docs for deeper or niche topics.
- Include a concise contents list immediately below each Markdown file’s description (except this file when referenced elsewhere by name alone).
- Avoid emojis or emoticons and keep the tone professional.
- Do not embed directory trees in docs or comments; describe behavior and architecture instead.
- When finishing a feature, update relevant docs so behavior stays current.

## Readability and style
- Favor clear, descriptive names; avoid vague identifiers.
- Follow naming conventions consistently: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants, and positive boolean predicates such as `is_ready` or `should_retry`.
- Keep functions shallow and organized; split helpers when nesting grows.
- Give each function a single, well-defined responsibility; extract unrelated work into helpers or new modules.
- Limit side effects and keep inputs/outputs narrowly scoped; document any unavoidable shared state or exceptions.
- Avoid using 'maybe' in function or variable names.
- Remove deprecated or unused logic rather than leaving shims.
- Delete unused parameters promptly so signatures match active behavior.
- Avoid lazy-loading or lazy-instantiation in all files.
- Highlight code smells or risky patterns so they can be addressed.
- Aim for straightforward control flow and obvious intent throughout.

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
- When multiple async tasks or threads might touch the same resource, guard access with `asyncio.Lock`, `contextlib.AsyncExitStack`, or threading locks rather than relying on timing.

## Shell and CLI scripts
- Start every shell script with `#!/usr/bin/env bash` and `set -euo pipefail`; enable `IFS=$'\n\t'` when splitting on lines.
- Declare read-only configuration with `readonly VAR=value` and prefer functions over inline command sequences for reuse.
- Keep script function names in `snake_case` and log via a shared helper (`log_info`, `log_error`) rather than ad-hoc `echo` prefixes.
- Before writing a new script, confirm whether the behavior belongs in an existing script under `scripts/` or `src/scripts/` and explain the decision in the change description.
