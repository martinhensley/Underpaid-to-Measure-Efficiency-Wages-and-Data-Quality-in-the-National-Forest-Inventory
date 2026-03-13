#!/usr/bin/env python3
"""
Download the Yanai et al. (2023) paired QA/production measurement dataset.

Citation:
    Yanai, R.D., Wayson, C., Lee, D., Espejo, A.B., Campbell, J.L.,
    Green, M.B., Zukswert, J.M., Yohe, S.W., Weyant, J.T., Duffy, P.A.,
    & Sass, E.M. (2023). Data for Quantifying Uncertainty in Estimation of
    Tree Attributes: Comparing Field Measurements of Trees Using
    Conventional Inventory and Quality Assurance Methods.
    Forest Service Research Data Archive.
    https://doi.org/10.2737/RDS-2022-0056

The dataset contains 94,459 paired tree observations across 24 northern
states (2011-2016) with matched production and QA crew measurements.

Usage:
    python download_yanai.py

If automatic download fails (USFS server restrictions), the script prints
manual instructions for obtaining the data.
"""

import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve, Request, urlopen
from urllib.error import HTTPError, URLError

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR = DATA_DIR / "yanai_paired"

# Standard USFS Research Data Archive download URL pattern
DOWNLOAD_URL = (
    "https://www.fs.usda.gov/rds/archive/products/RDS-2022-0056/"
    "RDS-2022-0056.zip"
)
CATALOG_URL = "https://doi.org/10.2737/RDS-2022-0056"

REQUIRED_FILES = ["Data/Tree.csv", "Data/Plot.csv"]


def verify_data() -> bool:
    """Check whether required data files already exist."""
    return all((OUT_DIR / f).is_file() for f in REQUIRED_FILES)


def download_and_extract() -> bool:
    """Attempt to download the dataset from USFS Research Data Archive."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "RDS-2022-0056.zip"

    print(f"Downloading from:\n  {DOWNLOAD_URL}")
    try:
        urlretrieve(DOWNLOAD_URL, zip_path)
    except (HTTPError, URLError) as e:
        print(f"\nAutomatic download failed: {e}")
        return False

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Downloaded {size_mb:.1f} MB, extracting...")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(OUT_DIR)
    except zipfile.BadZipFile:
        print("Error: Downloaded file is not a valid zip archive.")
        zip_path.unlink()
        return False

    zip_path.unlink()
    print(f"Extracted to {OUT_DIR}")
    return True


def print_manual_instructions():
    """Print instructions for manual data acquisition."""
    print(f"""
========================================================================
MANUAL DOWNLOAD REQUIRED
========================================================================

The USFS Research Data Archive may require browser-based access.
To obtain the dataset manually:

  1. Visit: {CATALOG_URL}
  2. Click the download link for the full dataset
  3. Extract the zip file into:
       {OUT_DIR}

The directory structure should be:
  {OUT_DIR}/
    Data/
      Tree.csv         (required)
      Plot.csv         (required)
      Condition.csv
      Subplot.csv
      ...
    Supplements/
      Map_study_area.pdf

After extracting, re-run this script to verify, or proceed directly
to: python analysis/paired_qa_analysis.py
========================================================================
""")


def main():
    if verify_data():
        print("Yanai et al. (2023) dataset already present:")
        for f in REQUIRED_FILES:
            p = OUT_DIR / f
            size_mb = p.stat().st_size / (1024 * 1024)
            print(f"  {p} ({size_mb:.1f} MB)")
        return 0

    print("Yanai et al. (2023) paired QA dataset not found.")
    print(f"Target directory: {OUT_DIR}\n")

    if download_and_extract():
        if verify_data():
            print("\nVerification passed. Required files present:")
            for f in REQUIRED_FILES:
                p = OUT_DIR / f
                size_mb = p.stat().st_size / (1024 * 1024)
                print(f"  {p} ({size_mb:.1f} MB)")
            return 0
        else:
            print("\nWarning: Download succeeded but required files not found.")
            print("The zip may have a different directory structure.")
            print(f"Check contents of: {OUT_DIR}")
            return 1

    print_manual_instructions()
    return 1


if __name__ == "__main__":
    sys.exit(main())
