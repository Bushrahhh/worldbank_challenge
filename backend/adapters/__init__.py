"""
UNMAPPED data adapters.

Each adapter fetches from one external data source and returns
SourcedData objects — values with SourceCitation metadata attached.
"""

from backend.adapters.esco import ESCOAdapter
from backend.adapters.ilostat import ILOSTATAdapter
from backend.adapters.onet import OnetAdapter
from backend.adapters.wittgenstein import WittgensteinAdapter
from backend.adapters.worldbank_wdi import WorldBankWDIAdapter, iso3_to_iso2

__all__ = [
    "ESCOAdapter",
    "ILOSTATAdapter",
    "OnetAdapter",
    "WittgensteinAdapter",
    "WorldBankWDIAdapter",
    "iso3_to_iso2",
]
