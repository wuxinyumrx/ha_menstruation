from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import MenstruationCoordinator, MenstruationState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MenstruationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name: str = entry.data.get(CONF_NAME, entry.title)

    async_add_entities(
        [
            MenstruationIsPeriodBinarySensor(coordinator, entry.entry_id, name),
            MenstruationIsSafeBinarySensor(coordinator, entry.entry_id, name),
            MenstruationIsOvulationBinarySensor(coordinator, entry.entry_id, name),
        ]
    )


class MenstruationBaseBinarySensor(
    CoordinatorEntity[MenstruationCoordinator], BinarySensorEntity
):
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


class MenstruationIsPeriodBinarySensor(MenstruationBaseBinarySensor):
    _attr_icon = "mdi:water"
    _attr_translation_key = "is_period"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_is_period"

    @property
    def is_on(self) -> bool:
        return self._state.is_period


class MenstruationIsSafeBinarySensor(MenstruationBaseBinarySensor):
    _attr_icon = "mdi:shield-check"
    _attr_translation_key = "is_safe"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_is_safe"

    @property
    def is_on(self) -> bool:
        return self._state.is_safe


class MenstruationIsOvulationBinarySensor(MenstruationBaseBinarySensor):
    _attr_icon = "mdi:egg-fried"
    _attr_translation_key = "is_ovulation"

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id, name)
        self._attr_unique_id = f"{entry_id}_is_ovulation"

    @property
    def is_on(self) -> bool:
        return self._state.is_ovulation
