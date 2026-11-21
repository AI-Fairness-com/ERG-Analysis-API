# Traffic Light and Statistical Thresholds in the ERG Analysis API

## Overview

The ERG Analysis API assigns each ERG parameter a Traffic Light zone against the age-specific percentile reference limits of Baker et al. (2025). This document defines the thresholds used in the pipeline.

---

## Traffic Light Zones

Source: Chapter 10 §10.4, Equation 10.2 and Table 10.4; Baker et al. (2025), Tables 4 and 5

Each ERG parameter is compared with the reference limits for its protocol and age group. The limits are the 2.5th percentile (L) and the 97.5th percentile (U) of healthy values, so 95% of healthy people fall between them. Each limit has a 90% confidence interval. L_lo is the lower bound of the interval of L, and U_hi is the upper bound of the interval of U.

| Zone | Amplitude | Implicit time | Recommended action |
|------|-----------|---------------|--------------------|
| 🟢 **GREEN** | L ≤ x ≤ U | L ≤ x ≤ U | No immediate action. Routine follow-up at the scheduled interval. |
| 🟡 **AMBER** | L_lo ≤ x < L | U < x ≤ U_hi | Flag for clinical review. Consider a repeat ERG to confirm reproducibility. |
| 🔴 **RED** | x < L_lo | x > U_hi | Prompt clinical review and diagnostic follow-up. |
| 🔵 **ATYPICAL DIRECTION** | x > U | x < L | Check the recording conditions and repeat the ERG before any diagnostic follow-up. |
| ⬜ **UNAVAILABLE** | electrode without limits | electrode without limits | Manual interpretation with laboratory-specific limits. |

The Green/Amber boundaries are the reference limits themselves, which favors sensitivity: about 5% of healthy people fall outside the limits for any single parameter, about half on each side. The Amber/Red boundaries are the outer bounds of the 90% confidence intervals, a design choice of this project, so that a value is Red only when it lies outside the limit even after allowing for how precisely the limit was estimated.

A value on the side opposite to disease, an enlarged amplitude or a shortened implicit time, is labeled ATYPICAL DIRECTION, not Amber or Red. Pigment, pupil size, media opacity, and recording conditions can all shift values this way (Chapter 10 §10.4).

The composite Traffic Light of a recording is its most severe zone: RED, then AMBER, then ATYPICAL DIRECTION, then GREEN. The b/a ratio and the PhNR amplitude have no published limits; they are reported as measured values and are not zoned.

### Electrodes

The limits are for silver thread electrodes in the lower fornix (DTL fiber). DTL fiber values are compared directly. Gold foil amplitudes are first converted to silver thread equivalents with the linear model of Baker et al. (2025), Table 2 (silver thread = slope × gold foil + intercept); gold foil peak times are compared without adjustment. No limits are held for contact lens or skin electrodes, so their zones are UNAVAILABLE.

### Reference limits (Baker et al., 2025)

Values are L–U, with L_lo and U_hi in brackets, for the three age groups. They are stored in `data/samples/normative_data_baker2025.json` (schema 2.0) together with both confidence intervals, the sample sizes, and the gold foil model.

**Amplitude (µV), Table 5**

| Component | ≤35 years | 36–59 years | ≥60 years |
|---|---|---|---|
| DA 0.01 b-wave | 138–297 (L_lo 130, U_hi 319) | 115–279 (L_lo 102, U_hi 315) | 107–288 (L_lo 100, U_hi 290) |
| DA 3.0 a-wave | 119–238 (L_lo 109, U_hi 261) | 100–226 (L_lo 90, U_hi 239) | 80–220 (L_lo 72, U_hi 234) |
| DA 3.0 b-wave | 191–404 (L_lo 178, U_hi 421) | 167–377 (L_lo 163, U_hi 469) | 162–407 (L_lo 151, U_hi 458) |
| DA 10.0 a-wave | 136–274 (L_lo 130, U_hi 283) | 124–277 (L_lo 118, U_hi 384) | 101–253 (L_lo 97, U_hi 280) |
| DA 10.0 b-wave | 202–409 (L_lo 192, U_hi 413) | 191–387 (L_lo 171, U_hi 481) | 177–414 (L_lo 170, U_hi 450) |
| LA 3.0 a-wave | 12–43 (L_lo 11, U_hi 49) | 13–40 (L_lo 8, U_hi 55) | 12–35 (L_lo 12, U_hi 41) |
| LA 3.0 b-wave | 73–227 (L_lo 54, U_hi 260) | 64–172 (L_lo 52, U_hi 247) | 49–153 (L_lo 45, U_hi 192) |
| LA 30 Hz flicker peak | 50–166 (L_lo 41, U_hi 187) | 45–140 (L_lo 41, U_hi 175) | 38–116 (L_lo 36, U_hi 160) |

**Peak time (ms), Table 4**

| Component | ≤35 years | 36–59 years | ≥60 years |
|---|---|---|---|
| DA 0.01 b-wave | 72–99.5 (L_lo 66.5, U_hi 106) | 77.5–107.5 (L_lo 73, U_hi 118.5) | 78–115 (L_lo 77.5, U_hi 116) |
| DA 3.0 a-wave | 13.5–16 (L_lo 13, U_hi 17) | 14.5–17 (L_lo 14.5, U_hi 17.5) | 14.5–18 (L_lo 14, U_hi 18.5) |
| DA 3.0 b-wave | 45.5–58.5 (L_lo 42.5, U_hi 60) | 46.5–59.5 (L_lo 45, U_hi 59.5) | 46.5–58 (L_lo 45.5, U_hi 60) |
| DA 10.0 a-wave | 10–14.5 (L_lo 10, U_hi 14.5) | 11–15 (L_lo 10.5, U_hi 16.5) | 11.5–15.5 (L_lo 11, U_hi 16.5) |
| DA 10.0 b-wave | 47–59.5 (L_lo 46, U_hi 60) | 47–59.5 (L_lo 46, U_hi 60) | 47–59.5 (L_lo 46, U_hi 60) |
| LA 3.0 a-wave | 13–15.5 (L_lo 13, U_hi 15.5) | 13–15.5 (L_lo 13, U_hi 16) | 13–15.5 (L_lo 12.5, U_hi 16.5) |
| LA 3.0 b-wave | 27–31.5 (L_lo 26.5, U_hi 32) | 27–31.5 (L_lo 26.5, U_hi 32) | 27.5–32.5 (L_lo 26.5, U_hi 33) |
| LA 30 Hz flicker peak | 24–28 (L_lo 24, U_hi 28) | 24–29.5 (L_lo 24, U_hi 30.5) | 24.5–30.5 (L_lo 24, U_hi 31) |

DA 10 b-wave timing has one set of limits for all ages. For the DA 10 a-wave amplitude at 36–59 years, Table 5 prints the upper-limit interval as 257–384 with a proportion of 0.18, which implies about 284; the printed value is kept, and it does not affect any zone, because an amplitude above U is ATYPICAL DIRECTION. The test `T-LIM-03` in `tests/test_pipeline.py` recomputes every zone printed in the Chapter 19 case tables from these limits.

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
| Hydroxychloroquine toxicity | Green-to-Amber crossing | Any parameter moving from GREEN to AMBER against its reference limits |
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