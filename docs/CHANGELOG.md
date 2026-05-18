# Changelog

All notable changes to the ERG Analysis API pipeline are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — V3.0 (Future)

### Planned

- Sensitivity validation on real pathology recordings
- External validation with clinically annotated datasets
- Additional electrode types (skin, DTL) with validated reference ranges
- Real-time processing mode for clinical workflows
- REST API deployment for remote access
- Mobile/tablet interface for point-of-care use

---

## [2.3.2] — 2026-05-18

### Added

- Age-stratified reference ranges from Baker et al. 2025 (n=407 healthy subjects)
- `_get_age_group()` method for ≤35, 36-59, ≥60 year stratification
- `patient_age` parameter threaded through `compute_z_scores()` and `generate_full_report()`
- `age_group_used` field in Layer 4 technical audit log
- Normative comparison metadata in Layer 3 (reference source, DOI, n_subjects, age_range, sex_distribution)
- Comprehensive specificity validation report (94.5% GREEN rate on 407 healthy subjects)

### Changed

- Cell 6 completely rewritten with Baker 2025 reference ranges
- Electrode mapping: Silver thread (fornix) and Gold foil (transformed) both mapped to contact_lens
- DA 0.01 a-wave references set to (0,0) per Baker 2025 convention (not extracted for scotopic threshold)
- LA 30 Hz a-wave references set to (0,0) per Baker 2025 convention (not extracted for flicker)
- Disclaimer text updated to reference Baker et al. 2025 and age-stratification
- Pipeline version updated to 2.3.2

### Fixed (15 Parameter Corrections)

- DA 3 ≤35: a_imp (14.5→15.0), b_amp (310→266)
- DA 3 36-59: b_imp (52→50.6, SD 4→2.4)
- DA 3 ≥60: a_imp (16.5→16.0, SD 1.2→0.8)
- DA 10 ≤35: a_imp (12.5→11.8, SD 1.0→0.9), b_amp (320→276)
- DA 10 36-59: a_imp (13.5→12.5, SD 1.2→1.0)
- DA 10 ≥60: a_imp (14.5→13.3, SD 1.2→1.0)
- DA 0.01 ≤35: b_amp (210→191, SD 48→38)
- LA 3 ≤35: b_amp (140→120)
- LA 3 ≥60: a_imp (14.5→14.2, SD 1.0→0.6)
- LA 30 Hz ≤35: b_imp (26.5→25.4, SD 1.5→0.9)
- LA 30 Hz 36-59: b_imp (27.5→25.7, SD 1.5→1.2)
- LA 30 Hz ≥60: b_imp (28.5→26.4, SD 1.5→1.4)

### Validation

- External specificity validation completed on Baker et al. 2025 dataset (n=407 healthy subjects)
- Overall specificity: 94.5% (387/407 correctly classified as GREEN)
- Age-stratified performance: ≤35 (84.7%), 36-59 (87.7%), ≥60 (90.5%)
- Both electrode types validated: Silver thread (n=254) and Gold foil transformed (n=153)

---

## [2.3.1] — 2026-05-15

### Added

- Initial ISCEV 2022 compliant pipeline release
- Four-layer report structure (Traffic Light, Clinical Summary, Specialist, Audit)
- Contact lens reference ranges from Davis & Hamilton 2021
- Notch filter OFF by default (ISCEV 2022 compliant)
- Median filter (5 ms kernel) for spike removal
- Butterworth bandpass (0.3-300 Hz, 4th order)
- Oscillatory Potential extraction (75-300 Hz)
- PhNR extraction for LA 3.0 protocol
- STFT spectrogram generation (Chapter 8)
- SHAP explainability framework (Chapter 14) — three-level implementation
- FHIR R4 compliant JSON output (Cell 9)
- Batch processing UI (Cell 10) with Colab integration

### Validation

- Synthetic validation: 7 disease classes, 100% correct classification
- OculusGraphy 2020 technical validation: 149 files, 100% processing success

### Fixed

- a-wave forced negative, b-wave forced positive (physiological constraints)
- b-wave search enforced after a-wave trough
- Flash midpoint correction for flash duration ≥5 ms
- OP sum calculation = OP2+OP3+OP4 per ISCEV 2022

---

## [2.3.0] — 2026-05-10

### Added

- Initial feature extraction module (a-wave, b-wave, ba-ratio)
- ISCEV protocol-specific search windows
- ERGAudit class for pre-processing quality assessment
- ERGFilter class with conditional filtering pipeline
- ERGReportGenerator with Z-score computation
- Age group handling with fallback to '18-80y'

### Changed

- Restructured from monolithic script to modular class-based architecture

---

## [2.2.0] — 2026-05-01

### Added

- SNR calculation per Chapter 2 §2.2.1
- EMG detection via high-frequency band (150-300 Hz)
- Mains interference detection (50/60 Hz)
- Bandwidth estimation from Welch PSD

### Fixed

- Spike detection using median absolute deviation (MAD)
- Saturation detection (amplifier ceiling + flat run detection)

---

## [2.1.0] — 2026-04-20

### Added

- ISCEV 2022 compliance validation
- Pre-stimulus baseline adequacy checking (≥20 ms requirement)
- Sampling rate validation (≥1 kHz requirement)
- Post-stimulus duration validation (≥300 ms requirement)

---

## [2.0.0] — 2026-04-01

### Added

- Complete refactor of Cell 6 with four-layer report structure
- Traffic light generation (GREEN/AMBER/RED)
- Z-score computation against reference ranges
- Electrode-specific reference ranges (contact_lens, gold_foil, dtl_fiber, skin)
- Protocol-specific reference ranges for all 5 ISCEV protocols

### Removed

- Hardcoded reference values replaced with electrode/protocol-specific dictionaries

---

## [1.0.0] — 2026-03-15

### Added

- Initial prototype
- Basic CSV loading and filtering
- Simple a-wave/b-wave peak detection

---

## Legend

| Symbol | Meaning |
|:---|:---|
| `Added` | New features or functionality |
| `Changed` | Changes to existing functionality |
| `Deprecated` | Features that will be removed in future |
| `Removed` | Features that were removed |
| `Fixed` | Bug fixes |
| `Security` | Security vulnerability fixes |
| `Validation` | Validation reports and results |

---

*For questions about this changelog, please contact info@ai-fairness.com or open a GitHub issue.*
