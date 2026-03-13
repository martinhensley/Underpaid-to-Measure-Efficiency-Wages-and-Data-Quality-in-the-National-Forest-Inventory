#!/usr/bin/env python3
"""
Analysis 4: Remeasurement Growth Anomalies — DBH vs Height

Exploits FIA's panel structure (trees remeasured every 5–10 years) to test
whether height measurements show more seasonal anomalies than DBH measurements.

Key insight: For a live, undamaged tree, both DBH and height should be
non-negative between remeasurements. "Impossible" values (negative growth,
or growth exceeding biological maxima) indicate measurement error in at least
one period. If ocular estimation concentrates on height (the harder-to-verify
margin), then:
  - Height anomaly rates should be higher than DBH anomaly rates overall
  - Height anomalies should increase more in late-season months than DBH anomalies
  - The seasonal effect should be stronger when conditioning on the *current*
    measurement being late-season (attributing the error to the current visit)

Important confound: In northern states, deciduous leaf-off in fall (Oct-Nov)
improves crown visibility, making height measurement mechanically *easier*
in late season. This works against detecting effort reduction in hardwoods.
Conifers (evergreens) provide a cleaner test — no leaf-off benefit, so
seasonal patterns more cleanly reflect effort changes rather than visibility.

This test requires no QA paired data — it uses the public FIA panel structure.

Outputs:
  - tables/remeasurement_anomaly_rates.csv
  - tables/remeasurement_anomaly_regression.csv
  - figures/remeasurement_anomalies.pdf

Usage:
    python remeasurement_growth.py
"""

import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA_DIR = Path(__file__).parent.parent / "data"
TABLE_DIR = Path(__file__).parent.parent / "tables"
FIG_DIR = Path(__file__).parent.parent / "figures"

STATE_FIPS = {
    9: "CT", 10: "DE", 23: "ME", 25: "MA", 27: "MN", 33: "NH",
    34: "NJ", 36: "NY", 41: "OR", 44: "RI", 50: "VT", 53: "WA",
    55: "WI", 13: "GA", 8: "CO", 30: "MT", 26: "MI",
}


