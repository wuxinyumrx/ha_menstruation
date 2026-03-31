from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MenstruationError(Exception):
    key: str
    placeholders: dict[str, Any] = field(default_factory=dict)

