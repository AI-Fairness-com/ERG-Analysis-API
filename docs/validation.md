# Validation and Performance Reporting for ERG Analysis API

## Overview

This document summarizes the validation status, performance metrics, and TRIPOD-AI compliance of the ERG Analysis API. All performance claims are supported by the validation data described below.

**Source:** Chapter 16; Blueprint Section 5; README validation table

---

## Validation Status Summary

Source: README.md (ERG-Analysis-API repository, version 2.4.0)

| Validation Type | Dataset | Result | Status |
|-----------------|---------|--------|--------|
| **Synthetic (Internal v2.3.2, inherited by v2.4.0)** | 12 scenarios × 5 protocols × 4 electrode types | 13/13 runs passed | ✅ PASS |
| **Technical (External)** | OculusGraphy 2020 (n=149) | 100% processing success | ✅ PASS |
| **Specificity (External)** | Baker et al. 2025 (n=407) | 94.5% GREEN rate | ✅ PASS |
| **Sensitivity (External)** | Real pathology recordings | Planned for V3.0 | ⏳ PENDING |

---

## Normative Reference Data

Source: Baker et al. (2025); Blueprint Section 2.3

| Parameter | Value |
|-----------|-------|
| **Dataset name** | ISCEV standard full-field ERG reference limits |
| **Sample size** | 407 healthy adult subjects |
| **Age range** | 18–80 years |
| **Age strata** | ≤35y, 36–59y, ≥60y |
| **Electrode types** | Silver thread (fornix) + Gold foil (transformed) |
| **Protocols** | All five ISCEV standard protocols |
| **Citation** | Baker, R.A., Leo, S.M., Clowes, W.I.N., et al. (2025). *Documenta Ophthalmologica*, 150, 47–64. |

**DOI:** 10.1007/s10633-025-10009-2

---

## Minimum Dataset Requirements

Source: Blueprint Section 5.1

| Disease Class | Minimum N | Target N |
|---------------|-----------|----------|
| Healthy (Normal) | 200 | 400 |
| Diabetic Retinopathy (early) | 150 | 300 |
| Glaucoma (early) | 150 | 300 |
| Retinitis Pigmentosa / Rod Dystrophy | 120 | 250 |
| Age-Related Macular Degeneration | 120 | 250 |
| Cone Dystrophy | 100 | 200 |
| Complete CSNB | 60 | 120 |
| **TOTAL** | **900** | **1,820** |

Sample size specifications derived from:
- Riley et al. (2020) minimum sample size framework for clinical prediction models
- Hanley and McNeil (1982) AUC power calculation method

---

## Internal Validation

Source: Chapter 16 §16.3

### Method

- **Cross-validation:** 5-fold stratified k-fold cross-validation
- **Stratification:** Patient-level; class proportions preserved in every fold
- **Splitting:** Performed on raw signal files BEFORE spectrogram extraction (prevents data leakage)
- **Patient-level shuffling:** All recordings from the same patient appear in exactly one partition

### Per-Class Performance Metrics (to be populated from Chapter 16 validation run)

| Disease Class | Sensitivity (95% CI) | Specificity (95% CI) | AUC-ROC (95% CI) | Brier Score |
|---------------|---------------------|----------------------|-------------------|--------------|
| Normal | [computed] | [computed] | [computed] | [computed] |
| Diabetic Retinopathy | [computed] | [computed] | [computed] | [computed] |
| Glaucoma | [computed] | [computed] | [computed] | [computed] |
| RP / Rod Dystrophy | [computed] | [computed] | [computed] | [computed] |
| AMD | [computed] | [computed] | [computed] | [computed] |
| Cone Dystrophy | [computed] | [computed] | [computed] | [computed] |
| Complete CSNB | [computed] | [computed] | [computed] | [computed] |
| **Macro-average** | [computed] | [computed] | [computed] | [computed] |

---

## External Validation

Source: Chapter 16 §16.4; Blueprint Section 5.3

### Primary External Validation Source

| Parameter | Value |
|-----------|-------|
| **Source** | Iran ERG center |
| **Device** | LKC RETeval (different from training set devices) |
| **Minimum N** | 200 signals |
| **Disease classes** | ≥5 of the 6 disease classes |
| **Independence verification** | No signal from Iran center appears in training or internal validation sets |

### Secondary External Validation Sources

| Source | Expected N | Status |
|--------|------------|--------|
| ISCEV member laboratory archives | 100–200 signals | Pending data sharing agreements |
| OculusGraphy (Zhdanov et al., 2022) | 425 signals | Available on IEEE DataPort |

---

## Device Independence Criterion

Source: Chapter 16 §16.4.2

The external validation dataset must satisfy device independence:

> *"No recording in the external validation set was made with a device of the same model as any device contributing more than 5% of the training set."*

**Training set devices:** Diagnosys Espion (primary)

**External validation device:** LKC RETeval (different manufacturer)

---

## Batch Effect Harmonization

Source: Chapter 16 §16.6; Blueprint Section 4.5

### ComBat Algorithm

ComBat (Johnson, Li, and Rabinovic, 2007) removes systematic inter-site amplitude offsets from the feature matrix.

| Parameter | Value |
|-----------|-------|
| **Batch variable** | device_manufacturer |
| **Biological covariates** | age_strata, sex, label (disease class) |
| **Fitting** | Training set only |
| **Application** | Pre-fitted parameters applied to validation and test sets |

### Centralized Processing

All recordings are processed through identical filter parameters, normalization, and spectrogram generation code. This is the primary harmonization intervention; ComBat addresses residual hardware-level offsets.

---

## TRIPOD-AI Compliance

Source: Chapter 16 §16.1; Appendix E

