#!/usr/bin/env python3
"""
Analysis 3: QA Crew vs. Production Crew Comparison (Difference-in-Differences)

Exploits QA_STATUS=7 plots as a natural control group. QA crews (supervisory
staff performing blind remeasurements) face fundamentally different incentive
structures than production crews: no seasonal appointment pressure, no
workload quotas, explicit quality mandate. If seasonal measurement patterns
are incentive-driven (ocular estimation), they should appear in production data
but not QA data. If environmental (weather, fatigue, leaf-off), both groups
should show similar patterns.

Key DID specification:
    |resid|_{itsy} = a0 + a1*QA_i + a2*LATE_t + a3*(QA_i × LATE_t)
                     + gamma_s + delta_y + eps_{itsy}

    a3 > 0: QA crews show MORE residual increase late-season than production
    → production crews suppress natural variance increase → ocular estimation

Outputs:
  - tables/qa_comparison_summary.csv
  - tables/qa_comparison_regression.csv
  - tables/qa_heaping_comparison.csv
  - tables/qa_residual_by_month.csv
  - figures/qa_comparison_residuals.pdf
  - figures/qa_comparison_heaping.pdf

Usage:
    python qa_comparison.py
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


def load_qa_and_production_data() -> pd.DataFrame:
    """
    Load both QA (STATUS=7) and production (STATUS=1) trees from all
    state SQLite databases. The parquet file only contains production data,
    so we query the databases directly.
    """
    db_files = sorted(DATA_DIR.glob("SQLite_FIADB_*.db"))
    if not db_files:
        print(f"Error: No FIA databases found in {DATA_DIR}")
        sys.exit(1)

    frames = []
    for db_path in db_files:
        state = db_path.stem.split("_")[-1]
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        df = pd.read_sql_query("""
            SELECT t.DIA, t.HT, t.SPGRPCD, t.STATUSCD,
                   p.MEASMON, p.MEASYEAR, p.STATECD, p.QA_STATUS
            FROM TREE t JOIN PLOT p ON t.PLT_CN = p.CN
            WHERE p.QA_STATUS IN (1, 7)
              AND t.STATUSCD = 1
              AND t.DIA > 0
              AND p.MEASMON IS NOT NULL
        """, conn)
        conn.close()
        print(f"  {state}: {len(df):,} trees "
              f"(prod={len(df[df['QA_STATUS']==1]):,}, "
              f"QA={len(df[df['QA_STATUS']==7]):,})")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df["STATE"] = df["STATECD"].map(STATE_FIPS)
    df["is_QA"] = (df["QA_STATUS"] == 7).astype(int)
    df["LATE_SEASON"] = df["MEASMON"].isin([9, 10, 11, 12]).astype(int)

    # Digit heaping indicators
    df["DIA_tenth"] = (df["DIA"] * 10).round().astype(int) % 10
    df["DIA_whole"] = (df["DIA_tenth"] == 0).astype(int)
    df["DIA_half"] = (df["DIA_tenth"].isin([0, 5])).astype(int)

    # Log transforms
    df["lnDIA"] = np.log(df["DIA"])
    ht_valid = df["HT"].notna() & (df["HT"] > 0)
    df.loc[ht_valid, "lnHT"] = np.log(df.loc[ht_valid, "HT"])

    # Height rounding
    df.loc[ht_valid, "HT_div5"] = (df.loc[ht_valid, "HT"] % 5 == 0).astype(int)

    # Integer types for FE
    df["MEASMON"] = df["MEASMON"].astype(int)
    df["MEASYEAR"] = df["MEASYEAR"].astype(int)

    return df


def fit_allometric_and_residuals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fit allometric model on PRODUCTION data only, then predict for both
    QA and production trees. This ensures residuals are measured against
    the same benchmark.

    Design choice: Fitting on production data only avoids mechanical
    contamination of the allometric benchmark by QA measurement
    differences. QA residuals are therefore out-of-sample predictions.
    If QA trees differ systematically in species composition or forest
    type, their residuals may be slightly inflated. In practice, QA
    plots are randomly selected from the same population as production
    plots, so species composition should be similar on expectation.
    """
    allo = df[df["lnHT"].notna() & df["SPGRPCD"].notna()].copy()
    allo["SPGRPCD"] = allo["SPGRPCD"].astype(int)

    prod = allo[allo["QA_STATUS"] == 1]
    model = smf.ols("lnHT ~ lnDIA + C(SPGRPCD)", data=prod).fit()

    print(f"\n--- Allometric Model (fit on production data only) ---")
    print(f"  N = {model.nobs:,.0f}")
    print(f"  R² = {model.rsquared:.4f}")
    print(f"  β(lnDIA) = {model.params['lnDIA']:.4f}")

    allo["predicted"] = model.predict(allo)
    allo["resid"] = allo["lnHT"] - allo["predicted"]
    allo["abs_resid"] = allo["resid"].abs()
    allo["resid_sq"] = allo["resid"] ** 2

    return allo


