# Linting, Hooks, and Quality Modernization Plan

## Executive Summary

This repo is not starting from zero. It already has a stronger-than-average Python lint base:

- `ruff`, `mypy`, `import-linter`, `shellcheck`
- custom Python AST linters for file length, function length, import cycles, config purity, singleton policy, Docker ignore policy, test layout, and related structure rules

The real gaps are orchestration and coverage:

- hooks are a single monolithic pre-commit entrypoint
- there is no commit-msg hook, no pre-push hook, no shared hook runtime, and no timeout/skip-flag strategy
- no markdown linting, commit linting, typo scanning, banned-term scanning, secret scanning, dependency vulnerability scanning, Dockerfile linting, image/config scanning, or copy-paste detection
- shell linting only covers `shellcheck` and optional `shfmt`, not repo-specific shell structure rules
- no Python-native command runner that plays the role `package.json` scripts play in the Swift repo
- no dedicated `src/`-only coverage workflow that can feed SonarQube
- no SonarQube or CodeQL wrapper structure for this repo
- the `rules/` docs are much thinner than the operational guidance in `yap-swift-app`

The plan below keeps the current Python-first linting model, ports the good architecture from `yap-swift-app`, and adds Python-specific tools where they are better fits than the monorepo's TS-focused stack.

## Current State in This Repo

### Keep and Build On

- `scripts/lint.sh` already centralizes Python and shell linting
- `pyproject.toml` already contains `ruff`, `mypy`, and `import-linter` config
- `linting/` already has useful custom rules:
  - file/function length
  - import cycles
  - no lazy module loading
  - no runtime singletons
  - no inline Python in shell
  - Docker ignore policy
  - no config functions / no config cross-imports
  - test placement / naming / domain layout
  - single-file folder and prefix-collision checks

### Missing or Weak

- only `.githooks/pre-commit` exists
- no `.githooks/lib/setup.sh`, `runtime.sh`, `timeout.sh`, or hook stage split
- no `commit-msg` or `pre-push`
- no dedicated security runner
- no Dockerfile/image security scanning beyond the custom `.dockerignore` rule
- no markdown or docs linting
- no commit message validation
- no typo / banned-term / secret scanning
- no complexity scan
- no duplicate-code scan
- no hook self-linting
- no documented hook flags / staged hook strategy

## What to Reuse From `yap-swift-app`

### Port Directly or Very Closely

- `.githooks` architecture:
  - `commit-msg`, `pre-commit`, `pre-push`
  - shared `lib/config.sh`, `lib/runtime.sh`, `lib/setup.sh`, `lib/timeout.sh`
  - concern-based hook scripts instead of one giant hook
- staged hook philosophy:
  - fast checks on commit
  - heavier quality and security checks on push
  - explicit skip flags and timeouts
- `lizard` runner pattern for complexity with whitelist support
- `trivy` wrapper pattern:
  - config scan
  - filesystem scan
  - image scan with fallback behavior and timeouts
- security wrapper layout:
  - `gitleaks`
  - `CodeQL`
  - `SonarQube`
  - central install/config scripts
- markdown linting approach, including custom rules
- typo and banned-term tooling pattern
- [DONE] shared naming/limits/config pattern from `yap-swift-app/linting/config/*`
- hook self-linting concept
- richer rule-writing style for `rules/`

### Adapt, Not Copy Verbatim

- shell custom rules:
  - the Swift repo implements these in JS
  - for this repo, the concepts are good, but the implementation should likely move into Python under `linting/shell/`
- naming/config constants:
  - the Swift repo centralizes forbidden generic names, thresholds, allowlists, and scopes under `linting/config/*`
  - we should mirror that pattern in Python/TOML config rather than scattering constants through scripts
- Semgrep setup:
  - keep the wrapper pattern
  - replace TS/Express/Supabase rules with Python, Bash, and Docker-focused rules
- CPD (`jscpd`):
  - useful, but only if we accept a tiny Node toolchain for lint-only use
- commitlint and markdownlint:
  - useful and easy to reuse
  - but they introduce Node-based tooling into a Python repo

### Do Not Port Directly

- TS/ESLint plugin rules themselves
  - many map poorly to Python
  - several already have Python equivalents in this repo's custom AST linters
