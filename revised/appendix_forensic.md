# Supplementary Materials: Forensic Analyses

This appendix presents four forensic statistical tests using public FIA data, a summary table of discriminating predictions, and robustness analyses. These supplement the paired QA/production comparison in Section 3 of the main text.

## A.1 FIA DataMart Data

We use tree-level measurement data from the FIA DataMart (apps.fs.usda.gov/fia/datamart), which provides state-level SQLite databases containing the complete public FIA database. We download data for eight states spanning five FIA regions and distinct labor markets: Vermont and Maine (Northeast), Minnesota and Wisconsin (Northern), Georgia (South), Colorado (Rocky Mountain), and Oregon and Washington (Pacific Northwest).

From each state database, we extract the PLOT table (plot-level metadata including measurement month, year, and QA status) and the TREE table (tree-level measurements including DBH, height, species, and species group). We restrict the primary analysis sample to production plots (QA_STATUS = 1) and live trees (STATUSCD = 1) with valid diameter measurements (DIA > 0), yielding 4,628,494 tree-observations across measurement years 1995–2025.

For the QA crew comparison (Section A.4), we additionally extract 91,493 trees from QA blind-check plots (QA_STATUS = 7). These plots were independently remeasured by QA crews as part of the FIA quality assurance program. QA crews are supervisory staff performing spot-check remeasurements under different institutional conditions: no seasonal appointment pressure, no production quotas, and an explicit quality mandate. The QA sample is distributed unevenly across states, with Georgia contributing the largest share (55,345 trees, reflecting its higher QA remeasurement rate of approximately 5%).

The primary identification strategy exploits seasonal variation in measurement quality. All production crews in a given state follow the same measurement protocols, use the same equipment, and are subject to the same QA program. However, the institutional factors affecting the NSC — cumulative fatigue, approaching end of appointment, weather degradation, and waning intrinsic motivation — systematically vary across the measurement season. If ocular estimation varies seasonally, it should intensify in late-season months (September through December) relative to mid-season months (May through July).

Key variables:
- **DIA**: Diameter at breast height, recorded to 0.1 inches.
- **HT**: Total tree height, recorded to the nearest foot.
- **MEASMON**: Month of measurement (1–12), our primary treatment variable.
- **QA_STATUS**: 1 for production plots, 7 for QA blind-check plots.
- **SPGRPCD**: Species group code, controlling for species-specific measurement difficulty.
- **MEASYEAR**: Measurement year, controlling for temporal trends.
- **STATE**: State identifier, controlling for regional differences.

All regressions use OLS with standard errors clustered at the state-year level. LATE_SEASON is defined as in Section 3.1 (indicator for months 9–12).

## A.2 Test 1: Digit Heaping

**Prediction.** Approximated DBH measurements cluster on round numbers — whole inches (x.0) and half inches (x.0, x.5) — because visual estimation and mental rounding naturally produce values at these focal points. Carefully tape-measured diameters, by contrast, distribute uniformly across tenths (each digit 0–9 should appear approximately 10% of the time). If ocular estimation increases late season, digit heaping rates should increase in late-season months.

**Methods.** For each tree observation, we compute: (1) a whole-inch indicator equal to 1 if the last digit of DIA (in tenths) is 0; (2) a half-inch indicator equal to 1 if the last digit is 0 or 5; and (3) height rounding indicators equal to 1 if HT is divisible by 5 or by 10. We estimate:

$$\text{DIA\_whole}_{itsy} = \beta_0 + \beta_1 \cdot \text{LATE\_SEASON}_t + \gamma_s + \delta_y + \varepsilon_{itsy}$$

where $i$ indexes trees, $t$ indexes measurement month, $s$ indexes states, $y$ indexes years. We also estimate specifications with species group fixed effects and month dummies (reference: June).

**Results.** The overall whole-inch DBH rate is 11.57%, substantially above the 10% expected under uniform measurement — a chi-squared test for uniformity of the last digit rejects strongly ($\chi^2$ = 41,283, $p$ < 0.001, $N$ = 4,628,494). Digit heaping is present in FIA data.

However, the seasonal pattern is weak. Whole-inch rates range from 11.50% (August) to 11.78% (November) across months, with no clear seasonal trend. The LATE_SEASON coefficient is positive but not statistically significant: $\hat{\beta}_1$ = 0.0005 (SE = 0.0003, $p$ = 0.135). Adding species group fixed effects does not change the conclusion ($\hat{\beta}_1$ = 0.0003, $p$ = 0.321). Height rounding (divisibility by 5) shows a similar null: $\hat{\beta}_1$ = $-$0.0019 ($p$ = 0.125).

