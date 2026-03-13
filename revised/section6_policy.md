# 5. Policy Recommendations

The calibrated model provides a framework for evaluating specific policy interventions. Rather than generic recommendations to "improve data quality," we derive quantitative targets from the NSC. These recommendations flow from the institutional analysis, model calibration, and the empirical finding that production crews estimate at approximately four times the QA crew rate. We frame these as implications of the benchmark model, acknowledging that the calibrated NSC values are indicative rather than precise thresholds.

## Wage Adjustments

At central parameters ($\bar{w} = \$16$/hr, $\bar{e} = \$4.32$/hr, $q = 0.01$, $r = 0.004$, $b = 0.02$), the NSC critical wage is approximately $30.69/hr — far above current GS-4 ($17.27) and GS-6 ($21.54) wages. Simply raising wages to satisfy the NSC at current detection probabilities is infeasible within the General Schedule structure.

However, the NSC is highly sensitive to the detection probability $q$. At $q = 0.04$ (the stated FIA QA rate applied monthly), the critical wage falls to approximately $22.91/hr, which is within reach of GS-7 ($23.94/hr) wages. This suggests that **increasing effective monitoring is more cost-effective than raising wages** as a strategy for satisfying the NSC.

## Increasing Detection Probability

The most direct route to NSC compliance is increasing the effective detection probability $q$. Several mechanisms are available:

**Expanded blind-check QA.** Increasing the blind-check audit rate from 4% to 10% of production plots would approximately double the effective per-period detection probability, reducing the efficiency wage premium by roughly half. The national FIA plot network consists of approximately 130,000 forested plots. Increasing the blind-check rate from 4% to 10% requires approximately 7,800 additional QA plot visits (130,000 × 0.06). At approximately 17 QA plots per crew-week, this requires roughly 450 additional crew-weeks. The incremental cost is approximately 450 additional QA crew-weeks nationally per year — roughly 9 per state — at approximately $4,000 per crew-week (two GS-7 technicians at $23.94/hr plus travel and per diem), or approximately $1.8 million/year nationally. Against the downstream value of FIA data in timber commerce and carbon markets, this is a modest investment.

**Technology-assisted monitoring.** GPS track logging and accelerometer data from field devices can verify that crews physically visited plot locations and spent appropriate time on-plot. This does not directly assess measurement quality but eliminates the possibility of "phantom plots" (fabricated data without plot visitation) and provides circumstantial evidence of protocol adherence. The marginal cost is near zero if field crews already carry GPS-enabled devices, as is increasingly standard.

**Automated consistency checks.** Machine learning models trained on historically verified measurements can flag anomalous submissions in near-real-time — for instance, height-diameter relationships that are implausibly tight (suggesting estimation from the allometric curve), species identifications inconsistent with known range maps, or diameter changes between remeasurements that are implausibly uniform. These checks increase the subjective detection probability $q$ by making technicians uncertain about what will be flagged.

## Institutional Redesign

Beyond the wage-monitoring tradeoff, structural changes to the employment relationship can address the NSC through multiple channels:

**Extended appointments with rehire guarantees.** Converting seasonal term appointments to multi-year terms (e.g., 2-year appointments with expected renewal) would reduce the end-of-season separation rate $b$ and increase the value of continued employment $V_E - V_U$. This requires modification of current appointment authorities under 5 CFR §316 but is consistent with recent Office of Personnel Management guidance encouraging agencies to stabilize seasonal workforces.

**Performance feedback loops.** Currently, QA results are used primarily for program-level quality reporting, not individual performance feedback. Linking QA blind-check results to individual technician performance records — and making this linkage transparent — would increase both the effective detection probability (because technicians know results are tracked) and the consequence of detection (performance records affect rehire decisions).

**Career ladders.** Establishing clearer promotion pathways from GS-4/5 seasonal to GS-7/9 permanent positions would increase the value of continued employment and align intrinsic motivation with institutional incentives. This is a long-term structural change but addresses the fundamental problem that seasonal employment undermines the efficiency wage mechanism.

## Feasibility Under Current Federal Constraints

These recommendations vary substantially in feasibility under current federal workforce conditions, including ongoing reductions in force across USDA agencies. We sequence them by implementation difficulty:

1. **Technology-assisted monitoring** (near-zero marginal cost). GPS track logging and time-on-plot verification require only software configuration on existing field devices. This is the most robust recommendation under any budget scenario and could be implemented immediately without additional appropriations or personnel actions.

2. **HTCD-based auditing** (low cost). Systematic analysis of HTCD method code distributions across crews and seasons is automatable within existing QA infrastructure. Flagging units with anomalously high estimation rates requires only analytical capacity, not field staff.

3. **Expanded blind-check QA** (~$1.8M/year nationally). Increasing blind-check rates from 4% to 10% requires sustained appropriations for additional QA crew-weeks. This is moderately feasible but vulnerable to annual budget fluctuations.

4. **Career ladders and extended appointments** (highest cost). Addressing the root cause — seasonal employment that undermines the efficiency wage mechanism — requires restructuring appointment authorities and creating permanent positions. This is the most effective long-term solution but also the most vulnerable to hiring freezes and workforce reduction mandates.

A potential vicious cycle deserves note: workforce instability simultaneously causes the data quality problem (by creating the institutional conditions that violate the NSC) and prevents its solution (by constraining the agency's capacity to implement monitoring reforms). Breaking this cycle requires recognizing that investment in monitoring infrastructure protects the downstream value of the data asset.

Finally, remote sensing (e.g., LiDAR-derived tree heights) may eventually eliminate the human measurement effort margin for the variable most susceptible to approximation, though ground-based measurement remains essential for species identification, crown condition, and other variables that remote sensing cannot reliably estimate.
