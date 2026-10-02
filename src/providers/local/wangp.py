"""WanGP candidate general-purpose local multimodal worker; inactive seam only."""
from .base import InactiveLocalProvider, LocalWorkerConfig


class WanGPProvider(InactiveLocalProvider):
    def __init__(self, config: LocalWorkerConfig | None = None, *, provider_id: str = "wangp"):
        super().__init__(provider_id, config)