def descriptive_comparison(allo: pd.DataFrame, df: pd.DataFrame):
    """Print and save descriptive comparisons between QA and production."""
    print("\n" + "=" * 70)
    print("DESCRIPTIVE COMPARISONS")
    print("=" * 70)

    # --- Sample sizes ---
    print("\n--- Sample Sizes ---")
    for label, qa_val in [("Production", 1), ("QA", 7)]:
        n = len(df[df["QA_STATUS"] == qa_val])
        n_allo = len(allo[allo["QA_STATUS"] == qa_val])
        states = sorted(df[df["QA_STATUS"] == qa_val]["STATE"].unique())
        print(f"  {label:12s}: {n:>10,} trees, {n_allo:>10,} with HT")
        print(f"               States: {', '.join(states)}")

    # --- QA sample by state ---
    print("\n--- QA Trees by State ---")
    qa_by_state = allo[allo["is_QA"] == 1].groupby("STATE").agg(
        n=("resid", "count"),
        months=("MEASMON", lambda x: f"{x.min()}-{x.max()}"),
    ).reset_index()
    print(qa_by_state.to_string(index=False))

    # --- Digit heaping ---
    print("\n--- Digit Heaping: Whole-Inch DBH Rate ---")
    heap = df.groupby(["QA_STATUS", "LATE_SEASON"]).agg(
        n=("DIA_whole", "count"),
        whole_rate=("DIA_whole", "mean"),
    ).reset_index()
    for _, row in heap.iterrows():
        label = "QA" if row["QA_STATUS"] == 7 else "Prod"
        season = "Late " if row["LATE_SEASON"] == 1 else "Early"
        print(f"  {label:5s} {season}: {row['whole_rate']*100:.2f}%  "
              f"(n={int(row['n']):,})")

    # --- Allometric residual variance ---
    print("\n--- Allometric Residual Variance ---")
    rv = allo.groupby(["QA_STATUS", "LATE_SEASON"]).agg(
        n=("resid", "count"),
        sd_resid=("resid", "std"),
        mean_abs_resid=("abs_resid", "mean"),
        median_abs_resid=("abs_resid", "median"),
    ).reset_index()
    for _, row in rv.iterrows():
        label = "QA" if row["QA_STATUS"] == 7 else "Prod"
        season = "Late " if row["LATE_SEASON"] == 1 else "Early"
        print(f"  {label:5s} {season}: SD={row['sd_resid']:.4f}, "
              f"|resid|={row['mean_abs_resid']:.4f}  "
              f"(n={int(row['n']):,})")

    # Save summary
    summary = rv.copy()
    summary["group"] = summary["QA_STATUS"].map({1: "Production", 7: "QA"})
    summary["season"] = summary["LATE_SEASON"].map({0: "Early", 1: "Late"})
    summary.to_csv(TABLE_DIR / "qa_comparison_summary.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'qa_comparison_summary.csv'}")


