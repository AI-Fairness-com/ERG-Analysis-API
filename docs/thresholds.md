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

**Who is behind the limits.** Baker et al. released their reference data with the paper (Mendeley Data, DOI [10.17632/kcptb9jrf5.1](https://doi.org/10.17632/kcptb9jrf5.1)). Of the 407 reference subjects, 353 were aged 18 to 80, 50 were children aged 7 to 17, and 4 were aged 83 to 86. All 50 children are in the ≤35 group, about 37% of its 135 subjects; the 4 oldest are in the ≥60 group. This project uses the published limits unchanged, so that they remain citable and match the pre-registered analysis plan. Restricting use to adults aged 18 to 80 is this project's choice, not a limit set by Baker et al., so a patient aged 18 to 35 is compared with limits that partly reflect children's ERGs. Limits recalculated from the adults aged 18 to 35 alone would rest on only 77 to 84 subjects per parameter, below the more than 120 in each published group, so they are not used (Chapter 10 §10.4).

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

---

## Signal Quality Thresholds

Source: Chapter 2 §2.3 and §2.5 (Table 2.3, Figure 2.2)

### Electrode-specific SNR thresholds (linear SNR)

| Electrode type | PASS (SNR ≥) | WARNING | FAIL (SNR <) |
|----------------|--------------|---------|--------------|
| Contact lens | 8 | 4 to 7.9 | 4 |
| Gold foil | 6 | 3 to 5.9 | 3 |
| DTL fiber | 4 | 2.5 to 3.9 | 2.5 |
| Skin | 3 | 2.0 to 2.9 | 2.0 |

The SNR is the signal amplitude divided by the noise amplitude of the pre-stimulus baseline; in decibels, SNR (dB) = 20 × log10(signal / noise). The thresholds are stored in `ERGConfig.ELECTRODE_SNR_THRESHOLDS` in `api/erg_v2_5_0.py`. A recording with no electrode type halts before any signal processing (Chapter 19 §19.9.2).

### Sweep rejection rate

| Share of single sweeps rejected | Flag |
|---------------------------------|------|
| Up to 20% | PASS |
| Above 20%, up to 40% | WARNING |
| Above 40% | FAIL |

A WARNING recording is processed with a quality caveat on every report layer, and the SHAP attribution is not shown. A FAIL recording receives no Traffic Light and produces a quality failure report instead.

---

## Serial Change Detection

Source: Chapter 15 (Tables 15.2 and 15.3)

For two recordings, the minimum detectable change at 95% confidence equals the coefficient of repeatability (CoR), so the CoR is the single change threshold. Amplitude changes are compared on the log10 scale.

| Change zone | Criterion | Flag | Recommended action |
|-------------|-----------|------|--------------------|
| Green: no significant change | \|Δ\| < CoR | NO_CHANGE | Routine follow-up at the scheduled interval |
| Red: significant progression | \|Δ\| ≥ CoR (amplitude fall or longer implicit time) | SIGNIFICANT_PROGRESSION | Specialist review |
| Blue: significant improvement | \|Δ\| ≥ CoR (amplitude rise or shorter implicit time) | SIGNIFICANT_IMPROVEMENT | Document and review in clinical context |

### Published CoR values (Knickelbein et al., 2021)

| Parameter | Electrode and group | CoR | Change beyond measurement noise |
|-----------|---------------------|-----|---------------------------------|
| DA 3.0 b-wave amplitude | Burian-Allen contact lens; birdshot chorioretinopathy | 0.216 log µV | Fall of more than 39% or rise of more than 64% |
| LA 30 Hz implicit time | Burian-Allen contact lens; birdshot chorioretinopathy | 3.4 ms | Change of more than 3.4 ms |

CoR values depend on the electrode, the protocol and the patient group. Each laboratory enters its own values; the code is in `chapters/ch15/chapter_15.py`.

---

## Device-Relative Normalization

Source: Chapter 10 §10.3

| Method | Formula or basis | When used |
|--------|------------------|-----------|
| Method 1: internal calibration signal | A_measured / A_calibration | A calibration signal is recorded in the same session and channel |
| Method 2: laboratory normative scaling | A_measured / µ_norm(electrode, protocol, age group) | The site has its own normative data, or data from an identical setup |
| Method 3: project-defined electrode-amplitude hierarchy | Amplitude relative to a reference value for its electrode type | Neither a calibration signal nor laboratory norms are available |

---

## Flash Duration

Source: Chapter 9 §9.1.1; Robson et al. (2022), p. 174

Implicit times are measured from the flash. A flash shorter than 1 ms is treated as instantaneous. Longer flashes, up to the ISCEV maximum of 5 ms, are timed from the middle of the flash.

---

## Calibration (Brier Score)

Source: Chapter 16 §16.5.3

Each class is compared with its own frequency-only reference, p(1 − p), where p is the share of recordings in the class. A class passes when its Brier score is below its reference. A class that fails sets CALIBRATION_WARNING, and its probability is withheld from clinical reports until recalibration on a larger calibration set passes.

---

## Deployment Thresholds

Source: Chapter 16 §16.2 and §16.5; judged on the lower bound of each 95% confidence interval, on external data

| Metric | Threshold |
|--------|-----------|
| Stage 1 binary AUC | at least 0.94 |
| Stage 2 macro-AUC | at least 0.80 |
| Sensitivity, every disease class | at least 0.75 |
| Brier score, every class | below its own frequency-only reference |

See `docs/validation.md` for what happens when a threshold is not met.

---

## References

- Baker, R.A., Leo, S.M., Clowes, W.I.N., et al. (2025). ISCEV standard full-field ERG reference limits from 407 healthy subjects. *Documenta Ophthalmologica*, 150, 47–64.
- Knickelbein, J.E., Jeffrey, B.G., Wei, M.M., et al. (2021). Reproducibility of full-field electroretinogram measurements in birdshot chorioretinopathy patients: an intra- and inter-visit analysis. *Ocular Immunology and Inflammation*, 29(5), 848–853.
- Robson, A.G., Frishman, L.J., Grigg, J., et al. (2022). ISCEV standard for full-field clinical electroretinography (2022 update). *Documenta Ophthalmologica*, 144(3), 165–177.