The last-digit frequency distribution reveals that heaping is concentrated at digits 0 and 1, with deficits at digits 7, 8, and 9. This pattern is consistent with small-tree rounding conventions (trees near the 5.0-inch minimum merchantability threshold) rather than with seasonal effort variation. Both early-season and late-season distributions show the same departure from uniformity.

In isolation, the digit heaping test does not support seasonally varying ocular estimation. The overall presence of heaping confirms that some approximation occurs in FIA measurement, but it does not intensify late-season within the resolution of these data.

## A.3 Test 2: Allometric Residual Patterns

**Prediction.** Tree height is related to diameter through allometric (power-law) relationships: $\ln(\text{HT}) = \beta_0 + \beta_1 \ln(\text{DIA}) + \varepsilon$. If technicians approximate heights by mentally estimating from diameter (using their internalized allometric model), the residuals from a fitted allometric relationship will have *lower* variance than residuals from carefully measured heights. This is because estimation produces heights that track the population-average allometric curve, while true heights reflect biological variation around the curve — soil conditions, competition, genetics, damage history — that careful measurement captures but estimation misses.

This generates opposite predictions from honest measurement error:

| | Residual Variance Late Season | Allometric R² Late Season |
|---|---|---|
| **Ocular estimation** | Decreases (estimates track the curve) | Increases (better "fit") |
| **Honest error** | Increases (fatigue adds noise) | Decreases (noisier measurements) |

**Methods.** We fit $\ln(\text{HT}) = \beta_0 + \beta_1 \ln(\text{DIA}) + \sum_g \lambda_g \cdot \mathbf{1}[\text{SPGRPCD} = g] + \varepsilon$ on the pooled production sample ($N$ = 4,587,949, $R^2$ = 0.848). For the DID analysis in Section A.4, the allometric model is fitted on production data only and then used to compute residuals for both production and QA trees. We compute the residual for each tree and estimate:

$$|\hat{\varepsilon}_{itsy}| = \alpha_0 + \alpha_1 \cdot \text{LATE\_SEASON}_t + \gamma_s + \delta_y + \eta_{itsy}$$

A negative $\alpha_1$ is consistent with ocular estimation; a positive $\alpha_1$ is consistent with honest error.

**Results.** Residual standard deviation varies by month from 0.194 (January) to 0.234 (July), following a pronounced hump-shaped seasonal profile peaking in summer. This summer peak is the *opposite* of the ocular estimation prediction (which predicts lowest late-season variance) and likely reflects the leaf-on confound: full summer foliage obscures tree crowns, making clinometer-based height measurement mechanically more difficult and increasing honest measurement noise. Month-specific allometric $R^2$ ranges from 0.819 (March) to 0.863 (September–October), with the highest fit in late-season months — consistent with the ocular estimation prediction but also consistent with the improving crown visibility of the leaf-off season.

A Levene's test comparing early-season (May–August) and late-season (September–December) residual variance is highly significant ($F$ = 1,642, $p$ < 0.001), with late-season variance *lower* (SD = 0.219 vs. 0.228). However, the regression with state and year fixed effects yields a near-zero coefficient: $\hat{\alpha}_1$ = 0.00007 (SE = 0.0008, $p$ = 0.93). Adding species group fixed effects produces $\hat{\alpha}_1$ = $-$0.0009 ($p$ = 0.21) — directionally consistent with ocular estimation but not statistically significant.

The attenuation from unconditional to conditional estimates suggests that the raw seasonal variance pattern partly reflects compositional differences — which states measure in which months — rather than within-crew behavioral changes.

**A note on circularity.** An important caveat is potential circularity: if technicians estimate heights from diameter, their estimates will by construction have small allometric residuals. The DID design partially addresses this (the circularity applies equally to both groups), but the unconditional allometric test alone is not a discriminating test of the incentive mechanism.

## A.4 Test 3: QA Crew Comparison (Difference-in-Differences)

**Motivation.** The production-only analyses in Sections A.2 and A.3 face a fundamental identification challenge: seasonal variation in measurement quality may reflect environmental factors (leaf-on conditions obscuring tree tops, winter conditions affecting crew access, foliage effects on clinometer readings) rather than strategic effort reductions. To distinguish incentive-driven from environment-driven seasonal patterns, we exploit a natural control group embedded in the FIA data.

