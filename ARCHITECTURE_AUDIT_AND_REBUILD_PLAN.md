# Architecture Audit and Rebuild Plan

This note captures what I would still change if we were rebuilding the server architecture from zero for stronger security, correctness, and contributor maintainability.

Date: March 6, 2026.

## Executive Summary

The codebase is in a much better shape after the recent cleanup, but I would still make several hard-cut changes:

1. Replace permissive dictionary-based WebSocket payload handling with strict typed contracts and explicit protocol versioning.
2. Harden authentication (header-only keys, constant-time compare, failed-auth throttling, origin checks).
3. Move to a true session state machine with serialized state transitions (instead of ad hoc mutable field updates across async tasks).
4. Remove remaining process-global registries from runtime paths and rely on dependency injection only.
5. Fix telemetry correctness gaps (request spans are defined but not used; completion metrics are char-approximated, not token-accurate).
6. Split large multi-responsibility modules into smaller focused units to reduce cognitive load and review risk.

The plan below assumes no compatibility shims and no dual implementations.

## Priority 0: Security and Correctness

### 1) Authentication hardening

Current behavior allows API keys in both headers and query parameters, and key validation is direct string equality.

Risks:
- Query-param keys can leak in reverse proxy/access logs and client telemetry.
- Direct equality is not constant-time.
- Auth failures are not separately rate-limited by client identity.

Hard-cut fix:
- Accept API keys only in one header (`X-API-Key` or `Authorization: Bearer`).
- Use constant-time comparison (`hmac.compare_digest`).
- Add failed-auth throttling keyed by client IP (and optionally key ID).
- Enforce an explicit WebSocket `Origin` allowlist for browser clients.

### 2) Strict inbound protocol contracts + payload ceilings

Current message parsing accepts generic JSON objects and then does field-level checks in handlers.

Risks:
- Unknown keys are silently accepted, which hides client bugs.
- No top-level raw payload size ceiling at parser/transport boundary.
- Very large `history` payloads can burn CPU/memory before trimming logic runs.

Hard-cut fix:
- Define typed message contracts (`start`, `message`, `cancel`, control frames) with `extra=forbid`.
- Require protocol version in each client message.
- Add hard ceilings:
  - max raw WebSocket message bytes
  - max `history` item count
  - max per-item char length
  - max total chars across history payload
- Reject invalid/oversized payloads at the parser boundary.

### 3) Session state transition model

Current state is mutable and touched from both the receive loop and background execution tasks.

Risks:
- Interleavings between cancel/supersede/disconnect can still create subtle logic races.
- Field-level writes are easy to duplicate incorrectly.

Hard-cut fix:
- Introduce explicit session/request lifecycle states (`idle`, `running`, `cancelling`, `closed`).
- Route all state transitions through one transition service.
- Protect state mutations with a per-session async lock.
- Keep transition methods as the only write path for request/task/cancel fields.

### 4) Exception handling policy in request path

The runtime includes multiple broad `except Exception` and `suppress(Exception)` blocks.

Risks:
- Hidden failures during cleanup/send paths reduce debuggability.
- Hard to distinguish expected disconnects from real defects.

Hard-cut fix:
- Suppress only explicitly-classified transport disconnect exceptions.
- For all other exceptions: structured logging + telemetry + re-raise (or typed conversion).
- Keep defensive suppression limited to shutdown/best-effort cleanup only.

## Priority 1: Architecture and Maintainability

### 5) Remove remaining global runtime registries from core flow

The runtime still exposes process-global registries for tokenizers, tool adapter, and engine runtime.

Risks:
- Hidden dependencies and non-obvious coupling.
- More fragile tests and harder local reasoning.

Hard-cut fix:
- Make runtime dependencies explicit in constructors/function parameters.
- Keep a single startup container that wires dependencies once.
- Remove public getter APIs that return global mutable runtime objects.

### 6) Split large modules by single responsibility

A few modules still combine multiple concerns and exceed the intended file size envelope.