- Knip as-is
  - it is a TS/JS dead-export/dependency tool
  - this repo needs Python analogs instead
- iOS, Swift, Supabase SQL, Nginx, and TS boundary-specific rules
- Bun-first project structure
  - steal the lint ideas, not the monorepo's language/runtime assumptions

## Recommended Target Tooling

| Area | Tool | Recommendation | Source / analog |
| --- | --- | --- | --- |
| Python format + lint | `ruff` | Keep; expand gradually | Existing |
| Python type checking | `mypy` | Keep; tighten config in phases | Existing |
| Python architecture | `import-linter` + current custom AST rules | Keep | Existing |
| Python command runner | `nox` | Add as the Python-native script/task hub | Python-specific |
| Test runner | `pytest`, `pytest-cov` | Add explicitly to dev deps if not already pinned | Python-specific |
| Coverage reports | `coverage.py` via `pytest-cov` | Add terminal + XML reports for `src/` only | Python-specific |
| Complexity | `lizard` | Add | Port from Swift repo |
| Security SAST | `semgrep` | Add with Python/Bash/Docker rules | Port/adapt from Swift repo |
| Python security lint | `bandit` | Add | Python-specific |
| Dependency vulnerabilities | `pip-audit` | Add | Python-specific analog to OSV flow |
| Repo-wide vulnerability scan | `osv-scanner` | Add for parity with the Swift repo | Port/adapt from Swift repo |
| Dependency hygiene | `deptry` | Add | Python analog to Knip |
| Dead code / unreachable code | `vulture` | Add later, after baseline | Python-specific analog to Knip/dead-code checks |
| Duplicate code | `jscpd` or fallback alternative | Add if minimal Node toolchain is accepted | Port from Swift repo |
| Typos | `typos` | Add | Port from Swift repo |
| Banned terms | custom script + config | Add | Port concept from Swift repo |
| Commit messages | `commitlint` or `gitlint` | Add; prefer `commitlint` only if Node toolchain is accepted | Port / Python fallback |
| Markdown | `markdownlint-cli2` + custom rules, or Python fallback | Add | Port / Python fallback |
| Shell lint | `shellcheck`, `shfmt` | Keep and make mandatory | Existing + Swift repo |
| Shell custom rules | repo-local Python scripts | Add | Port concepts from Swift repo |
| Dockerfile lint | `hadolint` | Add | Same pattern used in Swift repo API |
| Container / Docker security | `trivy` | Add | Port from Swift repo |
| Secrets | `gitleaks` | Add | Port from Swift repo |
| AppSec scanner | `bearer` | Required in the target state; tune overlap with Semgrep/Bandit during rollout | Port/adapt from Swift repo |
| Deep security scan | `CodeQL` | Required | Port from Swift repo |
| Code quality dashboard | `SonarQube` | Required | Port from Swift repo |
| License audit | `pip-licenses` or similar | Add | Analog to Swift repo license checks |

## Python-Specific Tools We Should Add

These are the main additions that matter specifically for this repo, not just generic "more scanners":

- `bandit`
  - catches insecure subprocess/network/file patterns in Python code
  - useful because this repo does environment, Docker, runtime, and model orchestration work
- `pip-audit`
  - the cleanest Python-native dependency vulnerability tool for `requirements-*.txt`
  - better fit here than blindly porting the Swift repo's OSV-only flow
- `osv-scanner`
  - worth adding as a second repo-wide vulnerability lens because the Swift repo already has wrapper/install patterns for it
  - complements `pip-audit` rather than replacing it
- `deptry`
  - finds missing, transitive, and unused dependencies
  - closest Python equivalent to "dependency hygiene / Knip-like value"
- `vulture`
  - useful for dead functions, unused code paths, and stale helpers
  - should be introduced after a baseline because the initial report may be noisy
- `pytest-cov`
  - not a lint tool, but needed if push hooks or CI should enforce coverage on important suites
- `lizard`
  - supports Python and Bash, so one tool can enforce complexity across the two biggest languages in this repo
- optional later: `basedpyright` or `pyright`
  - only if we want a second type checker after the mypy baseline is healthy
  - not phase 1, because it will create significant churn

