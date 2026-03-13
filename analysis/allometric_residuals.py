#!/usr/bin/env python3
"""
Analysis 2: Allometric Residual Patterns by Measurement Month

Fits regional height-diameter allometric models and tests whether residual
variance changes systematically across measurement months.

Key insight: If technicians approximate/estimate heights rather than measuring
them carefully, estimated heights will track the allometric curve closely
(lower residual variance, higher R²). This is because estimation relies on
the technician's mental model of height~diameter relationships. Carefully
measured heights reflect real biological variation (higher residual variance).

Ocular estimation prediction: residual variance DECREASES late season
Honest error prediction: residual variance INCREASES late season (fatigue)
→ Opposite predictions make this the sharpest discriminating test.

Outputs:
  - tables/allometric_model_fits.csv
  - tables/allometric_residual_variance.csv
  - tables/allometric_regression.csv
  - figures/allometric_residuals.pdf
  - figures/allometric_r2_by_month.pdf

Usage:
    python allometric_residuals.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

DATA_DIR = Path(__file__).parent.parent / "data"
TABLE_DIR = Path(__file__).parent.parent / "tables"
FIG_DIR = Path(__file__).parent.parent / "figures"

# FIA region mapping (approximate — based on FIA unit structure)
STATE_REGION = {
    "VT": "Northeast", "ME": "Northeast",
    "MN": "Northern", "WI": "Northern",
    "GA": "South",
    "CO": "Rocky Mountain",
    "OR": "Pacific Northwest", "WA": "Pacific Northwest",
}


def load_data() -> pd.DataFrame:
    """Load merged tree-level dataset with valid height and diameter."""
    path = DATA_DIR / "fia_trees.parquet"
    if not path.exists():
        print(f"Error: {path} not found. Run extract_data.py first.")
        sys.exit(1)

    df = pd.read_parquet(path)

    # Filter to trees with valid lnDIA and lnHT
    df = df[df["lnDIA"].notna() & df["lnHT"].notna() & np.isfinite(df["lnHT"])].copy()

    # Add region
    df["REGION"] = df["STATE"].map(STATE_REGION)

    print(f"Loaded {len(df):,} trees with valid DIA and HT")
    print(f"States: {sorted(df['STATE'].dropna().unique())}")
    print(f"Regions: {sorted(df['REGION'].dropna().unique())}")

    return df


def fit_allometric_model(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fit ln(HT) ~ ln(DIA) + species group FE, pooled across all states.
    Returns the dataframe with residuals added, and model summary dict.
    """
    print("\n--- Fitting Allometric Model: ln(HT) ~ ln(DIA) + C(SPGRPCD) ---")

    reg_df = df[df["SPGRPCD"].notna()].copy()
    reg_df["SPGRPCD"] = reg_df["SPGRPCD"].astype(int)

    model = smf.ols("lnHT ~ lnDIA + C(SPGRPCD)", data=reg_df).fit()

    print(f"  N = {model.nobs:,.0f}")
    print(f"  R² = {model.rsquared:.4f}")
    print(f"  ln(DIA) coef = {model.params['lnDIA']:.4f} (SE: {model.bse['lnDIA']:.4f})")
    print(f"  Residual Std Dev = {np.sqrt(model.mse_resid):.4f}")

    # Add residuals to dataframe
    reg_df["resid"] = model.resid
    reg_df["resid_sq"] = model.resid ** 2
    reg_df["abs_resid"] = np.abs(model.resid)

    summary = {
        "n": model.nobs,
        "r2": model.rsquared,
        "beta_lnDIA": model.params["lnDIA"],
        "se_lnDIA": model.bse["lnDIA"],
        "rmse": np.sqrt(model.mse_resid),
    }

    return reg_df, summary


