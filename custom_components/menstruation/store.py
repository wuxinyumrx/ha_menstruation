from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
import uuid
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .errors import MenstruationError


@dataclass(frozen=True)
class PeriodRecord:
    uid: str
    start: date
    end: date | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "PeriodRecord":
        uid_raw = raw.get("uid")
        start_raw = raw.get("start")
        end_raw = raw.get("end")
        if not isinstance(start_raw, str):
            raise MenstruationError("invalid_record_missing_start")

        return PeriodRecord(
            uid=uid_raw if isinstance(uid_raw, str) and uid_raw else start_raw,
            start=date.fromisoformat(start_raw),
            end=date.fromisoformat(end_raw) if isinstance(end_raw, str) else None,
        )


class MenstruationStore:
    def __init__(self, hass: HomeAssistant, storage_key: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, storage_key, private=True
        )
        self._records: list[PeriodRecord] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            self._records = []
            return

        raw_records = data.get("records", [])
        if not isinstance(raw_records, list):
            self._records = []
            return

        records: list[PeriodRecord] = []
        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            try:
                records.append(PeriodRecord.from_dict(raw))
            except (MenstruationError, ValueError):
                continue

        self._records = sorted(records, key=lambda r: r.start)
        self._ensure_unique_uids()

    async def async_save(self) -> None:
        await self._store.async_save({"records": [r.to_dict() for r in self._records]})

    def iter_records(self) -> Iterable[PeriodRecord]:
        return tuple(self._records)

    def get_ongoing(self) -> PeriodRecord | None:
        for record in reversed(self._records):
            if record.end is None:
                return record
        return None

    def get_last(self) -> PeriodRecord | None:
        if not self._records:
            return None
        return max(self._records, key=lambda r: r.start)

    def find_by_start(self, day: date) -> PeriodRecord | None:
        for record in self._records:
            if record.start == day:
                return record
        return None

    def find_by_end(self, day: date) -> PeriodRecord | None:
        for record in self._records:
            if record.end == day:
                return record
        return None

    def find_covering(self, day: date) -> PeriodRecord | None:
        for record in reversed(self._records):
            if record.end is None:
                continue
            if record.start <= day <= record.end:
                return record
        return None

    def find_latest_start_on_or_before(self, day: date) -> PeriodRecord | None:
        candidate: PeriodRecord | None = None
        for record in self._records:
            if record.start <= day and (candidate is None or record.start > candidate.start):
                candidate = record
        return candidate

    def find_starts_after_within(self, start_day: date, max_days: int) -> list[PeriodRecord]:
        if max_days < 0:
            return []
        result: list[PeriodRecord] = []
        for record in self._records:
            if record.start <= start_day:
                continue
            if (record.start - start_day).days <= max_days:
                result.append(record)
        return result

    async def async_add_period(
        self,
        start: date,
        end: date | None,
        uid: str | None = None,
    ) -> PeriodRecord:
        if end is not None and end < start:
            raise MenstruationError("end_before_start")
        if end is None and self.get_ongoing():
            raise MenstruationError("ongoing_exists")

        record = PeriodRecord(uid=uid or uuid.uuid4().hex, start=start, end=end)
        self._records.append(record)
        self._records.sort(key=lambda r: r.start)
        self._ensure_unique_uids()
        await self.async_save()
        return record

    async def async_update_period(
        self,
        uid: str,
        start: date,
        end: date | None,
    ) -> PeriodRecord:
        if end is not None and end < start:
            raise MenstruationError("end_before_start")
        if end is None and self.get_ongoing() and self.get_ongoing().uid != uid:
            raise MenstruationError("ongoing_exists")

        for idx, record in enumerate(self._records):
            if record.uid != uid:
                continue
            updated = PeriodRecord(uid=uid, start=start, end=end)
            self._records[idx] = updated
            self._records.sort(key=lambda r: r.start)
            self._ensure_unique_uids()
            await self.async_save()
            return updated

        raise MenstruationError("record_not_found")

    async def async_delete_period(self, uid: str) -> None:
        before = len(self._records)
        self._records = [r for r in self._records if r.uid != uid]
        if len(self._records) == before:
            raise MenstruationError("record_not_found")
        await self.async_save()

    def _ensure_unique_uids(self) -> None:
        seen: set[str] = set()
        updated: list[PeriodRecord] = []
        for record in self._records:
            uid = record.uid or record.start.isoformat()
            if uid not in seen:
                seen.add(uid)
                updated.append(PeriodRecord(uid=uid, start=record.start, end=record.end))
                continue

            new_uid = uid
            while new_uid in seen:
                new_uid = f"{uid}_{uuid.uuid4().hex[:8]}"
            seen.add(new_uid)
            updated.append(PeriodRecord(uid=new_uid, start=record.start, end=record.end))

        self._records = updated
