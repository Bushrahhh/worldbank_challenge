"""
Wittgenstein Centre Adapter

Loads education attainment projections for 2025–2035 from the
Wittgenstein Centre for Demography and Global Human Capital.

Data: WIC 2023 projections (SSP1/SSP2/SSP3 scenarios)
Source: https://www.wittgensteincentre.org/dataexplorer/
Download: see data/download_datasets.py

Seed data bundled in data/seed_wittgenstein.csv for the demo.
Full data download gets you all countries + 5-year intervals to 2100.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.models.sourced_data import DataUnavailable, SourceCitation, WittgensteinProjection

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SEED_PATH = _DATA_DIR / "seed_wittgenstein.csv"
_FULL_PATH = _DATA_DIR / "wittgenstein_2035.csv"

_SOURCE_CITATION = SourceCitation(
    name="Wittgenstein Centre (WIC 2023)",
    url="https://www.wittgensteincentre.org/dataexplorer/",
    data_date="2023",
    confidence="medium",
    notes=(
        "Wittgenstein Centre for Demography and Global Human Capital, 2023 revision. "
        "SSP scenarios: SSP1=fast progress, SSP2=medium, SSP3=slow. "
        "Projection uncertainty ±40% at district level. "
        "See data gap disclosure 'displacement_projections'."
    ),
)

# ISCED levels → UNMAPPED education tier mapping
WIC_TO_ISCED = {
    "e1": 0, "e2": 1, "e3": 1, "e4": 2, "e5": 3, "e6": 4, "e7": 5, "e8": 6,
}

SCENARIO_LABELS = {
    "SSP1": "Rapid progress (optimistic)",
    "SSP2": "Medium (most likely)",
    "SSP3": "Slow progress (challenging)",
}


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    path = _FULL_PATH if _FULL_PATH.exists() else _SEED_PATH
    if not path.exists():
        logger.error("No Wittgenstein data at %s or %s", _FULL_PATH, _SEED_PATH)
        return pd.DataFrame()
    df = pd.read_csv(path, dtype={"country_iso3": str})
    logger.info("Loaded Wittgenstein data: %d rows from %s", len(df), path.name)
    return df


class WittgensteinAdapter:
    """
    Local-file adapter for Wittgenstein Centre education projections.
    No network required — data loaded from CSV at startup.
    """

    def get_projections(
        self,
        country_iso3: str,
        years: list[int] | None = None,
        scenario: str = "SSP2",
        age_group: str = "25-64",
    ) -> list[WittgensteinProjection] | DataUnavailable:
        """
        Return education attainment projections for a country.
        Default: SSP2 (medium scenario), working-age adults 25-64.
        """
        df = _load_dataframe()
        if df.empty:
            return DataUnavailable(
                requested_for=f"wic_projections/{country_iso3}",
                reason="Wittgenstein CSV not loaded",
                fallback_used=None,
                data_gap_ids=["displacement_projections"],
                source=_SOURCE_CITATION,
            )

        mask = (
            (df["country_iso3"] == country_iso3.upper())
            & (df["scenario"] == scenario)
            & (df["age_group"] == age_group)
        )
        if years:
            mask &= df["year"].isin(years)

        rows = df[mask]
        if rows.empty:
            return DataUnavailable(
                requested_for=f"wic_projections/{country_iso3}/{scenario}",
                reason=f"No data for {country_iso3}/{scenario}/{age_group}",
                data_gap_ids=["displacement_projections"],
                source=SourceCitation(
                    **_SOURCE_CITATION.model_dump(exclude={"confidence", "notes"}),
                    confidence="estimate",
                    notes=f"Country {country_iso3} not in seed dataset. Download full WIC data.",
                ),
            )

        return [
            WittgensteinProjection(
                country_iso=country_iso3,
                year=int(row["year"]),
                scenario=scenario,
                education_level=str(row["education_level"]),
                education_label=str(row["education_label"]),
                population_share=float(row["population_share"]),
                source=_SOURCE_CITATION,
            )
            for _, row in rows.iterrows()
        ]

    def get_time_machine_data(
        self,
        country_iso3: str,
        base_year: int = 2025,
        target_year: int = 2035,
    ) -> dict:
        """
        Build the data for the Time Machine 2035 four-panel view.

        Returns:
            today:      education distribution now (base_year)
            do_nothing: SSP3 (slow scenario) at target_year
            path_a:     SSP2 (medium) at target_year
            path_b:     SSP1 (fast) at target_year
            regret:     what target_year would look like if SSP1 started in 2020
        """
        today = self.get_projections(country_iso3, years=[base_year], scenario="SSP2")
        do_nothing = self.get_projections(country_iso3, years=[target_year], scenario="SSP3")
        path_a = self.get_projections(country_iso3, years=[target_year], scenario="SSP2")
        path_b = self.get_projections(country_iso3, years=[target_year], scenario="SSP1")

        def _to_dict(result):
            if isinstance(result, DataUnavailable):
                return {"unavailable": True, "reason": result.reason}
            return {
                p.education_level: {
                    "label": p.education_label,
                    "share": p.population_share,
                }
                for p in result
            }

        return {
            "country_iso3": country_iso3,
            "base_year": base_year,
            "target_year": target_year,
            "today": _to_dict(today),
            "do_nothing": _to_dict(do_nothing),
            "path_a": {
                "scenario": "SSP2",
                "label": SCENARIO_LABELS["SSP2"],
                "data": _to_dict(path_a),
            },
            "path_b": {
                "scenario": "SSP1",
                "label": SCENARIO_LABELS["SSP1"],
                "data": _to_dict(path_b),
            },
            "regret_note": (
                f"If this infrastructure had existed in 2020, the {target_year} "
                f"outcome would approach the SSP1 scenario — "
                f"that gap is the cost of the missing 5 years."
            ),
            "source": _SOURCE_CITATION.model_dump(),
            "data_gap_disclosure": (
                "Projection uncertainty is ±40% at district level. "
                "Climate displacement and conflict not modelled. "
                "Source: Wittgenstein Centre WIC 2023."
            ),
        }

    def get_education_share(
        self,
        country_iso3: str,
        year: int,
        education_level: str,
        scenario: str = "SSP2",
    ) -> Optional[float]:
        """Return population share for one education level in one year."""
        df = _load_dataframe()
        if df.empty:
            return None
        row = df[
            (df["country_iso3"] == country_iso3.upper())
            & (df["year"] == year)
            & (df["education_level"] == education_level)
            & (df["scenario"] == scenario)
        ]
        if row.empty:
            return None
        return float(row.iloc[0]["population_share"])

    @property
    def available_countries(self) -> list[str]:
        df = _load_dataframe()
        return list(df["country_iso3"].unique()) if not df.empty else []