def fit_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fit separate allometric models by region, add residuals.
    This allows region-specific species composition to be captured.
    """
    print("\n--- Fitting Region-Specific Allometric Models ---")

    all_results = []
    model_fits = []

    for region in sorted(df["REGION"].dropna().unique()):
        rdf = df[df["REGION"] == region].copy()
        rdf = rdf[rdf["SPGRPCD"].notna()].copy()
        rdf["SPGRPCD"] = rdf["SPGRPCD"].astype(int)

        if len(rdf) < 100:
            continue

        model = smf.ols("lnHT ~ lnDIA + C(SPGRPCD)", data=rdf).fit()
        rdf["resid"] = model.resid
        rdf["resid_sq"] = model.resid ** 2
        rdf["abs_resid"] = np.abs(model.resid)

        print(f"  {region}: N={model.nobs:,.0f}, R²={model.rsquared:.4f}, "
              f"β(lnDIA)={model.params['lnDIA']:.3f}")

        model_fits.append({
            "region": region,
            "n": model.nobs,
            "r2": model.rsquared,
            "beta_lnDIA": model.params["lnDIA"],
            "rmse": np.sqrt(model.mse_resid),
        })

        all_results.append(rdf)

    fits_df = pd.DataFrame(model_fits)
    fits_df.to_csv(TABLE_DIR / "allometric_model_fits.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'allometric_model_fits.csv'}")

    return pd.concat(all_results, ignore_index=True)


def residual_variance_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute allometric residual variance (σ²) by measurement month.
    Key test: does variance DECREASE late season?
    """
    print("\n--- Residual Variance by Month ---")

    monthly = df.groupby("MEASMON").agg(
        n=("resid", "size"),
        mean_resid=("resid", "mean"),
        var_resid=("resid_sq", "mean"),  # E[resid²] = var when E[resid]=0
        sd_resid=("resid", "std"),
        mean_abs_resid=("abs_resid", "mean"),
        median_abs_resid=("abs_resid", "median"),
    ).reset_index()

    print(monthly.to_string(index=False, float_format="%.5f"))
    monthly.to_csv(TABLE_DIR / "allometric_residual_variance.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'allometric_residual_variance.csv'}")

    return monthly


def residual_variance_by_state_month(df: pd.DataFrame) -> pd.DataFrame:
    """Compute residual variance at state × month level for regression."""
    state_month = df.groupby(["STATE", "MEASYEAR", "MEASMON"]).agg(
        n=("resid", "size"),
        var_resid=("resid_sq", "mean"),
        sd_resid=("resid", "std"),
        mean_abs_resid=("abs_resid", "mean"),
    ).reset_index()

    return state_month


