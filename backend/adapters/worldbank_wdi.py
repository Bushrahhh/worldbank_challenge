"""
World Bank WDI Adapter

Pulls sector employment growth and education returns from the
World Bank Development Indicators REST API.

API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
Base URL: https://api.worldbank.org/v2/
"""

import logging
from typing import Optional

from backend.adapters.base import BaseAdapter
from backend.models.sourced_data import DataUnavailable, SectorGrowth, SourcedFloat

logger = logging.getLogger(__name__)

_WB_BASE = "https://api.worldbank.org/v2"

# WDI indicator codes used in UNMAPPED
WDI_INDICATORS = {
    # Employment share by sector (% of total employment)
    "empl_agriculture": "SL.AGR.EMPL.ZS",
    "empl_industry": "SL.IND.EMPL.ZS",
    "empl_services": "SL.SRV.EMPL.ZS",
    # Value added by sector (% of GDP)
    "gdp_agriculture": "NV.AGR.TOTL.ZS",
    "gdp_industry": "NV.IND.TOTL.ZS",
    "gdp_services": "NV.SRV.TOTL.ZS",
    # Education
    "school_enrollment_secondary": "SE.SEC.ENRR",
    "school_enrollment_tertiary": "SE.TER.ENRR",
    "literacy_rate": "SE.ADT.LITR.ZS",
    # Poverty / income
    "poverty_headcount_550": "SI.POV.DDAY",   # $5.50/day
    "gdp_per_capita": "NY.GDP.PCAP.CD",
}

SECTOR_LABELS = {
    "empl_agriculture": "Agriculture",
    "empl_industry": "Industry & Manufacturing",
    "empl_services": "Services",
}