def levene_tests(allo: pd.DataFrame):
    """Run Levene's tests for variance equality."""
    print("\n" + "=" * 70)
    print("LEVENE'S TESTS")
    print("=" * 70)

    results = {}

    # 1. QA vs Production (overall)
    prod_r = allo[allo["is_QA"] == 0]["resid"].values
    qa_r = allo[allo["is_QA"] == 1]["resid"].values
    stat, p = stats.levene(prod_r, qa_r, center="median")
    print(f"\n  QA vs Production (overall):")
    print(f"    Production SD: {prod_r.std():.4f} (n={len(prod_r):,})")
    print(f"    QA SD:         {qa_r.std():.4f} (n={len(qa_r):,})")
    print(f"    Levene F={stat:.1f}, p={p:.4e}")
    direction = "HIGHER" if qa_r.std() > prod_r.std() else "LOWER"
    print(f"    QA variance is {direction} than production")
    results["qa_vs_prod"] = {"F": stat, "p": p,
                             "prod_sd": prod_r.std(), "qa_sd": qa_r.std()}

    # 2. Seasonal within production
    p_early = allo[(allo["is_QA"] == 0) & (allo["LATE_SEASON"] == 0)]["resid"].values
    p_late = allo[(allo["is_QA"] == 0) & (allo["LATE_SEASON"] == 1)]["resid"].values
    stat, p = stats.levene(p_early, p_late, center="median")
    print(f"\n  Seasonal within Production:")
    print(f"    Early SD: {p_early.std():.4f} (n={len(p_early):,})")
    print(f"    Late SD:  {p_late.std():.4f} (n={len(p_late):,})")
    print(f"    Levene F={stat:.1f}, p={p:.4e}")
    direction = "INCREASES" if p_late.std() > p_early.std() else "DECREASES"
    print(f"    Production variance {direction} late season")
    results["prod_seasonal"] = {"F": stat, "p": p,
                                "early_sd": p_early.std(), "late_sd": p_late.std()}

    # 3. Seasonal within QA
    q_early = allo[(allo["is_QA"] == 1) & (allo["LATE_SEASON"] == 0)]["resid"].values
    q_late = allo[(allo["is_QA"] == 1) & (allo["LATE_SEASON"] == 1)]["resid"].values
    stat, p = stats.levene(q_early, q_late, center="median")
    print(f"\n  Seasonal within QA:")
    print(f"    Early SD: {q_early.std():.4f} (n={len(q_early):,})")
    print(f"    Late SD:  {q_late.std():.4f} (n={len(q_late):,})")
    print(f"    Levene F={stat:.1f}, p={p:.4e}")
    direction = "INCREASES" if q_late.std() > q_early.std() else "DECREASES"
    print(f"    QA variance {direction} late season")
    results["qa_seasonal"] = {"F": stat, "p": p,
                              "early_sd": q_early.std(), "late_sd": q_late.std()}

    return results