def r_squared_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute month-specific R² by fitting allometric model separately per month.
    Tests whether R² INCREASES late season (ocular estimation prediction).
    """
    print("\n--- Month-Specific Allometric R² ---")

    results = []
    for month in sorted(df["MEASMON"].unique()):
        mdf = df[df["MEASMON"] == month]
        if len(mdf) < 100:
            continue

        mdf = mdf[mdf["SPGRPCD"].notna()].copy()
        mdf["SPGRPCD"] = mdf["SPGRPCD"].astype(int)
        model = smf.ols("lnHT ~ lnDIA + C(SPGRPCD)", data=mdf).fit()

        results.append({
            "month": int(month),
            "n": model.nobs,
            "r2": model.rsquared,
            "beta_lnDIA": model.params["lnDIA"],
            "rmse": np.sqrt(model.mse_resid),
        })

    r2_df = pd.DataFrame(results)
    print(r2_df.to_string(index=False))
    return r2_df


def run_variance_regressions(df: pd.DataFrame) -> dict:
    """
    Regression tests for whether residual variance/dispersion changes
    with measurement month.

    Tree-level regression:
        |resid| ~ LATE_SEASON + C(STATE) + C(MEASYEAR)
        resid² ~ LATE_SEASON + C(STATE) + C(MEASYEAR)
    """
    results = {}
    df = df.copy()
    df["MEASMON"] = df["MEASMON"].astype(int)
    df["MEASYEAR"] = df["MEASYEAR"].astype(int)

    # Cluster variable
    cluster = df["STATE"].astype(str) + "_" + df["MEASYEAR"].astype(str)

    # --- Model 1: |resid| ~ LATE_SEASON ---
    print("\n--- Model 1: |Allometric Residual| ~ Late Season ---")
    m1 = smf.ols(
        "abs_resid ~ LATE_SEASON + C(STATE) + C(MEASYEAR)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    print(f"  LATE_SEASON coef: {m1.params['LATE_SEASON']:.6f} "
          f"(SE: {m1.bse['LATE_SEASON']:.6f}, p={m1.pvalues['LATE_SEASON']:.4f})")
    results["abs_resid_late"] = {
        "coef": m1.params["LATE_SEASON"],
        "se": m1.bse["LATE_SEASON"],
        "pvalue": m1.pvalues["LATE_SEASON"],
        "n": m1.nobs,
    }

    # --- Model 2: resid² ~ LATE_SEASON ---
    print("\n--- Model 2: Squared Residual ~ Late Season ---")
    m2 = smf.ols(
        "resid_sq ~ LATE_SEASON + C(STATE) + C(MEASYEAR)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    print(f"  LATE_SEASON coef: {m2.params['LATE_SEASON']:.6f} "
          f"(SE: {m2.bse['LATE_SEASON']:.6f}, p={m2.pvalues['LATE_SEASON']:.4f})")
    results["resid_sq_late"] = {
        "coef": m2.params["LATE_SEASON"],
        "se": m2.bse["LATE_SEASON"],
        "pvalue": m2.pvalues["LATE_SEASON"],
        "n": m2.nobs,
    }

    # --- Model 3: |resid| ~ month dummies ---
    print("\n--- Model 3: |Allometric Residual| ~ Month Dummies (ref=June) ---")
    m3 = smf.ols(
        "abs_resid ~ C(MEASMON, Treatment(reference=6)) + C(STATE) + C(MEASYEAR)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    month_coefs = {k: v for k, v in m3.params.items() if "MEASMON" in k}
    month_pvals = {k: v for k, v in m3.pvalues.items() if "MEASMON" in k}
    print("  Month coefficients (ref=June):")
    for k in sorted(month_coefs.keys()):
        print(f"    {k}: {month_coefs[k]:.6f} (p={month_pvals[k]:.4f})")
    results["abs_resid_months"] = {
        "month_coefs": month_coefs,
        "month_pvals": month_pvals,
        "n": m3.nobs,
    }

    # --- Model 4: With species group FE ---
    print("\n--- Model 4: |Residual| ~ Late Season + Species Group FE ---")
    sp_df = df[df["SPGRPCD"].notna()].copy()
    sp_df["SPGRPCD"] = sp_df["SPGRPCD"].astype(int)
    cluster_sp = sp_df["STATE"].astype(str) + "_" + sp_df["MEASYEAR"].astype(str)
    m4 = smf.ols(
        "abs_resid ~ LATE_SEASON + C(STATE) + C(MEASYEAR) + C(SPGRPCD)",
        data=sp_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": cluster_sp})
    print(f"  LATE_SEASON coef: {m4.params['LATE_SEASON']:.6f} "
          f"(SE: {m4.bse['LATE_SEASON']:.6f}, p={m4.pvalues['LATE_SEASON']:.4f})")
    results["abs_resid_late_species"] = {
        "coef": m4.params["LATE_SEASON"],
        "se": m4.bse["LATE_SEASON"],
        "pvalue": m4.pvalues["LATE_SEASON"],
        "n": m4.nobs,
    }

    return results


def plot_residual_variance(monthly: pd.DataFrame, r2_df: pd.DataFrame):
    """Generate publication-quality figures for allometric residual analysis."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: Residual std dev by month
    ax = axes[0]
    ax.plot(monthly["MEASMON"], monthly["sd_resid"], "ko-", markersize=5)
    overall_sd = monthly["sd_resid"].mean()
    ax.axhline(y=overall_sd, color="gray", linestyle="--", alpha=0.7,
               label=f"Overall mean ({overall_sd:.4f})")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Residual Std. Dev. (ln scale)")
    ax.set_title("(a) Allometric Residual Dispersion")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel B: R² by month
    ax = axes[1]
    ax.plot(r2_df["month"], r2_df["r2"], "ko-", markersize=5)
    overall_r2 = r2_df["r2"].mean()
    ax.axhline(y=overall_r2, color="gray", linestyle="--", alpha=0.7,
               label=f"Overall mean ({overall_r2:.4f})")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("R²")
    ax.set_title("(b) Allometric Model Fit by Month")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "allometric_residuals.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / "allometric_residuals.png", dpi=300, bbox_inches="tight")
    print(f"\nSaved: {FIG_DIR / 'allometric_residuals.pdf'}")
    plt.close(fig)


