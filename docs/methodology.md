# Methodology: ERG Signal Processing and Classification

This document provides the mathematical and methodological foundations for the ERG Analysis API. All formulas and explanations are sourced directly from the ERG manuscript (Tavakoli, 2027) and the Blueprint API Action Plan.

## Table of Contents

1. [Z-Score Calculation and Traffic Light Thresholds](#z-score-calculation-and-traffic-light-thresholds)
2. [ISCEV Filter Specifications](#iscev-filter-specifications)
3. [STFT Spectrogram Parameters](#stft-spectrogram-parameters)
4. [Longitudinal Change Detection](#longitudinal-change-detection)
5. [SHAP Explainability](#shap-explainability)
6. [References to Source](#references-to-source)

---

## Z-Score Calculation and Traffic Light Thresholds

### Z-Score Formula

Source: Chapter 10, Equation 10.1; Blueprint Section 2.3

\[Z = \frac{x - \mu_{norm}}{\sigma_{norm}}\]

Where:
- \(x\) = patient's measured ERG parameter value (after device-relative normalization)
- \(\mu_{norm}\) = normative mean for the matching electrode type, protocol, and age group
- \(\sigma_{norm}\) = normative standard deviation for the same stratum

### Traffic Light Zones

| Zone | Z-Score Criterion | Clinical Meaning |
|------|-------------------|------------------|
| 🟢 **GREEN** | \|Z\| ≤ 2.0 | Within normal limits |
| 🟡 **AMBER** | 2.0 < \|Z\| ≤ 3.0 | Borderline abnormality |
| 🔴 **RED** | \|Z\| > 3.0 | Significant abnormality |

**Rationale for 2.0 SD Green boundary (Source: Chapter 1 §1.7):**

> *"The 2.0 SD Green boundary was chosen to prioritize sensitivity for early disease detection over specificity. At this threshold, approximately 5% of healthy subjects will receive an Amber classification (a false-positive rate of 5%). This is considered acceptable for a screening triage tool whose primary purpose is to ensure that no early disease case is missed."*

### Age-Stratified Reference Ranges

Source: Baker et al. (2025); Blueprint Section 2.3

| Age Group | Range | Stratum Label |
|-----------|-------|---------------|
| ≤35 years | Young adults | `le35` |
| 36–59 years | Middle-aged adults | `36to59` |
| ≥60 years | Older adults | `ge60` |

Z-scores are computed against the age-matched normative stratum. Using an age-mismatched reference range will produce systematically incorrect Traffic Light assignments.

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
| Oscillatory potentials (OP1–OP4) | 75–300 Hz |
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
| Overlap (noverlap) | 56 samples | 87.5% overlap, 4 ms hop size |
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
| Z-score and Traffic Light thresholds | Chapter 1 §1.7, Chapter 10 Equation 10.1, Blueprint §2.3 |
| Age-stratified reference ranges | Baker et al. (2025), Blueprint §2.3 |
| Device-relative normalization | Chapter 10 §10.3, Blueprint §4.5 Step 5 |
| ISCEV filter specifications | Chapter 5 §5.1, Blueprint §4.5 Step 2 |
| Frequency content of ERG signals | Chapter 5 §5.2 |
| STFT spectrogram parameters | Chapter 8, Blueprint §4.5 Step 3 |
| Longitudinal change detection | Chapter 15 Equations 15.1–15.3 |
| SHAP explainability | Chapter 14 |

**Full reference:** Tavakoli, H. (2027). *Hands-On Electroretinography in the Age of AI: A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*. Apress/Springer-Nature.

**Repository:** https://github.com/AI-Fairness-com/ERG-Analysis-API