def load_remeasurement_pairs() -> pd.DataFrame:
    """
    Load pairs of tree measurements across inventory cycles by self-joining
    TREE on PREV_TRE_CN. Each row represents one tree with its current and
    previous measurements.
    """
    db_files = sorted(DATA_DIR.glob("SQLite_FIADB_*.db"))
    if not db_files:
        print(f"Error: No FIA databases found in {DATA_DIR}")
        sys.exit(1)

    frames = []
    for db_path in db_files:
        state = db_path.stem.split("_")[-1]
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        # Self-join: current tree (t1) linked to previous tree (t0) via PREV_TRE_CN
        # Both measurements must be live trees with valid DIA
        df = pd.read_sql_query("""
            SELECT
                t1.CN AS cn_curr,
                t1.DIA AS dia_curr,
                t1.HT AS ht_curr,
                t1.HTCD AS htcd_curr,
                t1.SPGRPCD,
                t1.STATUSCD AS status_curr,
                p1.MEASMON AS measmon_curr,
                p1.MEASYEAR AS measyear_curr,
                p1.STATECD,
                p1.QA_STATUS AS qa_curr,

                t0.CN AS cn_prev,
                t0.DIA AS dia_prev,
                t0.HT AS ht_prev,
                t0.HTCD AS htcd_prev,
                t0.STATUSCD AS status_prev,
                p0.MEASMON AS measmon_prev,
                p0.MEASYEAR AS measyear_prev,
                p0.QA_STATUS AS qa_prev

            FROM TREE t1
            JOIN PLOT p1 ON t1.PLT_CN = p1.CN
            JOIN TREE t0 ON t1.PREV_TRE_CN = t0.CN
            JOIN PLOT p0 ON t0.PLT_CN = p0.CN

            WHERE t1.STATUSCD = 1           -- current tree is live
              AND t0.STATUSCD = 1           -- previous tree was live
              AND t1.DIA > 0
              AND t0.DIA > 0
              AND p1.QA_STATUS = 1          -- production plots only
              AND p0.QA_STATUS = 1
              AND p1.MEASMON IS NOT NULL
              AND p0.MEASMON IS NOT NULL
              AND t1.DIA IS NOT NULL
              AND t0.DIA IS NOT NULL
        """, conn)
        conn.close()

        n_ht = df["ht_curr"].notna().sum() & df["ht_prev"].notna().sum()
        print(f"  {state}: {len(df):,} remeasurement pairs "
              f"({df['ht_curr'].notna().sum():,} with both HT)")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df["STATE"] = df["STATECD"].map(STATE_FIPS)

    # Compute growth
    df["delta_dia"] = df["dia_curr"] - df["dia_prev"]
    df["delta_ht"] = df["ht_curr"] - df["ht_prev"]

    # Time between measurements
    df["years_between"] = df["measyear_curr"] - df["measyear_prev"]

    # Annualized growth
    valid_years = df["years_between"] > 0
    df.loc[valid_years, "dia_growth_annual"] = (
        df.loc[valid_years, "delta_dia"] / df.loc[valid_years, "years_between"]
    )
    df.loc[valid_years, "ht_growth_annual"] = (
        df.loc[valid_years, "delta_ht"] / df.loc[valid_years, "years_between"]
    )

    # Season indicators
    df["measmon_curr"] = df["measmon_curr"].astype(int)
    df["measyear_curr"] = df["measyear_curr"].astype(int)
    df["late_curr"] = df["measmon_curr"].isin([9, 10, 11, 12]).astype(int)
    df["late_prev"] = df["measmon_prev"].astype(int).isin([9, 10, 11, 12]).astype(int)

    # Species group: conifers (SPGRPCD 1-24) vs hardwoods (25+)
    # Per FIA Database User Guide Appendix F (REF_SPECIES_GROUP table),
    # SPGRPCD 1-24 are softwood/conifer groups and 25-48 are hardwood groups.
    # This is the standard FIA classification; individual trees are assigned
    # SPGRPCD based on their species, so mixed-species plots are handled
    # at the tree level.
    # Conifers have no leaf-off, so seasonal patterns are unconfounded by
    # visibility changes. Hardwoods lose leaves in fall, making crown tops
    # *more* visible — which improves height measurement mechanically.
    df["is_conifer"] = (df["SPGRPCD"] <= 24).astype(int)
    df["is_hardwood"] = (df["SPGRPCD"] > 24).astype(int)

    # Anomaly indicators
    # Thresholds follow FIA QA tolerance standards and forestry growth norms:
    #   - DBH measurement tolerance: ±0.1 in for small trees (Bechtold &
    #     Patterson 2005, GTR SRS-80, Ch. 3); shrinkage beyond this indicates
    #     measurement error in at least one period.
    #   - DBH extreme growth: 1.0 in/yr exceeds observed maximum for nearly
    #     all North American species (Burns & Honkala 1990, Silvics of NA).
    #   - HT shrinkage: FIA QA tolerance is 10% or 5 ft (whichever is larger);
    #     we use -3 ft as a conservative threshold to flag likely errors while
    #     allowing normal inter-observer variability.
    #   - HT extreme growth: 5 ft/yr exceeds observed height growth for
    #     mature trees of virtually all species in the sample states.
    # DBH: shrinkage beyond measurement tolerance (allow -0.1 for rounding)
    df["dia_shrink"] = (df["delta_dia"] < -0.1).astype(int)
    # DBH: implausible growth (>1.0 inch/year is extreme for most species)
    df.loc[valid_years, "dia_extreme_growth"] = (
        df.loc[valid_years, "dia_growth_annual"] > 1.0
    ).astype(int)

    # Height: shrinkage beyond tolerance (allow -3 ft for measurement noise)
    ht_valid = df["ht_curr"].notna() & df["ht_prev"].notna() & (df["ht_prev"] > 0)
    df["ht_pair"] = ht_valid.astype(int)
    df.loc[ht_valid, "ht_shrink"] = (df.loc[ht_valid, "delta_ht"] < -3).astype(int)
    # Height: implausible growth (>5 ft/year is extreme)
    ht_years = ht_valid & valid_years
    df.loc[ht_years, "ht_extreme_growth"] = (
        df.loc[ht_years, "ht_growth_annual"] > 5.0
    ).astype(int)

    # Combined anomaly: any impossible value
    df.loc[ht_valid, "ht_anomaly"] = (
        (df.loc[ht_valid, "ht_shrink"] == 1) |
        (df.loc[ht_valid, "ht_extreme_growth"] == 1)
    ).astype(int)
    df["dia_anomaly"] = (
        (df["dia_shrink"] == 1) |
        (df["dia_extreme_growth"] == 1)
    ).astype(int)

    print(f"\nTotal: {len(df):,} remeasurement pairs")
    print(f"  With valid HT pairs: {ht_valid.sum():,}")
    print(f"  Years between: {df['years_between'].describe()}")

    return df


