from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 1800) -> None:
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        item = self._values.get(key)
        if item is None:
            return None
        if item.expires_at <= time.time():
            self._values.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: T) -> None:
        self._values[key] = _Entry(expires_at=time.time() + self.ttl_seconds, value=value)

    def clear(self) -> None:
        self._values.clear()
