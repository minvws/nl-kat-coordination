import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional


def deep_get(d: Optional[Any], keys: List[str]) -> Any:
    if not keys or d is None:
        return d
    return deep_get(d.get(keys[0]), keys[1:])


class ExpiredError(Exception):
    pass


class ExpiringDict:
    def __init__(self, lifetime: int = 300):
        self.lifetime: timedelta = timedelta(seconds=lifetime)
        self.expiration_time: datetime = datetime.now(timezone.utc) + self.lifetime
        self.lock: threading.Lock = threading.Lock()
        self.cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self[key] if key in self else default

    def __getitem__(self, key: str) -> Any:
        with self.lock:
            if key not in self.cache:
                raise KeyError(key)

            if datetime.now(timezone.utc) > self.expiration_time:
                self.cache.clear()
                self.expiration_time = datetime.now(timezone.utc) + self.lifetime
                raise ExpiredError

            return self.cache[key]

    def __setitem__(self, key: str, value: Any) -> None:
        with self.lock:
            self.cache[key] = value
            self.expiration_time = datetime.now(timezone.utc) + self.lifetime

    def __delitem__(self, key: str) -> None:
        with self.lock:
            del self.cache[key]

    def __contains__(self, key: str) -> bool:
        with self.lock:
            return key in self.cache

    def __len__(self) -> int:
        with self.lock:
            return len(self.cache)

    def __iter__(self) -> Iterator[str]:
        with self.lock:
            return iter(self.cache)