def did_regressions(allo: pd.DataFrame, df: pd.DataFrame):
    """
    Difference-in-differences regressions:
      - Allometric |residual| ~ is_QA + LATE + QA×LATE + state FE + year FE
      - Digit heaping ~ is_QA + LATE + QA×LATE + state FE + year FE
    """
    print("\n" + "=" * 70)
    print("DIFFERENCE-IN-DIFFERENCES REGRESSIONS")
    print("=" * 70)

    results = {}
    cluster_var = lambda d: d["STATE"].astype(str) + "_" + d["MEASYEAR"].astype(str)

    # --- Model 1: |Allometric Residual| DID ---
    print("\n--- Model 1: |Allometric Residual| ~ QA + LATE + QA×LATE ---")
    allo["QA_x_LATE"] = allo["is_QA"] * allo["LATE_SEASON"]
    m1 = smf.ols(
        "abs_resid ~ is_QA + LATE_SEASON + QA_x_LATE + C(STATE) + C(MEASYEAR)",
        data=allo,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(allo)})

    print(f"  N = {m1.nobs:,.0f}")
    print(f"  is_QA:       {m1.params['is_QA']:>10.6f} "
          f"(SE: {m1.bse['is_QA']:.6f}, p={m1.pvalues['is_QA']:.4f})")
    print(f"  LATE_SEASON: {m1.params['LATE_SEASON']:>10.6f} "
          f"(SE: {m1.bse['LATE_SEASON']:.6f}, p={m1.pvalues['LATE_SEASON']:.4f})")
    print(f"  QA × LATE:   {m1.params['QA_x_LATE']:>10.6f} "
          f"(SE: {m1.bse['QA_x_LATE']:.6f}, p={m1.pvalues['QA_x_LATE']:.4f})")

    results["did_abs_resid"] = {
        "dep_var": "|allometric residual|",
        "is_QA_coef": m1.params["is_QA"],
        "is_QA_se": m1.bse["is_QA"],
        "is_QA_p": m1.pvalues["is_QA"],
        "late_coef": m1.params["LATE_SEASON"],
        "late_se": m1.bse["LATE_SEASON"],
        "late_p": m1.pvalues["LATE_SEASON"],
        "interaction_coef": m1.params["QA_x_LATE"],
        "interaction_se": m1.bse["QA_x_LATE"],
        "interaction_p": m1.pvalues["QA_x_LATE"],
        "n": int(m1.nobs),
        "r2": m1.rsquared,
    }

    # --- Model 2: Squared Residual DID ---
    print("\n--- Model 2: Residual² ~ QA + LATE + QA×LATE ---")
    m2 = smf.ols(
        "resid_sq ~ is_QA + LATE_SEASON + QA_x_LATE + C(STATE) + C(MEASYEAR)",
        data=allo,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(allo)})

    print(f"  is_QA:       {m2.params['is_QA']:>10.6f} "
          f"(SE: {m2.bse['is_QA']:.6f}, p={m2.pvalues['is_QA']:.4f})")
    print(f"  LATE_SEASON: {m2.params['LATE_SEASON']:>10.6f} "
          f"(SE: {m2.bse['LATE_SEASON']:.6f}, p={m2.pvalues['LATE_SEASON']:.4f})")
    print(f"  QA × LATE:   {m2.params['QA_x_LATE']:>10.6f} "
          f"(SE: {m2.bse['QA_x_LATE']:.6f}, p={m2.pvalues['QA_x_LATE']:.4f})")

    results["did_resid_sq"] = {
        "dep_var": "residual²",
        "is_QA_coef": m2.params["is_QA"],
        "is_QA_se": m2.bse["is_QA"],
        "is_QA_p": m2.pvalues["is_QA"],
        "late_coef": m2.params["LATE_SEASON"],
        "late_se": m2.bse["LATE_SEASON"],
        "late_p": m2.pvalues["LATE_SEASON"],
        "interaction_coef": m2.params["QA_x_LATE"],
        "interaction_se": m2.bse["QA_x_LATE"],
        "interaction_p": m2.pvalues["QA_x_LATE"],
        "n": int(m2.nobs),
        "r2": m2.rsquared,
    }

    # --- Model 3: |Residual| DID with species group FE ---
    print("\n--- Model 3: |Residual| DID + Species Group FE ---")
    m3 = smf.ols(
        "abs_resid ~ is_QA + LATE_SEASON + QA_x_LATE + C(STATE) + C(MEASYEAR) + C(SPGRPCD)",
        data=allo,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(allo)})

    print(f"  is_QA:       {m3.params['is_QA']:>10.6f} "
          f"(SE: {m3.bse['is_QA']:.6f}, p={m3.pvalues['is_QA']:.4f})")
    print(f"  LATE_SEASON: {m3.params['LATE_SEASON']:>10.6f} "
          f"(SE: {m3.bse['LATE_SEASON']:.6f}, p={m3.pvalues['LATE_SEASON']:.4f})")
    print(f"  QA × LATE:   {m3.params['QA_x_LATE']:>10.6f} "
          f"(SE: {m3.bse['QA_x_LATE']:.6f}, p={m3.pvalues['QA_x_LATE']:.4f})")

    results["did_abs_resid_species"] = {
        "dep_var": "|allometric residual| + species FE",
        "is_QA_coef": m3.params["is_QA"],
        "is_QA_se": m3.bse["is_QA"],
        "is_QA_p": m3.pvalues["is_QA"],
        "late_coef": m3.params["LATE_SEASON"],
        "late_se": m3.bse["LATE_SEASON"],
        "late_p": m3.pvalues["LATE_SEASON"],
        "interaction_coef": m3.params["QA_x_LATE"],
        "interaction_se": m3.bse["QA_x_LATE"],
        "interaction_p": m3.pvalues["QA_x_LATE"],
        "n": int(m3.nobs),
        "r2": m3.rsquared,
    }

    # --- Model 4: Digit Heaping DID ---
    print("\n--- Model 4: Whole-Inch DBH ~ QA + LATE + QA×LATE ---")
    df["QA_x_LATE"] = df["is_QA"] * df["LATE_SEASON"]
    m4 = smf.ols(
        "DIA_whole ~ is_QA + LATE_SEASON + QA_x_LATE + C(STATE) + C(MEASYEAR)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(df)})

    print(f"  N = {m4.nobs:,.0f}")
    print(f"  is_QA:       {m4.params['is_QA']:>10.6f} "
          f"(SE: {m4.bse['is_QA']:.6f}, p={m4.pvalues['is_QA']:.4f})")
    print(f"  LATE_SEASON: {m4.params['LATE_SEASON']:>10.6f} "
          f"(SE: {m4.bse['LATE_SEASON']:.6f}, p={m4.pvalues['LATE_SEASON']:.4f})")
    print(f"  QA × LATE:   {m4.params['QA_x_LATE']:>10.6f} "
          f"(SE: {m4.bse['QA_x_LATE']:.6f}, p={m4.pvalues['QA_x_LATE']:.4f})")

    results["did_heaping"] = {
        "dep_var": "whole-inch DBH indicator",
        "is_QA_coef": m4.params["is_QA"],
        "is_QA_se": m4.bse["is_QA"],
        "is_QA_p": m4.pvalues["is_QA"],
        "late_coef": m4.params["LATE_SEASON"],
        "late_se": m4.bse["LATE_SEASON"],
        "late_p": m4.pvalues["LATE_SEASON"],
        "interaction_coef": m4.params["QA_x_LATE"],
        "interaction_se": m4.bse["QA_x_LATE"],
        "interaction_p": m4.pvalues["QA_x_LATE"],
        "n": int(m4.nobs),
        "r2": m4.rsquared,
    }

    # --- Model 5: Height rounding DID ---
    print("\n--- Model 5: Height Div-5 ~ QA + LATE + QA×LATE ---")
    ht_df = df[df["HT_div5"].notna()].copy()
    ht_df["QA_x_LATE"] = ht_df["is_QA"] * ht_df["LATE_SEASON"]
    m5 = smf.ols(
        "HT_div5 ~ is_QA + LATE_SEASON + QA_x_LATE + C(STATE) + C(MEASYEAR)",
        data=ht_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_var(ht_df)})

    print(f"  N = {m5.nobs:,.0f}")
    print(f"  is_QA:       {m5.params['is_QA']:>10.6f} "
          f"(SE: {m5.bse['is_QA']:.6f}, p={m5.pvalues['is_QA']:.4f})")
    print(f"  LATE_SEASON: {m5.params['LATE_SEASON']:>10.6f} "
          f"(SE: {m5.bse['LATE_SEASON']:.6f}, p={m5.pvalues['LATE_SEASON']:.4f})")
    print(f"  QA × LATE:   {m5.params['QA_x_LATE']:>10.6f} "
          f"(SE: {m5.bse['QA_x_LATE']:.6f}, p={m5.pvalues['QA_x_LATE']:.4f})")

    results["did_ht_rounding"] = {
        "dep_var": "height div-5 indicator",
        "is_QA_coef": m5.params["is_QA"],
        "is_QA_se": m5.bse["is_QA"],
        "is_QA_p": m5.pvalues["is_QA"],
        "late_coef": m5.params["LATE_SEASON"],
        "late_se": m5.bse["LATE_SEASON"],
        "late_p": m5.pvalues["LATE_SEASON"],
        "interaction_coef": m5.params["QA_x_LATE"],
        "interaction_se": m5.bse["QA_x_LATE"],
        "interaction_p": m5.pvalues["QA_x_LATE"],
        "n": int(m5.nobs),
        "r2": m5.rsquared,
    }

    # --- Wild Cluster Bootstrap for primary DID specification ---
    print("\n--- Wild Cluster Bootstrap (primary DID: |resid| ~ QA×LATE) ---")
    n_boot = 999
    cluster_ids = allo["STATE"].unique()
    n_clusters = len(cluster_ids)
    print(f"  Clusters (states): {n_clusters}")
    print(f"  Bootstrap replications: {n_boot}")

    # Absorb state and year FE by demeaning within state-year groups.
    # This reduces the design matrix to just 4 columns (const + 3 treatment vars).
    allo_dm = allo[["abs_resid", "is_QA", "LATE_SEASON", "QA_x_LATE", "STATE", "MEASYEAR"]].copy()
    group_cols = ["STATE", "MEASYEAR"]
    for col in ["abs_resid", "is_QA", "LATE_SEASON", "QA_x_LATE"]:
        group_means = allo_dm.groupby(group_cols)[col].transform("mean")
        allo_dm[col] = allo_dm[col] - group_means

    y_dm = allo_dm["abs_resid"].values.astype(np.float64)
    X_dm = allo_dm[["is_QA", "LATE_SEASON", "QA_x_LATE"]].values.astype(np.float64)
    qxl_idx = 2  # QA_x_LATE is third column

    # Map each observation to its cluster (state) index
    state_to_idx = {s: i for i, s in enumerate(cluster_ids)}
    cluster_map = allo["STATE"].map(state_to_idx).values.astype(int)

    # Restricted model (no interaction): demean only is_QA and LATE_SEASON
    X_r = X_dm[:, :2]  # just is_QA and LATE_SEASON (demeaned)
    beta_r = np.linalg.lstsq(X_r, y_dm, rcond=None)[0]
    fitted_r = X_r @ beta_r
    resid_r = y_dm - fitted_r

    # Full model
    beta_f = np.linalg.lstsq(X_dm, y_dm, rcond=None)[0]
    XtX_inv = np.linalg.inv(X_dm.T @ X_dm)

    # Observed t-stat (use the statsmodels one for consistency)
    t_obs = m1.params["QA_x_LATE"] / m1.bse["QA_x_LATE"]

    # Pre-compute cluster masks
    cluster_masks = [cluster_map == c for c in range(n_clusters)]
    cluster_X = [X_dm[mask] for mask in cluster_masks]

    # Wild cluster bootstrap (Rademacher weights)
    rng = np.random.default_rng(42)
    boot_t_stats = np.empty(n_boot)

    for b_iter in range(n_boot):
        weights = rng.choice([-1.0, 1.0], size=n_clusters)
        obs_weights = weights[cluster_map]

        y_boot = fitted_r + resid_r * obs_weights
        beta_boot = np.linalg.lstsq(X_dm, y_boot, rcond=None)[0]
        resid_boot = y_boot - X_dm @ beta_boot

        # Cluster-robust SE (sandwich, only 3x3 matrix)
        meat = np.zeros((3, 3))
        for c_idx in range(n_clusters):
            ec = resid_boot[cluster_masks[c_idx]]
            score_c = cluster_X[c_idx].T @ ec
            meat += np.outer(score_c, score_c)
        V = XtX_inv @ meat @ XtX_inv
        se_boot = np.sqrt(max(V[qxl_idx, qxl_idx], 0))
        boot_t_stats[b_iter] = beta_boot[qxl_idx] / se_boot if se_boot > 0 else 0.0

        if (b_iter + 1) % 200 == 0:
            print(f"    Bootstrap iteration {b_iter + 1}/{n_boot}")

    # Two-sided p-value
    boot_p = np.mean(np.abs(boot_t_stats) >= np.abs(t_obs))
    print(f"  Observed t-stat: {t_obs:.3f}")
    print(f"  Wild cluster bootstrap p-value: {boot_p:.4f}")
    results["wild_bootstrap"] = {
        "t_obs": t_obs,
        "boot_p": boot_p,
        "n_boot": n_boot,
        "n_clusters": n_clusters,
    }

    # Save regression table
    rows = []
    for model_name, res in results.items():
        if "interaction_coef" not in res:
            continue  # skip wild_bootstrap entry
        rows.append({
            "model": model_name,
            "dep_var": res["dep_var"],
            "is_QA_coef": round(res["is_QA_coef"], 6),
            "is_QA_se": round(res["is_QA_se"], 6),
            "is_QA_p": round(res["is_QA_p"], 4),
            "late_coef": round(res["late_coef"], 6),
            "late_se": round(res["late_se"], 6),
            "late_p": round(res["late_p"], 4),
            "interaction_coef": round(res["interaction_coef"], 6),
            "interaction_se": round(res["interaction_se"], 6),
            "interaction_p": round(res["interaction_p"], 4),
            "n": res["n"],
            "r2": round(res["r2"], 5),
        })
    # Append wild cluster bootstrap results as a separate row
    wb = results["wild_bootstrap"]
    rows.append({
        "model": "wild_cluster_bootstrap",
        "dep_var": "|allometric residual| (WCR bootstrap)",
        "interaction_coef": round(wb["t_obs"], 4),
        "interaction_p": round(wb["boot_p"], 4),
        "n": wb["n_clusters"],
        "r2": wb["n_boot"],
    })
    reg_df = pd.DataFrame(rows)
    reg_df.to_csv(TABLE_DIR / "qa_comparison_regression.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'qa_comparison_regression.csv'}")

    return results