## Python-Native Replacement for `package.json` Scripts

We should add a Python-native command hub so the repo has one ergonomic way to run linting, tests, coverage, security, and Sonar flows.

### Recommended

Add `nox` with a root `noxfile.py`.

Why `nox`:

- Python-native
- easy to call from hooks and CI
- works well for lint, security, tests, and coverage
- does not require converting the repo to Poetry/PDM/Hatch
- is close enough to `package.json` scripts in practice, but better for Python repos

### Recommended Sessions

- `nox -s lint`
- `nox -s lint_fast`
- `nox -s lint_shell`
- `nox -s lint_docs`
- `nox -s lint_docker`
- `nox -s lint_security`
- `nox -s quality`
- `nox -s test`
- `nox -s coverage`
- `nox -s sonar`

### Optional Fallback

If we want even thinner aliases, add a `Makefile` or `justfile` on top of `nox`, but `nox` should remain the canonical Python-native runner.

## Bun Tooling Decision

There are two reasonable paths:

### Recommended

Add a tiny Bun-managed root `package.json` for lint-only tooling:

- `commitlint`
- `markdownlint-cli2`
- `jscpd`

This is the easiest way to directly reuse the best markdown and commit-message tooling from `yap-swift-app`.

### Fallback if We Want Zero Node in This Repo

- use `gitlint` instead of `commitlint`
- use a Python markdown linter (`pymarkdown`, `mdformat`, or a custom script set) instead of `markdownlint-cli2`
- skip `jscpd` initially or replace it with a weaker Python-native duplicate-code option

### Recommendation

Use the tiny Bun-managed toolchain and commit `bun.lock`.

- run installs with `bun install`
- run package scripts with `bun run`
- run direct binaries with `bunx`
- do not use `npm`, `npx`, or `package-lock.json` in this repo

## Hook Architecture to Implement

This repo should copy the Swift repo's staged hook design, but simplify it for a single Python project.

### Proposed Layout

```text
.githooks/
  commit-msg
  pre-commit
  pre-push
  lib/
    config.sh
    runtime.sh
    setup.sh
    timeout.sh
  hooks/
    global/
      lint.sh
      security.sh
    project/
      python.sh
      quality.sh
      shell.sh
      docs.sh
      docker.sh
      security.sh
      tests.sh
    self/
      lint.sh
      quality.sh
      security.sh
      format.sh
```

### Pre-Commit Should Stay Fast

Run only fast or changed-file checks:

- staged secret scan
- `ruff format --check` / `ruff check`
- fast custom Python lint scripts
- `shellcheck` / `shfmt -d` on touched shell files
- `hadolint` on touched Dockerfiles
- typo / banned-term checks on changed files
- markdown lint on changed docs only

Do **not** build Docker images in pre-commit.

### Commit-Msg

Add conventional commit validation:

- if Node tooling is accepted: `commitlint`
- otherwise: `gitlint`

Suggested scopes for this repo:

- `core`
- `config`
- `handlers`
- `messages`
- `tokens`
- `engines`
- `quantization`
- `docker`
- `scripts`
- `tests`
- `lint`
- `hooks`
- `docs`
- `deps`
- `rules`

### Pre-Push

Run the expensive full-repo gates:

- full lint suite
- full shell custom rules
- full docs lint suite
- full Docker lint/security stage
- `semgrep`
- `bandit`
- `pip-audit`
- `osv-scanner`
- `deptry`
- `gitleaks`
- `bearer`
- `trivy`
- `lizard`
- optional `jscpd`
- `pytest` unit coverage for `src/`
- optional focused integration test suite

`CodeQL` and `SonarQube` are required end-state gates and must be enforced in CI.

Heavy items should support skip flags and, where possible, path-based change detection:

- only run `pip-audit` when `requirements-*.txt` or dependency metadata changes
- only run `osv-scanner` when dependency metadata changes or on full security passes
- only run Docker image scans when `docker/`, Dockerfiles, or image-related scripts change
- allow `RUN_CODEQL=1` or a similar opt-in model for very heavy scans

### Recommended Hook Command Map

- `hooks/project/python.sh`
  - `ruff check`
  - `ruff format --check`
  - `mypy`
  - `import-linter`
  - existing custom Python AST linters