class WorldBankWDIAdapter(BaseAdapter):
    source_name = "World Bank WDI"
    source_url = "https://data.worldbank.org"
    cache_ttl_hours = 168  # 1 week

    async def get_indicator(
        self,
        country_iso2: str,   # WB uses ISO 3166-1 alpha-2 (GH not GHA)
        indicator_key: str,
        years: int = 5,
    ) -> SourcedFloat | DataUnavailable:
        """
        Fetch a single WDI indicator for a country.
        Returns the most recent non-null value.
        """
        indicator_code = WDI_INDICATORS.get(indicator_key)
        if not indicator_code:
            return DataUnavailable(
                requested_for=indicator_key,
                reason=f"Unknown WDI indicator key: {indicator_key}",
                source=self.cite(confidence="low"),
            )

        url = f"{_WB_BASE}/country/{country_iso2}/indicator/{indicator_code}"
        params = {
            "format": "json",
            "mrv": years,     # most recent values
            "per_page": 10,
        }
        cache_key = f"wdi_{country_iso2}_{indicator_key}"
        raw = await self.fetch_json(url, params=params, cache_key=cache_key)

        if raw is None or len(raw) < 2:
            return DataUnavailable(
                requested_for=f"{indicator_key}/{country_iso2}",
                reason="World Bank WDI API unavailable or no data",
                source=self.cite(confidence="low"),
            )

        try:
            return self._parse_indicator(raw, country_iso2, indicator_key, indicator_code)
        except Exception as exc:
            logger.warning("WDI parse error %s/%s: %s", country_iso2, indicator_key, exc)
            return DataUnavailable(
                requested_for=f"{indicator_key}/{country_iso2}",
                reason=f"Parse error: {exc}",
                source=self.cite(confidence="low"),
            )

    def _parse_indicator(
        self, raw: list, country_iso2: str, indicator_key: str, indicator_code: str
    ) -> SourcedFloat | DataUnavailable:
        entries = raw[1] if len(raw) > 1 else []
        for entry in entries:
            value = entry.get("value")
            if value is not None:
                period = entry.get("date", "unknown")
                return SourcedFloat(
                    value=round(float(value), 3),
                    unit="%",
                    source=self.cite(
                        url=f"{_WB_BASE}/country/{country_iso2}/indicator/{indicator_code}",
                        data_date=str(period),
                        confidence="high",
                        notes=f"World Bank WDI {indicator_code}",
                    ),
                )
        return DataUnavailable(
            requested_for=f"{indicator_key}/{country_iso2}",
            reason="No non-null values in response",
            source=self.cite(confidence="low", notes="Data series may have gaps for this country"),
        )

    async def get_sector_growth(
        self,
        country_iso2: str,
        sector: str = "empl_services",
    ) -> SectorGrowth | DataUnavailable:
        """
        Compute year-over-year sector employment growth from WDI data.
        sector: "empl_agriculture" | "empl_industry" | "empl_services"
        """
        indicator_code = WDI_INDICATORS.get(sector)
        if not indicator_code:
            return DataUnavailable(
                requested_for=sector,
                reason=f"Unknown sector key: {sector}",
                source=self.cite(confidence="low"),
            )

        url = f"{_WB_BASE}/country/{country_iso2}/indicator/{indicator_code}"
        params = {"format": "json", "mrv": 6, "per_page": 10}
        cache_key = f"wdi_sector_{country_iso2}_{sector}"
        raw = await self.fetch_json(url, params=params, cache_key=cache_key)

        if raw is None or len(raw) < 2:
            return DataUnavailable(
                requested_for=f"sector_growth/{sector}/{country_iso2}",
                reason="WDI data unavailable",
                source=self.cite(confidence="low"),
            )

        try:
            entries = [e for e in (raw[1] or []) if e.get("value") is not None]
            if len(entries) < 2:
                return DataUnavailable(
                    requested_for=f"sector_growth/{sector}/{country_iso2}",
                    reason="Insufficient data points to compute growth",
                    source=self.cite(confidence="low"),
                )

            # entries are newest-first from WB API
            latest = entries[0]
            previous = entries[1]
            latest_val = float(latest["value"])
            prev_val = float(previous["value"])

            growth_rate = (latest_val - prev_val) / prev_val if prev_val else 0.0
            sector_label = SECTOR_LABELS.get(sector, sector)

            return SectorGrowth(
                sector_label=sector_label,
                isic_code=None,
                country_iso=country_iso2,
                growth_rate=round(growth_rate, 4),
                base_year=int(previous.get("date", 2021)),
                latest_year=int(latest.get("date", 2022)),
                source=self.cite(
                    url=f"{_WB_BASE}/country/{country_iso2}/indicator/{indicator_code}",
                    data_date=str(latest.get("date")),
                    confidence="high",
                    notes=f"WDI {indicator_code} — year-over-year change in employment share",
                ),
            )
        except Exception as exc:
            logger.warning("WDI sector growth parse error: %s", exc)
            return DataUnavailable(
                requested_for=f"sector_growth/{sector}/{country_iso2}",
                reason=str(exc),
                source=self.cite(confidence="low"),
            )

    async def get_multiple_indicators(
        self, country_iso2: str, indicator_keys: list[str]
    ) -> dict[str, SourcedFloat | DataUnavailable]:
        """Fetch multiple indicators in parallel."""
        import asyncio
        tasks = {key: self.get_indicator(country_iso2, key) for key in indicator_keys}
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)
        return dict(zip(tasks.keys(), results))


# ISO 3166-1 alpha-3 → alpha-2 mapping for WB API (which uses alpha-2)
ISO3_TO_ISO2 = {
    "GHA": "GH",
    "BGD": "BD",
    "KEN": "KE",
    "NGA": "NG",
    "ETH": "ET",
    "TZA": "TZ",
    "UGA": "UG",
    "ZMB": "ZM",
    "MOZ": "MZ",
    "MWI": "MW",
    "IND": "IN",
    "NPL": "NP",
    "KHM": "KH",
    "MMR": "MM",
    "LAO": "LA",
}


def iso3_to_iso2(iso3: str) -> str:
    return ISO3_TO_ISO2.get(iso3.upper(), iso3[:2])
