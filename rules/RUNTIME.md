# Runtime Rules

Use these rules for websocket handling, message execution, runtime bootstrap, engine orchestration, and telemetry paths under `src/`.

## Ownership

- Keep request parsing, websocket lifecycle, turn planning, and execution flow explicit. Do not hide runtime sequencing behind thin wrappers.
- `src/runtime` owns dependency construction and teardown, not message handlers.
- `src/execution` owns generation flow, not websocket transport concerns.
- `src/handlers/websocket` owns connection and protocol flow, not engine internals.
- `src/telemetry` owns instrumentation and exporter setup, not request shaping or business logic.

If a runtime change forces one layer to know too much about another, the code is in the wrong place.

## State and Lifetimes

- Avoid import-time runtime work.
- Keep cache resets, background daemons, and shutdown behavior explicit.
- If a runtime object is shared, make the ownership path obvious. Do not hide it behind lazy module-level singletons.
- When a websocket, stream, or task can be cancelled, trace the cleanup path before adding more work to it.

## Errors and Logging

- Runtime errors must carry operator-useful context: engine, mode, model, endpoint, or phase.
- Do not log raw prompts, auth tokens, full websocket payloads, or full environment dumps.
- If a failure changes what the client receives, update both the runtime path and the tests that lock the behavior in.

## Verification

Minimum verification for runtime changes:

```bash
nox -s lint_code
nox -s test
```

If the change touches execution flow, connection lifecycle, or telemetry wiring, also run:

```bash
nox -s coverage
```