- `hooks/project/shell.sh`
  - `shellcheck`
  - `shfmt -d`
  - custom Python shell rules
- `hooks/project/docs.sh`
  - markdown lint
  - typos
  - banned terms
- `hooks/project/docker.sh`
  - `hadolint`
  - `trivy config`
  - `.dockerignore` policy
- `hooks/project/security.sh`
  - `semgrep`
  - `bandit`
  - `pip-audit`
  - `osv-scanner`
  - `gitleaks`
  - `bearer`
  - `CodeQL`
- `hooks/project/quality.sh`
  - `lizard`
  - `deptry`
  - `vulture`
  - optional `jscpd`
- `hooks/project/tests.sh`
  - unit tests
  - unit coverage for `src/`

## Custom Rules to Add or Port

### Python / Architecture

Keep the current AST rule set and add only the missing pieces that are genuinely useful:

- explicit "no `print()` outside tests and CLI scripts"
- explicit "no `subprocess.*(..., shell=True)` without justification"
- explicit "no environment mutation outside approved initialization paths"
- explicit "no generic module names like `helpers`, `utils`, `misc`, `temp`, `tmp` in `src/`, `tests/`, `docker/`, or `scripts/` unless allowlisted"
- explicit "no generic function names like `helper`, `util`, `process_data`, `handle_data`, or `do_stuff` in production code" via a configurable banned-name list
- explicit "requirements and lint/security tooling must be pinned to exact versions"
- explicit "lint allowlists and baseline paths referenced by config must exist"
- optional Semgrep rules for:
  - import-time side effects
  - production code importing from `tests`
  - network or filesystem access in config modules
  - dangerous subprocess usage
  - `eval` / `exec`
  - broad exception swallowing in runtime-critical modules

Many TS custom rules from the Swift repo are already conceptually covered here by:

- `no_runtime_singletons.py`
- `no_config_functions.py`
- `no_config_cross_imports.py`
- `single_file_folders.py`
- `prefix_collisions.py`
- `file_length.py`
- `function_length.py`

### Naming and Keyword Policy Worth Adapting From the Swift Repo

The Swift repo's `linting/config/naming.js` is worth translating into Python/TOML config and enforcing with repo-local Python linters.

Rules to add:

- forbid files or directories named:
  - `helpers`
  - `utils`
  - `misc`
  - `temp`
  - `tmp`
- forbid filename suffixes/prefixes like:
  - `_helpers`
  - `_utils`
  - `helpers_`
  - `utils_`
- keep allowlists for legitimate exceptions
- [DONE] keep thresholds/config in one shared config file rather than scattering them through scripts

This should apply to:

- `src/`
- `tests/`
- `docker/`
- `scripts/`
- future `linting/` helpers

This is one of the cleanest "direct ideas" to take from the Swift repo because it translates well across languages.

### Shell

Port these concepts from the Swift repo and implement them in Python under `linting/shell/`:

- shellcheck-disable justification required
- function doc comments required for shared shell libs
- file/function line limits for shell
- dead / unused shell function detection
- config default expansions allowed only in central config files
- generic shell filename and directory naming bans where they make sense
- shell directory structure checks

Repo-specific shell rules worth adding here:

- all shell entrypoints require shebang + `set -euo pipefail`
- top-level scripts must source common logging / config helpers instead of redefining them
- inline Python remains forbidden except for tightly approved cases
- sourced config defaults like `${VAR:-default}` should only appear in central config/default files
- multi-line SSH/docker command blocks should live in named functions, not raw top-level script bodies

### Markdown and Docs

Port these first:

- banned terms rule
- heading title case rule

Evaluate separately before enabling:

- "no double hyphen" prose rule
  - useful in polished docs
  - lower priority and easier to disagree with

Also add:

- docs link validation, if the repo's doc surface keeps growing
- explicit markdown exclusions for generated templates or model prompt artifacts

### Docker

Add:

- `hadolint` for every Dockerfile
- `trivy config` for Dockerfiles and Docker-related config
- `trivy fs` on the repo or Docker directories
- `trivy image` for built images with timeout and fallback behavior
- existing `.dockerignore` policy stays in place and becomes part of the Docker stage

Later additions worth considering:

