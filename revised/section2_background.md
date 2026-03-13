# 2. Institutional Background and Theoretical Framework

## 2.1 The FIA Program

The Forest Inventory and Analysis program, administered by the USDA Forest Service, conducts the national forest inventory mandated by the Forest and Rangeland Renewable Resources Research Act of 1978 (16 U.S.C. §1641–1646). Since the transition from periodic to annual inventory in the early 2000s, FIA has operated a panel-based sampling design in which approximately one-fifth to one-seventh of permanent plot locations (depending on state cycle length) are visited each year. The national plot network consists of approximately 130,000 permanent sample plots on a hexagonal grid with one plot per approximately 6,000 acres of forest land (Bechtold and Patterson, 2005).

Each plot consists of four circular subplots (24-foot radius for trees ≥5.0 inches DBH, with nested microplots for seedlings and saplings). At each subplot, field crews measure all qualifying trees: diameter at breast height (DBH) with a diameter tape to the nearest 0.1 inch, total height with a clinometer or laser hypsometer to the nearest foot, species identification by visual assessment, crown class and condition, and numerous auxiliary variables including decay class, damage, and lean. A single production plot typically requires 4–8 hours to complete, including travel, navigation, and data entry.

The measurement season runs roughly April through November in most regions, with geographic variation. Southern states may begin earlier; northern and mountain states may extend into early winter depending on snow conditions. This seasonal window creates a natural cycle of fieldwork intensity that is central to our analysis.

## 2.2 Quality Assurance Structure

FIA operates a two-tier quality assurance program:

*Hot checks* are supervisory observations where a crew leader accompanies a field technician and evaluates adherence to measurement protocols. These are relatively frequent but not independent — the technician knows they are being observed.

*Blind checks* are independent re-measurements where a separate QA crew revisits a randomly selected production plot without the original crew's knowledge and measures all trees independently. Discrepancies between production and QA measurements are compared to tolerance thresholds defined in the FIA National Core Field Guide. The stated target is that approximately 4% of production plots receive blind-check QA re-measurement each year (USDA Forest Service, 2023). The actual QA re-measurement data are not available in the public FIA DataMart database — a point to which we return in Section 3.

From the technician's perspective, the effective detection probability is the product of (1) the probability that the specific plot is selected for QA, (2) the probability that the QA re-measurement is conducted before the technician's appointment ends, and (3) the probability that the comparison detects approximation conditional on it occurring. Even at the stated 4% annual rate, this compound probability is substantially less than 0.04 per plot-period.

## 2.3 The Seasonal Labor Market

FIA field crews are predominantly seasonal (term) federal employees hired under the General Schedule at GS-4 (entry) through GS-6 (experienced crew leader) pay grades. Term appointments under 5 CFR §316.401 are limited to 13 months and carry no guarantee of rehire. In practice, successful technicians are often rehired across multiple seasons, but the employment relationship is explicitly temporary.

This seasonal structure creates three features relevant to incentive analysis. First, the effective outside option $\bar{w}$ includes not just other jobs available at the time of potential termination but the full set of seasonal outdoor employment opportunities — wildfire suppression crews (often at higher base pay plus hazard pay), trail maintenance, seasonal National Park Service and Bureau of Land Management positions, and state forestry agency work. For technicians in forestry programs, graduate assistantships are also relevant. BLS Occupational Employment and Wage Statistics reveal substantial geographic variation in these outside options: median hourly wages for landscaping and groundskeeping range from approximately $15/hr in the Southeast to $19/hr in the Pacific Northwest, while logging worker wages range from $17/hr to $22/hr.

Second, the guaranteed end of the seasonal appointment creates an end-of-season dynamic that undermines the efficiency wage mechanism. As the appointment end date approaches, the termination threat loses potency — the technician is losing the job regardless. The effective separation rate $b$ increases toward the end of the season, raising the NSC precisely when cumulative fatigue and declining weather may also be reducing intrinsic motivation.

Third, mid-season termination for performance reasons, while legally permissible under term appointment rules, faces practical barriers: documentation requirements, progressive discipline expectations, and the difficulty of demonstrating that approximated data constitutes inadequate performance when the data superficially meets plausibility standards. This limits the credibility of the termination threat, reducing the effective detection probability $q$ even below the audit rate.

## 2.4 A Motivating Model

We use the Shapiro-Stiglitz (1984) efficiency wage framework as a quantitative lens for assessing whether institutional design creates conditions favoring measurement approximation — not a causal claim about why the HTCD differential documented in Section 3 exists. The calibration provides an indicative benchmark for the *magnitude* of a potential incentive gap, not the precise behavioral mechanism through which that gap translates into measurement decisions.