def monthly_comparison(allo: pd.DataFrame):
    """Compute residual variance by month separately for QA and production."""
    monthly = allo.groupby(["QA_STATUS", "MEASMON"]).agg(
        n=("resid", "count"),
        sd_resid=("resid", "std"),
        mean_abs_resid=("abs_resid", "mean"),
        median_abs_resid=("abs_resid", "median"),
    ).reset_index()

    monthly["group"] = monthly["QA_STATUS"].map({1: "Production", 7: "QA"})
    monthly.to_csv(TABLE_DIR / "qa_residual_by_month.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'qa_residual_by_month.csv'}")
    return monthly


def heaping_comparison_by_month(df: pd.DataFrame):
    """Compute heaping rates by month for QA vs production."""
    monthly = df.groupby(["QA_STATUS", "MEASMON"]).agg(
        n=("DIA_whole", "count"),
        whole_rate=("DIA_whole", "mean"),
        half_rate=("DIA_half", "mean"),
    ).reset_index()

    monthly["group"] = monthly["QA_STATUS"].map({1: "Production", 7: "QA"})
    monthly["whole_pct"] = (monthly["whole_rate"] * 100).round(2)
    monthly["half_pct"] = (monthly["half_rate"] * 100).round(2)
    monthly.to_csv(TABLE_DIR / "qa_heaping_comparison.csv", index=False)
    print(f"Saved: {TABLE_DIR / 'qa_heaping_comparison.csv'}")
    return monthly