Hard-cut fix:
- Break history management into separate concerns:
  - parsing
  - rendering
  - chat trimming policy
  - tool trimming policy
  - mutation operations
- Separate WebSocket loop responsibilities into:
  - parser/validator
  - command router
  - lifecycle and teardown

### 7) Unify turn handling pipeline

`start` and `message` flows still share similar orchestration patterns with separate code paths.

Hard-cut fix:
- Introduce one `TurnPlan` builder path with strict inputs.
- Keep `start`-only concerns (persona/prompt initialization) as a small pre-step.
- Execute both through one `TurnExecutor` contract.

## Priority 2: Telemetry and Operability

### 8) Make request tracing complete and correlated

Request-level span helper exists but is not wired into runtime turn handling.

Hard-cut fix:
- Create a request span for every `start`/`message` turn.
- Inject request/session/client IDs into logs and tracing attributes consistently.
- Record structured error class and phase (`parse`, `validate`, `tool`, `chat`, `send`, `cleanup`).

### 9) Fix metric semantics

Some generation metrics currently approximate tokens from character length.

Hard-cut fix:
- Count completion tokens with model tokenizer, not char heuristics.
- Keep separate latency metrics for:
  - tool classification latency
  - prompt build latency
  - chat generation latency
  - websocket send latency
- Add counters for client-disconnect-mid-stream, cancel-pre-first-token, empty-model-output, and retryable engine aborts.

### 10) Test ergonomics and telemetry isolation

Tests can still emit noisy telemetry/exporter errors depending on environment.

Hard-cut fix:
- Force telemetry off in test bootstrap unless a dedicated telemetry test marker is used.
- Keep deterministic telemetry fixtures for unit/integration tests.

## Priority 3: Configuration Model

### 11) Replace distributed import-time config resolution with one typed settings object

Current config is spread across many modules with import-time derived values.

Risks:
- Import order sensitivity.
- Hard to know the effective runtime configuration.
- Harder to test specific configurations in isolation.

Hard-cut fix:
- Build one immutable `Settings` object at startup.
- Move derivation/validation into explicit resolver functions.
- Forbid filesystem reads during config module import.
- Pass settings explicitly into factories/handlers.

## Target Package Shape (From-Zero Build)

I would structure runtime code by layer, not by transport message names:

- `transport`: websocket parser, protocol contracts, auth, outbound framing
- `application`: use-cases (`StartSession`, `HandleTurn`, `CancelTurn`, `CloseSession`)
- `domain`: session state machine, history policy, sampling policy, tool decision policy
- `infrastructure`: engines, tokenizers, model adapters, external service clients
- `observability`: metrics, traces, error reporting, correlation context
- `bootstrap`: startup wiring and dependency container

This layout makes boundaries obvious and keeps business logic independent from framework details.

## Execution Plan (No Shims)

### Phase 1: Protocol + Auth Hard Cut
- Ship strict typed message contracts, size limits, and version field.
- Remove query-param API key support.
- Enforce constant-time key compare and auth throttling.

### Phase 2: State Machine + Concurrency Hardening
- Introduce locked state transitions and request lifecycle states.
- Move all request/task writes behind one transition API.

### Phase 3: Runtime Dependency Purification
- Remove global registry getters from runtime path.
- Complete dependency-injection wiring via startup container.

### Phase 4: Observability Corrections
- Wire request spans end-to-end.
- Switch completion metrics to tokenizer-accurate counts.
- Add phase-specific error and latency metrics.

### Phase 5: Module Decomposition
- Split large multi-concern modules into focused units.
- Unify `start` and `message` execution pipeline via one turn planner/executor.

## Done Criteria

The rebuild is complete when:

1. Every client message is schema-validated with strict unknown-field rejection.
2. Auth accepts header-only keys with constant-time comparison and failed-auth throttling.
3. Session/request lifecycle is enforced by a single transition model.
4. No core runtime path depends on process-global registries.
5. Request-level tracing is present for every turn, with correlated logs and accurate token metrics.
6. Module responsibilities are small, explicit, and easy to test in isolation.

