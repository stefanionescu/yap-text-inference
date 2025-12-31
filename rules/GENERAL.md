# General Engineering Guidelines

Shared engineering expectations for all work in this codebase. Use these rules as the default approach for new logic and refactors.

## Planning and implementation
- Draft a plan before coding, share it, and get approval before changes.
- Iterate on the plan when constraints or questions arise; proceed only after clear agreement.
- Run project linters/tests from the CLI after implementation so the tree stays clean.

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
- Keep functions shallow and organized; split helpers when nesting grows.
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
