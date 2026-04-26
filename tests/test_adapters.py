"""
Phase 1 adapter tests.

Tests the local-file adapters (OnetAdapter, WittgensteinAdapter) synchronously,
and smoke-tests the live adapters (ILOSTAT, WDI, ESCO) with short timeouts.

Run: python -m pytest tests/test_adapters.py -v
  or: python tests/test_adapters.py  (for quick smoke test without pytest)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("ACTIVE_COUNTRY", "ghana")


# ── Local adapter tests (no network required) ───────────────────────────────

def test_onet_known_occupation():
    from backend.adapters.onet import OnetAdapter
    adapter = OnetAdapter()
    result = adapter.get_automation_score("7422")  # phone repair
    assert result.__class__.__name__ == "AutomationScore"
    assert result.isco_code == "7422"
    assert 0.0 < result.frey_osborne_probability <= 1.0
    assert result.source.name == "Frey & Osborne (2013/2017)"
    print("  ISCO 7422 automation: %.0f%% (US baseline)" % (result.frey_osborne_probability * 100))


def test_onet_unknown_occupation():
    from backend.adapters.onet import OnetAdapter
    from backend.models.sourced_data import DataUnavailable
    adapter = OnetAdapter()
    result = adapter.get_automation_score("9999")  # doesn't exist
    assert isinstance(result, DataUnavailable)
    print("  Unknown ISCO -> DataUnavailable: %s" % result.reason[:60])


def test_onet_dataset_loaded():
    from backend.adapters.onet import OnetAdapter
    adapter = OnetAdapter()
    assert adapter.dataset_size > 0
    print(f"  Frey-Osborne dataset: {adapter.data_source}")


def test_onet_high_risk_occupations():
    from backend.adapters.onet import OnetAdapter
    adapter = OnetAdapter()
    high_risk = adapter.get_high_risk_occupations(0.85)
    assert len(high_risk) > 0
    assert all(r["automation_probability"] >= 0.85 for r in high_risk)
    print(f"  High-risk occupations (>85%): {len(high_risk)}")
    for r in high_risk[:3]:
        print("    ISCO %s: %s -- %.0f%%" % (r['isco_code'], r['isco_label'], r['automation_probability'] * 100))


def test_onet_calibration():
    from backend.config_loader import calibrate_automation_score, get_config
    get_config.cache_clear()
    os.environ["ACTIVE_COUNTRY"] = "ghana"
    cal = calibrate_automation_score(0.89)
    assert cal["calibrated"] < cal["baseline"]
    assert cal["calibrated"] < 0.5  # calibration should bring US 89% below 50%
    print("  Ghana calibration: %.0f%% -> %.0f%%" % (cal["baseline"] * 100, cal["calibrated"] * 100))


def test_wittgenstein_ghana():
    from backend.adapters.wittgenstein import WittgensteinAdapter
    adapter = WittgensteinAdapter()
    result = adapter.get_projections("GHA", years=[2025, 2035], scenario="SSP2")
    assert not isinstance(result, type(None))
    assert len(result) > 0
    print("  Ghana WIC projections: %d data points" % len(result))
    for p in result[:2]:
        print("    %d SSP2 %s: %.1f%% - %s" % (p.year, p.education_level, p.population_share * 100, p.education_label))


def test_wittgenstein_time_machine():
    from backend.adapters.wittgenstein import WittgensteinAdapter
    adapter = WittgensteinAdapter()
    data = adapter.get_time_machine_data("GHA", base_year=2025, target_year=2035)
    assert "today" in data
    assert "do_nothing" in data
    assert "path_a" in data
    assert "path_b" in data
    assert "regret_note" in data
    print("  Time Machine data built for GHA 2025->2035")
    print("  Regret note: %s..." % data["regret_note"][:80])


def test_wittgenstein_bangladesh():
    from backend.adapters.wittgenstein import WittgensteinAdapter
    adapter = WittgensteinAdapter()
    result = adapter.get_projections("BGD", years=[2035], scenario="SSP1")
    assert not isinstance(result, type(None))
    print(f"  Bangladesh WIC 2035 SSP1: {len(result)} data points")


# ── Live adapter smoke tests (require network) ───────────────────────────────

async def test_worldbank_wdi_live():
    from backend.adapters.worldbank_wdi import WorldBankWDIAdapter
    adapter = WorldBankWDIAdapter()
    result = await adapter.get_indicator("GH", "empl_services")
    print(f"  WDI Ghana services employment: ", end="")
    if result.__class__.__name__ == "SourcedFloat":
        print(f"{result.value:.1f}% ({result.source.data_date}) — {result.source.name}")
        assert result.value > 0
    else:
        print(f"DataUnavailable: {result.reason[:60]}")
    await adapter.close()


async def test_worldbank_sector_growth():
    from backend.adapters.worldbank_wdi import WorldBankWDIAdapter
    adapter = WorldBankWDIAdapter()
    result = await adapter.get_sector_growth("GH", "empl_services")
    print(f"  WDI Ghana services growth: ", end="")
    if result.__class__.__name__ == "SectorGrowth":
        sign = "+" if result.growth_rate >= 0 else ""
        print("%s%.1f%% (%d->%d)" % (sign, result.growth_rate * 100, result.base_year, result.latest_year))
    else:
        print(f"DataUnavailable: {result.reason[:60]}")
    await adapter.close()


async def test_esco_search():
    from backend.adapters.esco import ESCOAdapter
    adapter = ESCOAdapter()
    result = await adapter.search_skills("mobile phone repair", language="en", limit=3)
    print(f"  ESCO skills for 'mobile phone repair': ", end="")
    if isinstance(result, list):
        print(f"{len(result)} results")
        for skill in result[:2]:
            print(f"    {skill.preferred_label} ({skill.uri[:50]}...)")
    else:
        print(f"DataUnavailable: {result.reason[:60]}")
    await adapter.close()


async def test_ilostat_wage():
    from backend.adapters.ilostat import ILOSTATAdapter
    adapter = ILOSTATAdapter()
    result = await adapter.get_wage_floor("GHA", "7422", "GHS")
    print(f"  ILOSTAT Ghana ISCO 7422 wage: ", end="")
    if result.__class__.__name__ == "WageFloor":
        estimated = " (estimated)" if result.is_estimated else ""
        print(f"{result.currency} {result.monthly_wage:.0f}/month ({result.period}){estimated}")
        assert result.monthly_wage > 0
    else:
        print(f"DataUnavailable: {result.reason[:60]}")
    await adapter.close()


# ── Test runner ──────────────────────────────────────────────────────────────

def run_all():
    print("\n=== UNMAPPED Phase 1 Adapter Tests ===\n")

    local_tests = [
        test_onet_known_occupation,
        test_onet_unknown_occupation,
        test_onet_dataset_loaded,
        test_onet_high_risk_occupations,
        test_onet_calibration,
        test_wittgenstein_ghana,
        test_wittgenstein_time_machine,
        test_wittgenstein_bangladesh,
    ]

    print("--- Local adapters (no network) ---")
    failed = 0
    for fn in local_tests:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
        except Exception as exc:
            print(f"  FAIL {fn.__name__}: {exc}")
            failed += 1

    print("\n--- Live adapters (network required) ---")
    live_tests = [
        test_worldbank_wdi_live,
        test_worldbank_sector_growth,
        test_esco_search,
        test_ilostat_wage,
    ]

    for fn in live_tests:
        try:
            asyncio.run(fn())
            print(f"  PASS {fn.__name__}")
        except Exception as exc:
            print(f"  FAIL {fn.__name__}: {exc}")
            failed += 1

    print(f"\n{'ALL PASS' if failed == 0 else f'{failed} FAILED'} ({len(local_tests + live_tests)} tests)")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
