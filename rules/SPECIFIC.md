# Inference Repo-Specific Rules

These rules describe how the inference project is organized and how its domain-specific subsystems work. Use them together with the [general rules](./GENERAL.md).

## Contents

- [Repo Shape](#repo-shape)
- [Architectural Boundaries](#architectural-boundaries)
- [Inference Priorities](#inference-priorities)
- [Placement and Naming](#placement-and-naming)
- [Runtime](#runtime)
- [Quantization](#quantization)
- [Testing](#testing)
- [Verification by Change Type](#verification-by-change-type)

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

## Runtime

### Ownership

- Keep request parsing, websocket lifecycle, turn planning, and execution flow explicit. Do not hide runtime sequencing behind thin wrappers.
- `src/runtime` owns dependency construction and teardown, not message handlers.
- `src/execution` owns generation flow, not websocket transport concerns.
- `src/handlers/websocket` owns connection and protocol flow, not engine internals.
- `src/telemetry` owns instrumentation and exporter setup, not request shaping or business logic.

If a runtime change forces one layer to know too much about another, the code is in the wrong place.

### State and Lifetimes

- Avoid import-time runtime work.
- Keep cache resets, background daemons, and shutdown behavior explicit.
- If a runtime object is shared, make the ownership path obvious. Do not hide it behind lazy module-level singletons.
- When a websocket, stream, or task can be cancelled, trace the cleanup path before adding more work to it.

### Errors and Logging

- Runtime errors must carry operator-useful context: engine, mode, model, endpoint, or phase.
- Do not log raw prompts, auth tokens, full websocket payloads, or full environment dumps.
- If a failure changes what the client receives, update both the runtime path and the tests that lock the behavior in.

## Quantization

### Ownership

- Keep TRT-specific behavior in `src/quantization/trt/`.
- Keep vLLM-specific behavior in `src/quantization/vllm/`.
- Keep shared quantization helpers genuinely shared. Do not move engine-specific edge cases into a fake common layer.
- Keep Docker-only quantization helpers under `docker/` and host-side orchestration under `scripts/`.

### Metadata and Packaging

- Metadata must describe what actually happened: backend, quant method, calibration inputs, runtime expectations, and source model identity.
- README or card generation must stay aligned with the metadata schema. If one changes, update the other in the same change.
- Preserve upstream license information correctly. Quantized artifacts inherit constraints from their base model; do not guess or hardcode a nicer answer.
- Treat model-card text as product output. Keep it precise and deterministic.

### Detection and Validation

- Detection code must be explicit about fallbacks and unknown states.
- If quantization detection cannot prove something, emit the conservative answer.
- Prefer additive metadata fixes over mutating hidden global state or patching values late in the pipeline.
- Keep validation and packaging steps reproducible from the checked-in scripts.

## Testing

### Layout

- Executable tests belong under `tests/suites/unit/`, `tests/suites/integration/`, or `tests/suites/e2e/`.
- Unit tests must live in a domain subfolder under `tests/suites/unit/<domain>/`.
- Test files use the `test_*.py` naming pattern.
- `tests/support/` is for helpers, canned messages, prompts, websocket payloads, and runners. It must not contain `test_*` functions.
- Keep the only `conftest.py` at `tests/conftest.py`.
- Shared config fixtures belong in `tests/config/`. Shared state builders belong in `tests/state/`.

### Writing Tests

- Ship every behavior change with a test that would fail without the change.
- For bug fixes, add a regression test that captures the old failure.
- Keep tests deterministic. Stub time, network, environment, and filesystem effects when practical.
- Prefer small, explicit helpers over magic fixtures that hide too much setup.
- Production code must never import test helpers.

### Test Support Code

- Use `tests/support/helpers/fmt.py` for CLI-style test output instead of inventing new formatting helpers.
- Keep prompts, persona variants, and large canned payloads in `tests/support/` so they can be reused across suites.
- Keep support modules importable and boring. They should help the tests, not become a second application.

### Coverage

- Coverage is measured against `src/` only.
- If you add runtime behavior in `src/`, either test it directly or explain why it is intentionally uncovered.
- Keep coverage artifacts Sonar-compatible by using the repo coverage command rather than ad hoc local commands when possible.

## Verification by Change Type

Use these minimum checks:

- runtime Python change: `nox -s lint_code` and `nox -s test`
- shell or hook change: `nox -s lint_shell`
- Docker change: `nox -s lint_docker` and `nox -s security`
- linting or hook framework change: `nox -s lint` and `nox -s security`
- docs or rules change: `nox -s lint_docs`
- coverage or Sonar change: `nox -s coverage`
- quantization or model-packaging change: `nox -s lint_code` and `nox -s test`
- test or coverage change: `python -m pytest -q` and `bash scripts/coverage.sh`

When the change spans multiple areas, run the full lint, test, coverage, and security commands.