def plot_residual_comparison(monthly: pd.DataFrame):
    """
    Figure: Allometric residual dispersion by month, QA vs Production.
    Two-panel: (a) residual SD, (b) mean |residual|.
    """
    prod = monthly[monthly["QA_STATUS"] == 1]
    qa = monthly[monthly["QA_STATUS"] == 7]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: Residual SD
    ax = axes[0]
    ax.plot(prod["MEASMON"], prod["sd_resid"], "ko-", markersize=5,
            label="Production crews")
    ax.plot(qa["MEASMON"], qa["sd_resid"], "k^--", markersize=5,
            label="QA crews")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Residual Std. Dev. (ln scale)")
    ax.set_title("(a) Allometric Residual Dispersion")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel B: Mean |residual|
    ax = axes[1]
    ax.plot(prod["MEASMON"], prod["mean_abs_resid"], "ko-", markersize=5,
            label="Production crews")
    ax.plot(qa["MEASMON"], qa["mean_abs_resid"], "k^--", markersize=5,
            label="QA crews")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Mean |Residual| (ln scale)")
    ax.set_title("(b) Mean Absolute Allometric Residual")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "qa_comparison_residuals.pdf", dpi=300,
                bbox_inches="tight")
    fig.savefig(FIG_DIR / "qa_comparison_residuals.png", dpi=300,
                bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'qa_comparison_residuals.pdf'}")
    plt.close(fig)


