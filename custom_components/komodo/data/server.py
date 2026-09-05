from komodo_api.types import (
    ServerListItem,
    ServerState,
    ResourceListItem,
)
from typing import List
import time


class KomodoServer:
    """Wrapper for a server list item returned from the API."""

    state: ServerState | None
    id: str
    name: str
    alerts: List[str]
    stack_count: int
    service_count: int
    periphery_version: str | None

    # Server resource stats, attached from getSystemStats (cached by core).
    cpu_perc: float | None
    load_1m: float | None
    load_5m: float | None
    load_15m: float | None
    mem_used_gb: float | None
    mem_total_gb: float | None
    mem_free_gb: float | None
    disk_used_gb: float | None
    disk_total_gb: float | None
    network_ingress_bytes: float | None
    network_egress_bytes: float | None
    stats_updated_at: float | None

    def __init__(self, item: ResourceListItem[ServerListItem]):
        self.state = item.info.state
        self.id = item.id
        self.name = item.name
        self.alerts = []
        self.stack_count = 0
        self.service_count = 0
        self.periphery_version = item.info.version
        self.cpu_perc = None
        self.load_1m = None
        self.load_5m = None
        self.load_15m = None
        self.mem_used_gb = None
        self.mem_total_gb = None
        self.mem_free_gb = None
        self.disk_used_gb = None
        self.disk_total_gb = None
        self.network_ingress_bytes = None
        self.network_egress_bytes = None
        self.stats_updated_at = None

    def apply_system_stats(self, stats) -> None:
        """Attach server resource stats from a SystemStats response."""
        self.cpu_perc = getattr(stats, "cpu_perc", None)
        load = getattr(stats, "load_average", None)
        if load is not None:
            self.load_1m = getattr(load, "one", None)
            self.load_5m = getattr(load, "five", None)
            self.load_15m = getattr(load, "fifteen", None)
        self.mem_used_gb = getattr(stats, "mem_used_gb", None)
        self.mem_total_gb = getattr(stats, "mem_total_gb", None)
        self.mem_free_gb = getattr(stats, "mem_free_gb", None)
        disks = getattr(stats, "disks", None) or []
        if disks:
            used = 0.0
            total = 0.0
            for disk in disks:
                used += float(getattr(disk, "used_gb", 0) or 0)
                total += float(getattr(disk, "total_gb", 0) or 0)
            self.disk_used_gb = used
            self.disk_total_gb = total
        else:
            self.disk_used_gb = None
            self.disk_total_gb = None
        self.network_ingress_bytes = getattr(stats, "network_ingress_bytes", None)
        self.network_egress_bytes = getattr(stats, "network_egress_bytes", None)
        self.stats_updated_at = time.time()

    def add_alert(self, alert) -> None:
        """Add an alert to this server."""
        self.alerts.append(alert.data.type)

    def add_stack(self) -> None:
        """Increment stack count for this server."""
        self.stack_count += 1

    def add_services(self, count: int) -> None:
        """Add services to this server."""
        self.service_count += count

    @classmethod
    def unknown(cls, server_id: str) -> "KomodoServer":
        """Create unknown server."""
        self = cls.__new__(cls)
        self.id = server_id
        self.name = f"Unknown Server {server_id}"
        self.state = None
        self.alerts = []
        self.stack_count = 0
        self.service_count = 0
        self.periphery_version = None
        self.cpu_perc = None
        self.load_1m = None
        self.load_5m = None
        self.load_15m = None
        self.mem_used_gb = None
        self.mem_total_gb = None
        self.mem_free_gb = None
        self.disk_used_gb = None
        self.disk_total_gb = None
        self.network_ingress_bytes = None
        self.network_egress_bytes = None
        self.stats_updated_at = None
        return self