**Setup.** A risk-neutral field technician employed at wage $w$ per period chooses effort $e \in \{0, \bar{e}\}$: careful measurement ($e = \bar{e}$, disutility $\bar{e}$) or approximation ($e = 0$). The principal detects approximation with probability $q$ per period through QA audits. Upon detection, the technician is terminated and earns outside option $\bar{w}$. With exogenous separation rate $b$ (reflecting end-of-season and other non-monitoring exits) and discount rate $r$, the standard value function analysis yields the no-shirking condition (NSC). Intuitively, if workers can cut corners without being caught, they will only refrain if the job pays enough above their next-best option to make the risk of termination costly. The minimum wage that makes honest effort worthwhile is:

$$w^* \geq \bar{w} + \bar{e} + \frac{\bar{e}}{q}(r + b)$$

The critical wage has three components: the outside option $\bar{w}$; a compensating differential for effort $\bar{e}$; and the efficiency wage premium $\frac{\bar{e}}{q}(r + b)$ — the extra pay needed to make the job valuable enough that workers fear losing it. This premium is large when detection is infrequent ($q$ small), the job is ending soon ($b$ large), or the discount rate is high. Risk aversion would increase the NSC, so our risk-neutral specification is conservative.

**Finite-horizon extension.** The stationary SS model assumes a constant hazard of termination, whereas seasonal FIA employment has a known endpoint. In a finite-horizon setting, the termination threat is vacuous in the final period — the worker is leaving regardless — and by backward induction, the NSC is violated in every period. The standard resolution in the repeated-game literature is that reputation or continuation value sustains cooperation, but these mechanisms require that the employment relationship extends beyond the current season. For a purely terminal seasonal worker with no prospect of rehire, backward induction implies that estimation is rational throughout the appointment, not merely at season's end. This is actually *more* consistent with the empirical finding of year-round estimation (Section 3.2) than the stationary model, which would predict late-season concentration as the effective separation rate $b$ increases. We therefore interpret the calibration as a benchmark indicating the direction and magnitude of incentive gaps, not as a precise wage threshold.

For career-track workers — GS-0462 technicians pursuing permanent GS-0460 positions through the GS-4→GS-5→GS-7 pipeline — the employment relationship is effectively indefinite-horizon with periodic re-contracting. The substantial employment rents of permanent federal service (FERS retirement, FEHB health insurance, job security) create continuation value that sustains cooperation across seasons. For this subpopulation, the stationary SS framework is a reasonable approximation: the multi-season career structure means the repeated-game logic applies over a multi-year horizon. The calibrated NSC therefore applies most directly to terminal seasonals without career pathways — the vulnerable margin where neither backward induction nor career incentives sustain measurement effort.

**Calibration.** We calibrate the NSC using FIA institutional data, federal pay schedules, and labor market statistics. Table 1 summarizes parameter values and sources.

[Table 1: Model Parameters and Sources — to be formatted as LaTeX table]

| Parameter | Symbol | Central Value | Range | Source |
|-----------|--------|---------------|-------|--------|
| GS-4 wage | $w$ | $17.27/hr | — | OPM 2025 GS, RUS locality |
| GS-5 wage | $w$ | $19.33/hr | — | OPM 2025 GS, RUS locality |
| GS-6 wage | $w$ | $21.54/hr | — | OPM 2025 GS, RUS locality |
| GS-7 wage | $w$ | $23.94/hr | — | OPM 2025 GS, RUS locality |
| Outside option | $\bar{w}$ | $16.00/hr | $14–$20 | BLS OES by state |
| Effort cost | $\bar{e}$ | $4.32/hr (0.25×GS-4) | 0.15w–0.40w | O*NET 19-4071.00 |
| Detection probability | $q$ | 0.01/month | 0.003–0.04 | FIA QA program; DataMart |
| Separation rate | $b$ | 0.02/month | 0.01–0.05 | OPM term appointment rules |
| Discount rate | $r$ | 0.004/month | 0.003–0.008 | Standard (~5% annual) |

Wages follow the 2025 General Schedule with Rest of U.S. (RUS) locality pay (OPM, 2025). The outside option ($\bar{w} = \$16$/hr) reflects a central estimate across competing seasonal occupations, with sensitivity from $14 to $20. The effort cost ($\bar{e} = 0.25 \times \$17.27 = \$4.32$/hr) is grounded in a time-budget micro-foundation: measuring tree height with instruments requires approximately 2–4 minutes per tree versus 15–30 seconds for ocular estimation; across ~35 height-measured trees per plot, substituting estimation saves 60–175 minutes per 4–8 hour plot day, implying $\bar{e}/w \in [0.13, 0.36]$.

The detection probability ($q = 0.01$ per month) is deliberately conservative — it overstates the effective detection probability for most states. We computed effective state-level QA rates as the ratio of blind-check plots (QA_STATUS = 7) to production plots (QA_STATUS = 1) in the FIA DataMart PLOT table, computed separately by state and measurement year and averaged across the sample period. State-level rates range from 0.0001 (VT) to 0.013 (GA, OR), with a cross-state median of approximately 0.003. The order-of-magnitude gap between the observed median (~0.3%) and the stated 4% target reflects both incomplete coverage (not all plots are revisited within a measurement year) and the compound probability structure described above. At this observed median, the NSC rises to approximately $54.92/hr, exceeding GS-4 wages by over 200%. The separation rate ($b = 0.02$ per month) reflects the low probability of mid-season termination given civil service documentation requirements. The discount rate ($r = 0.004$ per month) corresponds to approximately 5% annual discounting.