def plot_heaping_comparison(heap_monthly: pd.DataFrame):
    """Figure: Digit heaping by month, QA vs Production."""
    prod = heap_monthly[heap_monthly["QA_STATUS"] == 1]
    qa = heap_monthly[heap_monthly["QA_STATUS"] == 7]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(prod["MEASMON"], prod["whole_pct"], "ko-", markersize=5,
            label="Production crews")
    ax.plot(qa["MEASMON"], qa["whole_pct"], "k^--", markersize=5,
            label="QA crews")
    ax.axhline(y=10, color="gray", linestyle="--", alpha=0.5,
               label="Expected (uniform)")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Whole-Inch DBH Rate (%)")
    ax.set_title("Digit Heaping: Production vs. QA Crews")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "qa_comparison_heaping.pdf", dpi=300,
                bbox_inches="tight")
    fig.savefig(FIG_DIR / "qa_comparison_heaping.png", dpi=300,
                bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'qa_comparison_heaping.pdf'}")
    plt.close(fig)


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("ANALYSIS 3: QA vs. Production Crew Comparison (DID)")
    print("=" * 70)

    # Load data
    print("\nLoading QA and production data from state databases...")
    df = load_qa_and_production_data()
    print(f"\nTotal: {len(df):,} trees "
          f"(Production: {len(df[df['is_QA']==0]):,}, "
          f"QA: {len(df[df['is_QA']==1]):,})")

    # Fit allometric model and compute residuals
    allo = fit_allometric_and_residuals(df)

    # Descriptive comparisons
    descriptive_comparison(allo, df)

    # Levene's tests
    levene_results = levene_tests(allo)

    # DID regressions
    reg_results = did_regressions(allo, df)

    # Monthly breakdowns
    print("\n--- Monthly Residual Comparison ---")
    resid_monthly = monthly_comparison(allo)

    print("\n--- Monthly Heaping Comparison ---")
    heap_monthly = heaping_comparison_by_month(df)

    # Figures
    print("\n--- Generating Figures ---")
    plot_residual_comparison(resid_monthly)
    plot_heaping_comparison(heap_monthly)

    # --- Final Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY OF KEY FINDINGS")
    print("=" * 70)

    did = reg_results["did_abs_resid"]
    print(f"\n  DID interaction (QA × LATE_SEASON):")
    print(f"    Coefficient: {did['interaction_coef']:.6f}")
    print(f"    Standard error: {did['interaction_se']:.6f}")
    print(f"    p-value: {did['interaction_p']:.4f}")
    print(f"    N: {did['n']:,}")

    if did["interaction_coef"] > 0:
        print(f"\n  INTERPRETATION:")
        print(f"    QA crews show MORE late-season residual increase than production.")
        print(f"    Production crews suppress the natural seasonal increase in")
        print(f"    measurement scatter — consistent with estimation from diameter")
        print(f"    (ocular estimation) compressing residuals toward the allometric mean.")
    else:
        print(f"\n  INTERPRETATION:")
        print(f"    QA crews show LESS late-season residual increase than production.")
        print(f"    Not consistent with the ocular estimation hypothesis.")

    print(f"\n  Additional evidence:")
    heaping = reg_results["did_heaping"]
    print(f"    Heaping DID (QA × LATE): {heaping['interaction_coef']:.6f} "
          f"(p={heaping['interaction_p']:.4f})")
    print(f"    QA baseline heaping (is_QA): {heaping['is_QA_coef']:.6f} "
          f"(p={heaping['is_QA_p']:.4f})")

    print("\n" + "=" * 70)
    print("ANALYSIS 3 COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
