"""Convert Komodo container stats payloads into HA-friendly metrics.

Komodo exposes two different stats shapes depending on the komodo-api build:

- ``ContainerStats`` (string) - used on komodo-api 2.2.0b3 / Komodo 2.2.x.
  Values are pre-formatted Docker CLI strings, eg
  ``cpu_perc: "0.28%"``, ``mem_usage: "5.629MiB / 1.952GiB"``,
  ``net_io: "916B / 0B"``, ``pids: "9"``.
- ``FullContainerStats`` (raw) - used on komodo-api 2.3 beta / Komodo 2.3.x.
  Values are the raw Docker stats objects with ``cpu_stats``, ``precpu_stats``,
  ``memory_stats``, ``networks`` and ``pids_stats``.

Both are handled here; anything missing degrades to ``None``.
"""

from __future__ import annotations

import re
from typing import Any

_SIZE_UNITS = {
    "b": 1.0,
    "kb": 1e3, "mb": 1e6, "gb": 1e9, "tb": 1e12,
    "kib": 1024.0, "mib": 1024.0 ** 2, "gib": 1024.0 ** 3, "tib": 1024.0 ** 4,
}


def _num(obj: Any, *path: str) -> int | float | None:
    """Follow an attribute path on a (possibly optional) stats object."""
    cur = obj
    for key in path:
        if cur is None:
            return None
        cur = getattr(cur, key, None)
    return cur if isinstance(cur, (int, float)) else None


_SIZE_RE = re.compile(r"([0-9]*\.?[0-9]+)\s*([a-zA-Z]*)")


def _parse_size(text: str | None) -> float | None:
    """Parse a Docker size string like '5.629MiB', '916B' or '1.2GB'."""
    if not text:
        return None
    m = _SIZE_RE.match(text.strip())
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    return value * _SIZE_UNITS.get(unit, 1.0)


def _parse_percent(text: str | None) -> float | None:
    """Parse a percent string like '0.28%' -> 0.28."""
    if not text or not text.endswith("%"):
        return None
    try:
        return round(float(text[:-1]), 1)
    except (TypeError, ValueError):
        return None


def _extract_string_stats(stats: Any) -> dict[str, int | float | None]:
    """Extract metrics from the string-format ``ContainerStats`` (komodo-api 2.2)."""
    out: dict[str, int | float | None] = {
        "cpu_perc": None,
        "mem_used_bytes": None,
        "mem_total_bytes": None,
        "mem_perc": None,
        "net_rx_bytes": None,
        "net_tx_bytes": None,
        "pids": None,
    }

    out["cpu_perc"] = _parse_percent(getattr(stats, "cpu_perc", None))
    out["mem_perc"] = _parse_percent(getattr(stats, "mem_perc", None))

    mem_usage = getattr(stats, "mem_usage", None)
    if isinstance(mem_usage, str) and "/" in mem_usage:
        used_s, total_s = mem_usage.split("/", 1)
        used = _parse_size(used_s)
        total = _parse_size(total_s)
        if used is not None:
            out["mem_used_bytes"] = int(used)
        if total is not None:
            out["mem_total_bytes"] = int(total)
            if used is not None and total > 0 and out["mem_perc"] is None:
                out["mem_perc"] = round(used / total * 100, 1)

    net_io = getattr(stats, "net_io", None)
    if isinstance(net_io, str) and "/" in net_io:
        rx_s, tx_s = net_io.split("/", 1)
        rx = _parse_size(rx_s)
        tx = _parse_size(tx_s)
        out["net_rx_bytes"] = int(rx) if rx is not None else None
        out["net_tx_bytes"] = int(tx) if tx is not None else None

    pids = getattr(stats, "pids", None)
    if isinstance(pids, str):
        try:
            out["pids"] = int(pids)
        except (TypeError, ValueError):
            pass

    return out


def _extract_raw_stats(stats: Any) -> dict[str, int | float | None]:
    """Extract metrics from the raw-format ``FullContainerStats`` (komodo-api 2.3+)."""
    out: dict[str, int | float | None] = {
        "cpu_perc": None,
        "mem_used_bytes": None,
        "mem_total_bytes": None,
        "mem_perc": None,
        "net_rx_bytes": None,
        "net_tx_bytes": None,
        "pids": None,
    }

    # CPU %: delta(cpu total) / delta(system cpu) * online_cpus * 100
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

    mem = getattr(stats, "memory_stats", None)
    usage = _num(mem, "usage")
    limit = _num(mem, "limit")
    if usage is not None:
        out["mem_used_bytes"] = int(usage)
    if limit is not None:
        out["mem_total_bytes"] = int(limit)
        if usage is not None and limit > 0:
            out["mem_perc"] = round(usage / limit * 100, 1)

    networks = getattr(stats, "networks", None)
    if isinstance(networks, dict):
        rx = sum(int(_num(net, "rx_bytes") or 0) for net in networks.values())
        tx = sum(int(_num(net, "tx_bytes") or 0) for net in networks.values())
        out["net_rx_bytes"] = rx
        out["net_tx_bytes"] = tx

    pids = _num(getattr(stats, "pids_stats", None), "current")
    if pids is not None:
        out["pids"] = int(pids)

    return out


def extract_container_stats(stats: Any | None) -> dict[str, int | float | None]:
    """Extract per-container metrics from a Komodo ``ContainerStats`` payload.

    Accepts either the string format (komodo-api 2.2.x) or the raw format
    (komodo-api 2.3 beta / later). Missing values are ``None``.
    """
    if stats is None:
        return {
            "cpu_perc": None,
            "mem_used_bytes": None,
            "mem_total_bytes": None,
            "mem_perc": None,
            "net_rx_bytes": None,
            "net_tx_bytes": None,
            "pids": None,
        }
    if hasattr(stats, "cpu_stats") or hasattr(stats, "precpu_stats"):
        return _extract_raw_stats(stats)
    return _extract_string_stats(stats)
