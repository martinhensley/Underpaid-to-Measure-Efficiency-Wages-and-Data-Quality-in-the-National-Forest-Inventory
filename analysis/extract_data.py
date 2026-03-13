#!/usr/bin/env python3
"""
Extract and merge PLOT + TREE data from FIA SQLite databases into a unified
analysis dataset.

Outputs:
  - data/fia_trees.parquet: Merged tree-level dataset with plot metadata
  - data/fia_qa_summary.csv: QA_STATUS counts by state (for detection probability q)
  - data/fia_remeasured.parquet: Remeasurement pairs (current + previous tree data)

Usage:
    python extract_data.py
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

# Columns to extract from PLOT table
PLOT_COLS = [
    "CN",
    "INVYR",
    "STATECD",
    "UNITCD",
    "COUNTYCD",
    "PLOT",
    "MEASYEAR",
    "MEASMON",
    "MEASDAY",
    "REMPER",
    "KINDCD",
    "LAT",
    "LON",
    "QA_STATUS",
    "CYCLE",
    "SUBCYCLE",
]

# Columns to extract from TREE table
TREE_COLS = [
    "CN",
    "PLT_CN",
    "PREV_TRE_CN",
    "SUBP",
    "TREE",
    "STATUSCD",
    "SPCD",
    "SPGRPCD",
    "DIA",
    "HT",
    "ACTUALHT",
    "CR",
    "CCLCD",
    "TREECLCD",
    "DECAYCD",
    "TPA_UNADJ",
    "DRYBIO_AG",
    "CARBON_AG",
    "VOLCFNET",
    "VOLBFNET",
    "PREVDIA",
    "PREV_STATUS_CD",
    "STANDING_DEAD_CD",
]

# State FIPS codes for labeling
STATE_FIPS = {
    9: "CT", 10: "DE", 23: "ME", 25: "MA", 27: "MN", 33: "NH",
    34: "NJ", 36: "NY", 41: "OR", 44: "RI", 50: "VT", 53: "WA",
    55: "WI", 13: "GA", 8: "CO", 30: "MT", 26: "MI",
}


def extract_state(db_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Extract PLOT and TREE data from a single state SQLite database."""
    state_abbrev = db_path.stem.split("_")[-1]
    print(f"  {state_abbrev}: Reading {db_path.name}...")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    # Check which columns actually exist (schema varies slightly by state)
    cursor = conn.execute("PRAGMA table_info(PLOT)")
    plot_available = {row[1] for row in cursor.fetchall()}
    plot_cols = [c for c in PLOT_COLS if c in plot_available]

    cursor = conn.execute("PRAGMA table_info(TREE)")
    tree_available = {row[1] for row in cursor.fetchall()}
    tree_cols = [c for c in TREE_COLS if c in tree_available]

    # Extract PLOT data
    plot_query = f"SELECT {', '.join(plot_cols)} FROM PLOT"
    plots = pd.read_sql_query(plot_query, conn)

    # QA summary before filtering
    qa_summary = plots.groupby("QA_STATUS").size().to_dict()

    # Extract TREE data
    tree_query = f"SELECT {', '.join(tree_cols)} FROM TREE"
    trees = pd.read_sql_query(tree_query, conn)

    conn.close()

    print(f"  {state_abbrev}: {len(plots):,} plots, {len(trees):,} trees")
    print(f"  {state_abbrev}: QA_STATUS distribution: {qa_summary}")

    return plots, trees, {state_abbrev: qa_summary}


