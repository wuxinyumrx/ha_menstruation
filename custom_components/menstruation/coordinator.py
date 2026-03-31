from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import PHASE_OVULATION, PHASE_PERIOD, PHASE_SAFE
from .store import MenstruationStore, PeriodRecord


@dataclass(frozen=True)
class MenstruationState:
    today: date
    phase: str
    is_period: bool
    is_ovulation: bool
    is_safe: bool
    ovulation_day: date
    fertile_start: date
    fertile_end: date
    predicted_start: date
    predicted_end: date
    days_to_next_period: int
    days_to_ovulation: int
    cycle_day: int | None
    period_day: int | None
    cycle_length: int
    period_length: int
    last_start: date | None
    last_end: date | None

    def as_dict(self) -> dict:
        return {
            "today": self.today,
            "phase": self.phase,
            "is_period": self.is_period,
            "is_ovulation": self.is_ovulation,
            "is_safe": self.is_safe,
            "ovulation_day": self.ovulation_day,
            "fertile_start": self.fertile_start,
            "fertile_end": self.fertile_end,
            "predicted_start": self.predicted_start,
            "predicted_end": self.predicted_end,
            "days_to_next_period": self.days_to_next_period,
            "days_to_ovulation": self.days_to_ovulation,
            "cycle_day": self.cycle_day,
            "period_day": self.period_day,
            "cycle_length": self.cycle_length,
            "period_length": self.period_length,
            "last_start": self.last_start,
            "last_end": self.last_end,
        }


def _mean(values: list[int]) -> int | None:
    if not values:
        return None
    return max(1, round(sum(values) / len(values)))


def _compute_cycle_length(records: list[PeriodRecord]) -> int | None:
    starts = [r.start for r in records]
    if len(starts) < 2:
        return None
    diffs: list[int] = []
    for prev, cur in zip(starts, starts[1:]):
        diffs.append((cur - prev).days)
    return _mean([d for d in diffs if d > 0])


def _compute_period_length(records: list[PeriodRecord]) -> int | None:
    lengths: list[int] = []
    for r in records:
        if r.end is None:
            continue
        lengths.append((r.end - r.start).days + 1)
    return _mean([d for d in lengths if d > 0])


def _get_last_record(records: list[PeriodRecord]) -> PeriodRecord | None:
    if not records:
        return None
    return max(records, key=lambda r: r.start)


def _get_current_period_window(records: list[PeriodRecord], today: date) -> tuple[date, date] | None:
    ongoing = next((r for r in reversed(records) if r.end is None), None)
    if ongoing and ongoing.start <= today:
        return (ongoing.start, today)

    for r in reversed(records):
        if r.end is None:
            continue
        if r.start <= today <= r.end:
            return (r.start, r.end)

    return None


def _predict_next_window(
    today: date,
    records: list[PeriodRecord],
    cycle_length: int,
    period_length: int,
) -> tuple[date, date]:
    last = _get_last_record(records)
    anchor = last.start if last else today

    predicted_start = anchor + timedelta(days=cycle_length)
    while predicted_start <= today:
        predicted_start = predicted_start + timedelta(days=cycle_length)

    predicted_end = predicted_start + timedelta(days=max(1, period_length) - 1)
    return predicted_start, predicted_end


def compute_state(today: date, records: list[PeriodRecord]) -> MenstruationState:
    completed = [r for r in records if r.end is not None]
    cycle_length = _compute_cycle_length(completed) or 28
    period_length = _compute_period_length(completed) or 5

    predicted_start, predicted_end = _predict_next_window(
        today=today,
        records=records if records else completed,
        cycle_length=cycle_length,
        period_length=period_length,
    )

    current_window = _get_current_period_window(records, today)
    is_period = current_window is not None

    luteal_length = 14
    ovulation_day = predicted_start - timedelta(days=luteal_length)
    next_ovulation_day = ovulation_day
    while next_ovulation_day < today:
        next_ovulation_day = next_ovulation_day + timedelta(days=cycle_length)

    fertile_start = next_ovulation_day - timedelta(days=5)
    fertile_end = next_ovulation_day + timedelta(days=1)
    is_ovulation = fertile_start <= today <= fertile_end

    is_safe = not is_period and not is_ovulation

    if is_period:
        phase = PHASE_PERIOD
    elif is_ovulation:
        phase = PHASE_OVULATION
    else:
        phase = PHASE_SAFE

    last = _get_last_record(records)
    last_start = last.start if last else None
    last_end = last.end if last else None
    cycle_day = (today - last_start).days + 1 if last_start and last_start <= today else None
    period_day = (
        (today - current_window[0]).days + 1 if current_window else None
    )
    days_to_next_period = max(0, (predicted_start - today).days)
    days_to_ovulation = max(0, (next_ovulation_day - today).days)

    return MenstruationState(
        today=today,
        phase=phase,
        is_period=is_period,
        is_ovulation=is_ovulation,
        is_safe=is_safe,
        ovulation_day=next_ovulation_day,
        fertile_start=fertile_start,
        fertile_end=fertile_end,
        predicted_start=predicted_start,
        predicted_end=predicted_end,
        days_to_next_period=days_to_next_period,
        days_to_ovulation=days_to_ovulation,
        cycle_day=cycle_day,
        period_day=period_day,
        cycle_length=cycle_length,
        period_length=period_length,
        last_start=last_start,
        last_end=last_end,
    )


class MenstruationCoordinator(DataUpdateCoordinator[MenstruationState]):
    def __init__(self, hass: HomeAssistant, store: MenstruationStore) -> None:
        self._store = store
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="menstruation",
            update_interval=timedelta(hours=6),
        )

    async def _async_update_data(self) -> MenstruationState:
        await self._store.async_load()
        records = list(self._store.iter_records())

        now: datetime = dt_util.now()
        today: date = now.date()
        return compute_state(today=today, records=records)
