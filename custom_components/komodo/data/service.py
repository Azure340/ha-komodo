from __future__ import annotations

import re
import time

from komodo_api.types import (
    StackServiceWithUpdate,
    InspectStackContainerResponse,
    ContainerStateStatusEnum,
)

from .stats import extract_container_stats


_GHCR_RE = re.compile(r"^ghcr\.io/([^/:@]+)/([^/:@]+)")
_DOCKER_HUB_RE = re.compile(r"^(?:docker\.io/)?([^/:@]+)/([^/:@]+)")
_OFFICIAL_RE = re.compile(r"^([^/:@]+)$")


def derive_release_url(image: str | None) -> str | None:
    """Best-effort release / browse URL from an image reference.

    - ``ghcr.io/{owner}/{repo}``  -> ``https://github.com/{owner}/{repo}/releases``
    - ``{owner}/{repo}``          -> ``https://hub.docker.com/r/{owner}/{repo}``
    - official ``{name}`` images  -> ``https://hub.docker.com/_/{name}``

    Pinned digests (``@sha256:...``) and tags are stripped before matching.
    A registry ``host:port`` is kept intact so ``localhost:5000/x/y`` does not
    match anything. Returns ``None`` when no URL can be derived.
    """
    if not image:
        return None
    image = image.split("@")[0]  # drop any pinned digest
    # Drop a tag (e.g. :latest, :0.18.0-rc1) but keep a registry host:port.
    if ":" in image and "/" not in image.rsplit(":", 1)[1]:
        image = image.rsplit(":", 1)[0]
    if m := _GHCR_RE.match(image):
        return f"https://github.com/{m.group(1)}/{m.group(2)}/releases"
    if m := _DOCKER_HUB_RE.match(image):
        return f"https://hub.docker.com/r/{m.group(1)}/{m.group(2)}"
    if m := _OFFICIAL_RE.match(image):
        return f"https://hub.docker.com/_/{m.group(1)}"
    return None


class KomodoUpdateInfo:
    """Update information for a service."""

    current_version: str
    new_version: str
    release_url: str | None
    info_updated_at: float

    def __init__(self, info: InspectStackContainerResponse, updated_at: float):
        if info.config and info.config.labels:
            self.current_version = info.config.labels.get(
                "org.opencontainers.image.version", "0"
            )
        else:
            self.current_version = "0"
        # Prefer an explicit OCI source label; otherwise derive a URL from
        # the image reference (ghcr.io -> GitHub releases, else Docker Hub).
        self.release_url = None
        if info.config:
            if info.config.labels:
                self.release_url = info.config.labels.get(
                    "org.opencontainers.image.source"
                )
            if not self.release_url:
                self.release_url = derive_release_url(info.config.image)
        self.new_version = "update available"
        self.info_updated_at = updated_at


class KomodoService:
    """Wrapper for a stack service (container)."""

    name: str
    update_available: bool
    state: ContainerStateStatusEnum | None
    update_info: KomodoUpdateInfo | None

    # Per-container stats, attached from listStackServices.
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