def build_analysis_dataset(
    all_plots: pd.DataFrame, all_trees: pd.DataFrame
) -> pd.DataFrame:
    """
    Join PLOT and TREE tables, filter to production plots with live trees,
    and add derived columns for analysis.
    """
    # Filter to production plots (QA_STATUS=1) with measurement month data
    prod_plots = all_plots[
        (all_plots["QA_STATUS"] == 1) & (all_plots["MEASMON"].notna())
    ].copy()

    # Join trees to plots
    merged = all_trees.merge(
        prod_plots[["CN", "MEASYEAR", "MEASMON", "MEASDAY", "STATECD", "COUNTYCD",
                     "LAT", "LON", "CYCLE", "SUBCYCLE", "REMPER"]],
        left_on="PLT_CN",
        right_on="CN",
        how="inner",
        suffixes=("", "_plot"),
    )

    # Filter to live trees with valid measurements
    merged = merged[
        (merged["STATUSCD"] == 1)
        & (merged["DIA"].notna())
        & (merged["DIA"] > 0)
    ].copy()

    # Add state abbreviation
    merged["STATE"] = merged["STATECD"].map(STATE_FIPS)

    # Add derived digit-heaping indicators
    merged["DIA_tenth"] = (merged["DIA"] * 10).round().astype(int) % 10
    merged["DIA_whole"] = (merged["DIA_tenth"] == 0).astype(int)
    merged["DIA_half"] = (merged["DIA_tenth"].isin([0, 5])).astype(int)

    # Height rounding indicators (only where HT is not null)
    ht_valid = merged["HT"].notna()
    merged.loc[ht_valid, "HT_div5"] = (merged.loc[ht_valid, "HT"] % 5 == 0).astype(int)
    merged.loc[ht_valid, "HT_div10"] = (merged.loc[ht_valid, "HT"] % 10 == 0).astype(int)

    # Season indicators
    merged["LATE_SEASON"] = merged["MEASMON"].isin([9, 10, 11, 12]).astype(int)

    # Log transforms for allometric analysis
    merged["lnDIA"] = np.log(merged["DIA"])
    merged.loc[ht_valid & (merged["HT"] > 0), "lnHT"] = np.log(
        merged.loc[ht_valid & (merged["HT"] > 0), "HT"]
    )

    return merged


def build_remeasurement_pairs(
    all_trees: pd.DataFrame, all_plots: pd.DataFrame
) -> pd.DataFrame:
    """
    Build remeasurement pairs by linking PREV_TRE_CN to previous tree records.
    Returns a dataset with current and previous measurements side by side.
    """
    # Filter to production plots
    prod_plots = all_plots[all_plots["QA_STATUS"] == 1][
        ["CN", "MEASYEAR", "MEASMON", "STATECD", "CYCLE"]
    ].copy()

    # Current trees with plot info
    current = all_trees[
        (all_trees["STATUSCD"] == 1)
        & (all_trees["DIA"].notna())
        & (all_trees["PREV_TRE_CN"].notna())
    ].merge(prod_plots, left_on="PLT_CN", right_on="CN", how="inner", suffixes=("", "_plot"))

    # Previous trees with plot info
    prev = all_trees[
        (all_trees["STATUSCD"] == 1) & (all_trees["DIA"].notna())
    ].merge(prod_plots, left_on="PLT_CN", right_on="CN", how="inner", suffixes=("", "_plot"))

    # Join current to previous via PREV_TRE_CN
    pairs = current.merge(
        prev[["CN", "DIA", "HT", "SPCD", "SPGRPCD", "MEASYEAR", "MEASMON"]],
        left_on="PREV_TRE_CN",
        right_on="CN",
        how="inner",
        suffixes=("", "_prev"),
    )

    # Compute changes
    pairs["DIA_change"] = pairs["DIA"] - pairs["DIA_prev"]
    pairs["DIA_abs_change"] = pairs["DIA_change"].abs()
    if "HT" in pairs.columns and "HT_prev" in pairs.columns:
        ht_valid = pairs["HT"].notna() & pairs["HT_prev"].notna()
        pairs.loc[ht_valid, "HT_change"] = pairs.loc[ht_valid, "HT"] - pairs.loc[ht_valid, "HT_prev"]
        pairs.loc[ht_valid, "HT_abs_change"] = pairs.loc[ht_valid, "HT_change"].abs()

    pairs["STATE"] = pairs["STATECD"].map(STATE_FIPS)

    return pairs


