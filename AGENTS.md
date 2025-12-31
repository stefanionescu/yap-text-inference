# Agent Engineering Guidelines

These rules describe how every source file should be structured so that our agents stay consistent, readable, and easy to maintain. Follow each section carefully whenever you add or update code.

## Module Layout
- Always place the `__all__` export list at the very bottom of the file, after every class, function, and constant definition.
- Keep files focused: ideally one class per file. If you find yourself adding a second class, stop and split the logic into another module.
- Order logic so that internal helpers appear before any public exports. Readers should encounter the private plumbing before the API surface.
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
- The `helpers` directory is reserved for utilities that make sense across execution engines and other subdirectories. Prefer placing broadly applicable logic there instead of duplicating it inside specialized modules.
- Execution- or engine-specific logic must remain inside their respective directories (`execution`, `engines`, etc.).
- All token-related concerns—including tokenization utilities and tokenizer interactions—belong under the `tokens` subdirectory.

## Readability and Style
- Favor descriptive, clear names. Avoid vague terms like “maybe” in identifiers.
- Write a bit more commentary than usual, especially when explaining non-obvious control flow or algorithms.
- Keep every function clean and organized; keep indentation shallow and split helpers whenever doing so improves clarity.
- When a function grows deeply nested or relies on many chained conditionals/loops, refactor it into smaller pieces to keep the implementation straightforward.
- Strive for human readability above all else: clear ordering, straightforward control flow, and obvious intent in every block.
