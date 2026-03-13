# How to Work in This Repo

These rules apply across the inference repository. Start here, then see [SPECIFIC.md](./SPECIFIC.md) for inference-specific layout, boundaries, and domain rules.

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
- [Python](#python)
- [Shell](#shell)
- [Docker](#docker)
- [Operations](#operations)

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

## Python

### Module Design

- Start each module with a short docstring that says what the module owns.
- Keep files below the repo policy limits. Split before a file approaches 300 lines or a function approaches 60 lines.
- Prefer one stateful class per file. If a second class appears, confirm the file still has a single responsibility.
- Keep constants, dataclasses, TypedDicts, and error imports near the top of the module.
- Define `__all__` only when it adds value, and keep it at the bottom of the file.

### Imports and Boundaries

- Do not import from `tests` in production code.
- Keep imports acyclic. If a new import creates a cycle, extract a shared type or helper into the correct lower layer.
- `src/scripts` must compose through public APIs and must not import `src.engines` directly.
- `src/engines` must not import `src.handlers`.
- `src/config` must stay pure and must not reach into runtime orchestration packages.
- `src/runtime` and `src.handlers.session` have extra isolation rules. Respect them instead of routing around them.

If you are tempted to cross one of these boundaries, the ownership is probably wrong.

### Config, State, and Errors

- `src/config` exports constants, dataclasses, and resolved values only. No I/O, no environment mutation, no hidden runtime work.
- Put shared runtime shapes in `src/state`. Reuse them instead of redefining dictionaries ad hoc.
- Put runtime exceptions in `src/errors` and re-export public ones from `src/errors/__init__.py`.
- Keep state construction explicit. When a snapshot changes, build a new value instead of mutating a widely shared object in place.

### Runtime Safety

- Do not perform work at import time.
- Do not use lazy singleton patterns, module-level instance caches, or wrapper functions that hide shared global state.
- Do not use `print` for runtime diagnostics. Use a module logger.
- Do not use `subprocess` with `shell=True`.
- Do not silence exceptions with empty `except` blocks. Either add context and re-raise or convert to a typed error.
- Keep external I/O boundaries explicit and well-logged.

### Naming and Structure

- Use descriptive names. Generic names like `helpers`, `utils`, `misc`, `temp`, `helper`, or `process_data` are rejected outside allowlisted paths.
- Keep public APIs narrow. Avoid wrapper functions that add no value.
- Remove dead parameters, dead branches, and old compatibility shims instead of leaving them behind.
- Prefer explicit dependency injection over reaching into module globals.

## Shell

### Entrypoints

- Every executable shell entrypoint must start with `#!/usr/bin/env bash`.
- Every executable shell entrypoint must enable `set -euo pipefail` near the top.
- Keep shared library code in `scripts/lib/` or the local image script directory instead of duplicating blocks inline.
- Treat hook scripts and security wrappers as production code. They are gates for the repo.

### Structure

- Keep shell files under the repo shell file limit of 300 lines.
- Keep functions under the repo shell function limit of 100 lines.
- Add a one-line doc comment above non-trivial functions in hooks and security wrappers.
- If you disable a ShellCheck rule in hooks or security scripts, justify it on the same line.
- Prefer arrays, quoted variables, and small helper functions over string-built command lines.

### Safety

- Avoid `eval`.
- Do not embed inline Python in shell. Move non-trivial parsing or business logic into Python modules and call them from the shell layer.
- Keep configuration defaults centralized in `scripts/config/` or a local readonly config block, not spread across multiple scripts.
- Make destructive operations explicit and visible. Do not hide them behind vague function names.
- When a shell workflow becomes stateful or heavily conditional, move the complex logic into Python and keep shell as orchestration only.

### Hooks

- `pre-commit` should stay fast.
- `pre-push` is allowed to be heavier, but it still needs clear output and bounded scope.
- Skip flags exist for emergencies, not for normal development.
- Hook self-checks are part of the standard lint flow. Do not leave `.githooks/` exempt from the same standards the repo applies elsewhere.

## Docker

### Layout

- Keep shared image logic in `docker/common/`.
- Keep image-specific logic inside the image directory that owns it, such as `docker/trt/`, `docker/vllm/`, or `docker/tool/`.
- Each image directory must keep its own README current.
- Keep Docker-only Python helpers in `docker/`, not in `src/`.

### Dockerfiles

- Keep Dockerfiles focused on package installation, file copies, and entrypoint wiring.
- Move non-trivial logic into scripts or Python helpers and call them from the Dockerfile.
- Use non-root runtime users unless there is a documented reason not to.
- Use `--no-install-recommends` for `apt-get install` unless there is a real reason to pull recommended packages.
- Keep layers intentional and avoid hidden build-time side effects.

### Policy

- Use per-image `.dockerignore` files only. Do not add a root `.dockerignore`.
- Do not duplicate the same download or setup flow across multiple image directories. Shared logic belongs in `docker/common/`.
- Treat Docker changes as runtime behavior changes. If a Dockerfile affects startup, environment, ports, users, or mounted paths, update the corresponding README and verification steps.

### Security

- Docker changes must pass Hadolint and Trivy.
- Do not bake secrets into images, Dockerfiles, or example commands.
- Keep package versions pinned through the repo's normal dependency files or explicit Dockerfile arguments when needed.

## Operations

### Command Ownership

- Keep orchestration in `scripts/` and `.githooks/`.
- Keep scanner wrappers in `linting/security/`.
- Keep repo policy and scanner configuration in `linting/config/`.
- Keep Docker build/runtime concerns in `docker/`.

Do not bury operational behavior inside random Python modules under `src/` when the change is really a host or CI-style concern.

### Operational Discipline

- Destructive behavior must be obvious from the script name and output.
- Environment defaults should come from config files or a single local config block, not scattered literals.
- Wrapper scripts should explain what they run and why they failed. Buffered error output is preferred over noisy streaming logs.
- If a security tool supports a baseline or ignore file, keep the scope narrow and document the reason.

### Security and Quality Gates

- `nox -s security` is the canonical full local security gate.
- `nox -s coverage` is the canonical Sonar-compatible coverage and test-report generator.
- `linting/security/sonarqube/run.sh` must leave behind `.cache/security/sonarqube/sonar-report.md` and `.cache/security/sonarqube/sonar-todos.md`.
- Hook stages must stay intentionally split: fast checks in `pre-commit`, heavier scans in `pre-push`.
- Repo-local fallback installers or Dockerized scanners must stay version-pinned through config.
- Gitleaks baseline updates must go through `bash linting/security/gitleaks/run.sh baseline`, not ad hoc JSON edits.
- Trivy version bumps must update config pins first, then rerun the full security gate.
