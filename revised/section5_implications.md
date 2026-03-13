# 4. Implications for Timber Markets and Data Governance

## Systematic Error and Volume Estimation

The paired data provide a nuanced picture of estimation's consequences: estimated heights produce allometric residuals statistically indistinguishable from measured heights (Section 3.3), indicating that the variance-compression mechanism is not detectable at the population level. This limits the scope for systematic volume bias to subpopulations of less-skilled estimators or to residual components not captured by the species-group allometric model. To the extent that estimation reduces the biological information content of height measurements — compressing variation around the allometric mean — its effects on volume estimates would be non-random: height approximation errors would understate volume for tall trees (where true height exceeds the allometric prediction) and overstate it for short trees, with the net aggregate bias potentially modest if deviations approximately cancel.

The allometric conformity null indicates that this compression is not detectable at the population level, but the data quality concern extends beyond systematic volume bias to three other margins: (a) loss of biological variance information relevant to site-specific applications (timber sales, carbon market protocols), where allometric norms are poor substitutes for actual measurements; (b) attenuation of the HTCD method code signal — if estimation is forensically invisible, HTCD=1 ceases to reliably indicate instrument measurement, degrading the information value of method codes for downstream users; and (c) institutional corrosion of the monitoring architecture, as discussed in Section 3.3.

## Downstream Effects

FIA data propagate through multiple downstream applications:

**Stumpage pricing.** Timber sale appraisals use local volume estimates derived from FIA data. To the extent that estimation reduces the biological information content of height measurements, appraisals may understate merchantable volume on sites where trees exceed allometric expectations, creating arbitrary variation in appraised values.

**Carbon accounting.** National forest carbon stock estimates rely on allometric biomass equations applied to FIA diameter and height measurements. To the extent that estimation compresses variance around the allometric mean, it would reduce detected spatial heterogeneity in carbon stocks without necessarily biasing the national total. If carbon market protocols require site-specific estimates, the information loss is material.

**Forest health monitoring.** FIA's ancillary measurements — crown condition, damage codes, mortality — are arguably more susceptible to approximation than the core tree measurements, because they involve subjective categorical judgments with inherently lower inter-observer agreement. The multi-task framework (Section 2.5) predicts that effort reductions concentrate on these hard-to-verify margins.

## Data Governance Parallels

The ocular estimation problem is not unique to forest inventory. Analogous institutional structures — seasonal or temporary workforces, imperfect monitoring, hard-to-verify outputs — arise in fisheries observer programs (where observers aboard commercial fishing vessels record catch and bycatch), environmental compliance monitoring (Duflo et al., 2013), agricultural crop surveys, and health surveys in developing countries. In each case, the combination of low detection probability and limited employment rents creates theoretical preconditions for data quality degradation.

What distinguishes the FIA setting is the completeness of institutional information available for calibration: federal pay schedules are public, the QA program's structure and stated audit rates are documented, and the measurement data include precise timing. This makes FIA a particularly clean laboratory for studying monitoring incentive design in public data collection programs — findings here may inform institutional design in other monitoring contexts.

## Implications for Empirical Research Using Forest Inventory Data

More broadly, empirical studies that rely on inventory-derived volume estimates — including timber market analyses, carbon accounting models, and forest growth studies — could in principle be affected by systematic measurement error of the type characterized here. Critically, this error is non-classical: rather than adding noise symmetrically, ocular estimation compresses height values toward the allometric mean, attenuating biological variance in ways that standard measurement error corrections do not address. Characterizing these downstream effects across specific applications is a natural direction for future work, though the magnitude in any given study remains to be determined.
