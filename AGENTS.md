# Engineering Guidelines

These rules describe how every source file should be structured so that our agents stay consistent, readable, and easy to maintain. Follow each section carefully whenever you add or update code.

> **Note:** Never edit `AGENTS.md` unless the user explicitly requests changes to this file.

## Planning and Implementation
- Before writing code—whether for a refactor, restructure, or new feature—draft a plan that explains how you will satisfy these guidelines.
- Share that plan with the developer, capture any feedback, and explicitly ask for approval before touching the code.
- If new constraints or questions arise, iterate on the plan with the developer until everything is clear, then implement only after receiving a definitive go-ahead.
- When implementation is finished, run the project’s linters/tests yourself from the CLI (e.g., via the repo’s lint script) so the codebase is left in a lint-clean state before handing back results.

## Module Layout
- When using `__all__`, place it at the very bottom of the file, after every class, function, and constant definition; it is optional and only required when explicit export control is helpful.
- Keep files focused: ideally one class per file. If you find yourself adding a second class, stop and split the logic into another module.
- Start each file with a brief description that explains the file’s purpose, how it works, and why it exists (even for config modules) so readers have context before diving into the code.
- Order logic so that internal helpers appear before any public exports. Readers should encounter the private plumbing before the API surface.
- Export each public symbol from a single, well-defined place—preferably the module’s `__init__.py`—instead of re-exporting it through multiple files.
- `__init__.py` files are import/re-export hubs only; keep all executable logic in dedicated modules and simply re-export from the package init.
- If a public symbol is exported but unused, decide whether it should be removed, relocated, or refactored—unused exports are almost always a code smell.
- Avoid instantiating a singleton or global instance in the same file that defines the class; create those instances from a dedicated assembly point (e.g., the server entry module).
- Never trigger work at import time—do not auto-call functions when the module loads. Expose callable entry points and let the importer execute them explicitly.
- Keep total file length at or under 350 lines. Split the module whenever you approach that limit.
- Exception: data-heavy fixtures such as regression test cases or persona/prompt definitions (e.g., modules under `tests/`) may exceed the 350-line cap when splitting would reduce readability or introduce unnecessary indirection.
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
- Watch the directory layout: avoid subdirectories that contain a single file unless the file is intentionally split into multiple modules soon. Either split the logic further, move shared portions into `helpers`, or relocate the file into a better-suited directory and remove the redundant subfolder.
- When refactoring a large file into related modules, consider introducing a new subdirectory to host that cluster so the related pieces stay together and the parent directory remains organized.

## Scripts
- When reorganizing files, rely on shell or Python scripts (`mv`, helper utilities, etc.) to move assets or batch-create directories instead of rewriting files from scratch.
- Python helpers that power CLI scripts should live under `src/scripts`, organized either by category directories (e.g., `filtering`) or clearly named single-purpose modules when a category is unnecessary.
- Docker-related Python logic must remain inside the relevant `docker/` subdirectory rather than `src/scripts` so each image keeps its code self-contained.

## Docker
- Keep Python logic used by Docker assets inside clearly named directories under `docker/` so it remains separate from the shell scripts that drive each image.
- Factor out any logic shared by multiple Docker images (e.g., TRT and VLLM) into a common subdirectory; keep image-specific scripts and Python helpers inside that image’s folder.
- Every Docker image directory must ship with its own README that explains how to build and run it, and the root `docker/README.md` should cover the overall layout and entry points.
- Keep Dockerfiles focused on container setup instructions. Offload non-trivial logic to scripts or Python files and invoke them from the Dockerfile instead of embedding complex steps inline.

## Documentation
- Keep the primary README focused on the essential concepts: overall logic, how the scripts operate, and anything every developer must know to get started quickly.
- Use files like `ADVANCED.md` for in-depth walkthroughs or niche knowledge that only applies to specialized contributors.
- Avoid emojis or emoticons in every Markdown file; keep the tone professional and clear.
- Every Markdown file (other than `AGENTS.md`) must include a concise contents table or list immediately below its high-level description to help readers navigate.
- Never embed directory structures or tree listings inside README/Markdown files (and do not include them in code comments either); describe behavior and architecture instead of filesystem layouts.
- Whenever a feature or task is completed (not just partially done), review the README and any advanced docs to ensure they reflect the latest behavior.

## Readability and Style
- Favor descriptive, clear names. Avoid vague terms like “maybe” in identifiers.
- Keep every function clean and organized; keep indentation shallow and split helpers whenever doing so improves clarity.
- When refactoring, remove deprecated or unused logic entirely instead of leaving wrappers or compatibility shims; implement the new behavior cleanly.
- Delete unused parameters or arguments as soon as they become dead weight so signatures always reflect the active logic.
- Avoid lazy-loading or lazy-instantiation patterns that complicate reasoning; initialize dependencies directly unless there is a proven, critical need.
- If you encounter code smells or risky patterns, surface a warning to the developer before applying changes so the issue can be discussed.
- When a function grows deeply nested or relies on many chained conditionals/loops, refactor it into smaller pieces to keep the implementation straightforward.
- Strive for human readability above all else: clear ordering, straightforward control flow, and obvious intent in every block.

## Comments
- Keep code comments professional and concise—no emojis or emoticons, and avoid conversational tone.
- Describe what the surrounding code does right now. Never reference previous refactors, legacy decisions, or historical behavior unless the current implementation literally depends on that context.
- Err on the side of slightly more commentary for non-obvious control flow; focus on intent (the “why”) over narrating line-by-line execution.
- Do not delete useful comments just to satisfy the 350-line cap. If a file grows too large, split or reorganize the code while preserving the documentation.
