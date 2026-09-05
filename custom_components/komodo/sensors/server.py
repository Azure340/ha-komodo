from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from komodo_api.types import ServerState

from ..const import DOMAIN
from ..coordinator import KomodoCoordinator
from ..data.stats import human_size
from .common import KomodoOptionSensor, KomodoSensor, KomodoStatSensor

_GIB = 1024 ** 3


def _server_attr(server_id: str, attr: str):
    """Create an extractor for a plain server attribute."""
    def extractor(data, sid=server_id, a=attr):
        srv = data.get_server(sid)
        if srv is None:
            return None
        return getattr(srv, a, None)
    return extractor


def _server_gb_bytes(server_id: str, attr: str):
    """Create an extractor that converts a GB field to bytes."""
    def extractor(data, sid=server_id, a=attr):
        srv = data.get_server(sid)
        if srv is None:
            return None
        value = getattr(srv, a, None)
        return value * _GIB if value is not None else None
    return extractor


def _mem_perc(server_id: str):
    """Extractor for memory usage percentage."""
    def extractor(data, sid=server_id):
        srv = data.get_server(sid)
        if srv is None or srv.mem_used_gb is None or srv.mem_total_gb in (None, 0):
            return None
        return round(srv.mem_used_gb / srv.mem_total_gb * 100, 1)
    return extractor


def _disk_perc(server_id: str):
    """Extractor for disk usage percentage."""
    def extractor(data, sid=server_id):
        srv = data.get_server(sid)
        if srv is None or srv.disk_used_gb is None or srv.disk_total_gb in (None, 0):
            return None
        return round(srv.disk_used_gb / srv.disk_total_gb * 100, 1)
    return extractor


def create_server_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """Return a list of sensors, one device per server."""
    sensors: list[KomodoSensor] = []
    for server in coordinator.data.servers.values():
        device_info = DeviceInfo(
            identifiers={(DOMAIN, server.id)},
            name=server.name,
            manufacturer="Komodo",
            sw_version=server.periphery_version,
        )

        item_id = f"{entry_id}_{server.id}"

        def extractor(data, sid=server.id):
            srv = data.get_server(sid)
            state = srv.state
            if state is None:
                return None
            return state.name

        def joiner(data, sid=server.id):
            srv = data.get_server(sid)
            if srv.alerts:
                return ", ".join(srv.alerts)
            return ""

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=extractor,
                key="server_state",
                device_info=device_info,
                options=[state.name for state in ServerState],
            )
        )
        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=joiner,
                key="alert_list",
                device_info=device_info,
            )
        )

        def stack_counter(data, sid=server.id):
            return data.servers[sid].stack_count

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=stack_counter,
                key="stack_count",
                device_info=device_info,
            )
        )

        def service_counter(data, sid=server.id):
            return data.servers[sid].service_count

        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=service_counter,
                key="service_count",
                device_info=device_info,
            )
        )

        # ---- Server resource stats (getSystemStats) ----
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_server_attr(server.id, "cpu_perc"),
                key="server_cpu_usage",
                device_info=device_info,
                name="CPU Usage",
                device_class=SensorDeviceClass.POWER_FACTOR,
                unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:cpu-64-bit",
            )
        )
        for key, attr, label in (
            ("server_load_1m", "load_1m", "CPU Load 1m"),
            ("server_load_5m", "load_5m", "CPU Load 5m"),
            ("server_load_15m", "load_15m", "CPU Load 15m"),
        ):
            sensors.append(
                KomodoStatSensor(
                    coordinator=coordinator,
                    item_id=item_id,
                    extractor=_server_attr(server.id, attr),
                    key=key,
                    device_info=device_info,
                    name=label,
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:gauge",
                )
            )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_mem_perc(server.id),
                key="server_memory_usage",
                device_info=device_info,
                name="Memory Usage",
                device_class=SensorDeviceClass.POWER_FACTOR,
                unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:memory",
            )
        )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_server_gb_bytes(server.id, "mem_used_gb"),
                key="server_memory_used",
                device_info=device_info,
                name="Memory Used",
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:memory",
                formatter=human_size,
            )
        )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_server_gb_bytes(server.id, "mem_total_gb"),
                key="server_memory_total",
                device_info=device_info,
                name="Memory Total",
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:memory",
                formatter=human_size,
            )
        )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_disk_perc(server.id),
                key="server_disk_usage",
                device_info=device_info,
                name="Disk Usage",
                device_class=SensorDeviceClass.POWER_FACTOR,
                unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:harddisk",
            )
        )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_server_gb_bytes(server.id, "disk_used_gb"),
                key="server_disk_used",
                device_info=device_info,
                name="Disk Used",
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:harddisk",
                formatter=human_size,
            )
        )
        sensors.append(
            KomodoStatSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=_server_gb_bytes(server.id, "disk_total_gb"),
                key="server_disk_total",
                device_info=device_info,
                name="Disk Total",
                device_class=SensorDeviceClass.DATA_SIZE,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:harddisk",
                formatter=human_size,
            )
        )
        for key, attr, label, icon in (
            ("server_network_ingress", "network_ingress_bytes", "Network Ingress", "mdi:arrow-down-bold"),
            ("server_network_egress", "network_egress_bytes", "Network Egress", "mdi:arrow-up-bold"),
        ):
            sensors.append(
                KomodoStatSensor(
                    coordinator=coordinator,
                    item_id=item_id,
                    extractor=_server_attr(server.id, attr),
                    key=key,
                    device_info=device_info,
                    name=label,
                    device_class=SensorDeviceClass.DATA_SIZE,
                    state_class=SensorStateClass.MEASUREMENT,
                    icon=icon,
                    formatter=human_size,
                )
            )

    return sensors
