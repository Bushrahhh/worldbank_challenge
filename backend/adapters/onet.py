"""
O*NET / Frey-Osborne Adapter

Automation scores from Frey & Osborne (2013) "The Future of Employment."
Loads from local seed CSV (data/seed_frey_osborne.csv) with a
download path for the full dataset.

Full dataset download: see data/download_datasets.py
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.models.sourced_data import AutomationScore, DataUnavailable, SourceCitation

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SEED_PATH = _DATA_DIR / "seed_frey_osborne.csv"
_FULL_PATH = _DATA_DIR / "frey_osborne.csv"

_SOURCE_CITATION = SourceCitation(
    name="Frey & Osborne (2013/2017)",
    url="https://www.oxfordmartin.ox.ac.uk/downloads/academic/future-of-employment.pdf",
    data_date="2013",
    confidence="medium",
    notes=(
        "US labor market baseline. Automation probability reflects US task composition "
        "and digital infrastructure. Apply calibration factors for LMIC context. "
        "SOC→ISCO crosswalk: ILO SOC2010-ISCO08 mapping."
    ),
)


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    """Load Frey-Osborne data. Prefers full CSV if downloaded, else uses seed."""
    path = _FULL_PATH if _FULL_PATH.exists() else _SEED_PATH
    if not path.exists():
        logger.error("No Frey-Osborne data found at %s or %s", _FULL_PATH, _SEED_PATH)
        return pd.DataFrame(columns=["isco_code", "automation_probability"])

    df = pd.read_csv(path, dtype={"isco_code": str, "soc_code": str})
    df["isco_code"] = df["isco_code"].str.strip()
    logger.info(
        "Loaded Frey-Osborne data: %d occupations from %s",
        len(df), path.name,
    )
    return df


class OnetAdapter:
    """
    Local-file adapter for Frey-Osborne automation scores.
    No network required — data loaded from CSV at startup.
    """

    def get_automation_score(self, isco_code: str) -> AutomationScore | DataUnavailable:
        """
        Return the Frey-Osborne automation probability for an ISCO-08 occupation code.

        Returns DataUnavailable if the occupation is not in the dataset —
        this is disclosed in the UI with the data gap disclosure text.
        """
        df = _load_dataframe()
        code = str(isco_code).strip()
        row = df[df["isco_code"] == code]

        if row.empty:
            # Try partial match (ISCO codes are hierarchical — a 3-digit prefix may match)
            prefix = code[:3]
            row = df[df["isco_code"].str.startswith(prefix)]
            if not row.empty:
                matched_row = row.iloc[0]
                logger.info(
                    "Frey-Osborne: exact match for ISCO %s not found, using prefix match %s",
                    code, matched_row["isco_code"],
                )
                return AutomationScore(
                    isco_code=code,
                    isco_label=str(matched_row.get("isco_label", f"ISCO {code}")),
                    soc_code=str(matched_row.get("soc_code", "")),
                    frey_osborne_probability=float(matched_row["automation_probability"]),
                    paper_year=int(matched_row.get("paper_year", 2013)),
                    source=SourceCitation(
                        **_SOURCE_CITATION.model_dump(exclude={"notes"}),
                        notes=(
                            f"Prefix match used (ISCO {matched_row['isco_code']} → {code}). "
                            + (_SOURCE_CITATION.notes or "")
                        ),
                    ),
                )

            return DataUnavailable(
                requested_for=f"automation_score/isco_{code}",
                reason=f"ISCO {code} not in Frey-Osborne dataset ({len(df)} occupations loaded)",
                fallback_used="Regional LMIC average (0.55) — high uncertainty",
                data_gap_ids=["automation_rural"],
                source=SourceCitation(
                    name="Frey & Osborne (2013/2017) — not found",
                    url=_SOURCE_CITATION.url,
                    data_date="2013",
                    confidence="estimate",
                    notes=f"ISCO {code} not in crosswalk. Fallback: LMIC median automation estimate.",
                ),
            )

        matched_row = row.iloc[0]
        return AutomationScore(
            isco_code=code,
            isco_label=str(matched_row.get("isco_label", f"ISCO {code}")),
            soc_code=str(matched_row.get("soc_code", "")),
            frey_osborne_probability=float(matched_row["automation_probability"]),
            paper_year=int(matched_row.get("paper_year", 2013)),
            source=_SOURCE_CITATION,
        )

    def get_all_scores(self) -> dict[str, float]:
        """Return {isco_code: probability} for all loaded occupations."""
        df = _load_dataframe()
        return dict(zip(df["isco_code"].astype(str), df["automation_probability"].astype(float)))

    def get_high_risk_occupations(self, threshold: float = 0.70) -> list[dict]:
        """Return occupations above automation probability threshold."""
        df = _load_dataframe()
        high_risk = df[df["automation_probability"] >= threshold].sort_values(
            "automation_probability", ascending=False
        )
        return high_risk[["isco_code", "isco_label", "automation_probability"]].to_dict("records")

    def get_low_risk_occupations(self, threshold: float = 0.30) -> list[dict]:
        """Return occupations below automation probability threshold (durable skills)."""
        df = _load_dataframe()
        low_risk = df[df["automation_probability"] < threshold].sort_values("automation_probability")
        return low_risk[["isco_code", "isco_label", "automation_probability"]].to_dict("records")

    @property
    def dataset_size(self) -> int:
        return len(_load_dataframe())

    @property
    def data_source(self) -> str:
        path = _FULL_PATH if _FULL_PATH.exists() else _SEED_PATH
        return f"{path.name} ({self.dataset_size} occupations)"
