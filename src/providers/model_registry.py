"""Empty-by-default model/permission registry; no speculative model entries."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .contracts import Modality, optional_int, require_text, text_tuple


@dataclass(frozen=True)
class ModelMetadata:
    model_id: str
    provider: str
    modality: Modality
    min_vram_mb: int | None = None
    preferred_vram_mb: int | None = None
    reference_image_support: bool | None = None
    image_edit_support: bool | None = None
    quantization: str | None = None
    licence: str | None = None
    commercial_output_allowed: bool | None = None
    attribution_required: bool | None = None
    known_restrictions: tuple[str, ...] = ()
    benchmark_score: float | None = None

    def validate(self) -> None:
        require_text(self.model_id, "model_id")
        require_text(self.provider, "provider")
        if not isinstance(self.modality, Modality):
            raise ValueError("Model modality must use the explicit enum.")
        optional_int(self.min_vram_mb, "min_vram_mb", 1)
        optional_int(self.preferred_vram_mb, "preferred_vram_mb", 1)
        if (self.min_vram_mb is not None and self.preferred_vram_mb is not None and
                self.preferred_vram_mb < self.min_vram_mb):
            raise ValueError("Preferred VRAM must be at least minimum VRAM.")
        for name in ("reference_image_support", "image_edit_support", "commercial_output_allowed", "attribution_required"):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean or None.")
        for name in ("quantization", "licence"):
            if getattr(self, name) is not None:
                require_text(getattr(self, name), name)
        text_tuple(self.known_restrictions, "known_restrictions")
        if self.benchmark_score is not None and (type(self.benchmark_score) not in (int, float) or
                                                not math.isfinite(self.benchmark_score) or self.benchmark_score < 0):
            raise ValueError("benchmark_score must be finite and nonnegative.")


class ModelRegistry:
    def __init__(self, entries: tuple[ModelMetadata, ...] = ()):
        self._entries: dict[tuple[str, str, Modality], ModelMetadata] = {}
        for entry in entries:
            if not isinstance(entry, ModelMetadata):
                raise ValueError("Registry requires ModelMetadata entries.")
            entry.validate()
            key = (entry.provider, entry.model_id, entry.modality)
            if key in self._entries:
                raise ValueError("Duplicate model registry entry.")
            self._entries[key] = entry

    def get(self, provider_id: str, model_id: str, modality: Modality) -> ModelMetadata | None:
        return self._entries.get((provider_id, model_id, modality))