def levene_test_by_season(df: pd.DataFrame):
    """
    Levene's test for equality of variance between early and late season.
    More robust than F-test for non-normal residuals.
    """
    print("\n--- Levene's Test: Early vs Late Season Residual Variance ---")
    print("  (Using LATE_SEASON={9,10,11,12} to match regression definition)")

    early = df[df["MEASMON"].isin([5, 6, 7, 8])]["resid"].values
    late = df[df["MEASMON"].isin([9, 10, 11, 12])]["resid"].values

    stat, p = stats.levene(early, late, center="median")
    print(f"  Early season (May-Aug): n={len(early):,}, SD={early.std():.5f}")
    print(f"  Late season (Sep-Dec):  n={len(late):,}, SD={late.std():.5f}")
    print(f"  Levene statistic: {stat:.3f}, p={p:.4e}")

    # Also report the Oct-Dec definition for comparison
    late_narrow = df[df["MEASMON"].isin([10, 11, 12])]["resid"].values
    stat_n, p_n = stats.levene(early, late_narrow, center="median")
    print(f"\n  (Sensitivity: with late={'{10,11,12}'} only:)")
    print(f"    Late season (Oct-Dec): n={len(late_narrow):,}, SD={late_narrow.std():.5f}")
    print(f"    Levene statistic: {stat_n:.3f}, p={p_n:.4e}")

    direction = "LOWER" if late.std() < early.std() else "HIGHER"
    print(f"\n  Late-season (Sep-Dec) variance is {direction} than early season")
    print(f"  (Ocular estimation predicts LOWER; honest error predicts HIGHER)")
    print(f"  Note: Result is sensitive to month-9 cutoff (see sensitivity above).")

    return {
        "stat": stat, "p": p,
        "early_sd": early.std(), "late_sd": late.std(),
        "stat_narrow": stat_n, "p_narrow": p_n,
        "late_narrow_sd": late_narrow.std(),
    }


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ANALYSIS 2: Allometric Residual Patterns")
    print("=" * 60)

    df = load_data()

    # --- Fit allometric models by region ---
    df_with_resid = fit_by_region(df)

    # --- Also fit pooled model for reference ---
    pooled_df, pooled_summary = fit_allometric_model(df)

    # Use region-specific residuals for main analysis
    analysis_df = df_with_resid

    # --- Residual variance by month ---
    monthly = residual_variance_by_month(analysis_df)

    # --- R² by month ---
    r2_df = r_squared_by_month(df)
    r2_df.to_csv(TABLE_DIR / "allometric_r2_by_month.csv", index=False)
    print(f"Saved: {TABLE_DIR / 'allometric_r2_by_month.csv'}")

    # --- Levene's test ---
    levene_results = levene_test_by_season(analysis_df)

    # --- Regression tests ---
    reg_results = run_variance_regressions(analysis_df)

    # Save regression results
    reg_rows = []
    for model_name, res in reg_results.items():
        if "coef" in res:
            reg_rows.append({
                "model": model_name,
                "late_season_coef": round(res["coef"], 6),
                "late_season_se": round(res["se"], 6),
                "late_season_pvalue": round(res["pvalue"], 6),
                "n_obs": int(res["n"]),
            })
    reg_table = pd.DataFrame(reg_rows)
    reg_table.to_csv(TABLE_DIR / "allometric_regression.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'allometric_regression.csv'}")

    # --- Figures ---
    print("\n--- Generating Figures ---")
    plot_residual_variance(monthly, r2_df)

    print("\n" + "=" * 60)
    print("ANALYSIS 2 COMPLETE")
    print("=" * 60)

    # --- Summary of findings ---
    print("\n--- SUMMARY ---")
    late_var = monthly[monthly["MEASMON"].isin([10, 11, 12])]["sd_resid"].mean()
    early_var = monthly[monthly["MEASMON"].isin([5, 6, 7])]["sd_resid"].mean()
    print(f"Avg residual SD, early season (May-Jul): {early_var:.5f}")
    print(f"Avg residual SD, late season (Oct-Dec):  {late_var:.5f}")
    print(f"Direction: {'DECREASING (consistent with ocular estimation)' if late_var < early_var else 'INCREASING (consistent with honest error)'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
