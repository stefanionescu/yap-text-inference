# Shell Rules

Use these rules for `.githooks/`, `scripts/`, Docker shell entrypoints, and security wrappers.

## Entrypoints

- Every executable shell entrypoint must start with `#!/usr/bin/env bash`.
- Every executable shell entrypoint must enable `set -euo pipefail` near the top.
- Keep shared library code in `scripts/lib/` or the local image script directory instead of duplicating blocks inline.
- Treat hook scripts and security wrappers as production code. They are gates for the repo.

## Structure

- Keep shell files under the repo shell file limit of 300 lines.
- Keep functions under the repo shell function limit of 100 lines.
- Add a one-line doc comment above non-trivial functions in hooks and security wrappers.
- If you disable a ShellCheck rule in hooks or security scripts, justify it on the same line.
- Prefer arrays, quoted variables, and small helper functions over string-built command lines.

## Safety

- Avoid `eval`.
- Do not embed inline Python in shell. Move non-trivial parsing or business logic into Python modules and call them from the shell layer.
- Keep configuration defaults centralized in `scripts/config/` or a local readonly config block, not spread across multiple scripts.
- Make destructive operations explicit and visible. Do not hide them behind vague function names.
- When a shell workflow becomes stateful or heavily conditional, move the complex logic into Python and keep shell as orchestration only.

## Hooks

- `pre-commit` should stay fast.
- `pre-push` is allowed to be heavier, but it still needs clear output and bounded scope.
- Skip flags exist for emergencies, not for normal development.
- Hook self-checks are part of the standard lint flow. Do not leave `.githooks/` exempt from the same standards the repo applies elsewhere.

## Verification

Minimum verification for shell or hook changes:

```bash
bash scripts/lint.sh --only shell
```

If the change touches security wrappers, hook orchestration, or Docker shell, also run:

```bash
bash scripts/security.sh
```
