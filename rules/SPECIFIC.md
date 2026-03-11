# Inference Repo-Specific Rules

These rules describe how the inference project is organized. Use them together with the general rules.

## Contents

- [Repo Shape](#repo-shape)
- [Architectural Boundaries](#architectural-boundaries)
- [Inference Priorities](#inference-priorities)
- [Placement and Naming](#placement-and-naming)
- [Verification by Change Type](#verification-by-change-type)
- [Rule Map](#rule-map)

## Repo Shape

The repository is split by responsibility:

- `src/`: production runtime Python code
- `scripts/`: host-side shell orchestration and operational entrypoints
- `docker/`: image-specific Dockerfiles, scripts, and Docker-only Python helpers
- `linting/`: repo-local policy, wrappers, and custom lint rules
- `.githooks/`: staged hook runtime
- `tests/suites/`: executable unit, integration, and end-to-end tests
- `tests/support/`, `tests/config/`, `tests/state/`: test support modules, fixtures, and shared state builders

Keep logic in the layer that owns it. Do not move Docker-only or host-only behavior into `src/` just because it is written in Python.

## Architectural Boundaries

These boundaries matter and are enforced by custom lint rules or `import-linter`:

- production code must never import from `tests`
- `src/config` stays pure and must not import `src.state`, `src.handlers`, `src.execution`, `src.server`, or `src.scripts`
- `src/engines` must not import `src.handlers`
- `src/scripts` must not import `src.engines` directly
- `src.handlers.session` must not import the websocket stack, message stack, runtime bootstrap, or server layer
- `src/runtime` must not import the websocket stack
- `src/state` must not depend on the Hugging Face push modules

If a change pressures one of these boundaries, that is a design signal. Move the ownership instead of breaking the boundary.

## Inference Priorities

This repo is operational code, not just library code. Favor explicitness over cleverness:

- bootstrap and teardown should be explicit
- model, tokenizer, websocket, and quantization flows must expose real failure modes
- config resolution must be visible, testable, and side-effect free at import time
- runtime code must not hide global state behind lazy singletons
- logs should help operators answer what model, engine, mode, or endpoint failed without exposing secrets

Assume that shell scripts, Dockerfiles, and Python entrypoints are all part of the same production system. Treat them with the same rigor.

## Placement and Naming

Naming rules are intentionally strict:

- do not add files, folders, or functions named `helpers`, `utils`, `misc`, `temp`, or `tmp` outside the allowlisted shared locations
- use `src/helpers` only for genuinely cross-cutting runtime helpers
- keep engine-specific code inside the engine or quantization area that owns it
- keep Docker-only Python code under `docker/`
- keep prompt fixtures, websocket payloads, canned conversations, and persona data under `tests/support/`

Prefer extending an existing module over creating another shallow wrapper layer.

## Verification by Change Type

Use these minimum checks:

- runtime Python change: `bash scripts/lint.sh --only code` and `python -m pytest -q`
- shell or hook change: `bash scripts/lint.sh --only shell`
- Docker change: `bash scripts/lint.sh --only docker` and `bash scripts/security.sh`
- linting or hook framework change: `bash scripts/lint.sh` and `bash scripts/security.sh`
- docs or rules change: `bash scripts/lint.sh --only docs`
- coverage or Sonar change: `bash scripts/coverage.sh`

When the change spans multiple areas, run the full lint, test, coverage, and security commands.

## Rule Map

- [PYTHON.md](./PYTHON.md) for `src/` and Python under `docker/` or `linting/`
- [SHELL.md](./SHELL.md) for `.githooks/`, `scripts/`, and executable shell
- [DOCKER.md](./DOCKER.md) for image layout, Dockerfiles, and Trivy or Hadolint expectations
- [TESTING.md](./TESTING.md) for suite layout, support code, and coverage