QA crews (QA_STATUS = 7) perform blind remeasurements of randomly selected plots as part of FIA's quality assurance program. Critically, QA crews operate under fundamentally different institutional conditions than production crews:

- QA crews are typically senior technicians or supervisory staff, not seasonal appointees
- They have no production workload quotas — their mandate is quality verification
- They are not subject to the same end-of-season appointment pressures
- Their measurement incentives are aligned with accuracy, not throughput

If seasonal measurement degradation is driven by the institutional incentives modeled in Section 2 — the factors that enter the no-shirking condition — it should appear in production data but *not* in QA data. If it is driven by environmental conditions that affect all crews equally (weather, foliage, daylight), both groups should show similar seasonal patterns.

**Control group validity.** The parallel trends assumption underlying this DID design requires that, absent incentive-driven effort changes, production and QA crews would show similar seasonal measurement patterns. This assumption is not directly testable with the available data. QA crews differ from production crews in experience, seniority, and institutional mandate — factors that could generate differential seasonal patterns even without incentive effects.

**Specification.** We estimate:

$$|\hat{\varepsilon}_{itsy}| = \alpha_0 + \alpha_1 \cdot \text{QA}_i + \alpha_2 \cdot \text{LATE}_t + \alpha_3 \cdot (\text{QA}_i \times \text{LATE}_t) + \gamma_s + \delta_y + \eta_{itsy}$$

where $\text{QA}_i$ is an indicator for QA plots and all other variables are defined as before. The coefficient of interest is $\alpha_3$: a positive value indicates that QA crews experience a larger late-season increase in residual dispersion than production crews — consistent with production crews suppressing the natural seasonal increase through estimation.

**Results.** In the baseline specification with state and year fixed effects ($N$ = 4,679,419):

- $\hat{\alpha}_1$ (QA) = $-$0.0057 (SE = 0.0018, $p$ = 0.002): QA crew measurements have *lower* absolute residuals than production measurements, indicating greater care and experience.

- $\hat{\alpha}_2$ (LATE_SEASON) = 0.00005 (SE = 0.0008, $p$ = 0.95): For production crews, there is essentially no seasonal change in residual dispersion after controlling for state and year.

- $\hat{\alpha}_3$ (QA $\times$ LATE) = **0.0077** (SE = 0.0035, **$p$ = 0.026**): The DID estimate is positive using conventional cluster-robust inference. QA crews show 0.77 percentage points *more* late-season residual increase than production crews. However, the wild cluster bootstrap yields $p$ = 0.403 (Section A.7), indicating this result does not survive inference appropriate to the small number of effective clusters.

The interaction coefficient is positive when adding species group fixed effects ($\hat{\alpha}_3$ = 0.0067, conventional $p$ = 0.045) and when using squared residuals as the dependent variable ($\hat{\alpha}_3$ = 0.0039, conventional $p$ = 0.056). All conventional $p$-values are subject to the same small-cluster caveat.

**Interpretation.** *If taken at face value*, the positive interaction tells a coherent story: QA crews show increasing measurement scatter late-season (the natural baseline as conditions deteriorate), while production crews show none of this increase. The Shapiro-Stiglitz interpretation: as seasonal pressure builds, some production crews shift from measuring height with clinometers to estimating from diameter, compressing residuals toward the allometric mean — exactly counteracting the environmental deterioration visible in the QA control group.

However, the bootstrap result means we cannot statistically distinguish this pattern from chance variation across 8 state clusters. The evidence is suggestive but not definitive.

Levene's tests confirm the pattern at the unconditional level: QA residual variance is significantly higher than production variance overall ($F$ = 96.8, $p$ < 0.001), and within QA plots, variance *decreases* significantly from early to late season ($F$ = 84.7, $p$ < 0.001), while within production plots, variance slightly *increases* ($F$ = 28.4, $p$ < 0.001). The opposing directions of within-group seasonal change are consistent with the behavioral mechanism, though the unconditional Levene tests do not control for state and year composition.

The digit heaping DID is positive ($\hat{\alpha}_3$ = 0.0021) but not statistically significant ($p$ = 0.38), consistent with the earlier finding that DBH measurement precision does not vary meaningfully by season. Height estimation — not diameter approximation — appears to be the primary margin of effort reduction.

## A.5 Test 4: Remeasurement Growth Anomalies