def descriptive_anomalies(df: pd.DataFrame):
    """Descriptive anomaly rates overall and by season."""
    print("\n" + "=" * 70)
    print("DESCRIPTIVE: REMEASUREMENT ANOMALY RATES")
    print("=" * 70)

    # Overall rates
    n = len(df)
    ht_df = df[df["ht_pair"] == 1]
    n_ht = len(ht_df)

    print(f"\n--- Overall Anomaly Rates ---")
    print(f"  DBH shrinkage (< -0.1 in):   {df['dia_shrink'].mean()*100:.2f}% "
          f"(n={df['dia_shrink'].sum():,} / {n:,})")
    print(f"  DBH extreme growth (>1 in/yr): {df['dia_extreme_growth'].mean()*100:.2f}%")
    print(f"  DBH any anomaly:              {df['dia_anomaly'].mean()*100:.2f}%")
    print()
    print(f"  HT shrinkage (< -3 ft):       {ht_df['ht_shrink'].mean()*100:.2f}% "
          f"(n={ht_df['ht_shrink'].sum():,} / {n_ht:,})")
    print(f"  HT extreme growth (>5 ft/yr):  {ht_df['ht_extreme_growth'].mean()*100:.2f}%")
    print(f"  HT any anomaly:               {ht_df['ht_anomaly'].mean()*100:.2f}%")

    # By current measurement season
    print(f"\n--- Anomaly Rates by Current Measurement Season ---")
    for label, late_val in [("Early (May-Aug)", 0), ("Late (Sep-Dec)", 1)]:
        sub = df[df["late_curr"] == late_val]
        sub_ht = ht_df[ht_df["late_curr"] == late_val]
        print(f"\n  {label} (n={len(sub):,}, n_ht={len(sub_ht):,}):")
        print(f"    DBH anomaly: {sub['dia_anomaly'].mean()*100:.2f}%")
        if len(sub_ht) > 0:
            print(f"    HT anomaly:  {sub_ht['ht_anomaly'].mean()*100:.2f}%")
            print(f"    HT shrink:   {sub_ht['ht_shrink'].mean()*100:.2f}%")

    # By current × previous season (attribution)
    print(f"\n--- Anomaly Rates by Current × Previous Season ---")
    print(f"  (Shrinkage when previous=early isolates current-period error)")
    for prev_label, prev_val in [("Prev=Early", 0), ("Prev=Late", 1)]:
        for curr_label, curr_val in [("Curr=Early", 0), ("Curr=Late", 1)]:
            sub = df[(df["late_curr"] == curr_val) & (df["late_prev"] == prev_val)]
            sub_ht = ht_df[(ht_df["late_curr"] == curr_val) & (ht_df["late_prev"] == prev_val)]
            if len(sub) < 100:
                continue
            dia_rate = sub["dia_anomaly"].mean() * 100
            ht_rate = sub_ht["ht_anomaly"].mean() * 100 if len(sub_ht) > 0 else float("nan")
            print(f"  {prev_label}, {curr_label}: "
                  f"DBH={dia_rate:.2f}%, HT={ht_rate:.2f}% "
                  f"(n={len(sub):,}, n_ht={len(sub_ht):,})")

    # By species group (conifer vs hardwood) × season
    # Critical decomposition: leaf-off in fall makes hardwood HT *easier*,
    # masking effort reduction. Conifers are the clean test.
    print(f"\n--- Anomaly Rates by Species Group × Season ---")
    print(f"  (Leaf-off confound: hardwood HT measurement improves in fall)")
    for sp_label, sp_val in [("Conifer", 1), ("Hardwood", 0)]:
        sp_sub = df[df["is_conifer"] == sp_val]
        sp_ht = ht_df[ht_df["is_conifer"] == sp_val]
        print(f"\n  {sp_label} (n={len(sp_sub):,}, n_ht={len(sp_ht):,}):")
        for season_label, late_val in [("Early", 0), ("Late", 1)]:
            sub = sp_sub[sp_sub["late_curr"] == late_val]
            sub_ht = sp_ht[sp_ht["late_curr"] == late_val]
            dia_rate = sub["dia_anomaly"].mean() * 100
            ht_rate = sub_ht["ht_anomaly"].mean() * 100 if len(sub_ht) > 0 else float("nan")
            ht_shrink = sub_ht["ht_shrink"].mean() * 100 if len(sub_ht) > 0 else float("nan")
            print(f"    {season_label}: DBH anom={dia_rate:.2f}%, "
                  f"HT anom={ht_rate:.2f}%, HT shrink={ht_shrink:.2f}% "
                  f"(n={len(sub):,})")