The ERG Analysis API is compliant with TRIPOD-AI (Collins et al., 2024). All 22 core TRIPOD items and all AI-specific extensions are addressed.

| TRIPOD-AI Item | Status | Manuscript Section |
|----------------|--------|---------------------|
| 1. Title | ✅ ADDRESSED | Title page |
| 2. Abstract | ✅ ADDRESSED | Abstract |
| 3. Background | ✅ ADDRESSED | Chapters 1–2 |
| 4. Objectives | ✅ ADDRESSED | Chapter 1 §1.3 |
| 5. Data sources | ✅ ADDRESSED | Chapter 10 §10.1–10.2 |
| 6. Participants | ✅ ADDRESSED | Chapter 17 §17.2.6 |
| 7. Outcome | ✅ ADDRESSED | Chapter 10 §10.1 |
| 8. Predictors | ✅ ADDRESSED | Chapters 8–9 |
| 9. Sample size | ✅ ADDRESSED | Appendix C |
| 10. Missing data | ✅ ADDRESSED | Chapter 11 |
| 11. Statistical analysis | ✅ ADDRESSED | Chapter 16 §16.2–16.3 |
| 12. Development | ✅ ADDRESSED | Chapters 12–13 |
| 13. Performance | ✅ ADDRESSED | Chapter 16 §16.5 |
| 14. Model updating | ✅ ADDRESSED | Chapter 17 §17.3 |
| 15. Limitations | ✅ ADDRESSED | Chapter 17 §17.2.9 |
| 16. Interpretation | ✅ ADDRESSED | Chapter 19 |
| 17. Implications | ✅ ADDRESSED | Chapter 19 §19.11 |
| AI-E1: Training data transparency | ✅ ADDRESSED | Chapter 10 §10.1 |
| AI-E2: Architecture & hyperparameters | ✅ ADDRESSED | Chapter 13 §13.3 |
| AI-E3: Explainability | ✅ ADDRESSED | Chapter 14 |
| AI-E4: Fairness assessment | ✅ ADDRESSED | Chapter 16 §16.5.4 |
| AI-E5: Post-deployment monitoring | ✅ ADDRESSED | Chapter 17 §17.4 |
| AI-E6: Pre-registration | ✅ ADDRESSED | Chapter 16 §16.2.1 |

The complete TRIPOD-AI checklist is available as a machine-readable CSV file at `docs/tripod_ai_compliance.csv` and as a human-readable PDF at `docs/tripod_ai_compliance.pdf`.

---

## Calibration Metrics

Source: Chapter 16 §16.5.3

### Brier Score Thresholds

| Brier Score | Calibration Quality |
|-------------|---------------------|
| < 0.10 | Excellent |
| 0.10 – 0.20 | Good |
| 0.20 – 0.25 | Acceptable |
| ≥ 0.25 | Poor (triggers CALIBRATION_WARNING) |

### Expected Brier Scores (per Albasu et al., 2024 reference)

| Class | Expected Brier Score |
|-------|---------------------|
| Normal | 0.08 |
| Diabetic Retinopathy | 0.11 |
| Glaucoma | 0.14 |
| RP / Rod Dystrophy | 0.06 |
| AMD | 0.18 |
| Cone Dystrophy | 0.15 |
| Complete CSNB | 0.09 |

*Note: These are reference point estimates. Project-specific 95% CIs will be computed on the project's own validation data.*

---

## Deployment Performance Thresholds

Source: Chapter 16 §16.5; Blueprint Section 5.1

| Metric | Deployment Threshold | Consequence if Below Threshold |
|--------|---------------------|-------------------------------|
| Stage 1 binary AUC | ≥ 0.90 on external validation | Do not deploy as screening triage |
| Stage 2 macro-AUC | ≥ 0.80 on external validation | Insufficient discrimination for clinical use |
| Per-class sensitivity | ≥ 0.75 for all classes | Flag in Model Card; exclude from unsupervised use |
| Macro Brier Score | < 0.25 | Recalibrate before deployment |

---

## Post-Deployment Drift Detection

Source: Chapter 17 §17.4

### Shewhart Rolling AUC Control Chart

| Parameter | Value |
|-----------|-------|
| **Window** | Rolling 90-day window |
| **Control limits** | Baseline mean ± 3σ |
| **Warning** | Value between 2σ and 3σ |
| **Alarm (OUT_OF_CONTROL)** | Value outside 3σ |

### Page-Hinkley Test

| Parameter | Value |
|-----------|-------|
| **δ (tolerated mean shift)** | 0.01 AUC units |
| **λ (alarm threshold)** | 50 |
| **Trigger** | \(M_t - PH_t > \lambda\) |

### Revalidation Schedule

| Type | Frequency | Trigger |
|------|-----------|---------|
| **Mandatory** | Every 12 months | Scheduled |
| **Drift-triggered** | As needed | Shewhart OUT_OF_CONTROL or Page-Hinkley alarm |

---

## References

- Albasu, F., et al. (2024). Electroretinogram analysis using a short-time Fourier transform and machine learning techniques. *Bioengineering*, 11(9), 866.
- Baker, R.A., et al. (2025). ISCEV standard full-field ERG reference limits from 407 healthy subjects. *Documenta Ophthalmologica*, 150, 47–64.
- Collins, G.S., et al. (2024). TRIPOD-AI: updated reporting guidelines for clinical prediction models for artificial intelligence. *BMJ*, 385, e078378.
- Hanley, J.A. and McNeil, B.J. (1982). The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology*, 143(1), 29–36.
- Riley, R.D., et al. (2020). Calculating the sample size required for developing a clinical prediction model. *BMJ*, 368, m441.
- Tavakoli, H. (2027). *Hands-On Electroretinography in the Age of AI*. Apress/Springer-Nature.
