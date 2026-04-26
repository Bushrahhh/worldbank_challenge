"""
Disk-based JSON cache for adapter responses.

Cache layout:  data/cache/{adapter_name}/{sha256(key)}.json
Each entry:    {"data": ..., "cached_at": ISO8601, "ttl_hours": N}
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CACHE_ROOT = Path(__file__).parent.parent.parent / "data" / "cache"


class DiskCache:
    def __init__(self, namespace: str, ttl_hours: int = 24):
        self.namespace = namespace
        self.ttl_hours = ttl_hours
        self.cache_dir = _CACHE_ROOT / namespace
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.utcnow() - cached_at > timedelta(hours=entry.get("ttl_hours", self.ttl_hours)):
                logger.debug("cache STALE: %s/%s", self.namespace, key[:40])
                return None
            logger.debug("cache HIT: %s/%s", self.namespace, key[:40])
            return entry["data"]
        except Exception as exc:
            logger.warning("cache read error (%s): %s", path, exc)
            return None

    def set(self, key: str, data: Any, ttl_hours: Optional[int] = None) -> None:
        path = self._path(key)
        entry = {
            "data": data,
            "cached_at": datetime.utcnow().isoformat(),
            "ttl_hours": ttl_hours or self.ttl_hours,
            "key_preview": key[:80],
        }
        try:
            path.write_text(json.dumps(entry, ensure_ascii=False, default=str), encoding="utf-8")
            logger.debug("cache SET: %s/%s", self.namespace, key[:40])
        except Exception as exc:
            logger.warning("cache write error (%s): %s", path, exc)

    def get_stale(self, key: str) -> Optional[Any]:
        """Return cached value even if stale — used as fallback when API is down."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            logger.info("cache STALE FALLBACK: %s/%s", self.namespace, key[:40])
            return entry["data"]
        except Exception:
            return None

    def cached_at(self, key: str) -> Optional[datetime]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            return datetime.fromisoformat(entry["cached_at"])
        except Exception:
            return None