**NSC evaluation.** At central parameters:

$$w^* = 16 + 4.32 + \frac{4.32}{0.01}(0.004 + 0.02) = 16 + 4.32 + 10.37 = \$30.69/\text{hr}$$

This benchmark value is **78% above the GS-4 wage** ($17.27/hr), **59% above the GS-5 wage** ($19.33/hr), and **43% above the GS-6 wage** ($21.54/hr). The efficiency wage premium ($10.37/hr) dominates, driven primarily by the low detection probability. If $q$ increases to 0.04 (the stated FIA QA rate applied as a monthly probability):

$$w^* = 16 + 4.32 + \frac{4.32}{0.04}(0.024) = 16 + 4.32 + 2.59 = \$22.91/\text{hr}$$

At this higher detection probability, GS-6 wages ($21.54) fall short by only 6%, and GS-7 wages ($23.94) exceed the NSC. However, $q = 0.04$ represents the *stated* FIA target rate; the observed effective rate from FIA DataMart is approximately 0.003 across most states, so this favorable scenario requires closing the order-of-magnitude gap between stated and effective monitoring rates. This sensitivity underscores the calibration's central insight: the detection probability $q$ is the parameter that most strongly governs the incentive gap, and the gap between stated and effective monitoring rates is the most actionable policy margin.

The magnitude of the NSC gap is also sensitive to the effort cost assumption: at $\bar{e}$ = $2/hr (the lower bound of plausible values), $w^*$ falls to approximately $22/hr, within reach of GS-6. Table 2b presents the full sensitivity surface. The qualitative conclusion — that the NSC exceeds current wages under central and most alternative parameterizations — is robust, but specific percentage gaps should be interpreted as indicative benchmarks, not precise thresholds.

[Table 2: NSC Sensitivity to Outside Option and Separation Rate — to be generated from calibration code]

[Table 3: Cross-State NSC Variation — to be generated from BLS data]

## 2.5 Multi-Task Predictions and Behavioral Extensions

**Multi-task effort allocation.** When workers perform multiple tasks that differ in how easily supervisors can verify them, theory predicts effort will decline most on the hardest-to-monitor tasks. The binary effort model treats "careful measurement" as a single dimension, but FIA technicians allocate effort across multiple tasks with different costs and detection probabilities — a multi-task moral hazard problem (Holmström and Milgrom, 1991). DBH measurement with a diameter tape is easily verified by QA re-taping; height measurement with a clinometer requires retreating to find line-of-sight, identifying the correct top in closed canopy, and taking careful angle readings — and has inherently higher inter-observer variance even under honest effort. Species identification and condition codes involve partly subjective categorical judgments. The multi-task framework predicts that effort reductions concentrate on the hardest-to-verify margins — particularly height estimation. This prediction is directly testable with the paired data in Section 3.

**Intrinsic motivation.** Many FIA technicians are trained foresters with genuine professional commitment to data quality (Perry and Wise, 1990; Buurman et al., 2012). Following Bénabou and Tirole (2003, 2006), intrinsic motivation $m$ effectively reduces the net effort cost to $(\bar{e} - m)$; when $m \geq \bar{e}$, the NSC is automatically satisfied at any wage above the outside option. However, intrinsic motivation faces structural erosion in the FIA context: seasonal employment at GS-4/5 wages undermines professional identity and organizational attachment; cumulative fatigue reduces the psychic rewards of careful measurement over the season; and crowding out (Bénabou and Tirole, 2003) means that monitoring perceived as distrustful can itself reduce $m$. We note that our policy recommendation is not increased surveillance beyond stated expectations but credible monitoring at the existing stated rate — closing the gap between the stated 4% audit target and the observed effective rate of ~0.3%.

**Workforce heterogeneity.** The FIA seasonal workforce contains at least two distinct types. Career-track seasonals — GS-0462 technicians pursuing permanent GS-0460 positions — treat the seasonal appointment as a pipeline into federal careers with substantial employment rents (FERS retirement, FEHB health insurance, job security). For these workers, the effective outside option includes the option value of permanent employment, and the multi-season career structure (GS-4→GS-5 after one season, GS-7 upon degree completion) means the SS framework's repeated-game logic applies over a multi-year horizon. Terminal seasonals, by contrast, lack pathways to permanent employment and face the model's standard NSC. The calibrated NSC applies to the marginal (terminal) worker; the career-ladder mechanism implies that the vulnerable margin is concentrated among terminal seasonals rather than uniformly distributed across the workforce. Career-track workers' tendency to stay late in the season — forgoing fall semester to build supervisory relationships — means late-season crews are positively selected on effort quality, attenuating seasonal signals even if terminal seasonals engage in estimation.
