"""
Pydantic models for data values that carry source citations.

Every number displayed in the UNMAPPED UI must be accompanied by a
SourceCitation so the frontend can render the source tooltip.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    name: str                          # "ILO ILOSTAT"
    url: Optional[str] = None          # exact URL queried
    data_date: str                     # "2023" or "2023-Q4"
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: Literal["high", "medium", "low", "estimate"]
    notes: Optional[str] = None        # e.g. "regional proxy used"


class SourcedFloat(BaseModel):
    """A float value with its source citation attached."""
    value: float
    unit: str = ""
    source: SourceCitation

    def __repr__(self):
        return f"{self.value} {self.unit} (source: {self.source.name}, {self.source.data_date})"


class SourcedStr(BaseModel):
    """A string value with its source citation attached."""
    value: str
    source: SourceCitation


class WageFloor(BaseModel):
    """A wage floor value for one occupation in one country."""
    occupation_label: str
    isco_code: str
    country_iso: str
    monthly_wage: float
    currency: str
    currency_symbol: str
    period: str             # e.g. "2023"
    source: SourceCitation
    is_minimum_wage: bool = False
    is_median_wage: bool = False
    is_estimated: bool = False


class SectorGrowth(BaseModel):
    """Employment growth for one sector in one country."""
    sector_label: str
    isic_code: Optional[str] = None
    country_iso: str
    growth_rate: float      # e.g. 0.042 for 4.2%
    base_year: int
    latest_year: int
    source: SourceCitation


class ESCOSkill(BaseModel):
    """A skill from the ESCO taxonomy."""
    uri: str
    preferred_label: str
    description: Optional[str] = None
    skill_type: Optional[str] = None   # "skill/competence" | "knowledge" | "attitude"
    isco_groups: list[str] = Field(default_factory=list)
    broader_skills: list[str] = Field(default_factory=list)
    narrower_skills: list[str] = Field(default_factory=list)
    source: SourceCitation


class AutomationScore(BaseModel):
    """Frey-Osborne automation probability for one occupation."""
    isco_code: str
    isco_label: str
    soc_code: Optional[str] = None
    frey_osborne_probability: float    # 0.0–1.0 US baseline
    paper_year: int = 2013
    source: SourceCitation


class WittgensteinProjection(BaseModel):
    """Education attainment projection for a country/year/scenario."""
    country_iso: str
    year: int
    scenario: str                      # "SSP1" | "SSP2" | "SSP3"
    education_level: str               # "e1" through "e8" (WIC levels)
    education_label: str
    population_share: float            # 0.0–1.0
    source: SourceCitation


class DataUnavailable(BaseModel):
    """Returned when data cannot be obtained — surfaces in UI as honest disclosure."""
    requested_for: str
    reason: str
    fallback_used: Optional[str] = None
    data_gap_ids: list[str] = Field(default_factory=list)
    source: SourceCitation


# Union type used throughout the adapters
AdapterResult = SourcedFloat | WageFloor | SectorGrowth | ESCOSkill | AutomationScore | WittgensteinProjection | DataUnavailable
