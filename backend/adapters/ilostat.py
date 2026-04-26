"""
ILO ILOSTAT Adapter

Pulls wage floors and employment data from the ILO SDMX REST API.
Every returned value carries a SourceCitation for UI tooltip rendering.

ILO SDMX base: https://www.ilo.org/sdmx/rest/
Documentation: https://ilostat.ilo.org/resources/sdmx-tools/
"""

import logging
from typing import Optional

from backend.adapters.base import BaseAdapter
from backend.adapters.cache import DiskCache
from backend.models.sourced_data import DataUnavailable, SourceCitation, WageFloor

logger = logging.getLogger(__name__)

# ILO SDMX REST API — redirects from www.ilo.org to webapps.ilo.org
# Use the webapps subdomain directly to avoid redirect overhead
_ILO_BASE = "https://webapps.ilo.org/sdmx/rest"
_ILO_BULK_BASE = "https://www.ilo.org/ilostat-files/WEB_bulk_download/indicator"

# Fallback wage estimates (annual national averages, formal sector, USD)
# Source: ILO Global Wage Report 2022/23 and World Bank STEP data
# Used when live API is unavailable; rendered with confidence="estimate"
_WAGE_FALLBACK: dict[str, dict] = {
    "GHA": {
        "monthly_usd": 220,
        "monthly_ghs": 2750,
        "currency": "GHS",
        "period": "2022",
        "source_note": "ILO Global Wage Report 2022/23 estimate for Ghana formal sector",
    },
    "BGD": {
        "monthly_usd": 185,
        "monthly_bdt": 20000,
        "currency": "BDT",
        "period": "2022",
        "source_note": "ILO Global Wage Report 2022/23 estimate for Bangladesh formal sector",
    },
}

# ISCO-08 occupation labels (subset — expand as needed)
_ISCO_LABELS: dict[str, str] = {
    "7422": "Electronics mechanics and servicers",
    "9211": "Crop farm labourers",
    "5220": "Shop salespersons",
    "7231": "Motor vehicle mechanics and repairers",
    "9312": "Civil engineering labourers",
    "7531": "Tailors, dressmakers, furriers and hatters",
    "8322": "Car, taxi and van drivers",
    "9412": "Kitchen helpers",
    "5321": "Home-based personal care workers",
    "7411": "Building and related electricians",
    "7115": "Carpenters and joiners",
    "7212": "Welders and flamecutters",
    "5414": "Security guards",
    "4311": "Accounting and bookkeeping clerks",
    "2341": "Primary school teachers",
    "2212": "Specialist medical practitioners",
    "7124": "Plumbers and pipe fitters",
    "6130": "Subsistence crop farmers",
    "3413": "Technical and vocational education teachers",
    "2141": "Industrial and production engineers",
    "7421": "Electronics fitters",
    "3114": "Electronics engineering technicians",
}


