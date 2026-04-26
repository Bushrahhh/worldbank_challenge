"""
BaseAdapter — common HTTP + caching + retry logic for all data adapters.

Every adapter that hits an external API inherits from this. The pattern:
  1. Check disk cache — return immediately if fresh
  2. Fetch from API with exponential backoff retry
  3. On persistent failure — return stale cache if available, else propagate
  4. Every response includes a SourceCitation for the UI tooltip
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Optional

import httpx

from backend.adapters.cache import DiskCache
from backend.models.sourced_data import SourceCitation

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15.0   # seconds
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]   # exponential backoff


class BaseAdapter:
    source_name: str = "Unknown"
    source_url: str = ""
    cache_ttl_hours: int = 24

    def __init__(self):
        self.cache = DiskCache(
            namespace=self.__class__.__name__.lower(),
            ttl_hours=self.cache_ttl_hours,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT,
                headers={"User-Agent": "UNMAPPED/0.1 (open skills infrastructure; contact: unmapped@example.org)"},
                follow_redirects=True,
            )
        return self._client

    async def fetch_json(
        self,
        url: str,
        params: Optional[dict] = None,
        cache_key: Optional[str] = None,
        ttl_hours: Optional[int] = None,
    ) -> dict | list | None:
        """
        Fetch JSON from a URL. Returns cached data if fresh.
        Falls back to stale cache if the API is unreachable.
        Logs source + date for every successful fetch.
        """
        key = cache_key or self._cache_key(url, params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        client = await self._get_client()
        last_exc = None

        for attempt, delay in enumerate((_RETRY_DELAYS + [None])[:_MAX_RETRIES]):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                self.cache.set(key, data, ttl_hours=ttl_hours or self.cache_ttl_hours)
                logger.info(
                    "[%s] fetched %s → HTTP %s",
                    self.source_name, url[:80], resp.status_code,
                )
                return data
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "[%s] fetch attempt %d failed: %s — %s",
                    self.source_name, attempt + 1, url[:60], exc,
                )
                if delay:
                    await asyncio.sleep(delay)

        # All retries exhausted — try stale cache as fallback
        stale = self.cache.get_stale(key)
        if stale is not None:
            logger.warning(
                "[%s] API unreachable, using stale cache for %s",
                self.source_name, url[:60],
            )
            return stale

        logger.error(
            "[%s] all retries failed and no stale cache: %s — %s",
            self.source_name, url[:60], last_exc,
        )
        return None

    def _cache_key(self, url: str, params: Optional[dict]) -> str:
        if params:
            qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"{url}?{qs}"
        return url

    def cite(
        self,
        url: Optional[str] = None,
        data_date: str = "",
        confidence: str = "high",
        notes: Optional[str] = None,
    ) -> SourceCitation:
        return SourceCitation(
            name=self.source_name,
            url=url or self.source_url,
            data_date=data_date,
            accessed_at=datetime.utcnow(),
            confidence=confidence,  # type: ignore[arg-type]
            notes=notes,
        )

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
