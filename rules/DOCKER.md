# Docker Rules

Use these rules for everything under `docker/` and for Docker-related lint or security tooling.

## Layout

- Keep shared image logic in `docker/common/`.
- Keep image-specific logic inside the image directory that owns it, such as `docker/trt/`, `docker/vllm/`, or `docker/tool/`.
- Each image directory must keep its own README current.
- Keep Docker-only Python helpers in `docker/`, not in `src/`.

## Dockerfiles

- Keep Dockerfiles focused on package installation, file copies, and entrypoint wiring.
- Move non-trivial logic into scripts or Python helpers and call them from the Dockerfile.
- Use non-root runtime users unless there is a documented reason not to.
- Use `--no-install-recommends` for `apt-get install` unless there is a real reason to pull recommended packages.
- Keep layers intentional and avoid hidden build-time side effects.

## Policy

- Use per-image `.dockerignore` files only. Do not add a root `.dockerignore`.
- Do not duplicate the same download or setup flow across multiple image directories. Shared logic belongs in `docker/common/`.
- Treat Docker changes as runtime behavior changes. If a Dockerfile affects startup, environment, ports, users, or mounted paths, update the corresponding README and verification steps.

## Security

- Docker changes must pass Hadolint and Trivy.
- Do not bake secrets into images, Dockerfiles, or example commands.
- Keep package versions pinned through the repo's normal dependency files or explicit Dockerfile arguments when needed.

## Verification

Minimum verification for Docker changes:

```bash
bash scripts/lint.sh --only docker
bash scripts/security.sh
```
