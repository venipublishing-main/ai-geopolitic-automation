"""ComfyUI candidate specialist local image/edit worker; inactive seam only."""
from .base import InactiveLocalProvider, LocalWorkerConfig


class ComfyUIProvider(InactiveLocalProvider):
    def __init__(self, config: LocalWorkerConfig | None = None, *, provider_id: str = "comfyui"):
        super().__init__(provider_id, config)