**Motivation.** FIA's panel design — in which trees are remeasured every 5–10 years — enables a complementary test exploiting the temporal structure of measurements. For a live, undamaged tree, both DBH and height should increase (or at least not decrease) between remeasurements. "Impossible" values — negative growth or growth exceeding biological maxima — indicate measurement error in at least one period. If ocular estimation concentrates on height (the harder-to-verify margin, per Section 2.5), then height measurement anomalies should be more prevalent than DBH anomalies and should intensify in late-season months.

**Data construction.** We self-join the TREE table on PREV_TRE_CN across eight state databases, restricting to live trees with valid diameter measurements at both time points and production plots at both visits. This yields 2,464,859 remeasurement pairs with a median interval of 5 years.

We define anomaly indicators at thresholds accommodating normal measurement tolerance: DBH shrinkage (delta < −0.1 in.), DBH extreme growth (>1.0 in./yr annualized), height shrinkage (delta < −3 ft.), and height extreme growth (>5.0 ft./yr). The "any anomaly" indicator flags trees with either shrinkage or extreme growth for the respective variable.

**Results: Overall anomaly rates.** Height measurement anomalies are dramatically more prevalent than DBH anomalies. The overall height anomaly rate is 9.27% (218,694 of 2,464,830 pairs with valid height data), compared to 1.46% for DBH. Height shrinkage alone — trees recorded as shorter at remeasurement — occurs in 8.87% of pairs, compared to 1.43% for DBH shrinkage. This 6:1 ratio confirms that height is the noisier measurement variable, consistent with its greater physical difficulty and with the model's prediction that height is the primary margin for effort reduction.

**Results: Seasonal patterns.** Contrary to the ocular estimation prediction, height anomalies do not increase in late-season months. The regression of height anomaly on LATE_SEASON with state and year fixed effects yields a coefficient of −0.0027 (SE = 0.0020, $p$ = 0.17) — directionally negative but not significant. DBH anomalies show a small, significant late-season *increase* (+0.0015, $p$ = 0.02), likely reflecting general end-of-season fatigue affecting all measurements rather than height-specific effort reduction.

**Species group decomposition: The leaf-off confound.** An important confounder is deciduous leaf phenology. In northern states, hardwood leaf-off in October–November improves crown visibility, making height measurement mechanically *easier* in late-season months.

| Species group | $N$ | Late-season HT anomaly coef. | SE | $p$ |
|--------------|-----|------|------|-------|
| Conifers (clean test) | 1,253,416 | −0.000048 | 0.0022 | 0.982 |
| Hardwoods (leaf-off confounded) | 1,211,414 | −0.0039 | 0.0027 | 0.146 |
| Interaction (Late × Conifer) | 2,464,830 | +0.0018 | 0.0029 | 0.521 |

The conifer result is effectively zero — no seasonal signal whatsoever in the clean test. The hardwood result is negative (late-season anomalies decrease), consistent with leaf-off improving height measurement accuracy. Growth variance comparisons tell a consistent story: late-season height growth variance is *higher* than early-season for both conifers ($F$ = 355, $p$ < 0.001) and hardwoods ($F$ = 2,119, $p$ < 0.001). Ocular estimation would predict *lower* late-season variance; the observed increase is consistent with accumulating measurement noise, not with systematic approximation.

