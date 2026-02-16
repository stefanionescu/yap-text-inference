"""GPU observable gauges (multi-device) for OpenTelemetry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter, Observation

from ..config.telemetry import (
    METRIC_GPU_MEMORY_FREE,
    METRIC_GPU_MEMORY_USED,
    METRIC_GPU_UTILIZATION,
    METRIC_GPU_MEMORY_TOTAL,
)

logger = logging.getLogger(__name__)


def _read_gpu_memory_used() -> list[Observation]:
    return _read_gpu_metric("memory_allocated")


def _read_gpu_memory_free() -> list[Observation]:
    return _read_gpu_metric("memory_free")


def _read_gpu_memory_total() -> list[Observation]:
    return _read_gpu_metric("memory_total")


def _read_gpu_utilization() -> list[Observation]:
    return _read_gpu_metric("utilization")


def _read_gpu_metric(kind: str) -> list[Observation]:
    from opentelemetry.metrics import Observation

    try:
        import torch

        if not torch.cuda.is_available():
            return []
    except Exception:  # noqa: BLE001
        return []

    observations: list[Observation] = []
    for i in range(torch.cuda.device_count()):
        attrs = {"gpu.device.id": str(i)}
        if kind == "memory_allocated":
            observations.append(Observation(torch.cuda.memory_allocated(i), attrs))
        elif kind == "memory_free":
            free = torch.cuda.get_device_properties(i).total_mem - torch.cuda.memory_allocated(i)
            observations.append(Observation(free, attrs))
        elif kind == "memory_total":
            observations.append(Observation(torch.cuda.get_device_properties(i).total_mem, attrs))
        elif kind == "utilization":
            try:
                util = torch.cuda.utilization(i)
                observations.append(Observation(float(util), attrs))
            except Exception:  # noqa: BLE001
                pass
    return observations


def register_gpu_observables(meter: Meter) -> None:
    """Register all GPU observable gauges on the given meter."""
    name, unit, desc = METRIC_GPU_MEMORY_USED
    meter.create_observable_gauge(name, callbacks=[_read_gpu_memory_used], unit=unit, description=desc)

    name, unit, desc = METRIC_GPU_MEMORY_FREE
    meter.create_observable_gauge(name, callbacks=[_read_gpu_memory_free], unit=unit, description=desc)

    name, unit, desc = METRIC_GPU_MEMORY_TOTAL
    meter.create_observable_gauge(name, callbacks=[_read_gpu_memory_total], unit=unit, description=desc)

    name, unit, desc = METRIC_GPU_UTILIZATION
    meter.create_observable_gauge(name, callbacks=[_read_gpu_utilization], unit=unit, description=desc)


__all__ = ["register_gpu_observables"]
