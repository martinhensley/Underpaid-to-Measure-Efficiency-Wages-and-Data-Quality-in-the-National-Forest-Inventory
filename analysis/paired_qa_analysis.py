#!/usr/bin/env python3
"""
Analysis 5: Paired QA/Production Measurement Comparison

Uses the Yanai et al. (2023) dataset (doi:10.2737/RDS-2022-0056):
94,459 paired tree observations across 24 northern states (2011-2016),
with production (F_) and QA (Q_) measurements of the same trees.

Key finding: Production crews use HTCD=3 (ocular estimation) for ~17.5%
of heights; QA crews use it for only ~2.0%. This is direct, coded evidence
of differential estimation.

Sections:
  A. HTCD comparison (headline result)
  B. Paired measurement discrepancies
  C. Allometric conformity
  D. Digit heaping

Outputs:
  - tables/paired_qa_htcd_comparison.csv
  - tables/paired_qa_discrepancy_summary.csv
  - tables/paired_qa_regression.csv
  - figures/paired_qa_discrepancies.pdf
  - figures/paired_qa_htcd_by_month.pdf

Usage:
    python paired_qa_analysis.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.proportion import proportion_confint

BASE = Path(__file__).parent.parent
DATA_DIR = BASE / "data" / "yanai_paired" / "Data"
TABLE_DIR = BASE / "tables"
FIG_DIR = BASE / "figures"

STATE_FIPS = {
    9: "CT", 10: "DE", 17: "IL", 18: "IN", 19: "IA", 20: "KS",
    23: "ME", 24: "MD", 25: "MA", 26: "MI", 27: "MN", 29: "MO",
    31: "NE", 33: "NH", 34: "NJ", 36: "NY", 38: "ND", 39: "OH",
    42: "PA", 44: "RI", 46: "SD", 50: "VT", 54: "WV", 55: "WI",
}


def load_data() -> pd.DataFrame:
    """Load Tree.csv joined with Plot.csv on shared keys."""
    print("Loading Tree.csv...")
    tree = pd.read_csv(DATA_DIR / "Tree.csv", low_memory=False)
    print(f"  Tree rows: {len(tree):,}")

    print("Loading Plot.csv...")
    plot = pd.read_csv(DATA_DIR / "Plot.csv", low_memory=False)
    print(f"  Plot rows: {len(plot):,}")

    # Join on shared keys
    join_keys = ["STATECD", "COUNTYCD", "PLOT", "INVYR"]
    df = tree.merge(plot[join_keys + ["F_MEASMON", "Q_MEASMON"]],
                    on=join_keys, how="left")
    print(f"  Merged rows: {len(df):,}")

    # Restrict to live trees with both production and QA measurements present
    df = df[(df["F_STATUSCD"] == 1) & (df["Q_STATUSCD"] == 1)].copy()
    print(f"  After live-tree filter (F_STATUSCD=1, Q_STATUSCD=1): {len(df):,}")

    # State labels
    df["STATE"] = df["STATECD"].map(STATE_FIPS)
    df["YEAR"] = df["INVYR"]

    # Conifer/hardwood based on F_SPCD (standard FIA: <300 = conifer)
    df["CONIFER"] = (df["F_SPCD"] < 300).astype(int)
    df["SPECIES_TYPE"] = np.where(df["CONIFER"] == 1, "Conifer", "Hardwood")

    # Late season indicator
    df["LATE_SEASON"] = df["F_MEASMON"].isin([9, 10, 11, 12]).astype(int)

    return df


# ─────────────────────────────────────────────────────────────
# Section A: HTCD Comparison
# ─────────────────────────────────────────────────────────────

def section_a_htcd(df: pd.DataFrame) -> dict:
    """HTCD comparison: production vs QA crew estimation rates."""
    print("\n" + "=" * 70)
    print("SECTION A: HTCD COMPARISON (HEADLINE RESULT)")
    print("=" * 70)

    results = {}

    # Restrict to rows with valid HTCD
    ht = df[df["F_HTCD"].notna() & df["Q_HTCD"].notna()].copy()
    ht["F_HTCD"] = ht["F_HTCD"].astype(int)
    ht["Q_HTCD"] = ht["Q_HTCD"].astype(int)
    print(f"\nRows with valid F_HTCD and Q_HTCD: {len(ht):,}")

    # Cross-tabulation
    print("\n--- F_HTCD × Q_HTCD Cross-tabulation ---")
    xtab = pd.crosstab(ht["F_HTCD"], ht["Q_HTCD"], margins=True)
    print(xtab)

    # HTCD=3 rates by crew type
    f_htcd3_rate = (ht["F_HTCD"] == 3).mean()
    q_htcd3_rate = (ht["Q_HTCD"] == 3).mean()
    print(f"\n  Production HTCD=3 rate: {f_htcd3_rate*100:.1f}%")
    print(f"  QA HTCD=3 rate:         {q_htcd3_rate*100:.1f}%")
    print(f"  Ratio:                  {f_htcd3_rate/q_htcd3_rate:.1f}x" if q_htcd3_rate > 0 else "")
    results["f_htcd3_rate"] = f_htcd3_rate
    results["q_htcd3_rate"] = q_htcd3_rate

    # By conifer/hardwood
    print("\n--- HTCD=3 by Species Type ---")
    for stype in ["Conifer", "Hardwood"]:
        sub = ht[ht["SPECIES_TYPE"] == stype]
        f_rate = (sub["F_HTCD"] == 3).mean()
        q_rate = (sub["Q_HTCD"] == 3).mean()
        print(f"  {stype:10s}: Prod={f_rate*100:.1f}%, QA={q_rate*100:.1f}% "
              f"(N={len(sub):,})")

    # Monthly HTCD=3 rates for production crews
    print("\n--- Monthly HTCD=3 Rate (Production Crew) ---")
    monthly = ht.groupby("F_MEASMON").agg(
        n=("F_HTCD", "count"),
        n_htcd3_prod=("F_HTCD", lambda x: (x == 3).sum()),
        htcd3_rate=("F_HTCD", lambda x: (x == 3).mean()),
    ).reset_index()
    monthly.columns = ["month", "n", "n_htcd3_prod", "prod_htcd3_rate"]

    # QA monthly rates
    qa_monthly = ht.groupby("F_MEASMON").agg(
        n_htcd3_qa=("Q_HTCD", lambda x: (x == 3).sum()),
        qa_htcd3_rate=("Q_HTCD", lambda x: (x == 3).mean()),
    ).reset_index()
    qa_monthly.columns = ["month", "n_htcd3_qa", "qa_htcd3_rate"]
    monthly = monthly.merge(qa_monthly, on="month")

    # Wilson 95% CIs for both crew types
    prod_ci = [proportion_confint(int(row["n_htcd3_prod"]), int(row["n"]),
               alpha=0.05, method="wilson") for _, row in monthly.iterrows()]
    monthly["prod_ci_lo"] = [ci[0] for ci in prod_ci]
    monthly["prod_ci_hi"] = [ci[1] for ci in prod_ci]

    qa_ci = [proportion_confint(int(row["n_htcd3_qa"]), int(row["n"]),
             alpha=0.05, method="wilson") for _, row in monthly.iterrows()]
    monthly["qa_ci_lo"] = [ci[0] for ci in qa_ci]
    monthly["qa_ci_hi"] = [ci[1] for ci in qa_ci]

    for _, row in monthly.iterrows():
        print(f"  Month {int(row['month']):2d}: Prod={row['prod_htcd3_rate']*100:5.1f}%, "
              f"QA={row['qa_htcd3_rate']*100:5.1f}%  (N={int(row['n']):,})")
    results["monthly"] = monthly

    # Regression: Prob(F_HTCD==3) ~ LATE_SEASON + C(STATE) + C(YEAR)
    print("\n--- Regression: Prob(F_HTCD==3) ~ LATE_SEASON + C(STATE) + C(YEAR) ---")
    ht["F_HTCD3"] = (ht["F_HTCD"] == 3).astype(int)
    ht_reg = ht.dropna(subset=["F_MEASMON", "STATE", "YEAR"])

    cluster_var = ht_reg["STATE"].astype(str)
    m = smf.ols("F_HTCD3 ~ LATE_SEASON + C(STATE) + C(YEAR)",
                data=ht_reg).fit(cov_type="cluster",
                                  cov_kwds={"groups": cluster_var})
    print(f"  N = {m.nobs:,.0f}")
    print(f"  LATE_SEASON: {m.params['LATE_SEASON']:.6f} "
          f"(SE={m.bse['LATE_SEASON']:.6f}, p={m.pvalues['LATE_SEASON']:.4f})")
    results["late_reg_coef"] = m.params["LATE_SEASON"]
    results["late_reg_se"] = m.bse["LATE_SEASON"]
    results["late_reg_p"] = m.pvalues["LATE_SEASON"]
    results["late_reg_n"] = int(m.nobs)

    # By species type
    for stype in ["Conifer", "Hardwood"]:
        sub = ht_reg[ht_reg["SPECIES_TYPE"] == stype]
        cv = sub["STATE"].astype(str)
        ms = smf.ols("F_HTCD3 ~ LATE_SEASON + C(STATE) + C(YEAR)",
                     data=sub).fit(cov_type="cluster",
                                    cov_kwds={"groups": cv})
        print(f"  {stype:10s}: LATE coef={ms.params['LATE_SEASON']:.6f} "
              f"(p={ms.pvalues['LATE_SEASON']:.4f}, N={ms.nobs:,.0f})")

    # Save HTCD comparison table
    htcd_table = pd.DataFrame({
        "crew": ["Production", "QA"],
        "htcd3_rate_pct": [f_htcd3_rate * 100, q_htcd3_rate * 100],
        "n": [len(ht), len(ht)],
    })
    htcd_table.to_csv(TABLE_DIR / "paired_qa_htcd_comparison.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'paired_qa_htcd_comparison.csv'}")

    return results


def plot_htcd_by_month(htcd_results: dict):
    """Figure: HTCD=3 rates by month for production vs QA crews."""
    monthly = htcd_results["monthly"]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.fill_between(monthly["month"],
                    monthly["prod_ci_lo"] * 100, monthly["prod_ci_hi"] * 100,
                    color="black", alpha=0.12, label="_nolegend_")
    ax.plot(monthly["month"], monthly["prod_htcd3_rate"] * 100,
            "ko-", markersize=6, label="Production crews")
    ax.fill_between(monthly["month"],
                    monthly["qa_ci_lo"] * 100, monthly["qa_ci_hi"] * 100,
                    color="black", alpha=0.06, label="_nolegend_")
    ax.plot(monthly["month"], monthly["qa_htcd3_rate"] * 100,
            "k^--", markersize=6, label="QA crews")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("HTCD=3 (Ocular Estimation) Rate (%)")
    ax.set_title("Height Measurement Method: Production vs. QA Crews")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "paired_qa_htcd_by_month.pdf", dpi=300,
                bbox_inches="tight")
    fig.savefig(FIG_DIR / "paired_qa_htcd_by_month.png", dpi=300,
                bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'paired_qa_htcd_by_month.pdf'}")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
# Section B: Paired Measurement Discrepancies
# ─────────────────────────────────────────────────────────────

def section_b_discrepancies(df: pd.DataFrame) -> dict:
    """Paired measurement discrepancies between production and QA."""
    print("\n" + "=" * 70)
    print("SECTION B: PAIRED MEASUREMENT DISCREPANCIES")
    print("=" * 70)

    results = {}

    # DIA differences
    dia = df[df["F_DIA"].notna() & df["Q_DIA"].notna()].copy()
    dia["DIA_diff"] = dia["F_DIA"] - dia["Q_DIA"]
    dia["abs_DIA_diff"] = dia["DIA_diff"].abs()
    n_dia = len(dia)
    print(f"\n  Paired DIA observations: {n_dia:,}")
    print(f"  DIA diff: mean={dia['DIA_diff'].mean():.4f}, "
          f"SD={dia['DIA_diff'].std():.4f}, "
          f"mean |diff|={dia['abs_DIA_diff'].mean():.4f}")
    results["n_dia"] = n_dia
    results["dia_mean"] = dia["DIA_diff"].mean()
    results["dia_sd"] = dia["DIA_diff"].std()
    results["dia_abs_mean"] = dia["abs_DIA_diff"].mean()

    # HT differences
    ht = df[df["F_HT"].notna() & df["Q_HT"].notna() &
            (df["F_HT"] > 0) & (df["Q_HT"] > 0)].copy()
    ht["HT_diff"] = ht["F_HT"] - ht["Q_HT"]
    ht["abs_HT_diff"] = ht["HT_diff"].abs()
    n_ht = len(ht)
    print(f"\n  Paired HT observations: {n_ht:,}")
    print(f"  HT diff: mean={ht['HT_diff'].mean():.4f}, "
          f"SD={ht['HT_diff'].std():.4f}, "
          f"mean |diff|={ht['abs_HT_diff'].mean():.4f}")
    results["n_ht"] = n_ht
    results["ht_mean"] = ht["HT_diff"].mean()
    results["ht_sd"] = ht["HT_diff"].std()
    results["ht_abs_mean"] = ht["abs_HT_diff"].mean()

    # Regression: |HT_diff| ~ LATE_SEASON + C(STATE) + C(YEAR)
    print("\n--- Regression: |HT_diff| ~ LATE_SEASON + C(STATE) + C(YEAR) ---")
    ht_reg = ht.dropna(subset=["LATE_SEASON", "STATE", "YEAR"])
    cluster_var = ht_reg["STATE"].astype(str)
    m_ht = smf.ols("abs_HT_diff ~ LATE_SEASON + C(STATE) + C(YEAR)",
                   data=ht_reg).fit(cov_type="cluster",
                                     cov_kwds={"groups": cluster_var})
    print(f"  N = {m_ht.nobs:,.0f}")
    print(f"  LATE_SEASON: {m_ht.params['LATE_SEASON']:.4f} "
          f"(SE={m_ht.bse['LATE_SEASON']:.4f}, "
          f"p={m_ht.pvalues['LATE_SEASON']:.4f})")
    results["ht_late_coef"] = m_ht.params["LATE_SEASON"]
    results["ht_late_se"] = m_ht.bse["LATE_SEASON"]
    results["ht_late_p"] = m_ht.pvalues["LATE_SEASON"]

    # Placebo: |DIA_diff| ~ LATE_SEASON + C(STATE) + C(YEAR)
    print("\n--- Placebo: |DIA_diff| ~ LATE_SEASON + C(STATE) + C(YEAR) ---")
    dia_reg = dia.dropna(subset=["LATE_SEASON", "STATE", "YEAR"])
    cluster_var_d = dia_reg["STATE"].astype(str)
    m_dia = smf.ols("abs_DIA_diff ~ LATE_SEASON + C(STATE) + C(YEAR)",
                    data=dia_reg).fit(cov_type="cluster",
                                      cov_kwds={"groups": cluster_var_d})
    print(f"  N = {m_dia.nobs:,.0f}")
    print(f"  LATE_SEASON: {m_dia.params['LATE_SEASON']:.4f} "
          f"(SE={m_dia.bse['LATE_SEASON']:.4f}, "
          f"p={m_dia.pvalues['LATE_SEASON']:.4f})")
    results["dia_late_coef"] = m_dia.params["LATE_SEASON"]
    results["dia_late_se"] = m_dia.bse["LATE_SEASON"]
    results["dia_late_p"] = m_dia.pvalues["LATE_SEASON"]

    # Decompose by F_HTCD (measured vs estimated)
    print("\n--- |HT_diff| by F_HTCD ---")
    ht_with_htcd = ht[ht["F_HTCD"].notna()].copy()
    ht_with_htcd["F_HTCD"] = ht_with_htcd["F_HTCD"].astype(int)
    for htcd_val, label in [(1, "Measured (HTCD=1)"), (3, "Estimated (HTCD=3)")]:
        sub = ht_with_htcd[ht_with_htcd["F_HTCD"] == htcd_val]
        if len(sub) > 0:
            print(f"  {label}: mean |HT_diff|={sub['abs_HT_diff'].mean():.2f} ft, "
                  f"SD={sub['HT_diff'].std():.2f}, N={len(sub):,}")

    # Conifer vs hardwood decomposition
    print("\n--- |HT_diff| by Species Type ---")
    for stype in ["Conifer", "Hardwood"]:
        sub = ht[ht["SPECIES_TYPE"] == stype]
        print(f"  {stype:10s}: mean |HT_diff|={sub['abs_HT_diff'].mean():.2f} ft, "
              f"SD={sub['HT_diff'].std():.2f}, N={len(sub):,}")

    # Save discrepancy summary
    summary = pd.DataFrame([
        {"variable": "DIA", "n": n_dia,
         "mean_diff": dia["DIA_diff"].mean(),
         "sd_diff": dia["DIA_diff"].std(),
         "mean_abs_diff": dia["abs_DIA_diff"].mean(),
         "late_coef": m_dia.params["LATE_SEASON"],
         "late_se": m_dia.bse["LATE_SEASON"],
         "late_p": m_dia.pvalues["LATE_SEASON"]},
        {"variable": "HT", "n": n_ht,
         "mean_diff": ht["HT_diff"].mean(),
         "sd_diff": ht["HT_diff"].std(),
         "mean_abs_diff": ht["abs_HT_diff"].mean(),
         "late_coef": m_ht.params["LATE_SEASON"],
         "late_se": m_ht.bse["LATE_SEASON"],
         "late_p": m_ht.pvalues["LATE_SEASON"]},
    ])
    summary.to_csv(TABLE_DIR / "paired_qa_discrepancy_summary.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'paired_qa_discrepancy_summary.csv'}")

    return results


# ─────────────────────────────────────────────────────────────
# Section C: Allometric Conformity
# ─────────────────────────────────────────────────────────────

def section_c_allometric(df: pd.DataFrame) -> dict:
    """Allometric conformity: do estimated heights track the curve more closely?"""
    print("\n" + "=" * 70)
    print("SECTION C: ALLOMETRIC CONFORMITY")
    print("=" * 70)

    results = {}

    # Need valid QA measurements for fitting, and valid production for predicting
    allo = df[
        (df["Q_HT"].notna()) & (df["Q_HT"] > 0) &
        (df["Q_DIA"].notna()) & (df["Q_DIA"] > 0) &
        (df["F_HT"].notna()) & (df["F_HT"] > 0) &
        (df["F_DIA"].notna()) & (df["F_DIA"] > 0) &
        (df["F_SPCD"].notna())
    ].copy()

    allo["lnQ_HT"] = np.log(allo["Q_HT"])
    allo["lnQ_DIA"] = np.log(allo["Q_DIA"])
    allo["lnF_HT"] = np.log(allo["F_HT"])
    allo["lnF_DIA"] = np.log(allo["F_DIA"])

    # Species group: use broad groups based on SPCD ranges
    # Group by genus-level (first two digits of SPCD for rough grouping)
    allo["SPGRP"] = (allo["F_SPCD"] // 10).astype(int)
    print(f"\n  Allometric sample: {len(allo):,} trees")

    # Fit on QA measurements (gold standard)
    print("\n--- Fitting allometric model on QA measurements ---")
    m_qa = smf.ols("lnQ_HT ~ lnQ_DIA + C(SPGRP)", data=allo).fit()
    print(f"  N = {m_qa.nobs:,.0f}")
    print(f"  R² = {m_qa.rsquared:.4f}")
    print(f"  β(lnQ_DIA) = {m_qa.params['lnQ_DIA']:.4f}")

    # Predict production heights using QA-fitted model
    # We need to use production DIA with QA model coefficients
    # Create prediction frame with production DIA but same species groups
    pred_df = allo.copy()
    pred_df["lnQ_DIA"] = pred_df["lnF_DIA"]  # substitute production DIA
    allo["predicted_HT"] = m_qa.predict(pred_df)
    allo["resid_F"] = allo["lnF_HT"] - allo["predicted_HT"]
    allo["abs_resid_F"] = allo["resid_F"].abs()

    # Also compute QA residuals (in-sample) for comparison
    pred_df_qa = allo.copy()
    pred_df_qa["lnQ_DIA"] = allo["lnQ_DIA"]  # use QA DIA
    allo["predicted_HT_qa"] = m_qa.predict(pred_df_qa)
    allo["resid_Q"] = allo["lnQ_HT"] - allo["predicted_HT_qa"]
    allo["abs_resid_Q"] = allo["resid_Q"].abs()

    # Compare |resid| for F_HTCD=1 (measured) vs F_HTCD=3 (estimated)
    print("\n--- Allometric Residuals by F_HTCD ---")
    allo_htcd = allo[allo["F_HTCD"].notna()].copy()
    allo_htcd["F_HTCD"] = allo_htcd["F_HTCD"].astype(int)

    for htcd_val, label in [(1, "Measured (HTCD=1)"), (3, "Estimated (HTCD=3)")]:
        sub = allo_htcd[allo_htcd["F_HTCD"] == htcd_val]
        if len(sub) > 0:
            print(f"  {label}:")
            print(f"    Production |resid|: mean={sub['abs_resid_F'].mean():.4f}, "
                  f"SD={sub['resid_F'].std():.4f}")
            print(f"    N = {len(sub):,}")
            results[f"htcd{htcd_val}_abs_resid"] = sub["abs_resid_F"].mean()
            results[f"htcd{htcd_val}_resid_sd"] = sub["resid_F"].std()
            results[f"htcd{htcd_val}_n"] = len(sub)

    # Test: are HTCD=3 residuals smaller?
    meas = allo_htcd[allo_htcd["F_HTCD"] == 1]["abs_resid_F"]
    est = allo_htcd[allo_htcd["F_HTCD"] == 3]["abs_resid_F"]
    if len(meas) > 0 and len(est) > 0:
        from scipy import stats as sp_stats
        t_stat, p_val = sp_stats.ttest_ind(meas, est, equal_var=False)
        print(f"\n  Welch t-test (measured vs estimated |resid|):")
        print(f"    t = {t_stat:.3f}, p = {p_val:.4f}")
        print(f"    Measured mean: {meas.mean():.4f}")
        print(f"    Estimated mean: {est.mean():.4f}")
        diff_direction = "SMALLER" if est.mean() < meas.mean() else "LARGER"
        print(f"    Estimated residuals are {diff_direction} than measured")
        results["ttest_t"] = t_stat
        results["ttest_p"] = p_val

    # Overall production vs QA residual comparison
    print(f"\n  Production overall |resid|: {allo['abs_resid_F'].mean():.4f}")
    print(f"  QA overall |resid|:         {allo['abs_resid_Q'].mean():.4f}")

    return results


# ─────────────────────────────────────────────────────────────
# Section D: Digit Heaping
# ─────────────────────────────────────────────────────────────

def section_d_heaping(df: pd.DataFrame) -> dict:
    """Digit heaping comparison between production and QA measurements."""
    print("\n" + "=" * 70)
    print("SECTION D: DIGIT HEAPING")
    print("=" * 70)

    results = {}

    # DIA heaping
    dia = df[df["F_DIA"].notna() & df["Q_DIA"].notna()].copy()
    dia["F_DIA_tenth"] = (dia["F_DIA"] * 10).round().astype(int) % 10
    dia["Q_DIA_tenth"] = (dia["Q_DIA"] * 10).round().astype(int) % 10
    dia["F_DIA_whole"] = (dia["F_DIA_tenth"] == 0).astype(int)
    dia["Q_DIA_whole"] = (dia["Q_DIA_tenth"] == 0).astype(int)

    f_whole = dia["F_DIA_whole"].mean()
    q_whole = dia["Q_DIA_whole"].mean()
    print(f"\n  DIA whole-inch rate:")
    print(f"    Production: {f_whole*100:.2f}%")
    print(f"    QA:         {q_whole*100:.2f}%")
    results["f_dia_whole"] = f_whole
    results["q_dia_whole"] = q_whole

    # HT heaping (divisible by 5 and 10)
    ht = df[df["F_HT"].notna() & df["Q_HT"].notna() &
            (df["F_HT"] > 0) & (df["Q_HT"] > 0)].copy()
    ht["F_HT_div5"] = (ht["F_HT"] % 5 == 0).astype(int)
    ht["Q_HT_div5"] = (ht["Q_HT"] % 5 == 0).astype(int)
    ht["F_HT_div10"] = (ht["F_HT"] % 10 == 0).astype(int)
    ht["Q_HT_div10"] = (ht["Q_HT"] % 10 == 0).astype(int)

    f_div5 = ht["F_HT_div5"].mean()
    q_div5 = ht["Q_HT_div5"].mean()
    f_div10 = ht["F_HT_div10"].mean()
    q_div10 = ht["Q_HT_div10"].mean()
    print(f"\n  HT divisible by 5:")
    print(f"    Production: {f_div5*100:.2f}%")
    print(f"    QA:         {q_div5*100:.2f}%")
    print(f"\n  HT divisible by 10:")
    print(f"    Production: {f_div10*100:.2f}%")
    print(f"    QA:         {q_div10*100:.2f}%")
    results["f_ht_div5"] = f_div5
    results["q_ht_div5"] = q_div5
    results["f_ht_div10"] = f_div10
    results["q_ht_div10"] = q_div10

    # Seasonal DIA heaping for production
    print("\n--- Seasonal DIA Heaping (Production) ---")
    for season, label in [(0, "Early"), (1, "Late")]:
        sub = dia[dia["LATE_SEASON"] == season]
        rate = sub["F_DIA_whole"].mean()
        print(f"  {label}: {rate*100:.2f}% (N={len(sub):,})")

    # Seasonal HT heaping for production
    print("\n--- Seasonal HT Div-5 Rate (Production) ---")
    for season, label in [(0, "Early"), (1, "Late")]:
        sub = ht[ht["LATE_SEASON"] == season]
        rate = sub["F_HT_div5"].mean()
        print(f"  {label}: {rate*100:.2f}% (N={len(sub):,})")

    return results


# ─────────────────────────────────────────────────────────────
# Figures
# ─────────────────────────────────────────────────────────────

def plot_discrepancies(df: pd.DataFrame):
    """Figure: Distribution of paired measurement discrepancies."""
    ht = df[df["F_HT"].notna() & df["Q_HT"].notna() &
            (df["F_HT"] > 0) & (df["Q_HT"] > 0)].copy()
    ht["HT_diff"] = ht["F_HT"] - ht["Q_HT"]

    dia = df[df["F_DIA"].notna() & df["Q_DIA"].notna()].copy()
    dia["DIA_diff"] = dia["F_DIA"] - dia["Q_DIA"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: DIA discrepancies
    ax = axes[0]
    clip = dia["DIA_diff"].clip(-2, 2)
    ax.hist(clip, bins=80, color="black", alpha=0.6, edgecolor="none")
    ax.axvline(0, color="gray", linestyle="--", alpha=0.7)
    ax.set_xlabel("DIA: Production − QA (inches)")
    ax.set_ylabel("Count")
    ax.set_title("(a) Diameter Discrepancies")

    # Panel B: HT discrepancies
    ax = axes[1]
    clip_ht = ht["HT_diff"].clip(-30, 30)
    ax.hist(clip_ht, bins=80, color="black", alpha=0.6, edgecolor="none")
    ax.axvline(0, color="gray", linestyle="--", alpha=0.7)
    ax.set_xlabel("HT: Production − QA (feet)")
    ax.set_ylabel("Count")
    ax.set_title("(b) Height Discrepancies")

    # Add HTCD decomposition if available
    ht_htcd = ht[ht["F_HTCD"].notna()].copy()
    ht_htcd["F_HTCD"] = ht_htcd["F_HTCD"].astype(int)
    meas = ht_htcd[ht_htcd["F_HTCD"] == 1]["HT_diff"]
    est = ht_htcd[ht_htcd["F_HTCD"] == 3]["HT_diff"]
    if len(meas) > 100 and len(est) > 100:
        ax.axvline(meas.mean(), color="blue", linestyle=":", alpha=0.7,
                   label=f"HTCD=1 mean: {meas.mean():.1f}")
        ax.axvline(est.mean(), color="red", linestyle=":", alpha=0.7,
                   label=f"HTCD=3 mean: {est.mean():.1f}")
        ax.legend(fontsize=7)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "paired_qa_discrepancies.pdf", dpi=300,
                bbox_inches="tight")
    fig.savefig(FIG_DIR / "paired_qa_discrepancies.png", dpi=300,
                bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'paired_qa_discrepancies.pdf'}")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
# Save regression table
# ─────────────────────────────────────────────────────────────

def save_regression_table(htcd_results: dict, disc_results: dict,
                          allo_results: dict):
    """Save combined regression results."""
    rows = [
        {"model": "Prob(HTCD=3)", "dep_var": "Prob(F_HTCD==3)",
         "late_coef": htcd_results["late_reg_coef"],
         "late_se": htcd_results["late_reg_se"],
         "late_p": htcd_results["late_reg_p"],
         "n": htcd_results["late_reg_n"],
         "notes": "State and year FE, clustered by state"},
        {"model": "|HT_diff|", "dep_var": "|F_HT - Q_HT|",
         "late_coef": disc_results["ht_late_coef"],
         "late_se": disc_results["ht_late_se"],
         "late_p": disc_results["ht_late_p"],
         "n": disc_results["n_ht"],
         "notes": "State and year FE, clustered by state"},
        {"model": "|DIA_diff| (placebo)", "dep_var": "|F_DIA - Q_DIA|",
         "late_coef": disc_results["dia_late_coef"],
         "late_se": disc_results["dia_late_se"],
         "late_p": disc_results["dia_late_p"],
         "n": disc_results["n_dia"],
         "notes": "State and year FE, clustered by state (placebo)"},
    ]
    # Allometric conformity: HTCD=1 vs HTCD=3 residuals
    if "htcd1_abs_resid" in allo_results:
        rows.append({
            "model": "allometric_conformity",
            "dep_var": "|allometric resid| by HTCD",
            "late_coef": allo_results["htcd1_abs_resid"],
            "late_se": allo_results["htcd3_abs_resid"],
            "late_p": allo_results.get("ttest_p"),
            "n": allo_results.get("htcd1_n", 0)
                + allo_results.get("htcd3_n", 0),
            "notes": "late_coef=HTCD1 |resid|, late_se=HTCD3 |resid|, "
                     "late_p=Welch t-test p-value",
        })
    reg_df = pd.DataFrame(rows)
    reg_df.to_csv(TABLE_DIR / "paired_qa_regression.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'paired_qa_regression.csv'}")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("ANALYSIS 5: Paired QA/Production Measurement Comparison")
    print("        Yanai et al. (2023), doi:10.2737/RDS-2022-0056")
    print("=" * 70)

    # Load data
    df = load_data()

    # Section A: HTCD comparison
    htcd_results = section_a_htcd(df)

    # Section B: Paired discrepancies
    disc_results = section_b_discrepancies(df)

    # Section C: Allometric conformity
    allo_results = section_c_allometric(df)

    # Section D: Digit heaping
    heap_results = section_d_heaping(df)

    # Figures
    print("\n--- Generating Figures ---")
    plot_htcd_by_month(htcd_results)
    plot_discrepancies(df)

    # Combined regression table
    save_regression_table(htcd_results, disc_results, allo_results)

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY OF KEY FINDINGS")
    print("=" * 70)
    print(f"\n  HTCD=3 rate: Production={htcd_results['f_htcd3_rate']*100:.1f}%, "
          f"QA={htcd_results['q_htcd3_rate']*100:.1f}%")
    print(f"  Paired DIA: N={disc_results['n_dia']:,}, "
          f"mean |diff|={disc_results['dia_abs_mean']:.3f} in.")
    print(f"  Paired HT:  N={disc_results['n_ht']:,}, "
          f"mean |diff|={disc_results['ht_abs_mean']:.2f} ft.")
    if "htcd1_abs_resid" in allo_results and "htcd3_abs_resid" in allo_results:
        print(f"\n  Allometric |resid|:")
        print(f"    HTCD=1 (measured):  {allo_results['htcd1_abs_resid']:.4f}")
        print(f"    HTCD=3 (estimated): {allo_results['htcd3_abs_resid']:.4f}")

    print("\n" + "=" * 70)
    print("ANALYSIS 5 COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
