# Validation plan and status

This document summarizes how the ERG Analysis API is to be validated, following Chapter 16 (validation), Chapter 17 (Model Card and drift monitoring) and Chapter 10 (data) of *Hands-On Electroretinography in the Age of AI*. The reporting standard is TRIPOD+AI (Collins et al., 2024); Chapter 16 maps each checklist item to the chapter and function that address it.

## Current status

| Part | Status |
|:---|:---|
| Traffic Light zoning against Baker et al. (2025) limits | Implemented. Automated tests reproduce the zones and printed limits of the Chapter 19 case studies. |
| Signal quality, filtering and feature extraction | Implemented and tested on simulated recordings. |
| Stage 1 and Stage 2 classifiers | Pre-registered target (Chapter 19, Table 19.10). Not yet trained or validated on patient data. |
| External validation, Phase A (Traffic Light) | Registered on OSF (Update 5) before any data exist; software locked in release `phaseA-lock-2026-11-23`; protocol and templates in `docs/regulatory/` (T4-A to T4-F v2.0). Starts once a centre is identified, ethics approval is granted and the data agreement is signed. |
| External validation, Phase B (classifiers) | Follows the registered SAP v2.3 after the Stage 1 and Stage 2 classifiers are trained. |

No performance figure in this repository is a project result. The figures in the Model Card (Chapter 17, Table 17.4) and in the figures of Chapters 16 and 17 are illustrative placeholders.

## Statistical Analysis Plan

The plan is pre-registered on the Open Science Framework before any validation data are analyzed: https://doi.org/10.17605/OSF.IO/6WA42. The SAP file, `ERG_SAP_v2.3.pdf`, is stored on the associated OSF project and in `docs/`, with its SHA-256 hash on the OSF Wiki. Version 2.3 adds the ethnicity and iris color subgroups of registration Update 6; `ERG_SAP_v2.2.pdf` is kept for the audit trail and is superseded. As Chapter 16 §16.2 specifies, this hash is checked and written to the Layer 4 audit log of every report (`api/sap_audit.py`, entry `sap_integrity`: MATCH, MISMATCH or MISSING), and carried into the FHIR AuditEvent. A MISMATCH or MISSING entry means no validation result may be reported from that run (T4-A, item K2).

- **Primary outcomes:** Stage 1 binary AUC-ROC and Stage 2 macro-AUC-ROC across the six disease classes, both on the external validation dataset.
- **Secondary outcomes:** per-class sensitivity, specificity, PPV, NPV and Brier score.
- **Subgroups:** age stratum, sex and recording device.
- **Confidence intervals:** DeLong for each class AUC; a patient-level bootstrap with 2000 resamples for the macro-AUC and all other metrics. Significance level 0.05, two-tailed.

## Phase A: external validation of the Traffic Light (OSF Update 5)

- **Design:** consecutive adults aged 18 to 80 at one or more independent centres; one pre-specified eye per patient; reference standard the consultant ERG report (Normal, Borderline, Abnormal); flagged = composite AMBER or RED.
- **Primary criteria:** sensitivity with lower 95% exact bound at least 0.85; specificity with lower 95% exact bound at least 0.75.
- **Sample size:** 120 Abnormal and 250 Normal patients.
- **Secondary:** weighted kappa; results by protocol, electrode, age group (18–35 against 36–80) and sex.
- **Documents:** `docs/regulatory/T4-A_Validation_Protocol_v2_0.pdf` and the T4-B to T4-F templates.

## Deployment thresholds (Phase B, classifiers)

Each threshold is judged on the lower bound of its 95% confidence interval, on external data (Chapter 16 §16.2 and §16.5):

| Metric | Threshold | If not met |
|:---|:---|:---|
| Stage 1 binary AUC | at least 0.94 | Not fit for use as a screening triage tool, however well Stage 2 performs |
| Stage 2 macro-AUC | at least 0.80 | Targeted data collection before deployment at external sites |
| Sensitivity, every disease class | at least 0.75 | Class flagged in the Model Card and excluded from clinical decision support |
| Brier score, every class | below the class's own frequency-only reference p(1 − p) | CALIBRATION_WARNING; the class probability is withheld until recalibration passes |

The Stage 1 operating point is set so that sensitivity on the validation data reaches at least 0.90.

## Data

- **Partitions** (Chapter 10, Table 10.5): a test set of 10% of patients, used once only; the development set is split into training (about 72% of all patients) and validation (about 18%) in each fold. All recordings of one patient stay in one partition.
- **Internal validation:** five-fold stratified cross-validation, split by patient (Chapter 16 §16.3).
- **Sample size** (Chapter 10): planning numbers for the deep-learning pathway are set by a floor, target and ceiling with a learning curve. For a regression-type Stage 1 model, the Riley et al. (2020) criteria give a planning minimum of 2,308 recordings (1,177 Normal, 1,131 Abnormal; Table 10.2), computed with pmsampsize (`chapters/Appendices/appendices.py`, §C.2).
- **Diagnosis:** every training label needs a primary diagnosis and at least one corroborating modality (Chapter 10, Table 10.1).

## External validation

- **Site:** an independent university clinic with an established ERG program, whose recording device is not represented in the training set (Chapter 16 §16.4).
- **Dataset:** at least 200 recordings with confirmed diagnoses across at least five of the six disease classes, under the retrospective anonymized data pathway.
- **Transfer:** de-identified feature files in the format of Appendix A §A.3, extracted at the center with the project's pipeline code. No raw signal files are transferred.
- **Device independence:** no external recording may come from a device model that contributes more than 5% of the training set. External centers carry a `center_id` that begins with `EXT_`, and the leakage check must PASS before any external result is reported.
- **Investigation trigger:** an external AUC more than 0.10 below the internal AUC after harmonization.

## Harmonization

Centralized processing applies identical filtering, normalization, spectrogram and feature code to every recording. ComBat (Johnson et al., 2007) then removes remaining device offsets (Chapter 16 §16.6):

- **Batch:** device manufacturer. **Preserved covariates:** age stratum and sex. Disease labels are never used.
- **Step 1:** the training devices are harmonized with each other, using the training data only.
- **Step 2:** an unseen device, such as the external one, is adjusted toward the harmonized training features, which stay unchanged.
- A feature that fails the harmonization check and cannot be harmonized linearly is excluded and reported as a deviation from the plan.

## After deployment

Chapter 17 §17.4 monitors the rolling 90-day AUC of reports whose true diagnosis is known:

- **Shewhart chart:** WARNING between 2σ and 3σ from the baseline mean, OUT_OF_CONTROL beyond 3σ. The baseline is the first 90 days of deployment; σ comes from 2000 bootstrap AUCs.
- **Page-Hinkley test:** flags a slow, sustained fall in the average AUC. An alarm starts a root-cause investigation and does not retrain the model automatically.
- **Revalidation:** every 12 months from first deployment, on the confirmed-label data of the preceding 12 months.

The code is in `chapters/ch16/chapter_16.py` and `chapters/ch17/chapter_17.py`.

## References

- Baker, R.A., et al. (2025). ISCEV standard full-field ERG reference limits from 407 healthy subjects. *Documenta Ophthalmologica*, 150, 47–64.
- Collins, G.S., et al. (2024). TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*, 385, e078378.
- Johnson, W.E., Li, C. and Rabinovic, A. (2007). Adjusting batch effects in microarray expression data using empirical Bayes methods. *Biostatistics*, 8(1), 118–127.
- Riley, R.D., et al. (2020). Calculating the sample size required for developing a clinical prediction model. *BMJ*, 368, m441.