def anomaly_rates_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Compute anomaly rates by current measurement month."""
    ht_df = df[df["ht_pair"] == 1].copy()

    dia_monthly = df.groupby("measmon_curr").agg(
        n_dia=("dia_anomaly", "count"),
        dia_anomaly_rate=("dia_anomaly", "mean"),
        dia_shrink_rate=("dia_shrink", "mean"),
    ).reset_index()

    ht_monthly = ht_df.groupby("measmon_curr").agg(
        n_ht=("ht_anomaly", "count"),
        ht_anomaly_rate=("ht_anomaly", "mean"),
        ht_shrink_rate=("ht_shrink", "mean"),
    ).reset_index()

    monthly = dia_monthly.merge(ht_monthly, on="measmon_curr", how="left")
    for col in ["dia_anomaly_rate", "dia_shrink_rate", "ht_anomaly_rate", "ht_shrink_rate"]:
        monthly[col] = (monthly[col] * 100).round(3)

    print("\n--- Anomaly Rates by Month ---")
    print(monthly.to_string(index=False))
    monthly.to_csv(TABLE_DIR / "remeasurement_anomaly_rates.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'remeasurement_anomaly_rates.csv'}")

    return monthly


def run_anomaly_regressions(df: pd.DataFrame) -> dict:
    """
    Regression tests:
      anomaly ~ LATE_SEASON + C(STATE) + C(MEASYEAR)

    Run separately for DBH and HT anomalies. The key comparison is whether
    the LATE_SEASON coefficient is larger for HT than DBH.
    """
    print("\n" + "=" * 70)
    print("REGRESSION ANALYSIS: ANOMALY RATES")
    print("=" * 70)

    results = {}
    cluster_var = lambda d: d["STATE"].astype(str) + "_" + d["measyear_curr"].astype(str)

    # --- Model 1: DBH anomaly ~ LATE_SEASON ---
    print("\n--- Model 1: DBH Anomaly ~ Late Season (current) ---")
    m1 = smf.ols(
        "dia_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(df)})
    print(f"  LATE_SEASON coef: {m1.params['late_curr']:.6f} "
          f"(SE: {m1.bse['late_curr']:.6f}, p={m1.pvalues['late_curr']:.4f})")
    print(f"  N = {m1.nobs:,.0f}, R² = {m1.rsquared:.5f}")
    results["dia_anomaly_late"] = {
        "dep_var": "DBH anomaly",
        "coef": m1.params["late_curr"],
        "se": m1.bse["late_curr"],
        "pvalue": m1.pvalues["late_curr"],
        "n": int(m1.nobs),
        "r2": m1.rsquared,
    }

    # --- Model 2: HT anomaly ~ LATE_SEASON ---
    print("\n--- Model 2: HT Anomaly ~ Late Season (current) ---")
    ht_df = df[df["ht_anomaly"].notna()].copy()
    m2 = smf.ols(
        "ht_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
        data=ht_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_df)})
    print(f"  LATE_SEASON coef: {m2.params['late_curr']:.6f} "
          f"(SE: {m2.bse['late_curr']:.6f}, p={m2.pvalues['late_curr']:.4f})")
    print(f"  N = {m2.nobs:,.0f}, R² = {m2.rsquared:.5f}")
    results["ht_anomaly_late"] = {
        "dep_var": "HT anomaly",
        "coef": m2.params["late_curr"],
        "se": m2.bse["late_curr"],
        "pvalue": m2.pvalues["late_curr"],
        "n": int(m2.nobs),
        "r2": m2.rsquared,
    }

    # --- Model 3: DBH shrinkage only ---
    print("\n--- Model 3: DBH Shrinkage ~ Late Season (current) ---")
    m3 = smf.ols(
        "dia_shrink ~ late_curr + C(STATE) + C(measyear_curr)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(df)})
    print(f"  LATE_SEASON coef: {m3.params['late_curr']:.6f} "
          f"(SE: {m3.bse['late_curr']:.6f}, p={m3.pvalues['late_curr']:.4f})")
    results["dia_shrink_late"] = {
        "dep_var": "DBH shrinkage",
        "coef": m3.params["late_curr"],
        "se": m3.bse["late_curr"],
        "pvalue": m3.pvalues["late_curr"],
        "n": int(m3.nobs),
        "r2": m3.rsquared,
    }

    # --- Model 4: HT shrinkage only ---
    print("\n--- Model 4: HT Shrinkage ~ Late Season (current) ---")
    m4 = smf.ols(
        "ht_shrink ~ late_curr + C(STATE) + C(measyear_curr)",
        data=ht_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_df)})
    print(f"  LATE_SEASON coef: {m4.params['late_curr']:.6f} "
          f"(SE: {m4.bse['late_curr']:.6f}, p={m4.pvalues['late_curr']:.4f})")
    results["ht_shrink_late"] = {
        "dep_var": "HT shrinkage",
        "coef": m4.params["late_curr"],
        "se": m4.bse["late_curr"],
        "pvalue": m4.pvalues["late_curr"],
        "n": int(m4.nobs),
        "r2": m4.rsquared,
    }

    # --- Model 5: HT anomaly, conditioning on previous season ---
    # Restrict to cases where previous measurement was early-season,
    # so anomalies are more attributable to the current measurement.
    print("\n--- Model 5: HT Anomaly ~ Late Season (prev=early only) ---")
    ht_prev_early = ht_df[ht_df["late_prev"] == 0].copy()
    if len(ht_prev_early) > 1000:
        m5 = smf.ols(
            "ht_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
            data=ht_prev_early,
        ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_prev_early)})
        print(f"  LATE_SEASON coef: {m5.params['late_curr']:.6f} "
              f"(SE: {m5.bse['late_curr']:.6f}, p={m5.pvalues['late_curr']:.4f})")
        print(f"  N = {m5.nobs:,.0f}")
        results["ht_anomaly_late_prev_early"] = {
            "dep_var": "HT anomaly (prev=early)",
            "coef": m5.params["late_curr"],
            "se": m5.bse["late_curr"],
            "pvalue": m5.pvalues["late_curr"],
            "n": int(m5.nobs),
            "r2": m5.rsquared,
        }
    else:
        print(f"  Insufficient data (n={len(ht_prev_early):,})")

    # --- Model 6: DBH anomaly, conditioning on previous season ---
    print("\n--- Model 6: DBH Anomaly ~ Late Season (prev=early only) ---")
    dia_prev_early = df[df["late_prev"] == 0].copy()
    if len(dia_prev_early) > 1000:
        m6 = smf.ols(
            "dia_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
            data=dia_prev_early,
        ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(dia_prev_early)})
        print(f"  LATE_SEASON coef: {m6.params['late_curr']:.6f} "
              f"(SE: {m6.bse['late_curr']:.6f}, p={m6.pvalues['late_curr']:.4f})")
        print(f"  N = {m6.nobs:,.0f}")
        results["dia_anomaly_late_prev_early"] = {
            "dep_var": "DBH anomaly (prev=early)",
            "coef": m6.params["late_curr"],
            "se": m6.bse["late_curr"],
            "pvalue": m6.pvalues["late_curr"],
            "n": int(m6.nobs),
            "r2": m6.rsquared,
        }
    else:
        print(f"  Insufficient data (n={len(dia_prev_early):,})")

    # --- Model 7: HT anomaly with HTCD control ---
    # HTCD indicates how height was obtained (1=measured, 2+=modeled/estimated)
    # If HTCD is available and varies seasonally, that's direct evidence.
    print("\n--- Model 7: HTCD=1 (measured) rate ~ Late Season ---")
    ht_htcd = ht_df[ht_df["htcd_curr"].notna()].copy()
    ht_htcd["ht_measured"] = (ht_htcd["htcd_curr"] == 1).astype(int)
    if len(ht_htcd) > 1000:
        m7 = smf.ols(
            "ht_measured ~ late_curr + C(STATE) + C(measyear_curr)",
            data=ht_htcd,
        ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_htcd)})
        print(f"  LATE_SEASON coef: {m7.params['late_curr']:.6f} "
              f"(SE: {m7.bse['late_curr']:.6f}, p={m7.pvalues['late_curr']:.4f})")
        print(f"  N = {m7.nobs:,.0f}")
        print(f"  Overall HTCD=1 rate: {ht_htcd['ht_measured'].mean()*100:.1f}%")
        results["ht_measured_late"] = {
            "dep_var": "HTCD=1 (measured)",
            "coef": m7.params["late_curr"],
            "se": m7.bse["late_curr"],
            "pvalue": m7.pvalues["late_curr"],
            "n": int(m7.nobs),
            "r2": m7.rsquared,
        }
    else:
        print(f"  Insufficient HTCD data (n={len(ht_htcd):,})")

    # ======================================================================
    # SPECIES GROUP DECOMPOSITION: Leaf-off confound
    # ======================================================================
    # In northern states, deciduous leaf-off in fall improves crown visibility,
    # making height measurement mechanically easier. This works AGAINST finding
    # ocular estimation. Conifers (no leaf-off) provide the clean test.
    print("\n" + "=" * 70)
    print("SPECIES GROUP DECOMPOSITION: LEAF-OFF CONFOUND")
    print("=" * 70)

    # --- Model 8: HT anomaly ~ LATE × is_conifer (interaction) ---
    print("\n--- Model 8: HT Anomaly ~ Late × Conifer (interaction) ---")
    ht_df["late_x_conifer"] = ht_df["late_curr"] * ht_df["is_conifer"]
    m8 = smf.ols(
        "ht_anomaly ~ late_curr + is_conifer + late_x_conifer "
        "+ C(STATE) + C(measyear_curr)",
        data=ht_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_df)})
    print(f"  LATE_SEASON coef:        {m8.params['late_curr']:.6f} "
          f"(SE: {m8.bse['late_curr']:.6f}, p={m8.pvalues['late_curr']:.4f})")
    print(f"  is_conifer coef:         {m8.params['is_conifer']:.6f} "
          f"(SE: {m8.bse['is_conifer']:.6f}, p={m8.pvalues['is_conifer']:.4f})")
    print(f"  LATE × conifer coef:     {m8.params['late_x_conifer']:.6f} "
          f"(SE: {m8.bse['late_x_conifer']:.6f}, p={m8.pvalues['late_x_conifer']:.4f})")
    print(f"  N = {m8.nobs:,.0f}")
    print(f"  Interpretation: late_curr = hardwood seasonal effect (baseline)")
    print(f"                  late_x_conifer = ADDITIONAL seasonal effect for conifers")
    print(f"                  Total conifer late effect = "
          f"{m8.params['late_curr'] + m8.params['late_x_conifer']:.6f}")
    results["ht_anomaly_late_x_conifer"] = {
        "dep_var": "HT anomaly (Late × Conifer interaction)",
        "coef": m8.params["late_x_conifer"],
        "se": m8.bse["late_x_conifer"],
        "pvalue": m8.pvalues["late_x_conifer"],
        "n": int(m8.nobs),
        "r2": m8.rsquared,
    }

    # --- Model 9: HT anomaly ~ LATE, conifers only ---
    print("\n--- Model 9: HT Anomaly ~ Late Season (CONIFERS only) ---")
    ht_conifer = ht_df[ht_df["is_conifer"] == 1].copy()
    m9 = smf.ols(
        "ht_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
        data=ht_conifer,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_conifer)})
    print(f"  LATE_SEASON coef: {m9.params['late_curr']:.6f} "
          f"(SE: {m9.bse['late_curr']:.6f}, p={m9.pvalues['late_curr']:.4f})")
    print(f"  N = {m9.nobs:,.0f}")
    print(f"  (Clean test — no leaf-off visibility confound)")
    results["ht_anomaly_late_conifer"] = {
        "dep_var": "HT anomaly (conifers only)",
        "coef": m9.params["late_curr"],
        "se": m9.bse["late_curr"],
        "pvalue": m9.pvalues["late_curr"],
        "n": int(m9.nobs),
        "r2": m9.rsquared,
    }

    # --- Model 10: HT anomaly ~ LATE, hardwoods only ---
    print("\n--- Model 10: HT Anomaly ~ Late Season (HARDWOODS only) ---")
    ht_hardwood = ht_df[ht_df["is_conifer"] == 0].copy()
    m10 = smf.ols(
        "ht_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
        data=ht_hardwood,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_hardwood)})
    print(f"  LATE_SEASON coef: {m10.params['late_curr']:.6f} "
          f"(SE: {m10.bse['late_curr']:.6f}, p={m10.pvalues['late_curr']:.4f})")
    print(f"  N = {m10.nobs:,.0f}")
    print(f"  (Confounded by leaf-off — improvement may mask effort reduction)")
    results["ht_anomaly_late_hardwood"] = {
        "dep_var": "HT anomaly (hardwoods only)",
        "coef": m10.params["late_curr"],
        "se": m10.bse["late_curr"],
        "pvalue": m10.pvalues["late_curr"],
        "n": int(m10.nobs),
        "r2": m10.rsquared,
    }

    # --- Model 11: HT shrinkage ~ LATE, conifers only ---
    print("\n--- Model 11: HT Shrinkage ~ Late Season (CONIFERS only) ---")
    m11 = smf.ols(
        "ht_shrink ~ late_curr + C(STATE) + C(measyear_curr)",
        data=ht_conifer,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_conifer)})
    print(f"  LATE_SEASON coef: {m11.params['late_curr']:.6f} "
          f"(SE: {m11.bse['late_curr']:.6f}, p={m11.pvalues['late_curr']:.4f})")
    results["ht_shrink_late_conifer"] = {
        "dep_var": "HT shrinkage (conifers only)",
        "coef": m11.params["late_curr"],
        "se": m11.bse["late_curr"],
        "pvalue": m11.pvalues["late_curr"],
        "n": int(m11.nobs),
        "r2": m11.rsquared,
    }

    # --- Model 12: DBH anomaly ~ LATE, conifers only (placebo) ---
    print("\n--- Model 12: DBH Anomaly ~ Late Season (CONIFERS only, placebo) ---")
    dia_conifer = df[df["is_conifer"] == 1].copy()
    m12 = smf.ols(
        "dia_anomaly ~ late_curr + C(STATE) + C(measyear_curr)",
        data=dia_conifer,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(dia_conifer)})
    print(f"  LATE_SEASON coef: {m12.params['late_curr']:.6f} "
          f"(SE: {m12.bse['late_curr']:.6f}, p={m12.pvalues['late_curr']:.4f})")
    print(f"  (DBH is not affected by leaf-off — placebo check)")
    results["dia_anomaly_late_conifer"] = {
        "dep_var": "DBH anomaly (conifers only, placebo)",
        "coef": m12.params["late_curr"],
        "se": m12.bse["late_curr"],
        "pvalue": m12.pvalues["late_curr"],
        "n": int(m12.nobs),
        "r2": m12.rsquared,
    }

    # Save regression results
    rows = []
    for model_name, res in results.items():
        rows.append({
            "model": model_name,
            "dep_var": res["dep_var"],
            "late_season_coef": round(res["coef"], 6),
            "late_season_se": round(res["se"], 6),
            "late_season_pvalue": round(res["pvalue"], 6),
            "n_obs": res["n"],
            "r_squared": round(res["r2"], 6),
        })
    reg_df = pd.DataFrame(rows)
    reg_df.to_csv(TABLE_DIR / "remeasurement_anomaly_regression.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'remeasurement_anomaly_regression.csv'}")

    return results


def plot_anomaly_rates(monthly: pd.DataFrame):
    """
    Figure: Anomaly rates by month for DBH vs HT.
    If height is the margin of effort reduction, the HT line should show
    more seasonal variation than the DBH line.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: Total anomaly rates
    ax = axes[0]
    ax.plot(monthly["measmon_curr"], monthly["dia_anomaly_rate"],
            "ko-", markersize=5, label="DBH anomaly")
    ax.plot(monthly["measmon_curr"], monthly["ht_anomaly_rate"],
            "k^--", markersize=5, label="Height anomaly")
    ax.set_xlabel("Current Measurement Month")
    ax.set_ylabel("Anomaly Rate (%)")
    ax.set_title("(a) Growth Anomaly Rate by Month")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel B: Shrinkage rates only
    ax = axes[1]
    ax.plot(monthly["measmon_curr"], monthly["dia_shrink_rate"],
            "ko-", markersize=5, label="DBH shrinkage")
    ax.plot(monthly["measmon_curr"], monthly["ht_shrink_rate"],
            "k^--", markersize=5, label="Height shrinkage")
    ax.set_xlabel("Current Measurement Month")
    ax.set_ylabel("Shrinkage Rate (%)")
    ax.set_title("(b) Impossible Shrinkage Rate by Month")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "remeasurement_anomalies.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / "remeasurement_anomalies.png", dpi=300, bbox_inches="tight")
    print(f"\nSaved: {FIG_DIR / 'remeasurement_anomalies.pdf'}")
    plt.close(fig)


