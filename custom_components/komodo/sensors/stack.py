from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from ..coordinator import KomodoCoordinator
from ..data.stats import human_size
from .common import KomodoSensor, KomodoOptionSensor, KomodoStatSensor
from komodo_api.types import StackState
from ..utils import create_stack_device_info


# (translation key, service attribute, display label, device class, unit, icon, formatter)
_STAT_SENSORS = (
    ("cpu_usage", "cpu_perc", "CPU Usage", SensorDeviceClass.POWER_FACTOR, "%", "mdi:cpu-64-bit", None),
    ("memory_usage", "mem_perc", "Memory Usage", SensorDeviceClass.POWER_FACTOR, "%", "mdi:memory", None),
    ("memory_used", "mem_used_bytes", "Memory Used", SensorDeviceClass.DATA_SIZE, None, "mdi:memory", human_size),
    ("network_rx", "net_rx_bytes", "Network Ingress", SensorDeviceClass.DATA_SIZE, None, "mdi:arrow-down-bold", human_size),
    ("network_tx", "net_tx_bytes", "Network Egress", SensorDeviceClass.DATA_SIZE, None, "mdi:arrow-up-bold", human_size),
    ("pids", "pids", "PIDs", None, None, "mdi:run-fast", None),
)


def _make_stat_extractor(stack_id: str, service_name: str, attr: str):
    """Create an extractor for one stat attribute of one service."""
    def extractor(data, sid=stack_id, sname=service_name, a=attr):
        stack = data.get_stack(sid)
        service = stack.services.get(sname)
        if service is None:
            return None
        return getattr(service, a, None)
    return extractor


def create_stack_sensors(
    coordinator: KomodoCoordinator,
    entry_id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    sensors: list[KomodoSensor] = []
    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(
            stack.id, stack.name, stack.server_id
        )

        item_id = f"{entry_id}_{stack.id}"

        def extractor(data, sid=stack.id):
            stk = data.get_stack(sid)
            return stk.state.name

        def joiner(data, sid=stack.id):
            stk = data.get_stack(sid)
            if stk.alerts:
                return ", ".join(stk.alerts)
            return ""

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=extractor,
                key="stack_state",
                device_info=device_info,
                options=[state.name for state in StackState],
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

        # Per-service container stat sensors (Option B).
        for service in stack.services.values():
            for key, attr, label, dev_class, unit, icon, formatter in _STAT_SENSORS:
                sensors.append(
                    KomodoStatSensor(
                        coordinator=coordinator,
                        item_id=f"{entry_id}_{stack.id}_{service.name}",
                        extractor=_make_stat_extractor(
                            stack.id, service.name, attr
                        ),
                        key=key,
                        device_info=device_info,
                        name=f"{service.name} {label}",
                        device_class=dev_class,
                        unit_of_measurement=unit,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon=icon,
                        formatter=formatter,
                    )
                )

    return sensors
