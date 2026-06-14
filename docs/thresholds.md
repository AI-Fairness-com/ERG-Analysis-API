# Traffic Light and Statistical Thresholds in ERG Analysis API

## Overview

The ERG Analysis API uses a traffic light classification system (GREEN / AMBER / RED) to communicate the degree of deviation from age-stratified normative reference ranges. This document defines all thresholds used in the pipeline.

**Source:** Chapter 1 §1.7; Blueprint Section 2.3

---

## Traffic Light Z-Score Thresholds

| Color | Z-Score Criterion | Clinical Meaning | Action Required |
|-------|-------------------|------------------|-----------------|
| 🟢 **GREEN** | \|Z\| ≤ 2.0 | Within normal limits | No immediate action |
| 🟡 **AMBER** | 2.0 < \|Z\| ≤ 3.0 | Borderline abnormality | Specialist review recommended |
| 🔴 **RED** | \|Z\| > 3.0 | Significant abnormality | Urgent specialist review |

### Rationale for Thresholds

**Green/Amber boundary (\|Z\| = 2.0):** Prioritizes sensitivity for early disease detection. At this threshold, approximately 5% of healthy subjects will receive an Amber classification (false-positive rate of 5%). This is documented in the Model Card as an acceptable trade-off for a screening triage tool.

**Amber/Red boundary (\|Z\| = 3.0):** Minimizes false Red classifications in healthy subjects. At 3.0 SD, fewer than 0.3% of healthy subjects would receive a Red classification under a Gaussian distribution.

---

## Age-Stratified Reference Ranges

Source: Baker et al. (2025); Blueprint Section 2.3

| Age Group | Stratum Label | Sample Size (Baker et al. 2025) |
|-----------|---------------|--------------------------------|
| ≤35 years | `le35` | ~136 subjects |
| 36–59 years | `36to59` | ~135 subjects |
| ≥60 years | `ge60` | ~136 subjects |

**Total normative dataset:** 407 healthy adult subjects (Robson, Baker et al., 2025)

**Electrode types covered:** Silver thread (fornix) and Gold foil (transformed)

**Protocols covered:** All five ISCEV standard protocols (DA 0.01, DA 3.0, DA 10.0, LA 3.0, LA 30 Hz)

---

## Signal Quality Thresholds

Source: Chapter 2 §2.3; Blueprint Section 4.5, Step 1

### Electrode-Specific SNR Thresholds (Linear SNR)

| Electrode Type | PASS (SNR ≥) | WARNING (SNR) | FAIL (SNR <) |
|----------------|--------------|----------------|---------------|
| Contact lens | 8.0 | 4.0 – 7.9 | 4.0 |
| Gold foil | 6.0 | 3.0 – 5.9 | 3.0 |
| DTL fiber | 4.0 | 2.5 – 3.9 | 2.5 |
| Skin | 3.0 | 1.5 – 2.9 | 1.5 |

### SNR Formula

\[SNR = \frac{A_{signal}}{A_{noise}}\]

\[SNR_{dB} = 20 \times \log_{10}\left(\frac{A_{signal}}{A_{noise}}\right)\]

Where:
- \(A_{signal}\) = peak-to-trough amplitude of the ERG response (b-wave peak minus a-wave trough)
- \(A_{noise}\) = RMS of the pre-stimulus baseline (typically 0–100 ms)

### Sweep Rejection Rate Thresholds

Source: Chapter 2 §2.5

| Rejection Rate | Quality Flag | Action |
|----------------|--------------|--------|
| ≤ 20% | PASS | Continue processing |
| 20% – 40% | WARNING | Process with caveat; review recommended |
| > 40% | FAIL | Halt processing; return recording to operator |

---

## Longitudinal Change Detection Thresholds

Source: Chapter 15 §15.4–15.5

### Coefficient of Repeatability (CoR) by Parameter (DTL Fiber, DA 3.0)

| Parameter | CoR | Clinical Interpretation |
|-----------|-----|------------------------|
| DA 3.0 b-wave amplitude | 17.6 μV | Change > 17.6 μV is statistically significant |
| DA 3.0 b-wave implicit time | 2.4 ms | Change > 2.4 ms is statistically significant |
| LA 3.0 PhNR amplitude | 5.7 μV | Change > 5.7 μV is statistically significant |
| DA 3.0 OP2 amplitude | 2.8 μV | Change > 2.8 μV is statistically significant |
| LA 30 Hz flicker amplitude | 7.7 μV | Change > 7.7 μV is statistically significant |

