# Repo-Specific Guidelines

Expectations tailored to this repository’s layout and inference workflows. Use these rules when placing code or assets within this project.

## Configuration and parameters
- Avoid inline magic values; store configuration knobs in the `config/` directory. Reuse an existing module when possible before adding new ones.

## Directories and code reuse
- Keep code DRY; prefer reusing existing helpers over duplicating logic.
- Reserve `helpers/` for utilities that make sense across execution engines and other subdirectories.
- Keep execution- or engine-specific logic inside `execution/` and `engines/` respectively.
- Place all token-related utilities and tokenizer interactions under `tokens/`.
- Avoid subdirectories that contain a single file unless further splits are imminent. Otherwise, move logic into a better-suited location and remove the extra folder.
- When refactoring large files into related modules, group them under a shared subdirectory to keep organization clear.

## Scripts
- Place Python helpers that power CLI scripts under `src/scripts`, organized by category directories when useful.
- Keep Docker-related Python logic inside the relevant `docker/` subdirectory for each image rather than under `src/scripts`.

## Docker
- Keep Python logic used by Docker assets inside clearly named directories under `docker/` so it stays separate from shell drivers.
- Factor out logic shared by multiple Docker images (e.g., TRT and VLLM) into a common subdirectory; keep image-specific scripts and helpers inside that image’s folder.
- Each Docker image directory must include its own README explaining how to build and run it; the root `docker/README.md` should cover overall layout and entry points.
- Keep Dockerfiles focused on setup steps; move non-trivial logic into scripts or Python files and invoke them from the Dockerfile.