**Interpretation.** The remeasurement analysis confirms that height is substantially noisier than DBH (consistent with the model's prediction about the margin of effort reduction) but finds no seasonal signal consistent with increased late-season ocular estimation. This null result is consistent with the finding in Section 3.2 that estimation is pervasive year-round rather than seasonally concentrated, and with the career-ladder self-selection mechanism discussed in Section 2.5.

## A.6 Discriminating Predictions

Table A1 summarizes the discriminating predictions and observed results across all analyses, including both the main-text paired comparison and the supplementary forensic tests.

**Table A1: Discriminating Predictions and Results**

| Test | Ocular Estimation Prediction | Honest Error Prediction | Observed | Assessment |
|------|----------------------|------------------------|----------|------------|
| Digit heaping (DBH) increases late season | Yes | No | Not significant ($p$ = 0.13) | Null — neither hypothesis supported |
| Allometric residual variance decreases late season | Yes | No (increases) | Significant unconditionally; attenuated to zero with FE | Consistent with ocular estimation unconditionally, but confounded by composition |
| Allometric $R^2$ increases late season | Yes | No (decreases) | Yes — $R^2$ peaks Sept–Oct | Consistent, but subject to same composition concerns |
| DID: Production suppresses natural variance increase | Yes | No | Conventional $p$ = 0.026; WCR bootstrap $p$ = 0.403 | Directionally consistent, but not significant under cluster-appropriate inference |
| QA variance higher than production | Yes | No | Yes ($p$ < 0.001) | Consistent, but could reflect experience/skill differences |
| HT anomaly rate higher than DBH | Yes | Yes (HT harder) | Yes — 9.3% vs 1.5% ($N$ = 2.46M pairs) | Consistent, but expected from measurement difficulty alone |
| HT anomalies increase late season | Yes | No change or increase | No — coefficient ≈ 0, $p$ = 0.17 | Null; no seasonal HT-specific effort signal |
| Conifer HT anomalies increase late season (clean test) | Yes | No change | No — coefficient ≈ 0, $p$ = 0.98 | Null; cleanest test shows dead zero |
| Late-season HT growth variance decreases | Yes (compression) | No (increases) | Increases for both conifers and hardwoods | Opposite to ocular estimation prediction |
| **Paired: Production HTCD=3 rate > QA** | **Yes** | **No** | **Yes — 23.1% vs 5.8% (4:1 ratio)** | **Direct evidence: production crews estimate at 4× QA rate** |
| **Paired: HT discrepancy > DIA discrepancy** | **Yes** | **Yes (HT harder)** | **Yes — 3.31 ft vs 0.06 in.** | **Consistent; confirms height as the noisier margin** |
| Paired: Estimated heights have smaller allometric residuals | Yes (track curve) | No | No — HTCD=1 and HTCD=3 residuals nearly identical ($p$ = 0.44) | Null; estimation does not visibly compress toward allometric mean |

The seasonal forensic tests — which sought to identify *when* ocular estimation intensifies — largely return nulls. This is consistent with the paired comparison finding that estimation is pervasive year-round (HTCD=3 rate shows no seasonal variation, $p$ = 0.54): if estimation rates do not vary seasonally, seasonal forensic tests have no signal to detect.

## A.7 Robustness

**State sensitivity.** The uneven distribution of QA observations across states raises the question of whether the DID result is driven by a single state's QA program. Georgia contributes 55,345 of 91,493 QA trees (60%); three western states (Colorado, Oregon, Washington) contribute another 32,709; and the remaining four states (Maine, Minnesota, Wisconsin, Vermont) contribute only 3,416 combined.

**Table A2: DID Sensitivity by State Grouping**

| Sample | QA Trees | $\hat{\alpha}_3$ | SE | $p$ |
|--------|----------|-------------------|------|-------|
| Full sample (8 states) | 91,493 | 0.0077 | 0.0035 | 0.026 |
| Georgia only | 55,345 | 0.0053 | 0.0044 | 0.228 |
| CO + OR + WA | 32,709 | $-$0.0019 | 0.0093 | 0.838 |
| All except GA (7 states) | 36,125 | 0.0027 | 0.0079 | 0.729 |

No individual subsample produces a statistically significant interaction. The full-sample result should be interpreted as suggestive rather than definitive.

**Wild cluster bootstrap.** To address the small-cluster concern, we implement a wild cluster bootstrap (Cameron et al., 2008) with Rademacher weights at the state level for the primary DID specification (999 replications). The wild cluster bootstrap $p$-value is 0.403 — substantially above the conventional clustered $p$-value of 0.026. This discrepancy reflects the very small effective cluster count (8 states) and the dominance of Georgia in the QA sample. The DID result should be interpreted as directionally suggestive rather than statistically confirmed.

**Effective cluster count.** Standard errors in all DID specifications are clustered at the state-year level, yielding approximately 80–120 effective clusters. However, for the wild cluster bootstrap we cluster at the state level, because the identifying variation for the QA × LATE interaction occurs between states. With only 8 states providing QA data — and one state dominating the sample — the effective degrees of freedom for the interaction coefficient are limited.

**Multiple testing.** Across the forensic analyses, we estimate five DID models, twelve remeasurement regression specifications, and several additional regressions in the paired analysis, yielding over twenty-five total specifications. A Bonferroni correction applied to the five DID models would raise the threshold to $\alpha = 0.01$, under which the primary DID result ($p$ = 0.026) would not be significant.

**Geographic robustness.** The paired QA/production analysis in Section 3 addresses the GA-dominance concern directly: the Yanai et al. dataset covers 24 northern states, none of which is Georgia, yet production crews still estimate at 4× the QA rate. The HTCD differential is present across all states in the sample, confirming that the pattern is not an artifact of a single state's QA program.
