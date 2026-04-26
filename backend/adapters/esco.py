"""
ESCO Adapter

Searches and retrieves skills/occupations from the ESCO taxonomy
(European Skills, Competences, Qualifications and Occupations).

API docs: https://esco.ec.europa.eu/en/use-esco/esco-web-services
Base URL: https://esco.ec.europa.eu/api/
"""

import logging
from typing import Optional

from backend.adapters.base import BaseAdapter
from backend.models.sourced_data import DataUnavailable, ESCOSkill

logger = logging.getLogger(__name__)

_ESCO_BASE = "https://esco.ec.europa.eu/api"
_ESCO_VERSION = "1.2.0"   # current ESCO API version (v1.2.0 as of 2024)

# ESCO requires Accept: application/json header to avoid 403
_ESCO_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en",
}


class ESCOAdapter(BaseAdapter):
    source_name = "ESCO API"
    source_url = "https://esco.ec.europa.eu"
    cache_ttl_hours = 720  # 30 days — taxonomy is very stable

    async def _esco_get(self, url: str, params: dict, cache_key: str) -> dict | None:
        """ESCO-specific fetch with required Accept header."""
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        import asyncio
        client = await self._get_client()
        for attempt, delay in enumerate([1.0, 2.0, None]):
            try:
                resp = await client.get(url, params=params, headers=_ESCO_HEADERS)
                resp.raise_for_status()
                data = resp.json()
                self.cache.set(cache_key, data)
                return data
            except Exception as exc:
                logger.warning("[ESCO] attempt %d failed: %s", attempt + 1, exc)
                if delay:
                    await asyncio.sleep(delay)

        stale = self.cache.get_stale(cache_key)
        return stale

    async def search_skills(
        self,
        text: str,
        language: str = "en",
        limit: int = 10,
    ) -> list[ESCOSkill] | DataUnavailable:
        """Search ESCO taxonomy for skills matching a text query."""
        url = f"{_ESCO_BASE}/search"
        params = {
            "text": text,
            "type": "skill",
            "language": language,
            "limit": limit,
            "full": "false",
        }
        cache_key = f"esco_search_{language}_{text[:50]}_{limit}"
        raw = await self._esco_get(url, params=params, cache_key=cache_key)

        if raw is None:
            return DataUnavailable(
                requested_for=f"esco_search/{text}",
                reason="ESCO API unavailable",
                source=self.cite(confidence="low"),
            )

        try:
            results = raw.get("_embedded", {}).get("results", [])
            skills = [self._parse_skill(r) for r in results if r]
            return [s for s in skills if s is not None]
        except Exception as exc:
            logger.warning("ESCO search parse error for '%s': %s", text, exc)
            return DataUnavailable(
                requested_for=f"esco_search/{text}",
                reason=str(exc),
                source=self.cite(confidence="low"),
            )

    async def search_occupations(
        self,
        text: str,
        language: str = "en",
        limit: int = 10,
    ) -> list[dict] | DataUnavailable:
        """Search ESCO for occupations matching a text query."""
        url = f"{_ESCO_BASE}/search"
        params = {
            "text": text,
            "type": "occupation",
            "language": language,
            "limit": limit,
        }
        cache_key = f"esco_occ_{language}_{text[:50]}"
        raw = await self._esco_get(url, params=params, cache_key=cache_key)

        if raw is None:
            return DataUnavailable(
                requested_for=f"esco_occupation/{text}",
                reason="ESCO API unavailable",
                source=self.cite(confidence="low"),
            )

        results = raw.get("_embedded", {}).get("results", [])
        citation = self.cite(
            url=url,
            data_date=f"ESCO v{_ESCO_VERSION}",
            confidence="high",
        )
        return [
            {
                "uri": r.get("uri"),
                "title": r.get("title"),
                "isco_group": r.get("iscoGroup", {}).get("code"),
                "description": r.get("description", {}).get("en", {}).get("literal"),
                "source": citation.model_dump(),
            }
            for r in results
        ]

    async def get_skill(
        self, uri: str, language: str = "en"
    ) -> ESCOSkill | DataUnavailable:
        """Retrieve a specific ESCO skill by its URI."""
        url = f"{_ESCO_BASE}/resource/skill"
        params = {"uri": uri, "language": language}
        cache_key = f"esco_skill_{uri}"
        raw = await self._esco_get(url, params=params, cache_key=cache_key)

        if raw is None:
            return DataUnavailable(
                requested_for=f"esco_skill/{uri}",
                reason="ESCO API unavailable",
                source=self.cite(confidence="low"),
            )

        skill = self._parse_skill(raw)
        if skill:
            return skill
        return DataUnavailable(
            requested_for=f"esco_skill/{uri}",
            reason="Could not parse ESCO skill response",
            source=self.cite(confidence="low"),
        )

    async def get_related_skills(
        self, uri: str, language: str = "en", limit: int = 8
    ) -> list[ESCOSkill]:
        """
        Get skills adjacent to a given skill — used for the Constellation Map.
        Returns narrower skills + broader skills + skills in same occupation group.
        """
        skill = await self.get_skill(uri, language)
        if isinstance(skill, DataUnavailable):
            return []

        related: list[ESCOSkill] = []

        # Fetch broader skills (one level up)
        for broader_uri in skill.broader_skills[:3]:
            s = await self.get_skill(broader_uri, language)
            if isinstance(s, ESCOSkill):
                related.append(s)

        # Fetch narrower skills (one level down)
        for narrower_uri in skill.narrower_skills[:5]:
            s = await self.get_skill(narrower_uri, language)
            if isinstance(s, ESCOSkill):
                related.append(s)

        return related[:limit]

    def _parse_skill(self, raw: dict) -> Optional[ESCOSkill]:
        try:
            uri = raw.get("uri") or raw.get("conceptUri")
            title = raw.get("title") or raw.get("preferredLabel", {}).get("en", "")
            if not uri or not title:
                return None

            description_obj = raw.get("description", {})
            description = None
            if isinstance(description_obj, dict):
                description = description_obj.get("en", {}).get("literal")

            # Extract ISCO groups if present
            isco_groups = []
            iscos = raw.get("hasEssentialSkillFor", []) or raw.get("iscoGroup", [])
            if isinstance(iscos, dict):
                code = iscos.get("code")
                if code:
                    isco_groups = [code]
            elif isinstance(iscos, list):
                isco_groups = [i.get("code", "") for i in iscos if i.get("code")]

            # Extract hierarchy
            broader = [r.get("uri") or r.get("conceptUri", "") for r in raw.get("broaderSkill", []) or []]
            narrower = [r.get("uri") or r.get("conceptUri", "") for r in raw.get("narrowerSkill", []) or []]

            return ESCOSkill(
                uri=uri,
                preferred_label=str(title),
                description=description,
                skill_type=raw.get("skillType"),
                isco_groups=isco_groups,
                broader_skills=[b for b in broader if b],
                narrower_skills=[n for n in narrower if n],
                source=self.cite(
                    url=uri,
                    data_date=f"ESCO v{_ESCO_VERSION}",
                    confidence="high",
                ),
            )
        except Exception as exc:
            logger.debug("ESCO skill parse error: %s | raw keys: %s", exc, list(raw.keys()))
            return None