def compute_detection_probability(qa_summaries: dict) -> pd.DataFrame:
    """
    Compute detection probability q from QA_STATUS=7 (QA plots)
    relative to QA_STATUS=1 (production plots).
    """
    rows = []
    for state, qa_dist in qa_summaries.items():
        n_prod = qa_dist.get(1, qa_dist.get(1.0, 0))
        n_qa = qa_dist.get(7, qa_dist.get(7.0, 0))
        n_null = qa_dist.get(None, 0) + qa_dist.get("", 0)
        q = n_qa / n_prod if n_prod > 0 else 0
        rows.append({
            "state": state,
            "n_production": n_prod,
            "n_qa_status7": n_qa,
            "n_null": n_null,
            "q_observed": round(q, 5),
        })
    return pd.DataFrame(rows).sort_values("state")


def main():
    db_files = sorted(DATA_DIR.glob("SQLite_FIADB_*.db"))
    if not db_files:
        print(f"No FIA databases found in {DATA_DIR}")
        print("Run download_fia.py first.")
        return 1

    print(f"Found {len(db_files)} state databases in {DATA_DIR}\n")

    all_plots = []
    all_trees = []
    qa_summaries = {}

    for db_path in db_files:
        plots, trees, qa = extract_state(db_path)
        all_plots.append(plots)
        all_trees.append(trees)
        qa_summaries.update(qa)

    print("\nMerging all states...")
    all_plots_df = pd.concat(all_plots, ignore_index=True)
    all_trees_df = pd.concat(all_trees, ignore_index=True)
    print(f"Total: {len(all_plots_df):,} plots, {len(all_trees_df):,} trees\n")

    # Build main analysis dataset
    print("Building analysis dataset (production plots, live trees)...")
    analysis_df = build_analysis_dataset(all_plots_df, all_trees_df)
    print(f"Analysis dataset: {len(analysis_df):,} tree-observations")
    print(f"States: {sorted(analysis_df['STATE'].dropna().unique())}")
    print(f"Year range: {analysis_df['MEASYEAR'].min()}-{analysis_df['MEASYEAR'].max()}")
    print(f"Month distribution:\n{analysis_df['MEASMON'].value_counts().sort_index()}\n")

    # Save main dataset
    out_path = DATA_DIR / "fia_trees.parquet"
    analysis_df.to_parquet(out_path, index=False)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Saved: {out_path} ({size_mb:.1f} MB)")

    # Build remeasurement pairs
    print("\nBuilding remeasurement pairs...")
    pairs_df = build_remeasurement_pairs(all_trees_df, all_plots_df)
    print(f"Remeasurement pairs: {len(pairs_df):,}")

    pairs_path = DATA_DIR / "fia_remeasured.parquet"
    pairs_df.to_parquet(pairs_path, index=False)
    size_mb = pairs_path.stat().st_size / (1024 * 1024)
    print(f"Saved: {pairs_path} ({size_mb:.1f} MB)")

    # QA summary and detection probability
    print("\n--- QA Status Summary & Detection Probability ---")
    qa_df = compute_detection_probability(qa_summaries)
    print(qa_df.to_string(index=False))
    qa_df.to_csv(DATA_DIR / "fia_qa_summary.csv", index=False)
    print(f"\nSaved: {DATA_DIR / 'fia_qa_summary.csv'}")

    # Overall q estimate
    total_prod = qa_df["n_production"].sum()
    total_qa = qa_df["n_qa_status7"].sum()
    q_overall = total_qa / total_prod if total_prod > 0 else 0
    print(f"\nOverall detection probability q (QA_STATUS=7/QA_STATUS=1): {q_overall:.5f}")
    print(f"  ({total_qa} QA plots / {total_prod} production plots)")
    print(f"  FIA Business Report stated rate: ~4% (0.04)")
    print(f"  Note: QA_STATUS=7 may not fully capture QA remeasurement activity")

    return 0


if __name__ == "__main__":
    sys.exit(main())