- `container-structure-test` for runtime image validation
- `syft` + `grype` if SBOM generation becomes a requirement

## What Not to Copy Blindly

- do not port the Swift repo's multi-project hook tree one-for-one
  - this repo is a single project
  - one `project/` hook group is cleaner than fake `api/`, `ios/`, `supabase/` buckets
- do not port TS ESLint rules that overlap current Python custom AST rules
- do not add Bun as a required repo runtime just because the other repo uses it
- do not turn pre-commit into a 10-minute hook
- do not enable every new scanner as blocking on day 1
- do not replace Python-native tooling with Node tooling when there is already a good Python equivalent

## Baseline and Rollout Strategy

Several of these tools will be noisy if enabled immediately. The rollout should be staged.

### Phase 0 - Inventory and Baseline [DONE]

- [DONE] record current `scripts/lint.sh` behavior and custom rule coverage
- [DONE] choose the Node-tooling decision
- [DONE] choose the Python-native command hub (`nox`)
- [DONE] generate initial reports for:
  - `lizard`
  - `semgrep`
  - `bandit`
  - `osv-scanner`
  - `deptry`
  - `vulture`
  - `gitleaks`
  - `trivy`
  - optional `jscpd`
- [DONE] create ignore/baseline files where needed:
  - `.trivyignore`
  - `.semgrepignore`
  - gitleaks baseline/config
  - `.whitelizard`
  - `typos.toml`
  - `deptry.toml`
  - `bandit.yaml`
  - SonarQube config / exclusions

### Phase 1 - Normalize Commands and Dependencies [DONE]

- [DONE] split `scripts/lint.sh` into logical stages behind one public entrypoint
- [DONE] add `noxfile.py` as the canonical command runner
- [DONE] add explicit commands/stages for:
  - `code`
  - `shell`
  - `docs`
  - `docker`
  - `quality`
  - `security`
  - `hooks`
- [DONE] pin new Python tools in dev requirements
- [DONE] add minimal Node lint package only if approved
- [DONE] add coverage commands that target `src/` only

### Phase 2 - Rebuild Git Hooks [DONE]

- [DONE] add `.githooks/lib/setup.sh`
- [DONE] add `commit-msg` and `pre-push`
- [DONE] replace the current monolithic hook flow with staged concern scripts
- [DONE] document skip flags and timeouts
- [DONE] add hook self-linting once the hook tree exists

### Phase 3 - Quality and Security Hardening [DONE]

- [DONE] enable `lizard`
- [DONE] enable `semgrep`
- [DONE] enable `bandit`
- [DONE] enable `pip-audit`
- [DONE] enable `osv-scanner`
- [DONE] enable `deptry`
- [DONE] enable `gitleaks`
- [DONE] enable `hadolint`
- [DONE] enable `trivy`
- [DONE] enable markdown and typo linting
- [DONE] introduce CPD only after reviewing baseline noise
- [DONE] enable SonarQube scan and make it blocking once coverage and exclusions are stable

### Phase 4 - Rule Docs Modernization [DONE]

Apply the strongest lessons from the Swift repo's `rules/` docs:

- [DONE] expand `rules/GENERAL.md` with:
  - development workflow
  - lint/security expectations
  - hook behavior and flags
  - scope discipline
  - verification checklists
- [DONE] add focused rule docs only where they map to real tooling:
  - `rules/PYTHON.md`
  - `rules/SHELL.md`
  - `rules/DOCKER.md`
  - `rules/TESTING.md`
- [DONE] keep the docs operational, not aspirational
  - every rule should map to an implemented command, a real checker, or a clear review expectation

### Phase 5 - Required Heavy Scans and CI Gates [DONE]

- [DONE] required `CodeQL`
- [DONE] required `SonarQube`
- [DONE] required `bearer`
- [DONE] required coverage gate for unit coverage on `src/`
- optional image-behavior tests

These should land after the local developer loop is healthy, not before.

Because `CodeQL` is required, plan for:

- [DONE] `linting/security/codeql/run.sh`
- [DONE] `linting/security/codeql/scan.sh`
- [DONE] `linting/codeql/config.yml` or equivalent root CodeQL config

### Phase 6 - SonarQube and Coverage Parity [DONE]

