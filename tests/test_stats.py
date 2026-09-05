"""Tests for the container stats extraction helpers."""

from types import SimpleNamespace

from custom_components.komodo.data.stats import extract_container_stats


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


def _fake_raw_stats():
    return _ns(
        cpu_stats=_ns(
            cpu_usage=_ns(total_usage=3000),
            system_cpu_usage=100000,
            online_cpus=2,
        ),
        precpu_stats=_ns(
            cpu_usage=_ns(total_usage=1000),
            system_cpu_usage=50000,
        ),
        memory_stats=_ns(
            usage=512 * 1024 * 1024,
            limit=1024 * 1024 * 1024,
        ),
        networks={
            "eth0": _ns(rx_bytes=1000, tx_bytes=2000),
            "eth1": _ns(rx_bytes=500, tx_bytes=700),
        },
        pids_stats=_ns(current=12),
    )


def test_raw_format_all_metrics():
    out = extract_container_stats(_fake_raw_stats())
    assert out["cpu_perc"] == 8.0  # (3000-1000)/(100000-50000)*2*100
    assert out["mem_used_bytes"] == 512 * 1024 * 1024
    assert out["mem_total_bytes"] == 1024 * 1024 * 1024
    assert out["mem_perc"] == 50.0
    assert out["net_rx_bytes"] == 1500
    assert out["net_tx_bytes"] == 2700
    assert out["pids"] == 12


def test_string_format_all_metrics():
    # komodo-api 2.2.0b3 style: Docker CLI formatted strings
    stats = _ns(
        name="mongo-1",
        cpu_perc="0.28%",
        mem_perc="5.63%",
        mem_usage="5.629MiB / 1.952GiB",
        net_io="916B / 2.43kB",
        block_io="147kB / 0B",
        pids="9",
    )
    out = extract_container_stats(stats)
    assert out["cpu_perc"] == 0.3
    assert out["mem_perc"] == 5.6
    assert out["mem_used_bytes"] == int(5.629 * 1024 * 1024)
    assert out["mem_total_bytes"] == int(1.952 * 1024 * 1024 * 1024)
    assert out["net_rx_bytes"] == 916
    assert out["net_tx_bytes"] == int(2.43 * 1e3)
    assert out["pids"] == 9


def test_none_when_no_stats():
    out = extract_container_stats(None)
    assert all(v is None for v in out.values())


def test_guard_against_missing_fields():
    out = extract_container_stats(_ns(cpu_stats=None, memory_stats=None))
    assert out["cpu_perc"] is None
    assert out["mem_used_bytes"] is None


def test_zero_cpu_delta_yields_none():
    stats = _fake_raw_stats()
    stats.precpu_stats.system_cpu_usage = 100000  # equal deltas -> div-by-zero guard
    out = extract_container_stats(stats)
    assert out["cpu_perc"] is None
