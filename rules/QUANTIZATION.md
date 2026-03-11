# Quantization Rules

Use these rules for `src/quantization/`, Hugging Face packaging helpers, quantization scripts, and model metadata generation.

## Ownership

- Keep TRT-specific behavior in `src/quantization/trt/`.
- Keep vLLM-specific behavior in `src/quantization/vllm/`.
- Keep shared quantization helpers genuinely shared. Do not move engine-specific edge cases into a fake common layer.
- Keep Docker-only quantization helpers under `docker/` and host-side orchestration under `scripts/`.

## Metadata and Packaging

- Metadata must describe what actually happened: backend, quant method, calibration inputs, runtime expectations, and source model identity.
- README or card generation must stay aligned with the metadata schema. If one changes, update the other in the same change.
- Preserve upstream license information correctly. Quantized artifacts inherit constraints from their base model; do not guess or hardcode a nicer answer.
- Treat model-card text as product output. Keep it precise and deterministic.

## Detection and Validation

- Detection code must be explicit about fallbacks and unknown states.
- If quantization detection cannot prove something, emit the conservative answer.
- Prefer additive metadata fixes over mutating hidden global state or patching values late in the pipeline.
- Keep validation and packaging steps reproducible from the checked-in scripts.

## Verification

Minimum verification for quantization or model-packaging changes:

```bash
nox -s lint_code
nox -s test
```

If the change touches Docker packaging, dependency resolution, or generated metadata consumed by scanners, also run:

```bash
nox -s security
```
