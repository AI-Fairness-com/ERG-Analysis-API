# Methodology: ERG Signal Processing and Classification

This document provides the mathematical and methodological foundations for the ERG Analysis API. All formulas and explanations are sourced directly from the ERG manuscript (Tavakoli, 2027) and the Blueprint API Action Plan.

*Feature Coverage section reconciled against the pipeline's actual feature set on 2026-09-07, after a same-day self-correction (see `docs/CHANGELOG.md`) restored the full 28-feature design following a brief, mistaken reduction to 11 features earlier that day.*

## Table of Contents

1. [Traffic Light Zones](#traffic-light-zones)
2. [ISCEV Filter Specifications](#iscev-filter-specifications)
3. [STFT Spectrogram Parameters](#stft-spectrogram-parameters)
4. [Longitudinal Change Detection](#longitudinal-change-detection)
5. [SHAP Explainability](#shap-explainability)
6. [References to Source](#references-to-source)

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

### Parameters with Traffic Light zones

The zones cover the a-wave and b-wave amplitudes and peak times of each ISCEV protocol, and the LA 30 Hz flicker amplitude and peak time, because Baker et al. (2025) publish limits for these. Every other feature the pipeline extracts is reported as a measured value and does not contribute to the Traffic Light. This includes the b/a ratio, the OP amplitudes and OP2 implicit time, the PhNR amplitude, and the nonlinear, DWT, derivative, and frequency-domain features of Chapter 9. Zoning them would need reference limits measured with this pipeline's own methods, which do not yet exist.

### Device-Relative Normalization

Source: Chapter 10 §10.3; Blueprint Section 4.5, Step 5

Three normalization methods are available:

| Method | Description | When to Use |
|--------|-------------|-------------|
| **Method 1** | Internal calibration signal normalization | Device provides reference calibration flash |
| **Method 2** | Laboratory normative scaling (amplitude as % of lab's normative mean) | Laboratory has established its own reference data |
| **Method 3** | ISCEV relative criteria only | Fallback when Methods 1 and 2 unavailable (carries mandatory caveat) |

---

## ISCEV Filter Specifications

Source: Chapter 5 §5.1; Blueprint Section 4.5, Step 2

### Bandpass Filter Parameters

| Protocol | High-Pass Cutoff | Low-Pass Cutoff | Filter Order |
|----------|------------------|-----------------|--------------|
| DA 0.01 | 0.3 Hz | 300 Hz | 4th order Butterworth |
| DA 3.0 | 0.3 Hz | 300 Hz | 4th order Butterworth |
| DA 10.0 | 0.3 Hz | 300 Hz | 4th order Butterworth |
| LA 3.0 | 0.3 Hz | 300 Hz | 4th order Butterworth |
| LA 30 Hz | 0.3 Hz | 300 Hz | 4th order Butterworth |

### Frequency Content of ERG Signals

Source: Chapter 5 §5.2

| ERG Component | Dominant Frequency Band |
|---------------|-------------------------|
| a-wave (trough and descent) | 5–30 Hz |
| b-wave (peak and ascent) | 5–40 Hz |
| Oscillatory potentials (OP2–OP4) | 75–300 Hz |
| PhNR (photopic negative response) | 0.3–5 Hz |
| 30 Hz flicker steady-state | 30 Hz and harmonics (60, 90, 120 Hz) |

### Notch Filter Policy

Source: Chapter 5 §5.1.4; Blueprint Section 4.5, Step 2

Per ISCEV 2022 guidance, **notch filters are NOT RECOMMENDED for routine clinical use** as they distort the ERG waveform. If post-acquisition removal is clinically justified (e.g., high-noise screening environment), explicit user consent is required and output metadata is flagged accordingly.

---

## STFT Spectrogram Parameters

Source: Chapter 8; Blueprint Section 4.5, Step 3

### Default Configuration (Deep Learning Pathway)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Window function | Hamming | Lowest leakage among common windows; empirically validated (Albasu et al., 2024) |
| Window size (nperseg) | 64 samples | 32 ms time resolution at 2000 Hz sampling |
| Overlap (noverlap) | 58 samples | 90.625% overlap, 3 ms hop size |
| Sampling rate (fs) | 2000 Hz | Safety margin above Nyquist limit for 300 Hz OP band |
| Frequency range | 0–300 Hz | ISCEV 2022 specified passband |
| Output resolution | 224 × 224 pixels | Compatible with Vision Transformer (ViT) input |


### STFT Mathematical Definition

Source: Chapter 8, Equation 8.1

\[STFT(\tau, f) = \int x(t) \cdot w(t - \tau) \cdot e^{-j2\pi ft} dt\]

Where:
- \(x(t)\) is the input ERG signal in the time domain
- \(w(t - \tau)\) is the window function centred at time \(\tau\)
- \(e^{-j2\pi ft}\) is the complex exponential at frequency \(f\)
- The spectrogram is the squared magnitude \(|STFT(\tau, f)|^2\)

### Alternative Window Configurations (Classical ML Pathway)

Source: Albasu et al. (2024); Blueprint Section 8

| Window Type | Best For | Performance |
|-------------|----------|-------------|
| **Hamming** | Deep learning (ViT) | AUC = 0.888 (primary pathway) |
| **Boxcar** | Classical ML (Random Forest) | Accuracy = 70.83%, AUC = 0.722 |
| **Bartlett** | Classical ML (Random Forest) | Accuracy = 70.83%, AUC = 0.722 |

---

## Longitudinal Change Detection

Source: Chapter 15, Equations 15.1–15.3

### Limits of Agreement (LoA)

\[LoA = \bar{d} \pm 1.96 \times SD_d\]

Where:
- \(\bar{d}\) = mean difference between two recordings
- \(SD_d\) = standard deviation of the differences

### Coefficient of Repeatability (CoR)

\[CoR = 1.96 \times \sqrt{2} \times s_w\]

Where:
- \(s_w\) = within-subject standard deviation

The CoR is the minimum detectable change threshold at 95% confidence. A change exceeding the CoR in the direction of deterioration is flagged as statistically significant progression.

### Minimum Detectable Change (MDC95)

\[MDC95 = 1.96 \times \sqrt{2} \times SEM\]

Where:
- \(SEM\) = Standard Error of Measurement = \(s_w / \sqrt{n}\)
- \(n\) = number of repeated measurements per subject

For test-retest data (n = 2): \(MDC95 = CoR\)

### Change Flagging Rules

Source: Chapter 15 §15.5

| Change Zone | Criterion | Flag |
|-------------|-----------|------|
| NO_CHANGE | \|Δ\| < MDC95 | No significant change |
| BORDERLINE | MDC95 ≤ \|Δ\| < CoR | Borderline change; repeat recording recommended |
| PROGRESSION | \|Δ\| ≥ CoR (reduction) | Significant progression; urgent review |
| IMPROVEMENT | \|Δ\| ≥ CoR (increase) | Significant improvement; document response |

---

## SHAP Explainability

Source: Chapter 14

### Three-Level SHAP Framework

| Level | Method | Input | Output |
|-------|--------|-------|--------|
| **Level 1** | TreeSHAP (shap.TreeExplainer) | Random Forest feature vector | Ranked bar chart of per-parameter contributions |
| **Level 2** | GradientSHAP (shap.GradientExplainer) | ViT Small spectrogram | Saliency overlay on time-frequency spectrogram |
| **Level 3** | Plain-language translation | SHAP values → sentence mapping table | Clinician-readable narrative |

### SHAP Value Interpretation

Source: Chapter 14 §14.2.3

| SHAP Value Magnitude | Clinical Significance | Reporting Action |
|----------------------|----------------------|------------------|
| \|SHAP\| ≥ 0.20 | Dominant contributor | Named first in plain-language narrative |
| 0.10 ≤ \|SHAP\| < 0.20 | Significant contributor | Named in plain-language narrative |
| 0.05 ≤ \|SHAP\| < 0.10 | Supporting contributor | Shown in waterfall chart; grouped in narrative |
| \|SHAP\| < 0.05 | Negligible contribution | Shown in waterfall chart; not mentioned in narrative |

---

## References to Source

All content in this document is derived from:

| Topic | Source |
|-------|--------|
| Traffic Light zones | Chapter 10 §10.4 (Equation 10.2, Table 10.4); Baker et al. (2025), Tables 2, 4 and 5 |
| Age-stratified reference ranges | Baker et al. (2025), Blueprint §2.3 |
| Device-relative normalization | Chapter 10 §10.3, Blueprint §4.5 Step 5 |
| ISCEV filter specifications | Chapter 5 §5.1, Blueprint §4.5 Step 2 |
| Frequency content of ERG signals | Chapter 5 §5.2 |
| STFT spectrogram parameters | Chapter 8, Blueprint §4.5 Step 3 |
| Longitudinal change detection | Chapter 15 Equations 15.1–15.3 |
| SHAP explainability | Chapter 14 |

**Full reference:** Tavakoli, H. (2027). *Hands-On Electroretinography in the Age of AI: A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*. Apress/Springer-Nature.

**Repository:** https://github.com/AI-Fairness-com/ERG-Analysis-API
