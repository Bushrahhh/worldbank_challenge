"""
UNMAPPED — Dataset Downloader

Downloads and caches the full versions of the static datasets used by UNMAPPED.
Run once before the demo. The adapters use seed CSVs if full files are absent.

Usage:
    python data/download_datasets.py [--all] [--frey-osborne] [--wittgenstein]

Data sources:
  Frey-Osborne:    Frey & Osborne 2013, Oxford Martin School
  Wittgenstein:    Wittgenstein Centre WIC 2023, wittgensteincentre.org
"""

import argparse
import logging
import sys
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent


def download_frey_osborne():
    """
    Download the Frey-Osborne automation probability dataset.

    The original supplementary table from:
    Frey, C.B. & Osborne, M.A. (2013). "The Future of Employment:
    How Susceptible Are Jobs to Computerisation?" Oxford Martin School.

    Multiple archives host this data. We try in order of reliability.
    """
    target = _DATA_DIR / "frey_osborne.csv"
    if target.exists():
        logger.info("frey_osborne.csv already exists — skipping. Delete to re-download.")
        return

    # Sources in order of preference
    sources = [
        # Widely-cited community archive of the paper's appendix table
        "https://raw.githubusercontent.com/philipjball/frey-osborne-automation/main/data/frey_osborne_2013.csv",
        # Alternative: OECD data archive
        "https://stats.oecd.org/fileview2.aspx?IDFile=4ea55c7e-3b9c-4dc4-86e5-68d820e7c75b",
    ]

    for url in sources:
        try:
            logger.info("Trying %s ...", url)
            resp = httpx.get(url, follow_redirects=True, timeout=30.0)
            if resp.status_code == 200 and len(resp.text) > 1000:
                target.write_text(resp.text, encoding="utf-8")
                lines = resp.text.strip().split("\n")
                logger.info(
                    "Downloaded frey_osborne.csv: %d occupations from %s",
                    len(lines) - 1, url,
                )
                return
            logger.warning("Bad response from %s: HTTP %s", url, resp.status_code)
        except Exception as exc:
            logger.warning("Failed to fetch from %s: %s", url, exc)

    logger.warning(
        "Could not download full Frey-Osborne dataset. "
        "Seed file (data/seed_frey_osborne.csv) will be used instead — "
        "covers %d key LMIC occupations. "
        "To use the full dataset, download from:\n"
        "  https://www.oxfordmartin.ox.ac.uk/publications/the-future-of-employment/\n"
        "  Save as: data/frey_osborne.csv\n"
        "  Required columns: isco_code, isco_label, soc_code, automation_probability",
        _count_seed_occupations(),
    )


def download_wittgenstein():
    """
    Download Wittgenstein Centre WIC 2023 education projections.

    Source: Wittgenstein Centre Data Explorer
    https://www.wittgensteincentre.org/dataexplorer/

    Note: The WIC data portal requires a form submission. This script
    attempts a direct download of the bulk CSV; if blocked, manual
    download instructions are provided.
    """
    target = _DATA_DIR / "wittgenstein_2035.csv"
    if target.exists():
        logger.info("wittgenstein_2035.csv already exists — skipping.")
        return

    # WIC bulk data endpoint (SSP scenarios, all countries, education by age)
    # This URL may change with WIC data revisions — check the portal if it fails
    url = "http://dataexplorer.wittgensteincentre.org/wcde/data/wic_data_20230901.zip"

    logger.info("Attempting WIC data download from %s ...", url)
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=120.0)
        if resp.status_code == 200:
            import io
            import zipfile
            zip_bytes = io.BytesIO(resp.content)
            with zipfile.ZipFile(zip_bytes) as zf:
                csvs = [n for n in zf.namelist() if n.endswith(".csv")]
                logger.info("ZIP contains: %s", csvs)
                if csvs:
                    # Look for the main projection file
                    main_csv = next((c for c in csvs if "pop" in c.lower()), csvs[0])
                    zf.extract(main_csv, _DATA_DIR)
                    ((_DATA_DIR / main_csv)).rename(target)
                    logger.info("Extracted %s → wittgenstein_2035.csv", main_csv)
                    return
    except Exception as exc:
        logger.warning("WIC download failed: %s", exc)

    logger.warning(
        "Could not download Wittgenstein data automatically.\n"
        "Manual download:\n"
        "  1. Go to https://www.wittgensteincentre.org/dataexplorer/\n"
        "  2. Select: All countries, 2025-2035, SSP1+SSP2+SSP3, Education (8 levels)\n"
        "  3. Download as CSV\n"
        "  4. Save as: data/wittgenstein_2035.csv\n"
        "  Required columns: country_iso3, year, scenario, education_level, "
        "education_label, age_group, population_share\n\n"
        "Seed file (data/seed_wittgenstein.csv) covers Ghana and Bangladesh for the demo."
    )


def _count_seed_occupations() -> int:
    seed = _DATA_DIR / "seed_frey_osborne.csv"
    if not seed.exists():
        return 0
    return sum(1 for line in seed.read_text().splitlines()) - 1  # minus header


def main():
    parser = argparse.ArgumentParser(description="Download UNMAPPED static datasets")
    parser.add_argument("--all", action="store_true", help="Download all datasets")
    parser.add_argument("--frey-osborne", action="store_true", help="Download Frey-Osborne data")
    parser.add_argument("--wittgenstein", action="store_true", help="Download Wittgenstein data")
    args = parser.parse_args()

    if not any([args.all, args.frey_osborne, args.wittgenstein]):
        parser.print_help()
        print("\nRun with --all to download everything for the demo.")
        sys.exit(0)

    if args.all or args.frey_osborne:
        download_frey_osborne()

    if args.all or args.wittgenstein:
        download_wittgenstein()

    logger.info("Done. Run 'python -c \"from backend.adapters.onet import OnetAdapter; "
                "a=OnetAdapter(); print(a.data_source)\"' to verify.")


if __name__ == "__main__":
    main()
