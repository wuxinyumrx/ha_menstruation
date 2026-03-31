from __future__ import annotations

from datetime import date, timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SERVICE_APPLY_DAY, STORAGE_KEY
from .coordinator import MenstruationCoordinator, compute_state
from .errors import MenstruationError
from .i18n import err
from .store import MenstruationStore
from .const import CONF_PERSON

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "calendar"]

SERVICE_SCHEMA_REQUIRED_DATE = vol.Schema({vol.Required("date"): cv.date})
SERVICE_SCHEMA_APPLY_DAY = vol.Schema(
    {
        vol.Required("date"): cv.date,
        vol.Optional(CONF_PERSON): cv.entity_id,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    person_entity_id = entry.data.get(CONF_PERSON)
    storage_key = STORAGE_KEY
    if isinstance(person_entity_id, str) and person_entity_id:
        storage_key = f"{STORAGE_KEY}_{person_entity_id.replace('.', '_')}"

    store = MenstruationStore(hass, storage_key)
    coordinator = MenstruationCoordinator(hass, store)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "coordinator": coordinator,
        "person": person_entity_id,
    }

    if not hass.services.has_service(DOMAIN, SERVICE_APPLY_DAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_APPLY_DAY,
            _async_apply_day_service(hass),
            schema=SERVICE_SCHEMA_APPLY_DAY,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_apply_day_service(hass: HomeAssistant):
    async def _handler(call: ServiceCall) -> None:
        entry = _resolve_entry_for_call(hass, call)
        if entry is None:
            raise ServiceValidationError(
                err(
                    hass,
                    "multiple_profiles_require_person",
                    "Multiple profiles are configured; please specify a person or link this user to a person.",
                )
            )

        store: MenstruationStore = entry["store"]
        coordinator: MenstruationCoordinator = entry["coordinator"]

        target: date = call.data["date"]
        today = dt_util.now().date()
        if target > today:
            raise ServiceValidationError(err(hass, "date_in_future", "Date must not be in the future"))

        await store.async_load()
        try:
            await _apply_day(store, target, today)
        except MenstruationError as exc:
            raise ServiceValidationError(err(hass, exc.key, exc.key)) from exc
        except ValueError as exc:
            raise ServiceValidationError(str(exc)) from exc
        records = list(store.iter_records())
        coordinator.async_set_updated_data(compute_state(today, records))

    return _handler


def _resolve_entry_for_call(hass: HomeAssistant, call: ServiceCall) -> dict | None:
    domain_data = hass.data.get(DOMAIN, {})
    if not isinstance(domain_data, dict) or not domain_data:
        return None

    person_override = call.data.get(CONF_PERSON)
    if isinstance(person_override, str) and person_override:
        for entry in domain_data.values():
            if entry.get("person") == person_override:
                return entry
        return None

    user_id = getattr(call.context, "user_id", None)
    if user_id:
        for state in hass.states.async_all("person"):
            if state.attributes.get("user_id") == user_id:
                person_entity_id = state.entity_id
                for entry in domain_data.values():
                    if entry.get("person") == person_entity_id:
                        return entry

    if len(domain_data) == 1:
        return next(iter(domain_data.values()))

    return None


async def _apply_day(store: MenstruationStore, target: date, today: date) -> None:
    end_record = store.find_by_end(target)
    if end_record is not None:
        return

    start_record = store.find_by_start(target)
    if start_record is not None:
        await store.async_delete_period(uid=start_record.uid)
        return

    covering = store.find_covering(target)
    if covering is not None:
        await store.async_update_period(uid=covering.uid, start=covering.start, end=target)
        return

    last = store.find_latest_start_on_or_before(target)
    if last is not None and (target - last.start).days <= 7:
        await store.async_update_period(uid=last.uid, start=last.start, end=target)
        return

    if last is not None and last.end is None:
        auto_end = last.start + timedelta(days=3)
        auto_end = min(auto_end, today)
        await store.async_update_period(uid=last.uid, start=last.start, end=auto_end)

    new_end = None if target == today else min(target + timedelta(days=3), today)

    for record in store.find_starts_after_within(target, 7):
        await store.async_delete_period(uid=record.uid)

    await store.async_add_period(start=target, end=new_end)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