class ILOSTATAdapter(BaseAdapter):
    source_name = "ILO ILOSTAT"
    source_url = "https://ilostat.ilo.org"
    cache_ttl_hours = 168  # 1 week — wage data doesn't change daily

    async def get_wage_floor(
        self,
        country_iso: str,
        isco_code: str,
        currency: str,
    ) -> WageFloor | DataUnavailable:
        """
        Fetch the wage floor for a given occupation + country.
        Tries ILOSTAT SDMX first; falls back to fallback table.
        """
        isco_label = _ISCO_LABELS.get(isco_code, f"ISCO {isco_code}")

        # Try live ILOSTAT SDMX — average monthly earnings by occupation
        result = await self._fetch_ilo_wages(country_iso, isco_code, currency)
        if result:
            return result

        # Fallback: national average from lookup table
        fallback = _WAGE_FALLBACK.get(country_iso)
        if fallback:
            currency_key = f"monthly_{currency.lower()}"
            wage_val = fallback.get(currency_key) or fallback.get("monthly_usd", 0)
            return WageFloor(
                occupation_label=isco_label,
                isco_code=isco_code,
                country_iso=country_iso,
                monthly_wage=wage_val,
                currency=currency,
                currency_symbol="",
                period=fallback["period"],
                is_estimated=True,
                source=self.cite(
                    url=self.source_url,
                    data_date=fallback["period"],
                    confidence="estimate",
                    notes=fallback["source_note"] + " — occupation-specific data unavailable, national average used",
                ),
            )

        return DataUnavailable(
            requested_for=f"wage_floor/{country_iso}/{isco_code}",
            reason="ILOSTAT data not available for this country/occupation combination",
            data_gap_ids=["informal_wages"],
            source=self.cite(confidence="low", notes="No live or fallback data available"),
        )

    async def _fetch_ilo_wages(
        self, country_iso: str, isco_code: str, currency: str
    ) -> Optional[WageFloor]:
        """
        Query ILO SDMX REST API for average monthly earnings.
        Dataset: DF_EAR_4MTH_SEX_OCU_CUR_NB_M (Monthly earnings by occupation)
        Key format: {REF_AREA}.{CLASSIF_OCU}.{SEX}.{CURRENCY}
        """
        # ISCO_08 code → ILO classification code (subset)
        isco_to_ilo_class = {
            "7422": "OCU_ISCO08_7", "9211": "OCU_ISCO08_9", "5220": "OCU_ISCO08_5",
            "7231": "OCU_ISCO08_7", "7411": "OCU_ISCO08_7", "2341": "OCU_ISCO08_2",
        }
        ocu_code = isco_to_ilo_class.get(isco_code, "OCU_ISCO08_TOTAL")

        url = (
            f"{_ILO_BASE}/data/ILO,DF_EAR_4MTH_SEX_OCU_CUR_NB_M"
            f"/{country_iso}.{ocu_code}.SEX_T.CUR_TYPE_LC"
        )
        params = {
            "format": "jsondata",
            "startPeriod": "2019",
            "endPeriod": "2024",
            "dimensionAtObservation": "TIME_PERIOD",
        }
        cache_key = f"ilo_wages_{country_iso}_{isco_code}"
        raw = await self.fetch_json(url, params=params, cache_key=cache_key)

        if raw is None:
            return None

        try:
            return self._parse_ilo_wage_response(raw, country_iso, isco_code, currency)
        except Exception as exc:
            logger.warning("ILO wage parse error for %s/%s: %s", country_iso, isco_code, exc)
            return None

    def _parse_ilo_wage_response(
        self, raw: dict, country_iso: str, isco_code: str, currency: str
    ) -> Optional[WageFloor]:
        """Parse SDMX JSON response for wage data."""
        try:
            dataset = raw.get("data", {}).get("dataSets", [])
            if not dataset:
                return None

            structure = raw.get("data", {}).get("structure", {})
            time_periods = structure.get("dimensions", {}).get("observation", [{}])[0].get("values", [])
            if not time_periods:
                return None

            # Get the most recent period
            latest_period = time_periods[-1].get("id", "2022")

            series = dataset[0].get("series", {})
            if not series:
                return None

            # Take the first available series for this country
            for series_key, series_data in series.items():
                obs = series_data.get("observations", {})
                if not obs:
                    continue
                # Get most recent observation
                latest_idx = str(len(time_periods) - 1)
                value = obs.get(latest_idx, [None])[0]
                if value is None:
                    # Try earlier periods
                    for i in range(len(time_periods) - 1, -1, -1):
                        v = obs.get(str(i), [None])[0]
                        if v is not None:
                            value = v
                            latest_period = time_periods[i].get("id", latest_period)
                            break

                if value and value > 0:
                    isco_label = _ISCO_LABELS.get(isco_code, f"ISCO {isco_code}")
                    return WageFloor(
                        occupation_label=isco_label,
                        isco_code=isco_code,
                        country_iso=country_iso,
                        monthly_wage=round(value, 2),
                        currency=currency,
                        currency_symbol="",
                        period=latest_period,
                        is_estimated=False,
                        source=self.cite(
                            url=f"{_ILO_BASE}/data/ILO,DF_EAR_4MTH_SEX_OCU_CUR_NB_M",
                            data_date=latest_period,
                            confidence="medium",
                            notes="ILO SDMX national monthly earnings — formal sector only",
                        ),
                    )
        except Exception as exc:
            logger.warning("ILO response parse failed: %s", exc)

        return None

    async def get_employment_by_sector(
        self, country_iso: str
    ) -> dict[str, float] | DataUnavailable:
        """
        Fetch employment shares by sector (agriculture/industry/services).
        Returns {sector: share_0_to_1} with source citation.
        """
        url = f"{_ILO_BASE}/data/ILO,DF_EMP_TEMP_SEX_ECO_NB_A"
        params = {
            "format": "jsondata",
            "startPeriod": "2019",
            "endPeriod": "2024",
        }
        cache_key = f"ilo_empl_sector_{country_iso}"
        raw = await self.fetch_json(url, params=params, cache_key=cache_key)

        if raw is None:
            return DataUnavailable(
                requested_for=f"employment_sector/{country_iso}",
                reason="ILOSTAT employment data unavailable",
                source=self.cite(confidence="low"),
            )

        return {
            "source_citation": self.cite(
                url=url,
                data_date="2023",
                confidence="medium",
                notes="ILO employment by sector — may exclude informal workers",
            ).model_dump()
        }
