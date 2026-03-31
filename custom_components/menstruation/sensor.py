from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CYCLE_LENGTH,
    ATTR_LAST_END,
    ATTR_LAST_START,
    ATTR_PERIOD_LENGTH,
    ATTR_PREDICTED_END,
    ATTR_PREDICTED_START,
    CONF_NAME,
    DOMAIN,
)
from .coordinator import MenstruationCoordinator, MenstruationState
from .store import MenstruationStore, PeriodRecord


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MenstruationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    store: MenstruationStore = hass.data[DOMAIN][entry.entry_id]["store"]
    name: str = entry.data.get(CONF_NAME, entry.title)

    async_add_entities(
        [
            MenstruationPhaseSensor(coordinator, entry.entry_id, name),
            MenstruationNextStartSensor(coordinator, entry.entry_id, name),
            MenstruationNextEndSensor(coordinator, entry.entry_id, name),
            MenstruationOvulationDaySensor(coordinator, entry.entry_id, name),
            MenstruationFertileStartSensor(coordinator, entry.entry_id, name),
            MenstruationFertileEndSensor(coordinator, entry.entry_id, name),
            MenstruationDaysToNextPeriodSensor(coordinator, entry.entry_id, name),
            MenstruationDaysToOvulationSensor(coordinator, entry.entry_id, name),
            MenstruationCycleDaySensor(coordinator, entry.entry_id, name),
            MenstruationPeriodDaySensor(coordinator, entry.entry_id, name),
            MenstruationCalendarDataSensor(hass, coordinator, store, entry.entry_id, name),
        ]
    )


class MenstruationBaseSensor(CoordinatorEntity[MenstruationCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._name = name
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
        }

    @property
    def _state(self) -> MenstruationState:
        return self.coordinator.data


class MenstruationPhaseSensor(MenstruationBaseSensor):
    _attr_icon = "mdi:calendar-heart"
    _attr_translation_key = "phase"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_phase"

    @property
    def native_value(self) -> str:
        return self._state.phase

    @property
    def extra_state_attributes(self) -> dict:
        state = self._state
        return {
            ATTR_PREDICTED_START: state.predicted_start.isoformat(),
            ATTR_PREDICTED_END: state.predicted_end.isoformat(),
            ATTR_CYCLE_LENGTH: state.cycle_length,
            ATTR_PERIOD_LENGTH: state.period_length,
            ATTR_LAST_START: state.last_start.isoformat() if state.last_start else None,
            ATTR_LAST_END: state.last_end.isoformat() if state.last_end else None,
        }


class MenstruationNextStartSensor(MenstruationBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-start"
    _attr_translation_key = "next_start"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_next_start"

    @property
    def native_value(self):
        return self._state.predicted_start


class MenstruationNextEndSensor(MenstruationBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-end"
    _attr_translation_key = "next_end"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_next_end"

    @property
    def native_value(self):
        return self._state.predicted_end


class MenstruationOvulationDaySensor(MenstruationBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:star-four-points"
    _attr_translation_key = "ovulation_day"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_ovulation_day"

    @property
    def native_value(self):
        return self._state.ovulation_day


class MenstruationFertileStartSensor(MenstruationBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-right"
    _attr_translation_key = "fertile_start"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_fertile_start"

    @property
    def native_value(self):
        return self._state.fertile_start


class MenstruationFertileEndSensor(MenstruationBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-left"
    _attr_translation_key = "fertile_end"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_fertile_end"

    @property
    def native_value(self):
        return self._state.fertile_end


class MenstruationDaysToNextPeriodSensor(MenstruationBaseSensor):
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "days_to_next_period"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_days_to_next_period"

    @property
    def native_value(self):
        return self._state.days_to_next_period


class MenstruationDaysToOvulationSensor(MenstruationBaseSensor):
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "days_to_ovulation"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_days_to_ovulation"

    @property
    def native_value(self):
        return self._state.days_to_ovulation


class MenstruationCycleDaySensor(MenstruationBaseSensor):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "cycle_day"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_cycle_day"

    @property
    def native_value(self):
        return self._state.cycle_day


class MenstruationPeriodDaySensor(MenstruationBaseSensor):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "period_day"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_period_day"

    @property
    def native_value(self):
        return self._state.period_day


def _find_by_start(records: list[PeriodRecord], day: date) -> PeriodRecord | None:
    for r in records:
        if r.start == day:
            return r
    return None


def _find_by_end(records: list[PeriodRecord], day: date) -> PeriodRecord | None:
    for r in records:
        if r.end == day:
            return r
    return None


def _find_covering(records: list[PeriodRecord], day: date) -> PeriodRecord | None:
    for r in reversed(records):
        if r.end is None:
            continue
        if r.start <= day <= r.end:
            return r
    return None


def _find_latest_start_on_or_before(records: list[PeriodRecord], day: date) -> PeriodRecord | None:
    candidate: PeriodRecord | None = None
    for r in records:
        if r.start <= day and (candidate is None or r.start > candidate.start):
            candidate = r
    return candidate


class MenstruationCalendarDataSensor(
    CoordinatorEntity[MenstruationCoordinator], SensorEntity
):
    _attr_icon = "mdi:calendar-multiselect"
    _attr_translation_key = "calendar_data"
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: MenstruationCoordinator,
        store: MenstruationStore,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._store = store
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
        }
        self._attr_object_id = "menstruation_calendar_data"
        self._attr_unique_id = f"{entry_id}_calendar_data"

    @property
    def native_value(self) -> str:
        return dt_util.now().isoformat()

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data
        records = list(self._store.iter_records())
        return {
            "records": [
                {
                    "uid": r.uid,
                    "start": r.start.isoformat(),
                    "end": r.end.isoformat() if r.end else None,
                }
                for r in records
            ],
            "predicted_period": {
                "start": state.predicted_start.isoformat(),
                "end": state.predicted_end.isoformat(),
            },
            "fertile_window": {
                "start": state.fertile_start.isoformat(),
                "end": state.fertile_end.isoformat(),
            },
            "today": dt_util.now().date().isoformat(),
        }