*Note: CoR values are electrode-specific. These values are for DTL fiber electrodes. Contact lens and gold foil electrodes will have larger CoR values reflecting higher absolute amplitudes.*

### Change Flagging Zones

| Change Zone | Criterion | Flag | Recommended Action |
|-------------|-----------|------|---------------------|
| GREEN (No significant change) | \|Δ\| < MDC95 | NO_CHANGE | Routine follow-up |
| AMBER (Borderline) | MDC95 ≤ \|Δ\| < CoR | BORDERLINE_CHANGE | Repeat recording in 3–6 months |
| RED (Significant progression) | \|Δ\| ≥ CoR (reduction) | SIGNIFICANT_PROGRESSION | Urgent specialist review (within 4 weeks) |
| BLUE (Significant improvement) | \|Δ\| ≥ CoR (increase) | SIGNIFICANT_IMPROVEMENT | Document and review in clinical context |

### Disease-Specific Milestone Thresholds

Source: Chapter 15 §15.5.3

| Disease | Milestone | Threshold |
|---------|-----------|-----------|
| Retinitis Pigmentosa | 50% amplitude reduction | Current amplitude < 50% of baseline (regardless of CoR) |
| Hydroxychloroquine toxicity | Green-to-Amber crossing | Any parameter crossing \|Z\| = 2.0 SD threshold |
| Diabetic Retinopathy (surveillance) | OP2 delay confirmation | OP2 implicit time increase confirmed on two consecutive visits |

---

## Device-Relative Normalization Methods

Source: Chapter 10 §10.3; Blueprint §4.5 Step 5

| Method | Description | When to Use |
|--------|-------------|-------------|
| **Method 1** | Internal calibration signal normalization | Device provides reference calibration flash |
| **Method 2** | Laboratory normative scaling | Laboratory has its own normative reference data |
| **Method 3** | ISCEV relative criteria only | Fallback when Methods 1 and 2 unavailable (carries mandatory caveat) |

---

## Flash Duration Correction for Implicit Times

Source: Blueprint §4.5, Step 4; ISCEV 2022 (Page 10, Col 1, Para 2)

For flashes of duration ≥5 ms (e.g., LED stimulators), implicit times are measured from the **flash MIDPOINT**, not from flash onset.

**Correction formula:**

\[ImplicitTime_{corrected} = ImplicitTime_{measured} - \frac{FlashDuration}{2}\]

This correction is applied automatically when `flash_duration_ms` is provided in the input CSV. The correction is documented in the Layer 4 audit log.

---

## Calibration Metrics (Brier Score)

Source: Chapter 14 §14.5.3; Chapter 16 §16.5.3

| Brier Score | Calibration Quality | Action |
|-------------|---------------------|--------|
| < 0.10 | Excellent | PASS |
| 0.10 – 0.20 | Good | PASS |
| 0.20 – 0.25 | Acceptable | PASS with caveat |
| ≥ 0.25 | Poor | CALIBRATION_WARNING; probability withheld from clinical report |

---

## Validation Performance Thresholds

Source: Chapter 16 §16.5; Blueprint Section 5.1

| Metric | Deployment Threshold | Rationale |
|--------|---------------------|-----------|
| Stage 1 binary AUC | ≥ 0.90 on external validation | Screening gate: missing a true abnormality is unacceptable |
| Stage 2 macro-AUC | ≥ 0.80 on external validation | Minimum clinically actionable discrimination |
| Per-class sensitivity | ≥ 0.75 for all classes | Classes below this threshold flagged in Model Card |
| Brier Score (macro) | < 0.25 | Calibration quality minimum |

---

## References

- Baker, R.A., Leo, S.M., Clowes, W.I.N., et al. (2025). ISCEV standard full-field ERG reference limits from 407 healthy subjects. *Documenta Ophthalmologica*, 150, 47–64.
- Robson, A.G., Frishman, L.J., Grigg, J., et al. (2022). ISCEV standard for full-field clinical electroretinography (2022 update). *Documenta Ophthalmologica*, 144(3), 165–177.
- Tavakoli, H. (2027). *Hands-On Electroretinography in the Age of AI*. Apress/Springer-Nature.