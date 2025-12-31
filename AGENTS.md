# Engineering Guidelines

These rules describe how every source file should be structured so that our agents stay consistent, readable, and easy to maintain. Follow each section carefully whenever you add or update code.

> **Note:** Never edit `AGENTS.md` unless the user explicitly requests changes to this file.

## Planning and Implementation
- Before writing code—whether for a refactor, restructure, or new feature—draft a plan that explains how you will satisfy these guidelines.
- Share that plan with the developer, capture any feedback, and explicitly ask for approval before touching the code.
- If new constraints or questions arise, iterate on the plan with the developer until everything is clear, then implement only after receiving a definitive go-ahead.

## Module Layout
- Always place the `__all__` export list at the very bottom of the file, after every class, function, and constant definition.
- Keep files focused: ideally one class per file. If you find yourself adding a second class, stop and split the logic into another module.
- Start each file with a brief description that explains the file’s purpose, how it works, and why it exists (even for config modules) so readers have context before diving into the code.
- When reorganizing files, use shell scripts (`mv`, helper bash/Python scripts, etc.) to move or batch-move assets and create directories; do not rewrite a file from zero just to change its location.
- Order logic so that internal helpers appear before any public exports. Readers should encounter the private plumbing before the API surface.
- Export each public symbol from a single, well-defined place—preferably the module’s `__init__.py`—instead of re-exporting it through multiple files.
- If a public symbol is exported but unused, decide whether it should be removed, relocated, or refactored—unused exports are almost always a code smell.
- Keep total file length at or under 300 lines. Split the module whenever you approach that limit.
- Use section dividers exactly in this format, followed by a single blank line before the first symbol:
  ```
  # ============================================================================
  # CLI
  # ============================================================================
  ```

## Imports, Data Structures, and Constants
- Place locally defined data structures (e.g., dataclasses, typed dictionaries) and custom errors directly under the imports so that readers see the types before the logic that uses them.
- Other module-level values—mappings, constant dictionaries, look-up tables—should also stay near the top, under the types/errors, so they are defined before any executable code.

## Configuration and Parameters
- Avoid magic values inline. Store configuration knobs inside the appropriate file under the `config` directory. Reuse an existing config module when possible; only create a new file when a fitting one does not exist.

## Directories and Code Reuse
- Keep code DRY. Before introducing new helpers or utilities, check whether identical or similar logic already lives elsewhere and reuse it.
- Regularly review the main `helpers` directory and the local helper utilities scattered across `src` subdirectories to ensure logic lives in the most sensible spot.
- The `helpers` directory is reserved for utilities that make sense across execution engines and other subdirectories. Prefer placing broadly applicable logic there instead of duplicating it inside specialized modules.
- Move shared logic from a local module into `helpers` when it becomes generally useful, and likewise relocate a helper from `helpers` into a local module if it turns out to be specific to that execution engine or feature.
- Execution- or engine-specific logic must remain inside their respective directories (`execution`, `engines`, etc.).
- All token-related concerns—including tokenization utilities and tokenizer interactions—belong under the `tokens` subdirectory.
- Scripts that need Python helpers should import them from `src/scripts`; keep that directory organized by category subfolders (e.g., `filtering`) or by clearly named single-purpose modules when no category is necessary.

## Documentation
- Keep the primary README focused on the essential concepts: overall logic, how the scripts operate, and anything every developer must know to get started quickly.
- Use files like `ADVANCED.md` for in-depth walkthroughs or niche knowledge that only applies to specialized contributors.
- Avoid emojis or emoticons in every Markdown file and in code comments; keep the tone professional and clear.
- Every Markdown file (other than `AGENTS.md`) must include a concise contents table or list immediately below its high-level description to help readers navigate.
- Whenever a feature or task is completed (not just partially done), review the README and any advanced docs to ensure they reflect the latest behavior.

## Readability and Style
- Favor descriptive, clear names. Avoid vague terms like “maybe” in identifiers.
- Write a bit more commentary than usual, especially when explaining non-obvious control flow or algorithms.
- Keep every function clean and organized; keep indentation shallow and split helpers whenever doing so improves clarity.
- When refactoring, remove deprecated or unused logic entirely instead of leaving wrappers or compatibility shims; implement the new behavior cleanly.
- Delete unused parameters or arguments as soon as they become dead weight so signatures always reflect the active logic.
- Avoid lazy-loading or lazy-instantiation patterns that complicate reasoning; initialize dependencies directly unless there is a proven, critical need.
- If you encounter code smells or risky patterns, surface a warning to the developer before applying changes so the issue can be discussed.
- When a function grows deeply nested or relies on many chained conditionals/loops, refactor it into smaller pieces to keep the implementation straightforward.
- Strive for human readability above all else: clear ordering, straightforward control flow, and obvious intent in every block.