def growth_distribution_comparison(df: pd.DataFrame):
    """
    Compare the distribution of annualized growth by season.
    Tests whether late-season height growth has lower variance (consistent
    with estimation compressing toward species-typical growth rates).
    """
    print("\n" + "=" * 70)
    print("GROWTH DISTRIBUTION COMPARISON")
    print("=" * 70)

    ht_df = df[df["ht_growth_annual"].notna() & np.isfinite(df["ht_growth_annual"])].copy()
    # Trim extreme outliers for summary stats
    ht_trim = ht_df[
        (ht_df["ht_growth_annual"] > -10) & (ht_df["ht_growth_annual"] < 15)
    ]

    for label, late_val in [("Early (May-Aug)", 0), ("Late (Sep-Dec)", 1)]:
        sub = ht_trim[ht_trim["late_curr"] == late_val]
        print(f"\n  {label} (n={len(sub):,}):")
        print(f"    HT growth: mean={sub['ht_growth_annual'].mean():.2f} ft/yr, "
              f"SD={sub['ht_growth_annual'].std():.2f}, "
              f"median={sub['ht_growth_annual'].median():.2f}")
        sub_dia = df[df["late_curr"] == late_val]
        print(f"    DBH growth: mean={sub_dia['dia_growth_annual'].mean():.3f} in/yr, "
              f"SD={sub_dia['dia_growth_annual'].std():.3f}, "
              f"median={sub_dia['dia_growth_annual'].median():.3f}")

    # Levene test on height growth variance: early vs late
    early_ht = ht_trim[ht_trim["late_curr"] == 0]["ht_growth_annual"].values
    late_ht = ht_trim[ht_trim["late_curr"] == 1]["ht_growth_annual"].values
    stat, p = stats.levene(early_ht, late_ht, center="median")
    print(f"\n  Levene test (HT growth variance, early vs late):")
    print(f"    Early SD: {early_ht.std():.3f}, Late SD: {late_ht.std():.3f}")
    print(f"    F={stat:.1f}, p={p:.4e}")
    direction = "LOWER" if late_ht.std() < early_ht.std() else "HIGHER"
    print(f"    Late-season HT growth variance is {direction}")
    print(f"    (Ocular estimation predicts LOWER — estimates track typical growth)")

    # Same for DBH
    early_dia = df[df["late_curr"] == 0]["dia_growth_annual"].dropna().values
    late_dia = df[df["late_curr"] == 1]["dia_growth_annual"].dropna().values
    stat_d, p_d = stats.levene(early_dia, late_dia, center="median")
    print(f"\n  Levene test (DBH growth variance, early vs late):")
    print(f"    Early SD: {early_dia.std():.3f}, Late SD: {late_dia.std():.3f}")
    print(f"    F={stat_d:.1f}, p={p_d:.4e}")

    # --- Species group decomposition ---
    print(f"\n--- Growth Variance by Species Group (Leaf-Off Test) ---")
    for sp_label, sp_val in [("CONIFER", 1), ("HARDWOOD", 0)]:
        sp_ht = ht_trim[ht_trim["is_conifer"] == sp_val]
        early_sp = sp_ht[sp_ht["late_curr"] == 0]["ht_growth_annual"].values
        late_sp = sp_ht[sp_ht["late_curr"] == 1]["ht_growth_annual"].values
        if len(early_sp) > 100 and len(late_sp) > 100:
            stat_sp, p_sp = stats.levene(early_sp, late_sp, center="median")
            direction_sp = "LOWER" if late_sp.std() < early_sp.std() else "HIGHER"
            print(f"\n  {sp_label} HT growth variance (early vs late):")
            print(f"    Early: SD={early_sp.std():.3f} (n={len(early_sp):,})")
            print(f"    Late:  SD={late_sp.std():.3f} (n={len(late_sp):,})")
            print(f"    Levene F={stat_sp:.1f}, p={p_sp:.4e}")
            print(f"    Late-season variance is {direction_sp}")
            if sp_val == 1:
                print(f"    (Clean test — no leaf-off confound)")
            else:
                print(f"    (Confounded — leaf-off improves late-season visibility)")


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("ANALYSIS 4: Remeasurement Growth Anomalies (DBH vs Height)")
    print("=" * 70)

    # Load data
    print("\nLoading remeasurement pairs from state databases...")
    df = load_remeasurement_pairs()

    # Descriptive statistics
    descriptive_anomalies(df)

    # Monthly rates
    monthly = anomaly_rates_by_month(df)

    # Regressions
    reg_results = run_anomaly_regressions(df)

    # Growth distribution comparison
    growth_distribution_comparison(df)

    # Figures
    print("\n--- Generating Figures ---")
    plot_anomaly_rates(monthly)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    dia_res = reg_results.get("dia_anomaly_late", {})
    ht_res = reg_results.get("ht_anomaly_late", {})
    ht_con = reg_results.get("ht_anomaly_late_conifer", {})
    ht_hw = reg_results.get("ht_anomaly_late_hardwood", {})

    print(f"\n  POOLED:")
    print(f"    DBH anomaly ~ LATE_SEASON: coef={dia_res.get('coef', 'N/A'):.6f}, "
          f"p={dia_res.get('pvalue', 'N/A'):.4f}")
    print(f"    HT anomaly  ~ LATE_SEASON: coef={ht_res.get('coef', 'N/A'):.6f}, "
          f"p={ht_res.get('pvalue', 'N/A'):.4f}")

    print(f"\n  SPECIES DECOMPOSITION (leaf-off test):")
    print(f"    HT anomaly ~ LATE (conifers):  coef={ht_con.get('coef', 'N/A'):.6f}, "
          f"p={ht_con.get('pvalue', 'N/A'):.4f}  <-- clean test")
    print(f"    HT anomaly ~ LATE (hardwoods): coef={ht_hw.get('coef', 'N/A'):.6f}, "
          f"p={ht_hw.get('pvalue', 'N/A'):.4f}  <-- confounded by leaf-off")

    # Interpretation
    conifer_coef = ht_con.get("coef", 0)
    hardwood_coef = ht_hw.get("coef", 0)
    if conifer_coef > 0 and conifer_coef > hardwood_coef:
        print(f"\n  Conifer HT anomalies INCREASE more in late season than hardwoods")
        print(f"  Consistent with: leaf-off masks effort reduction in hardwoods,")
        print(f"  and the clean conifer test reveals seasonal effort changes")
    elif conifer_coef > 0:
        print(f"\n  Conifer HT anomalies increase in late season (positive coef)")
        print(f"  Suggestive of effort reduction, but hardwood effect is also positive")
    elif conifer_coef < hardwood_coef:
        print(f"\n  Hardwood HT anomalies increase MORE than conifer in late season")
        print(f"  Opposite to leaf-off prediction — may reflect other confounds")
    else:
        print(f"\n  Both species groups show decreased/flat HT anomalies late season")
        print(f"  Not consistent with height-specific effort reduction")

    print("\n" + "=" * 70)
    print("ANALYSIS 4 COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
