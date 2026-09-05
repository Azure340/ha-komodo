from __future__ import annotations

import time

from komodo_api.types import (
    StackServiceWithUpdate,
    InspectStackContainerResponse,
    ContainerStateStatusEnum,
)

from .stats import extract_container_stats


class KomodoUpdateInfo:
    """Update information for a service."""

    current_version: str
    new_version: str
    info_updated_at: float

    def __init__(self, info: InspectStackContainerResponse, updated_at: float):
        if info.config and info.config.labels:
            self.current_version = info.config.labels.get(
                "org.opencontainers.image.version", "0"
            )
        else:
            self.current_version = "0"
        self.new_version = "update available"
        self.info_updated_at = updated_at


class KomodoService:
    """Wrapper for a stack service (container)."""

    name: str
    update_available: bool
    state: ContainerStateStatusEnum | None
    update_info: KomodoUpdateInfo | None

    # Per-container stats, attached from listAllStackServices.
    container_id: str | None
    container_name: str | None
    cpu_perc: float | None
    mem_used_bytes: int | None
    mem_total_bytes: int | None
    mem_perc: float | None
    net_rx_bytes: int | None
    net_tx_bytes: int | None
    pids: int | None
    stats_updated_at: float | None

    def __init__(self, item: StackServiceWithUpdate, update_info: KomodoUpdateInfo | None = None):
        self.name = item.service
        self.update_available = item.update_available
        self.state = None
        self.container_id = None
        self.container_name = None
        self.cpu_perc = None
        self.mem_used_bytes = None
        self.mem_total_bytes = None
        self.mem_perc = None
        self.net_rx_bytes = None
        self.net_tx_bytes = None
        self.pids = None
        self.stats_updated_at = None
        if item.update_available:
            self.update_info = update_info
        else:
            self.update_info = None

    def apply_stack_service(self, stack_service) -> None:
        """Attach container + computed stats from a StackService list item."""
        container = getattr(stack_service, "container", None)
        if container is None:
            return
        self.container_id = getattr(container, "id", None)
        self.container_name = getattr(container, "name", None)
        metrics = extract_container_stats(getattr(container, "stats", None))
        for key, value in metrics.items():
            setattr(self, key, value)
        self.stats_updated_at = time.time()

    def apply_update_info(
        self,
        update_info: KomodoUpdateInfo,
    ) -> None:
        """Apply new update info."""
        self.update_info = update_info
