from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_NAME, DOMAIN
from .coordinator import MenstruationCoordinator, MenstruationState, compute_state
from .errors import MenstruationError
from .i18n import cal, err
from .store import MenstruationStore, PeriodRecord


def _overlaps(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end


def _to_local_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return dt_util.as_local(value).date()
    return value


def _event_dates(
    hass: HomeAssistant, start: date | datetime, end: date | datetime
) -> tuple[date, date]:
    start_d = _to_local_date(start)
    end_d = _to_local_date(end)
    if end_d <= start_d:
        raise HomeAssistantError(
            err(hass, "calendar_event_end_after_start", "Event end must be after start")
        )
    return start_d, end_d


def _is_period_summary(summary: str | None) -> bool:
    if not summary:
        return True
    lowered = summary.lower()
    keywords = [
        "period",
        "menstru",
        "regla",
        "règle",
        "règles",
        "月经",
        "经期",
        "生理",
        "월경",
        "생리",
        "менстру",
    ]
    return any(k in lowered or k in summary for k in keywords)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store: MenstruationStore = hass.data[DOMAIN][entry.entry_id]["store"]
    coordinator: MenstruationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name: str = entry.data.get(CONF_NAME, entry.title)

    async_add_entities([MenstruationCalendar(coordinator, store, entry.entry_id, name)])


class MenstruationCalendar(
    CoordinatorEntity[MenstruationCoordinator],
    CalendarEntity,
):
    _attr_icon = "mdi:calendar-heart"
    _attr_translation_key = "calendar"
    _attr_has_entity_name = True
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
    )

    def __init__(
        self,
        coordinator: MenstruationCoordinator,
        store: MenstruationStore,
        entry_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._store = store
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
        }
        self._attr_unique_id = f"{entry_id}_calendar"

    @property
    def _state(self) -> MenstruationState:
        return self.coordinator.data

    @property
    def event(self) -> CalendarEvent | None:
        state = self._state
        if state.is_period and state.last_start:
            return CalendarEvent(
                summary=cal(self.hass, "period_recorded", "Period (Recorded)"),
                start=state.last_start,
                end=state.today + timedelta(days=1),
            )

        return CalendarEvent(
            summary=cal(self.hass, "period_predicted", "Period (Predicted)"),
            start=state.predicted_start,
            end=state.predicted_end + timedelta(days=1),
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        await self._store.async_load()
        records = list(self._store.iter_records())

        start_d = dt_util.as_local(start_date).date()
        end_d = dt_util.as_local(end_date).date()

        events: list[CalendarEvent] = []
        events.extend(self._build_recorded_events(records, start_d, end_d))
        events.extend(self._build_predicted_events(start_d, end_d))
        return events

    async def async_create_event(self, **kwargs: Any) -> None:
        summary: str | None = kwargs.get("summary")
        if not _is_period_summary(summary):
            raise HomeAssistantError(err(self.hass, "calendar_only_period_create", "Only period events can be created on this calendar"))

        dtstart = kwargs.get("dtstart")
        dtend = kwargs.get("dtend")
        if dtstart is None or dtend is None:
            raise HomeAssistantError(err(self.hass, "calendar_dtstart_dtend_required", "dtstart and dtend are required"))

        start_d, end_excl_d = _event_dates(self.hass, dtstart, dtend)
        end_d = end_excl_d - timedelta(days=1)
        uid: str | None = kwargs.get("uid")

        await self._store.async_load()
        try:
            await self._store.async_add_period(start=start_d, end=end_d, uid=uid)
        except MenstruationError as exc:
            raise HomeAssistantError(err(self.hass, exc.key, exc.key)) from exc
        records = list(self._store.iter_records())
        self.coordinator.async_set_updated_data(compute_state(dt_util.now().date(), records))

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        summary = event.get("summary")
        if not _is_period_summary(summary):
            raise HomeAssistantError(err(self.hass, "calendar_only_period_update", "Only period events can be updated on this calendar"))

        dtstart = event.get("dtstart")
        dtend = event.get("dtend")
        if dtstart is None or dtend is None:
            raise HomeAssistantError(err(self.hass, "calendar_dtstart_dtend_required", "dtstart and dtend are required"))

        start_d, end_excl_d = _event_dates(self.hass, dtstart, dtend)
        end_d = end_excl_d - timedelta(days=1)

        await self._store.async_load()
        try:
            await self._store.async_update_period(uid=uid, start=start_d, end=end_d)
        except MenstruationError as exc:
            raise HomeAssistantError(err(self.hass, exc.key, exc.key)) from exc
        records = list(self._store.iter_records())
        self.coordinator.async_set_updated_data(compute_state(dt_util.now().date(), records))

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        await self._store.async_load()
        try:
            await self._store.async_delete_period(uid=uid)
        except MenstruationError as exc:
            raise HomeAssistantError(err(self.hass, exc.key, exc.key)) from exc
        records = list(self._store.iter_records())
        self.coordinator.async_set_updated_data(compute_state(dt_util.now().date(), records))

    def _build_recorded_events(
        self,
        records: list[PeriodRecord],
        start_d: date,
        end_d: date,
    ) -> list[CalendarEvent]:
        today = self._state.today
        events: list[CalendarEvent] = []

        for record in records:
            record_end = record.end or today
            if not _overlaps(record.start, record_end, start_d, end_d):
                continue
            events.append(
                CalendarEvent(
                    summary=cal(self.hass, "period_recorded", "Period (Recorded)"),
                    start=record.start,
                    end=record_end + timedelta(days=1),
                    uid=record.uid,
                )
            )

        return events

    def _build_predicted_events(self, start_d: date, end_d: date) -> list[CalendarEvent]:
        state = self._state
        events: list[CalendarEvent] = []

        if _overlaps(state.predicted_start, state.predicted_end, start_d, end_d):
            events.append(
                CalendarEvent(
                    summary=cal(self.hass, "period_predicted", "Period (Predicted)"),
                    start=state.predicted_start,
                    end=state.predicted_end + timedelta(days=1),
                )
            )

        if _overlaps(state.fertile_start, state.fertile_end, start_d, end_d):
            events.append(
                CalendarEvent(
                    summary=cal(self.hass, "fertile_predicted", "Fertile Window (Predicted)"),
                    start=state.fertile_start,
                    end=state.fertile_end + timedelta(days=1),
                )
            )

        return events
