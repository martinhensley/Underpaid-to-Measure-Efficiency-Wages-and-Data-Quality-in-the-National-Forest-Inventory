#!/usr/bin/env python3
"""
Analysis 1: Digit Heaping / Rounding Patterns by Measurement Month

Tests whether digit heaping in DBH and height measurements increases in
late-season months, consistent with approximation rather than careful
measurement.

Key insight: Approximated measurements cluster on round numbers (whole inches
for DBH, multiples of 5 or 10 for height). Carefully tape-measured diameters
distribute uniformly across tenths. Rounding is a signature of estimation,
not random measurement error.

Outputs:
  - tables/digit_heaping_by_month.csv
  - tables/digit_heaping_regression.csv
  - figures/digit_heaping_dbh.pdf
  - figures/digit_heaping_height.pdf
  - figures/last_digit_distribution.pdf

Usage:
    python digit_heaping.py
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


def load_data() -> pd.DataFrame:
    """Load the merged tree-level analysis dataset."""
    path = DATA_DIR / "fia_trees.parquet"
    if not path.exists():
        print(f"Error: {path} not found. Run extract_data.py first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    print(f"Loaded {len(df):,} tree observations from {path.name}")
    return df


def descriptive_heaping(df: pd.DataFrame) -> pd.DataFrame:
    """Compute heaping rates by measurement month across all states."""
    monthly = df.groupby("MEASMON").agg(
        n_trees=("DIA", "size"),
        pct_whole_dia=("DIA_whole", "mean"),
        pct_half_dia=("DIA_half", "mean"),
    ).reset_index()

    # Height heaping (only where HT available)
    ht_df = df[df["HT"].notna() & (df["HT"] > 0)].copy()
    ht_monthly = ht_df.groupby("MEASMON").agg(
        n_trees_ht=("HT", "size"),
        pct_ht_div5=("HT_div5", "mean"),
        pct_ht_div10=("HT_div10", "mean"),
    ).reset_index()

    monthly = monthly.merge(ht_monthly, on="MEASMON", how="left")

    # Convert to percentages
    for col in ["pct_whole_dia", "pct_half_dia", "pct_ht_div5", "pct_ht_div10"]:
        monthly[col] = (monthly[col] * 100).round(2)

    return monthly


def descriptive_by_state_month(df: pd.DataFrame) -> pd.DataFrame:
    """Compute heaping rates by state x month for regression input."""
    ht_valid = df["HT"].notna() & (df["HT"] > 0)

    state_month = df.groupby(["STATE", "MEASYEAR", "MEASMON"]).agg(
        n_trees=("DIA", "size"),
        pct_whole_dia=("DIA_whole", "mean"),
        pct_half_dia=("DIA_half", "mean"),
    ).reset_index()

    ht_agg = df[ht_valid].groupby(["STATE", "MEASYEAR", "MEASMON"]).agg(
        pct_ht_div5=("HT_div5", "mean"),
        pct_ht_div10=("HT_div10", "mean"),
    ).reset_index()

    state_month = state_month.merge(
        ht_agg, on=["STATE", "MEASYEAR", "MEASMON"], how="left"
    )

    # Convert to percentages
    for col in ["pct_whole_dia", "pct_half_dia", "pct_ht_div5", "pct_ht_div10"]:
        state_month[col] = (state_month[col] * 100).round(4)

    return state_month


def run_heaping_regressions(df: pd.DataFrame) -> dict:
    """
    Regression: heaping_rate ~ MEASMON + state FE + year FE + species group FE

    Tests whether digit heaping increases in late-season months after
    controlling for state, year, and species composition.

    Runs at tree level for maximum power.
    """
    # Prepare data
    reg_df = df[["DIA_whole", "DIA_half", "MEASMON", "STATE", "MEASYEAR",
                 "SPGRPCD", "LATE_SEASON", "HT_div5", "HT_div10", "HT"]].copy()

    # Create month dummies (reference: month 6, mid-season)
    reg_df["MEASMON"] = reg_df["MEASMON"].astype(int)
    reg_df["MEASYEAR"] = reg_df["MEASYEAR"].astype(int)

    results = {}

    # --- Model 1: Whole-inch DBH heaping ~ late-season dummy ---
    print("\n--- Model 1: Whole-inch DBH ~ Late Season (binary) ---")
    m1 = smf.ols(
        "DIA_whole ~ LATE_SEASON + C(STATE) + C(MEASYEAR)",
        data=reg_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": reg_df["STATE"].astype(str) + "_" + reg_df["MEASYEAR"].astype(str)})
    print(f"  LATE_SEASON coef: {m1.params['LATE_SEASON']:.5f} "
          f"(SE: {m1.bse['LATE_SEASON']:.5f}, p={m1.pvalues['LATE_SEASON']:.4f})")
    results["m1_late_season"] = {
        "dep_var": "DIA_whole_inch",
        "coef": m1.params["LATE_SEASON"],
        "se": m1.bse["LATE_SEASON"],
        "pvalue": m1.pvalues["LATE_SEASON"],
        "n": m1.nobs,
        "r2": m1.rsquared,
    }

    # --- Model 2: Whole-inch DBH heaping ~ month dummies ---
    print("\n--- Model 2: Whole-inch DBH ~ Month Dummies ---")
    m2 = smf.ols(
        "DIA_whole ~ C(MEASMON, Treatment(reference=6)) + C(STATE) + C(MEASYEAR)",
        data=reg_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": reg_df["STATE"].astype(str) + "_" + reg_df["MEASYEAR"].astype(str)})
    month_coefs = {k: v for k, v in m2.params.items() if "MEASMON" in k}
    month_pvals = {k: v for k, v in m2.pvalues.items() if "MEASMON" in k}
    print("  Month coefficients (ref=June):")
    for k in sorted(month_coefs.keys()):
        print(f"    {k}: {month_coefs[k]:.5f} (p={month_pvals[k]:.4f})")
    results["m2_month_dummies"] = {
        "dep_var": "DIA_whole_inch",
        "month_coefs": month_coefs,
        "month_pvals": month_pvals,
        "n": m2.nobs,
        "r2": m2.rsquared,
    }

    # --- Model 3: With species group FE ---
    print("\n--- Model 3: Whole-inch DBH ~ Late Season + Species Group FE ---")
    reg_df_sp = reg_df[reg_df["SPGRPCD"].notna()].copy()
    reg_df_sp["SPGRPCD"] = reg_df_sp["SPGRPCD"].astype(int)
    m3 = smf.ols(
        "DIA_whole ~ LATE_SEASON + C(STATE) + C(MEASYEAR) + C(SPGRPCD)",
        data=reg_df_sp,
    ).fit(cov_type="cluster", cov_kwds={"groups": reg_df_sp["STATE"].astype(str) + "_" + reg_df_sp["MEASYEAR"].astype(str)})
    print(f"  LATE_SEASON coef: {m3.params['LATE_SEASON']:.5f} "
          f"(SE: {m3.bse['LATE_SEASON']:.5f}, p={m3.pvalues['LATE_SEASON']:.4f})")
    results["m3_with_species"] = {
        "dep_var": "DIA_whole_inch",
        "coef": m3.params["LATE_SEASON"],
        "se": m3.bse["LATE_SEASON"],
        "pvalue": m3.pvalues["LATE_SEASON"],
        "n": m3.nobs,
        "r2": m3.rsquared,
    }

    # --- Model 4: Height heaping (div by 5) ---
    print("\n--- Model 4: Height div-5 ~ Late Season ---")
    ht_reg = reg_df[reg_df["HT"].notna() & (reg_df["HT"] > 0)].copy()
    m4 = smf.ols(
        "HT_div5 ~ LATE_SEASON + C(STATE) + C(MEASYEAR)",
        data=ht_reg,
    ).fit(cov_type="cluster", cov_kwds={"groups": ht_reg["STATE"].astype(str) + "_" + ht_reg["MEASYEAR"].astype(str)})
    print(f"  LATE_SEASON coef: {m4.params['LATE_SEASON']:.5f} "
          f"(SE: {m4.bse['LATE_SEASON']:.5f}, p={m4.pvalues['LATE_SEASON']:.4f})")
    results["m4_ht_div5"] = {
        "dep_var": "HT_div5",
        "coef": m4.params["LATE_SEASON"],
        "se": m4.bse["LATE_SEASON"],
        "pvalue": m4.pvalues["LATE_SEASON"],
        "n": m4.nobs,
        "r2": m4.rsquared,
    }

    # --- Model 5: Half-inch DBH heaping ---
    print("\n--- Model 5: Half-inch DBH ~ Late Season ---")
    m5 = smf.ols(
        "DIA_half ~ LATE_SEASON + C(STATE) + C(MEASYEAR)",
        data=reg_df,
    ).fit(cov_type="cluster", cov_kwds={"groups": reg_df["STATE"].astype(str) + "_" + reg_df["MEASYEAR"].astype(str)})
    print(f"  LATE_SEASON coef: {m5.params['LATE_SEASON']:.5f} "
          f"(SE: {m5.bse['LATE_SEASON']:.5f}, p={m5.pvalues['LATE_SEASON']:.4f})")
    results["m5_half_inch"] = {
        "dep_var": "DIA_half_inch",
        "coef": m5.params["LATE_SEASON"],
        "se": m5.bse["LATE_SEASON"],
        "pvalue": m5.pvalues["LATE_SEASON"],
        "n": m5.nobs,
        "r2": m5.rsquared,
    }

    return results


def last_digit_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Compute last-digit frequency distribution for DBH by season."""
    df = df.copy()
    df["last_digit"] = (df["DIA"] * 10).round().astype(int) % 10

    early = df[df["MEASMON"].isin([5, 6, 7])]
    late = df[df["MEASMON"].isin([10, 11, 12])]

    early_dist = early["last_digit"].value_counts(normalize=True).sort_index() * 100
    late_dist = late["last_digit"].value_counts(normalize=True).sort_index() * 100

    dist_df = pd.DataFrame({
        "digit": range(10),
        "early_season_pct": [early_dist.get(d, 0) for d in range(10)],
        "late_season_pct": [late_dist.get(d, 0) for d in range(10)],
    })
    dist_df["expected_uniform"] = 10.0
    dist_df["early_excess"] = dist_df["early_season_pct"] - 10.0
    dist_df["late_excess"] = dist_df["late_season_pct"] - 10.0

    return dist_df


