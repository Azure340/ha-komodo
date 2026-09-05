"""Convert Komodo's raw docker-stats payload into HA-friendly metrics.

Komodo builds its ``ContainerStats`` payload from Docker's ``docker stats``
output. The raw numbers are cumulative counters, so the derived values
(CPU %, mem %) are computed here instead of being exposed by the API.

The payload is navigated with ``getattr`` so missing/optional fields never
crash the poll cycle; everything degrades to ``None``.
"""

from __future__ import annotations

from typing import Any


def _num(obj: Any, *path: str) -> int | float | None:
    """Follow an attribute path on a (possibly optional) stats object."""
    cur = obj
    for key in path:
        if cur is None:
            return None
        cur = getattr(cur, key, None)
    return cur if isinstance(cur, (int, float)) else None


def extract_container_stats(stats: Any | None) -> dict[str, int | float | None]:
    """Compute per-container metrics from a Komodo ``ContainerStats`` payload.

    Returns a dict with keys ``cpu_perc``, ``mem_used_bytes``,
    ``mem_total_bytes``, ``mem_perc``, ``net_rx_bytes``, ``net_tx_bytes``
    and ``pids``. Missing values are ``None``.
    """
    out: dict[str, int | float | None] = {
        "cpu_perc": None,
        "mem_used_bytes": None,
        "mem_total_bytes": None,
        "mem_perc": None,
        "net_rx_bytes": None,
        "net_tx_bytes": None,
        "pids": None,
    }
    if stats is None:
        return out

    # CPU %: same formula as `docker stats`:
    # delta(cpu total) / delta(system cpu) * online_cpus * 100
    cpu = getattr(stats, "cpu_stats", None)
    precpu = getattr(stats, "precpu_stats", None)
    total = _num(cpu, "cpu_usage", "total_usage")
    prev_total = _num(precpu, "cpu_usage", "total_usage")
    system = _num(cpu, "system_cpu_usage")
    prev_system = _num(precpu, "system_cpu_usage")
    online_cpus = _num(cpu, "online_cpus")
    if (
        total is not None
        and prev_total is not None
        and system is not None
        and prev_system is not None
        and online_cpus is not None
        and system - prev_system > 0
    ):
        perc = (total - prev_total) / (system - prev_system) * online_cpus * 100
        out["cpu_perc"] = round(max(perc, 0.0), 1)

    # Memory
    mem = getattr(stats, "memory_stats", None)
    usage = _num(mem, "usage")
    limit = _num(mem, "limit")
    if usage is not None:
        out["mem_used_bytes"] = int(usage)
    if limit is not None:
        out["mem_total_bytes"] = int(limit)
        if usage is not None and limit > 0:
            out["mem_perc"] = round(usage / limit * 100, 1)

    # Network: cumulative totals summed across all interfaces
    networks = getattr(stats, "networks", None)
    if isinstance(networks, dict):
        rx = sum(int(_num(net, "rx_bytes") or 0) for net in networks.values())
        tx = sum(int(_num(net, "tx_bytes") or 0) for net in networks.values())
        out["net_rx_bytes"] = rx
        out["net_tx_bytes"] = tx

    # PIDs
    pids = _num(getattr(stats, "pids_stats", None), "current")
    if pids is not None:
        out["pids"] = int(pids)

    return out
