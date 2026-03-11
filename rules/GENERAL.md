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

- Fast lint loop: `nox -s lint_fast`
- Full lint: `nox -s lint`
- Tests: `nox -s test`
- Coverage: `nox -s coverage`
- Security: `nox -s security`
- Focused sessions: `nox -s lint_code`, `nox -s lint_shell`, `nox -s lint_docs`, `nox -s lint_docker`, `nox -s quality`, `nox -s hooks`

## Verification

Verification is required, not optional. Pick the commands that match the scope:

- Python or runtime logic: `nox -s lint_code` and `nox -s test`
- Shell, hooks, or host scripts: `nox -s lint_shell`
- Docs or rules changes: `nox -s lint_docs`
- Docker changes: `nox -s lint_docker`
- Structural or dependency hygiene work: `nox -s quality`
- Coverage and Sonar inputs: `nox -s coverage`
- Security-sensitive, dependency, Docker, or hook work: `nox -s security`

If you changed more than one area, run the full suites instead of a partial one.

## Git Hooks

Hooks live under `.githooks/`. Install them with:

```bash
bun install
bash .githooks/lib/setup.sh
```

Current hook model:

- `pre-commit`: fast repo guards, docs checks, code lint, shell lint, Docker lint, quality checks, and hook self-checks
- `commit-msg`: conventional commit validation through `gitlint`
- `pre-push`: security checks and opt-in coverage

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
- `pymarkdownlnt`, custom markdown prose rules, `codespell`, banned-term checks
- `lizard`, `deptry`, `vulture`, `jscpd`
- `bandit`, `pip-audit`, `semgrep`
- `gitleaks`, `trivy`, `bearer`, license audit, `CodeQL`, `SonarQube`

`deptry` and `vulture` are the repo's Python equivalents to Knip-style dependency and dead-code hygiene. Keep them clean instead of treating them as advisory noise.

If a tool needs a baseline or allowlist, document the reason in the baseline file. Do not hide real findings behind broad ignores.

### Trivy Pin Management

Trivy must stay version-pinned. Do not switch the repo to a floating Trivy tag.

When updating Trivy:

1. Change the version in `linting/config/security/tool-versions.env` or `linting/config/security/trivy.env`.
2. Run `bash linting/security/trivy/run.sh all`.
3. Run `nox -s security`.
4. Mention the pin change in the commit message.

### SonarQube Local Auth and Reports

Local SonarQube credentials and analysis tokens live under `.cache/security/sonarqube/`. Do not commit them.

Use one of these paths when working on Sonar-sensitive changes:

- `bash linting/security/sonarqube/run.sh`
- `RUN_SONAR=1 nox -s security`

Generated markdown reports live here:

- `.cache/security/sonarqube/sonar-report.md`
- `.cache/security/sonarqube/sonar-todos.md`

Review those files before assuming the dashboard is the only source of truth.

### Gitleaks Baseline

Gitleaks uses `linting/config/security/gitleaks/baseline.json` to suppress known intentional non-secrets and still fail on new findings.

Regenerate the baseline only when:

- a new intentional, non-secret finding is added
- Gitleaks changes fingerprint behavior and existing baseline entries stop matching

Use:

```bash
bash linting/security/gitleaks/run.sh baseline
```

Never baseline a real secret. Remove it, rotate it, and keep it out of the baseline.

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

`nox` remains the canonical Python-native command hub. Bun exists here only for the tiny remaining root JS toolchain, currently `jscpd`.

## Rule Map

Use the narrower rule file when the task is concentrated in one area:

- [SPECIFIC.md](./SPECIFIC.md): repo layout, boundaries, and inference-specific priorities
- [PYTHON.md](./PYTHON.md): Python module, config, state, and runtime rules
- [RUNTIME.md](./RUNTIME.md): websocket, execution, telemetry, and runtime orchestration rules
- [QUANTIZATION.md](./QUANTIZATION.md): quantization, metadata, licensing, and model-packaging rules
- [OPERATIONS.md](./OPERATIONS.md): scripts, hooks, scanners, deployment-side, and ops rules
- [SHELL.md](./SHELL.md): shell, hooks, and host-orchestration rules
- [DOCKER.md](./DOCKER.md): Docker image, Dockerfile, and container-security rules
- [TESTING.md](./TESTING.md): test layout, deterministic testing, and coverage rules