Replicate the useful parts of the Swift repo's SonarQube setup, adapted for a single Python project.

Add:

- [DONE] root `sonar-project.properties`
- [DONE] `scripts/coverage.sh` or `nox -s coverage`
- [DONE] coverage output focused on `src/` only:
  - `coverage.xml`
  - `pytest.xml`
  - terminal summary
- [DONE] Sonar properties for:
  - source roots
  - test roots
  - exclusions
  - coverage report path
  - xUnit report path if generated

Required wrapper structure to plan for:

- [DONE] `linting/security/sonarqube/run.sh`
- [DONE] `linting/security/sonarqube/server.sh`
- [DONE] `linting/security/sonarqube/scan.sh`
- [DONE] `linting/security/sonarqube/collect.sh`

This repo does not need the Swift monorepo's multi-project complexity, but it does benefit from the same wrapper structure.

## Important Repo-Specific Caveats

- `tests/support/messages/**` and `tests/support/prompts/**` contain intentional slang, typos, and odd phrasing
  - typo and banned-term rules must support exclusions or allowlists
- shell scripts are a major part of this repo
  - shell custom rules are not optional if we want real quality gains
- Docker is first-class here
  - Docker lint/security checks should be a real stage, not an afterthought
- existing custom Python lint rules are valuable
  - this effort should wrap and extend them, not replace them with generic off-the-shelf tools
- coverage should target `src/`, not inflate itself with `tests/` or helper-only files
- SonarQube will only be useful if exclusions and coverage scope are kept tight

## Recommended "Take" Vs "Skip" Summary

### Definitely Take From `yap-swift-app`

- hook runtime architecture
- staged pre-commit / commit-msg / pre-push model
- timeout and skip-flag discipline
- `lizard`
- `trivy` wrapper design
- security wrapper layout
- `osv-scanner` wrapper idea
- SonarQube wrapper structure
- [DONE] naming/config constants pattern
- markdownlint custom-rule approach
- typo / banned-term scanning
- hook self-linting idea
- richer rule-writing style for `rules/`

### Take the Concept, but Implement it Differently Here

- shell custom rules
- Semgrep custom rules
- CPD
- commit linting if we choose a Python-native fallback
- package integrity concepts, translated to `pyproject.toml` / `requirements*.txt`

### Do Not Bother Porting

- TS ESLint plugin rule implementations
- Knip itself
- iOS / Swift / Supabase / Nginx specific checks
- Bun-specific repo assumptions

## Success Criteria

This plan is complete when the repo has:

- [DONE] a staged hook system with `setup.sh`, `pre-commit`, `commit-msg`, and `pre-push`
- [DONE] a Python-native command runner (`noxfile.py`) acting as the repo's script hub
- [DONE] a single public lint entrypoint with sub-stages
- [DONE] mandatory shell, Docker, markdown, and security linting
- [DONE] Python-specific dependency/security/dead-code tooling
- [DONE] exact-version and config-integrity checks for Python tooling metadata
- [DONE] coverage generation for `src/` only
- [DONE] SonarQube-compatible scan inputs
- [DONE] required `CodeQL`, `SonarQube`, and `bearer` integration
- documented rule files that explain how the tooling is supposed to be used
- [DONE] baseline/ignore files for the scanners that need them
- [DONE] a fast default local loop and a heavier push/CI loop

## Recommended Implementation Order

1. [DONE] Keep current Python custom linting exactly as the foundation.
2. [DONE] Add hook architecture from the Swift repo.
3. [DONE] Add `noxfile.py` as the Python-native command hub.
4. [DONE] Add Python-native quality/security tools (`bandit`, `pip-audit`, `osv-scanner`, `deptry`, `lizard`).
5. [DONE] Add shell custom rules, naming/keyword rules, and Docker checks.
6. [DONE] Add markdown, commit, typo, banned-term, secret scanning, and exact-version/config-integrity checks.
7. [DONE] Add `src/`-only coverage and SonarQube inputs.
8. [DONE] Add optional Node-only extras (`jscpd`) if the team is comfortable with the tiny package toolchain.
9. [DONE] Add required CI enforcement for `CodeQL`, `SonarQube`, `bearer`, and coverage gating.
