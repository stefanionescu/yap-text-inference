# Operations Rules

Use these rules for host scripts, hook orchestration, local scanners, coverage generation, and other operator-facing workflows.

## Command Ownership

- Keep orchestration in `scripts/` and `.githooks/`.
- Keep scanner wrappers in `linting/security/`.
- Keep repo policy and scanner configuration in `linting/config/`.
- Keep Docker build/runtime concerns in `docker/`.

Do not bury operational behavior inside random Python modules under `src/` when the change is really a host or CI-style concern.

## Operational Discipline

- Destructive behavior must be obvious from the script name and output.
- Environment defaults should come from config files or a single local config block, not scattered literals.
- Wrapper scripts should explain what they run and why they failed. Buffered error output is preferred over noisy streaming logs.
- If a security tool supports a baseline or ignore file, keep the scope narrow and document the reason.

## Security and Quality Gates

- `scripts/security.sh` is the canonical full local security gate.
- `scripts/coverage.sh` is the canonical Sonar-compatible coverage and test-report generator.
- Hook stages must stay intentionally split: fast checks in `pre-commit`, heavier scans in `pre-push`.
- Repo-local fallback installers or Dockerized scanners must stay version-pinned through config.

## Verification

Minimum verification for ops, hook, or scanner changes:

```bash
bash scripts/lint.sh
bash scripts/security.sh
```

If the change affects coverage artifacts or Sonar inputs, also run:

```bash
bash scripts/coverage.sh
```
