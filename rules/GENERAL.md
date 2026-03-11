# How to Work in This Repo

These rules apply across the inference repository. Start here, then follow the narrower rule file for the area you are touching.

## Contents

- [Thinking Before Coding](#thinking-before-coding)
- [Development Workflow](#development-workflow)
- [Verification](#verification)
- [Git Hooks](#git-hooks)
- [Linting and Security](#linting-and-security)
- [Fix What You Find](#fix-what-you-find)
- [Documentation](#documentation)
- [Secrets and Sensitive Data](#secrets-and-sensitive-data)
- [Package Management](#package-management)
- [Rule Map](#rule-map)

## Thinking Before Coding

Read the relevant code before editing it. Trace the real runtime path, identify the failure modes, and choose the smallest correct change.

Before adding a new file or directory, check whether an existing module already owns the behavior. Extending an existing file is usually better than creating a new catch-all helper.

Plan before editing. Share the plan when the work is broad, risky, or crosses multiple subsystems. For small, local changes, think through the plan and execute it directly.

## Development Workflow

1. Read the code and understand the boundary you are changing.
2. Calibrate the solution. Avoid both underengineering and speculative abstraction.
3. Implement incrementally. Verify after each meaningful step.
4. Run the narrowest useful checks first, then the full repo gates for the touched area.
5. Review the changed files before stopping. Make sure every file belongs to the change.

Prefer the repo command hub over ad hoc one-off commands:

- Fast lint loop: `bash scripts/lint.sh --fast`
- Full lint: `bash scripts/lint.sh`
- Tests: `python -m pytest -q`
- Coverage: `bash scripts/coverage.sh`
- Security: `bash scripts/security.sh`
- Nox sessions: `nox -s lint`, `nox -s test`, `nox -s coverage`, `nox -s security`

## Verification

Verification is required, not optional. Pick the commands that match the scope:

- Python or runtime logic: `bash scripts/lint.sh --only code` and `python -m pytest -q`
- Shell, hooks, or host scripts: `bash scripts/lint.sh --only shell`
- Docs or rules changes: `bash scripts/lint.sh --only docs`
- Docker changes: `bash scripts/lint.sh --only docker`
- Structural or dependency hygiene work: `bash scripts/lint.sh --only quality`
- Coverage and Sonar inputs: `bash scripts/coverage.sh`
- Security-sensitive, dependency, Docker, or hook work: `bash scripts/security.sh`

If you changed more than one area, run the full suites instead of a partial one.

## Git Hooks

Hooks live under `.githooks/`. Install them with:

```bash
bun install
bun run setup:hooks
```

Current hook model:

- `pre-commit`: fast repo guards, docs checks, code lint, shell lint, Docker lint, and hook self-checks
- `commit-msg`: conventional commit validation through `commitlint`
- `pre-push`: heavier quality, coverage, and security checks

Use skip flags only when there is a real reason. They are escape hatches, not the normal workflow.

Commit messages follow conventional commits:

```text
type(scope): lowercase subject
```

Allowed scopes are:

`core`, `config`, `handlers`, `messages`, `tokens`, `engines`, `quantization`, `docker`, `scripts`, `tests`, `lint`, `hooks`, `docs`, `deps`, `rules`

## Linting and Security

Lint is a gate. Do not suppress findings just to get a green run.

This repo now treats the following as standard quality and security signals:

- `ruff`, `mypy`, `import-linter`, custom AST rules
- `shellcheck`, `shfmt`, custom shell rules
- `markdownlint`, `codespell`, banned-term checks
- `lizard`, `deptry`, `vulture`, `jscpd`
- `bandit`, `pip-audit`, `osv-scanner`, `semgrep`
- `gitleaks`, `trivy`, `bearer`, `CodeQL`, `SonarQube`

If a tool needs a baseline or allowlist, document the reason in the baseline file. Do not hide real findings behind broad ignores.

## Fix What You Find

If you are already in a file and you see a nearby lint violation, dead code path, stale comment, bad type, or obvious code smell, fix it.

Do not widen the change into an unrelated refactor. Small adjacent cleanup is expected. Broad redesign is not.

## Documentation

Docs must match the code and scripts that exist today.

Whenever behavior changes, update the corresponding docs in the same change:

- README-level docs for core workflows
- ADVANCED docs for deeper operational details
- Docker README files for image-specific build and run flows
- rules docs for agent-facing engineering guidance

Do not hardcode stale defaults in prose when the script or config is the real source of truth. Prefer naming the flag, config variable, or command over copying its current literal value unless the value is intentionally stable.

## Secrets and Sensitive Data

Never commit secrets, tokens, private keys, or internal credentials.

Do not log sensitive payloads, raw auth headers, full environment dumps, or user data that is not needed for debugging. Log identifiers and context instead.

Treat prompt fixtures, websocket payloads, and model runtime config as potentially sensitive. Keep test fixtures sanitized.

## Package Management

Python dependencies stay in the pinned `requirements-*.txt` files and are executed through Python or `nox`.

JS-based lint tooling at the repo root is Bun-managed:

- use `bun install` to sync dependencies
- use `bun run <script>` for package scripts
- use `bunx <tool>` for direct binary execution
- commit `bun.lock`
- do not introduce `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`

`nox` remains the canonical Python-native command hub. Bun exists here to manage the markdown, commit, and duplication tooling cleanly.

## Rule Map

Use the narrower rule file when the task is concentrated in one area:

- [SPECIFIC.md](./SPECIFIC.md): repo layout, boundaries, and inference-specific priorities
- [PYTHON.md](./PYTHON.md): Python module, config, state, and runtime rules
- [SHELL.md](./SHELL.md): shell, hooks, and host-orchestration rules
- [DOCKER.md](./DOCKER.md): Docker image, Dockerfile, and container-security rules
- [TESTING.md](./TESTING.md): test layout, deterministic testing, and coverage rules
