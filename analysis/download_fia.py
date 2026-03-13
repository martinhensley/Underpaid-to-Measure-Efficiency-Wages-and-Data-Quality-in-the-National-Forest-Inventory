#!/usr/bin/env python3
"""
Download FIA SQLite databases from USDA FIA DataMart.

Downloads state-level SQLite databases for multi-state analysis.
URL pattern: https://apps.fs.usda.gov/fia/datamart/Databases/SQLite_FIADB_{STATE}.zip

Usage:
    python download_fia.py                  # Download all target states
    python download_fia.py --states VT MN   # Download specific states
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

# Target states spanning multiple FIA regions and labor markets
TARGET_STATES = [
    # Northern Region
    "MN",  # Minnesota
    "WI",  # Wisconsin
    # Northeast Region
    "VT",  # Vermont
    "ME",  # Maine
    # Southern Region
    "GA",  # Georgia
    # Rocky Mountain Region
    "CO",  # Colorado
    # Pacific Northwest Region
    "OR",  # Oregon
    "WA",  # Washington
]

BASE_URL = "https://apps.fs.usda.gov/fia/datamart/Databases/SQLite_FIADB_{state}.zip"
DATA_DIR = Path(__file__).parent.parent / "data"


def download_state(state: str, data_dir: Path) -> Path:
    """Download and extract FIA SQLite database for a single state."""
    db_path = data_dir / f"SQLite_FIADB_{state}.db"
    zip_path = data_dir / f"SQLite_FIADB_{state}.zip"

    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"  {state}: Already downloaded ({size_mb:.0f} MB), skipping")
        return db_path

    url = BASE_URL.format(state=state)
    print(f"  {state}: Downloading from {url}")

    try:
        urlretrieve(url, zip_path)
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"  {state}: Downloaded {zip_size_mb:.0f} MB zip, extracting...")

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Find the .db file inside the zip
            db_names = [n for n in zf.namelist() if n.endswith(".db")]
            if not db_names:
                print(f"  {state}: ERROR - No .db file found in zip")
                zip_path.unlink()
                return None

            # Extract the db file
            zf.extract(db_names[0], data_dir)
            extracted = data_dir / db_names[0]

            # Rename if needed (some zips have subdirectories)
            if extracted != db_path:
                extracted.rename(db_path)

        # Clean up zip
        zip_path.unlink()
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"  {state}: Extracted ({size_mb:.0f} MB)")
        return db_path

    except Exception as e:
        print(f"  {state}: ERROR - {e}")
        if zip_path.exists():
            zip_path.unlink()
        return None


def main():
    parser = argparse.ArgumentParser(description="Download FIA SQLite databases")
    parser.add_argument(
        "--states",
        nargs="+",
        default=TARGET_STATES,
        help=f"State abbreviations to download (default: {' '.join(TARGET_STATES)})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help=f"Output directory (default: {DATA_DIR})",
    )
    args = parser.parse_args()

    args.data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading FIA databases to {args.data_dir}")
    print(f"States: {', '.join(args.states)}\n")

    results = {}
    for state in args.states:
        results[state] = download_state(state.upper(), args.data_dir)

    print("\n--- Summary ---")
    success = [s for s, p in results.items() if p is not None]
    failed = [s for s, p in results.items() if p is None]
    print(f"Downloaded: {', '.join(success)} ({len(success)} states)")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
