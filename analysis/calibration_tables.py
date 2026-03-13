#!/usr/bin/env python3
"""
Generate calibration tables for the NSC model.

Tables:
  - Table 2: NSC sensitivity to outside option (w̄) and separation rate (b)
  - Table 3: Cross-state NSC variation using BLS wage data

Usage:
    python calibration_tables.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TABLE_DIR = Path(__file__).parent.parent / "tables"
FIG_DIR = Path(__file__).parent.parent / "figures"


def nsc_wage(w_bar, e_bar, q, r, b):
    """Compute the no-shirking condition critical wage w*."""
    return w_bar + e_bar + (e_bar / q) * (r + b)


def table1_parameters():
    """Table 1: Model Parameters and Sources."""
    params = [
        ("w (GS-4 Step 1)", "$17.27/hr", "—", "OPM 2025 GS, RUS locality"),
        ("w (GS-5 Step 1)", "$19.33/hr", "—", "OPM 2025 GS, RUS locality"),
        ("w (GS-6 Step 1)", "$21.54/hr", "—", "OPM 2025 GS, RUS locality"),
        ("w (GS-7 Step 1)", "$23.94/hr", "—", "OPM 2025 GS, RUS locality"),
        ("w̄ (outside option)", "$16.00/hr", "$14–$20", "BLS OES, multiple occupations"),
        ("ē (effort cost)", "$4.32/hr (0.25×GS-4)", "0.15w–0.40w", "O*NET 19-4071.00"),
        ("q (detection prob.)", "0.010/month", "0.005–0.040", "FIA QA program; DataMart"),
        ("b (separation rate)", "0.020/month", "0.010–0.050", "OPM 5 CFR §316.401"),
        ("r (discount rate)", "0.004/month", "0.003–0.008", "Standard (~5% annual)"),
    ]

    df = pd.DataFrame(params, columns=["Parameter", "Central Value", "Range", "Source"])
    df.to_csv(TABLE_DIR / "table1_parameters.csv", index=False)
    print("Table 1: Model Parameters")
    print(df.to_string(index=False))
    print(f"\nSaved: {TABLE_DIR / 'table1_parameters.csv'}")
    return df


def table2_sensitivity():
    """
    Table 2: NSC sensitivity to outside option (w̄) and separation rate (b).
    Shows w* for combinations of w̄ and b at fixed q, ē, r.
    """
    # Fixed parameters
    e_bar = 4.32  # 0.25 × GS-4 $17.27 (2025 RUS)
    q = 0.01
    r = 0.004

    w_bars = [14, 15, 16, 17, 18, 19, 20]
    b_vals = [0.01, 0.02, 0.03, 0.04, 0.05]

    rows = []
    for w_bar in w_bars:
        row = {"w̄ ($/hr)": w_bar}
        for b in b_vals:
            w_star = nsc_wage(w_bar, e_bar, q, r, b)
            row[f"b={b:.2f}"] = round(w_star, 2)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(TABLE_DIR / "table2_nsc_sensitivity.csv", index=False)

    print("\nTable 2: NSC Sensitivity (w* in $/hr)")
    print(f"Fixed: ē=${e_bar}/hr, q={q}, r={r}")
    print(df.to_string(index=False))

    # Note GS wage thresholds (2025 RUS locality pay)
    print(f"\nGS-4 wage: $17.27/hr")
    print(f"GS-5 wage: $19.33/hr")
    print(f"GS-6 wage: $21.54/hr")
    print(f"GS-7 wage: $23.94/hr")
    print("Cells ≤ GS-6 wage indicate NSC compliance at GS-6")

    print(f"\nSaved: {TABLE_DIR / 'table2_nsc_sensitivity.csv'}")
    return df


def table2b_sensitivity_q():
    """
    Supplementary: NSC sensitivity to detection probability (q) and effort cost.
    """
    w_bar = 16.0
    r = 0.004
    b = 0.02

    q_vals = [0.005, 0.010, 0.015, 0.020, 0.030, 0.040]
    e_fracs = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

    # Use GS-4 base for effort cost scaling (2025 RUS)
    w_gs4 = 17.27

    rows = []
    for e_frac in e_fracs:
        e_bar = e_frac * w_gs4
        row = {"ē (fraction of w)": f"{e_frac:.0%}", "ē ($/hr)": round(e_bar, 2)}
        for q in q_vals:
            w_star = nsc_wage(w_bar, e_bar, q, r, b)
            row[f"q={q:.3f}"] = round(w_star, 2)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(TABLE_DIR / "table2b_nsc_q_sensitivity.csv", index=False)

    print("\nTable 2b: NSC Sensitivity to q and ē (w* in $/hr)")
    print(f"Fixed: w̄=${w_bar}/hr, b={b}, r={r}")
    print(df.to_string(index=False))
    print(f"\nSaved: {TABLE_DIR / 'table2b_nsc_q_sensitivity.csv'}")
    return df


def table3_cross_state():
    """
    Table 3: Cross-state NSC variation using BLS wage data.
    Uses state-specific outside options and computes state-specific w*.
    """
    # BLS OES 2023 approximate median wages for relevant occupations by state
    # Note: These are approximate values from BLS OES summary tables.
    # Exact state-occupation-level OES data should be verified against
    # https://www.bls.gov/oes/current/oes_nat.htm for final publication.
    state_data = {
        "VT": {"landscaping": 16.50, "logging": 19.00, "retail": 14.50, "wildfire": 18.00},
        "ME": {"landscaping": 16.00, "logging": 18.50, "retail": 14.00, "wildfire": 17.50},
        "MN": {"landscaping": 17.50, "logging": 20.00, "retail": 15.00, "wildfire": 18.50},
        "WI": {"landscaping": 16.00, "logging": 18.00, "retail": 14.50, "wildfire": 17.50},
        "GA": {"landscaping": 15.00, "logging": 17.00, "retail": 13.50, "wildfire": 16.50},
        "CO": {"landscaping": 18.00, "logging": 20.50, "retail": 16.00, "wildfire": 20.00},
        "OR": {"landscaping": 17.50, "logging": 21.00, "retail": 15.50, "wildfire": 19.50},
        "WA": {"landscaping": 19.00, "logging": 22.00, "retail": 16.50, "wildfire": 21.00},
    }

    # Central parameters (2025 RUS locality pay)
    e_frac = 0.25
    w_gs4 = 17.27
    w_gs5 = 19.33
    w_gs6 = 21.54
    e_bar = e_frac * w_gs4  # $4.32
    q = 0.01
    r = 0.004
    b = 0.02

    rows = []
    for state in sorted(state_data.keys()):
        wages = state_data[state]
        # Outside option: report both max and weighted average
        w_bar_max = max(wages.values())
        w_bar_max_label = [k for k, v in wages.items() if v == w_bar_max][0]
        # Weighted average across accessible occupations (equal weights)
        w_bar_avg = np.mean(list(wages.values()))

        w_star_max = nsc_wage(w_bar_max, e_bar, q, r, b)
        w_star_avg = nsc_wage(w_bar_avg, e_bar, q, r, b)
        gs4_gap = ((w_star_max - w_gs4) / w_gs4) * 100
        gs6_gap = ((w_star_max - w_gs6) / w_gs6) * 100

        gs4_gap_avg = ((w_star_avg - w_gs4) / w_gs4) * 100
        gs6_gap_avg = ((w_star_avg - w_gs6) / w_gs6) * 100

        rows.append({
            "State": state,
            "Best outside option": f"{w_bar_max_label} (${w_bar_max:.2f})",
            "w̄ avg ($/hr)": round(w_bar_avg, 2),
            "w̄ max ($/hr)": w_bar_max,
            "w* at avg ($/hr)": round(w_star_avg, 2),
            "w* at max ($/hr)": round(w_star_max, 2),
            "Gap vs GS-4 avg (%)": round(gs4_gap_avg, 1),
            "Gap vs GS-6 avg (%)": round(gs6_gap_avg, 1),
            "Gap vs GS-4 max (%)": round(gs4_gap, 1),
            "Gap vs GS-6 max (%)": round(gs6_gap, 1),
        })

    df = pd.DataFrame(rows)
    df.to_csv(TABLE_DIR / "table3_cross_state_nsc.csv", index=False)

    print("\nTable 3: Cross-State NSC Variation")
    print(f"Fixed: ē=0.25×GS-4=${e_bar:.2f}/hr, q={q}, b={b}, r={r}")
    print(f"GS-4=${w_gs4}/hr, GS-5=${w_gs5}/hr, GS-6=${w_gs6}/hr")
    print("Note: BLS wages are approximate; see code comments.")
    print(df.to_string(index=False))

    print(f"\nSaved: {TABLE_DIR / 'table3_cross_state_nsc.csv'}")
    return df


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("CALIBRATION TABLES")
    print("=" * 60)

    table1_parameters()
    print()
    table2_sensitivity()
    print()
    table2b_sensitivity_q()
    print()
    table3_cross_state()

    print("\n" + "=" * 60)
    print("ALL CALIBRATION TABLES GENERATED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