def plot_heaping_by_month(monthly: pd.DataFrame):
    """Generate publication-quality figures for digit heaping by month."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: DBH heaping
    ax = axes[0]
    ax.plot(monthly["MEASMON"], monthly["pct_whole_dia"], "ko-", markersize=5,
            label="Whole inch (x.0)")
    ax.axhline(y=10, color="gray", linestyle="--", alpha=0.7, label="Expected (uniform)")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Proportion at Whole Inch (%)")
    ax.set_title("(a) DBH Digit Heaping")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    # Panel B: Height heaping
    ax = axes[1]
    ax.plot(monthly["MEASMON"], monthly["pct_ht_div5"], "ko-", markersize=5,
            label="Divisible by 5 ft")
    ax.plot(monthly["MEASMON"], monthly["pct_ht_div10"], "k^--", markersize=5,
            label="Divisible by 10 ft")
    ax.axhline(y=20, color="gray", linestyle="--", alpha=0.7, label="Expected (div 5)")
    ax.axhline(y=10, color="gray", linestyle=":", alpha=0.7, label="Expected (div 10)")
    ax.set_xlabel("Measurement Month")
    ax.set_ylabel("Proportion at Round Number (%)")
    ax.set_title("(b) Height Digit Heaping")
    ax.set_xticks(range(1, 13))
    ax.set_xlim(0.5, 12.5)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "digit_heaping.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / "digit_heaping.png", dpi=300, bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'digit_heaping.pdf'}")
    plt.close(fig)


def plot_last_digit_distribution(dist_df: pd.DataFrame):
    """Plot last-digit frequency distribution comparing early vs late season."""
    fig, ax = plt.subplots(figsize=(6, 4))

    x = np.arange(10)
    width = 0.35
    ax.bar(x - width / 2, dist_df["early_season_pct"], width, color="0.7",
           edgecolor="black", linewidth=0.5, label="Early season (May–Jul)")
    ax.bar(x + width / 2, dist_df["late_season_pct"], width, color="0.3",
           edgecolor="black", linewidth=0.5, label="Late season (Oct–Dec)")
    ax.axhline(y=10, color="black", linestyle="--", alpha=0.5, label="Uniform (10%)")
    ax.set_xlabel("Last Digit of DBH (tenths of inch)")
    ax.set_ylabel("Frequency (%)")
    ax.set_title("Distribution of DBH Last Digit by Season")
    ax.set_xticks(x)
    ax.set_xticklabels([f".{d}" for d in range(10)])
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "last_digit_distribution.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / "last_digit_distribution.png", dpi=300, bbox_inches="tight")
    print(f"Saved: {FIG_DIR / 'last_digit_distribution.pdf'}")
    plt.close(fig)


def chi_squared_uniformity_test(df: pd.DataFrame) -> dict:
    """
    Chi-squared test for uniformity of last digit by season.
    Under no heaping, each digit should appear with equal frequency.
    """
    results = {}
    for label, months in [("early", [5, 6, 7]), ("late", [10, 11, 12]), ("all", list(range(1, 13)))]:
        subset = df[df["MEASMON"].isin(months)]
        last_digits = (subset["DIA"] * 10).round().astype(int) % 10
        observed = last_digits.value_counts().sort_index()
        expected = np.full(10, len(last_digits) / 10)
        chi2, p = stats.chisquare(observed.values, expected)
        results[label] = {"chi2": chi2, "p": p, "n": len(last_digits)}
        print(f"  {label}: chi2={chi2:.1f}, p={p:.2e}, n={len(last_digits):,}")

    return results


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ANALYSIS 1: Digit Heaping / Rounding Patterns")
    print("=" * 60)

    df = load_data()

    # --- Descriptive statistics ---
    print("\n--- Descriptive: Heaping Rates by Month ---")
    monthly = descriptive_heaping(df)
    print(monthly.to_string(index=False))
    monthly.to_csv(TABLE_DIR / "digit_heaping_by_month.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'digit_heaping_by_month.csv'}")

    # --- Last digit distribution ---
    print("\n--- Last Digit Distribution (Early vs Late Season) ---")
    dist_df = last_digit_distribution(df)
    print(dist_df.to_string(index=False))
    dist_df.to_csv(TABLE_DIR / "last_digit_distribution.csv", index=False)

    # --- Chi-squared uniformity tests ---
    print("\n--- Chi-Squared Test for Uniform Last Digit ---")
    chi2_results = chi_squared_uniformity_test(df)

    # --- Regression analysis ---
    print("\n--- Regression Analysis ---")
    reg_results = run_heaping_regressions(df)

    # Save regression results
    reg_rows = []
    for model_name, res in reg_results.items():
        if "coef" in res:
            reg_rows.append({
                "model": model_name,
                "dep_var": res["dep_var"],
                "late_season_coef": round(res["coef"], 6),
                "late_season_se": round(res["se"], 6),
                "late_season_pvalue": round(res["pvalue"], 6),
                "n_obs": int(res["n"]),
                "r_squared": round(res["r2"], 5),
            })
    reg_table = pd.DataFrame(reg_rows)
    reg_table.to_csv(TABLE_DIR / "digit_heaping_regression.csv", index=False)
    print(f"\nSaved: {TABLE_DIR / 'digit_heaping_regression.csv'}")

    # --- State-month breakdown ---
    print("\n--- State × Month Heaping Rates ---")
    sm_df = descriptive_by_state_month(df)
    sm_df.to_csv(TABLE_DIR / "digit_heaping_state_month.csv", index=False)
    print(f"Saved: {TABLE_DIR / 'digit_heaping_state_month.csv'}")

    # --- Figures ---
    print("\n--- Generating Figures ---")
    plot_heaping_by_month(monthly)
    plot_last_digit_distribution(dist_df)

    print("\n" + "=" * 60)
    print("ANALYSIS 1 COMPLETE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
