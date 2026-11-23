# Methodology: ERG Signal Processing and Classification

This document summarizes the methods of the ERG Analysis API. Every rule and value comes from *Hands-On Electroretinography in the Age of AI* (Tavakoli, Apress, forthcoming); the section numbers point to the book.

## Contents

1. [Traffic Light Zones](#traffic-light-zones)
2. [Device-Relative Normalization](#device-relative-normalization)
3. [Filtering](#filtering)
4. [STFT Spectrogram](#stft-spectrogram)
5. [Serial Change Detection](#serial-change-detection)
6. [SHAP Explainability](#shap-explainability)

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

**Who is behind the limits.** Baker et al. released their reference data with the paper (Mendeley Data, DOI [10.17632/kcptb9jrf5.1](https://doi.org/10.17632/kcptb9jrf5.1)). Of the 407 reference subjects, 353 were aged 18 to 80, 50 were children aged 7 to 17, and 4 were aged 83 to 86. All 50 children are in the ≤35 group, about 37% of its 135 subjects; the 4 oldest are in the ≥60 group. This project uses the published limits unchanged, so that they remain citable and match the pre-registered analysis plan. Restricting use to adults aged 18 to 80 is this project's choice, not a limit set by Baker et al., so a patient aged 18 to 35 is compared with limits that partly reflect children's ERGs. Limits recalculated from the adults aged 18 to 35 alone would rest on only 77 to 84 subjects per parameter, below the more than 120 in each published group, so they are not used (Chapter 10 §10.4).

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

---

## Device-Relative Normalization

Source: Chapter 10 §10.3

| Method | Formula or basis | When used |
|--------|------------------|-----------|
| Method 1: internal calibration signal | A_measured / A_calibration | A calibration signal is recorded in the same session and channel, with the same electrodes |
| Method 2: laboratory normative scaling | A_measured / µ_norm(electrode, protocol, age group) | The site has its own normative data, or data from an identical setup. The main method for the project's training data |
| Method 3: project-defined electrode-amplitude hierarchy | Amplitude relative to a reference value for its electrode type | Neither a calibration signal nor laboratory norms are available, for example at a new site |

---

## Filtering

Source: Chapter 5, Table 5.1

| Setting | ISCEV | This pipeline |
|---------|-------|---------------|
| High-pass corner, standard responses | 0.3 Hz or lower | 0.3 Hz |
| Low-pass corner, standard responses | 300 Hz or higher | 300 Hz |
| OP band | 75 Hz to 300 Hz or higher | 75 to 300 Hz |
| PhNR band | 0.3 Hz or lower to at least 300 Hz | 0.3 to 300 Hz |
| Filter roll-off | Not standardized | Fourth-order Butterworth |
| Notch filter | Should not be used | Off by default; on request only |
| Sampling rate | 1000 Hz or higher | 2000 Hz |
| Pre-flash baseline | At least 20 ms | 100 ms (Chapter 2) |

Stored recordings are filtered forward and backward (zero phase). Before a notch is considered, `detect_mains_interference()` reports a peak at the mains frequency more than 6 dB above its surroundings. The code is in `chapters/ch05/filtering/`.

---

## STFT Spectrogram

Source: Chapter 8 (§8.2.3, Tables 8.1 and 8.2)

| Setting | Value | Reason |
|---------|-------|--------|
| Window function | Hamming | Peak side lobe −43 dB with adequate frequency resolution; the highest AUC of eight windows for a ViT Small on ERG spectrograms (Albasu et al., 2024) |
| Window size (nperseg) | 64 samples (32 ms at 2000 Hz) | Its 3 dB width (about 41 Hz) separates the b-wave and OP bands |
| Overlap (noverlap) | 32 samples (50%), a 16 ms hop | The smallest standard overlap that still gives a usable image |
| Frequency range kept | 0 to 300 Hz | The ISCEV passband: 10 frequency rows |
| Output | 224 × 224 pixels | The input size of the ViT, reached by bicubic resizing of the 10 × 33 grid of a 500 ms sweep |

Each spectrogram is converted to dB, z-scored on its own mean and clipped at ±3 standard deviations before resizing. For classical machine learning, the Bartlett or Boxcar window is used, and four statistics of the whole spectrogram (maximum, minimum, median and mean) form the feature vector (§8.4.2). The settings are in `STFT_CONFIG` in `api/erg_v2_5_0.py` and in `chapters/ch08/chapter_8.py`.

---

## Serial Change Detection

Source: Chapter 15 (Tables 15.2 and 15.3)

- **Limits of agreement:** mean difference ± 1.96 × SD of the differences (Bland and Altman, 1986).
- **Coefficient of repeatability:** CoR = 1.96 × √2 × s_w, where s_w is the within-subject standard deviation.
- **Minimum detectable change:** the standard error of measurement equals s_w (Weir, 2005), so for two recordings the MDC₉₅ equals the CoR. The CoR is therefore the single change threshold.
- Amplitudes are compared on the log10 scale and reported as a percent change.

| Change zone | Criterion | Flag |
|-------------|-----------|------|
| Green: no significant change | \|Δ\| < CoR | NO_CHANGE |
| Red: significant progression | \|Δ\| ≥ CoR (amplitude fall or longer implicit time) | SIGNIFICANT_PROGRESSION |
| Blue: significant improvement | \|Δ\| ≥ CoR (amplitude rise or shorter implicit time) | SIGNIFICANT_IMPROVEMENT |

Published CoR values are in `docs/thresholds.md`; the code is in `chapters/ch15/chapter_15.py`.

---

## SHAP Explainability

Source: Chapter 14 (Table 14.1)

| Level | Method | Output |
|-------|--------|--------|
| Level 1 | TreeSHAP on the Random Forest feature vector | Waterfall chart of each feature's contribution |
| Level 2 | GradientExplainer on the 330 time-frequency cells of the ViT spectrogram | Saliency map, summarized by named ERG component |
| Level 3 | Plain-language translation | Narrative for the clinical report |

| \|SHAP\| | Contributor level | Reporting |
|----------|-------------------|-----------|
| ≥ 0.20 | Dominant | Named first in the narrative; top of the waterfall chart |
| 0.10 to < 0.20 | Significant | Named in the narrative |
| 0.05 to < 0.10 | Supporting | Shown in the chart; summarized as a group in the narrative |
| < 0.05 | Negligible | Shown in the chart (up to 15 features); not mentioned in the narrative |

The SHAP attribution is not shown for a recording with a signal quality warning (Chapter 19 §19.9.1). The code is in `chapters/ch14/chapter_14.py`.

---

## References

- Albasu, F., et al. (2024). Electroretinogram analysis using a short-time Fourier transform and machine learning techniques. *Bioengineering*, 11(9), 866.
- Baker, R.A., et al. (2025). ISCEV standard full-field ERG reference limits from 407 healthy subjects. *Documenta Ophthalmologica*, 150, 47–64.
- Bland, J.M. and Altman, D.G. (1986). Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet*, 327(8476), 307–310.
- Robson, A.G., et al. (2022). ISCEV standard for full-field clinical electroretinography (2022 update). *Documenta Ophthalmologica*, 144(3), 165–177.
- Weir, J.P. (2005). Quantifying test-retest reliability using the intraclass correlation coefficient and the SEM. *Journal of Strength and Conditioning Research*, 19(1), 231–240.
