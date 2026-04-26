"""Phase 0 smoke test: config loader + country swap."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["ACTIVE_COUNTRY"] = "ghana"
from backend.config_loader import get_config, calibrate_automation_score  # noqa: E402

cfg = get_config()
print("Country: %s (%s)" % (cfg.country.name, cfg.country.iso_code))
print("Currency: %s" % cfg.country.currency)
print("Informal share: %.0f%%" % (cfg.labor_market.informal_sector_share * 100))
print("Education levels: %s" % [l.id for l in cfg.education_taxonomy.levels])
print("Data gaps: %d" % len(cfg.data_gaps))
print()

cal = calibrate_automation_score(0.89)
b, ia, c = cal["baseline"], cal["infrastructure_adjusted"], cal["calibrated"]
print("Frey-Osborne calibration (phone repair, ISCO 7422):")
print("  US baseline:              %.0f%%" % (b * 100))
print("  Infrastructure adjusted:  %.1f%%" % (ia * 100))
print("  Fully calibrated (Ghana): %.1f%%" % (c * 100))
print()

get_config.cache_clear()
os.environ["ACTIVE_COUNTRY"] = "bangladesh"
cfg2 = get_config()
print("--- LIVE COUNTRY SWAP ---")
print("Country: %s (%s)" % (cfg2.country.name, cfg2.country.iso_code))
print("Currency: %s" % cfg2.country.currency)
print("Script: %s" % cfg2.language.script)
print("Informal share: %.0f%%" % (cfg2.labor_market.informal_sector_share * 100))
print("Data gaps: %d" % len(cfg2.data_gaps))
print()
print("SWAP COMPLETE. Zero code changes. One env var.")
