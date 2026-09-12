from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfInformation

from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor, KomodoStatSensor
from komodo_api.types import StackState
from ..utils import create_stack_device_info


# (translation key, service attribute, display label, device class, unit, icon, scale)
# ``scale`` converts the stored value into the sensor's fixed unit
# (bytes -> MB is 1 / 1024 ** 2). Units are fixed, never computed per update.
_STAT_SENSORS = (
    ("cpu_usage", "cpu_perc", "CPU Usage", SensorDeviceClass.POWER_FACTOR, "%", "mdi:cpu-64-bit", 1.0),
    ("memory_usage", "mem_perc", "Memory Usage", SensorDeviceClass.POWER_FACTOR, "%", "mdi:memory", 1.0),
    (
        "memory_used",
        "mem_used_bytes",
        "Memory Used",
        SensorDeviceClass.DATA_SIZE,
        UnitOfInformation.MEGABYTES,
        "mdi:memory",
        1 / 1024 ** 2,
    ),
)


def _make_stat_extractor(stack_id: str, service_name: str, attr: str, scale: float = 1.0):
    """Create an extractor for one stat attribute of one service."""
    def extractor(data, sid=stack_id, sname=service_name, a=attr, s=scale):
        stack = data.get_stack(sid)
        service = stack.services.get(sname)
        if service is None:
            return None
        value = getattr(service, a, None)
        if value is None:
            return None
        return value * s
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
            for key, attr, label, dev_class, unit, icon, scale in _STAT_SENSORS:
                sensors.append(
                    KomodoStatSensor(
                        coordinator=coordinator,
                        item_id=f"{entry_id}_{stack.id}_{service.name}",
                        extractor=_make_stat_extractor(
                            stack.id, service.name, attr, scale
                        ),
                        key=key,
                        device_info=device_info,
                        name=f"{service.name} {label}",
                        device_class=dev_class,
                        unit_of_measurement=unit,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon=icon,
                    )
                )

    return sensors
