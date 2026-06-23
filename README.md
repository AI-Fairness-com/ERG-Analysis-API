# ERG Analysis API

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pipeline Version](https://img.shields.io/badge/pipeline-v2.4.0-lightgreen.svg)](https://github.com/AI-Fairness-com/ERG-Analysis-API/blob/main/docs/CHANGELOG.md)
[![Validation](https://img.shields.io/badge/v2.4.0%20validation-30%2F41%20conditional-yellow.svg)](https://github.com/AI-Fairness-com/ERG-Analysis-API/blob/main/validation/VALIDATION_REPORT_v2_4_0_FINAL.docx)


**Full-field ERG signal processing, machine learning classification, and clinical decision support API.**

This repository accompanies the textbook "**Hands-On Electroretinography in the Age of AI**
_*A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*" (Apress/Springer-Nature, forthcoming (Tavakoli 2027)).

## Version Information

**Current Version: 2.4.0** | Release Date: 18 June 2026

- **V2.4.0**: PhNR amplitude extraction added for LA 3 protocol (raw µV, negative sign convention); PhNR displayed in result panel, Layer 2 clinical summary, Layer 4 technical audit, FHIR bundle, and .txt report; PhNR Z-score and traffic light classification deferred pending validated normative dataset; pipeline file renamed to `erg_v2_4_0.py`; HTML renamed to `ERG_API_v2_4.html`. Comprehensive 41-case synthetic validation completed 23 June 2026 — 30/41 PASS (conditional); all failures attributable to CSV generator calibration defects; zero API pipeline bugs identified. Released 18 June 2026; validation updated 23 June 2026.
- **V2.3.2**: 18 defects resolved (3 blocking, 2 critical, 6 significant, 5 minor, 2 additional blocking); Baker et al. (2025) N=407 normative data integrated with all 48 µ/σ values verified; electrode gating architecture (Gold Foil and DTL supported; Contact Lens and Skin UNAVAILABLE with positive flag); LA 30 Hz b-wave extraction bug fixed; synthetic validation 13/13 passed; external validation cleared. Released 16 June 2026.
- **V2.3.1**: Initial ISCEV 2022 compliant release; OculusGraphy 2020 technical validation (149 files; 100% success). Released May 2026.

See `docs/CHANGELOG.md` for complete version history.

## Overview

This project provides a complete, reproducible pipeline for:
- **ISCEV-compliant ERG filtering** (Butterworth bandpass, notch Q=50, median)
- **Time-frequency analysis** (STFT spectrograms, wavelet transforms)
- **Feature extraction** (time-domain, frequency-domain, STFT statistics)
- **Machine learning classification** (Random Forest baseline + Vision Transformer)
- **SHAP explainability** (feature-level, spectrogram-level, plain-language)
- **No-code clinical API** (four-layer report: Traffic Light + Clinical Summary + Specialist + Audit)

## Repository Structure

| Directory | Contents |
|:---|:---|
| `/chapter_scripts` | Complete Python code for all 19 textbook chapters |
| `/api` | Flask/FastAPI application for no-code clinical decision support |
| `/data` | De-identified sample ERG recordings + normative reference data |
| `/notebooks` | Interactive Jupyter notebooks including `ERG_V2_4_0.ipynb` |
| `/tests` | Unit tests for filters, features, and API endpoints |
| `/docs` | Documentation including CHANGELOG.md and validation reports |
| `/synthetic_validation` | Synthetic dataset generator and validation manifest (v2.3.2 inherited); v2.4.0 comprehensive 41-case datasets and corrected generator |
| `/validation` | v2.4.0 validation reports — `VALIDATION_REPORT_v2_4_0_comprehensive.docx` (22 Jun 2026, conditional) and `VALIDATION_REPORT_v2_4_0_FINAL.docx` (23 Jun 2026, supersedes) |
| **Comprehensive Synthetic v2.4.0 — Run 1** | 41 synthetic CSVs — 5 protocols × 3 age strata × 4 electrodes (22 Jun 2026) | 11/41 PASS — generator defects G1–G5 identified | ⚠️ CONDITIONAL |
| **Comprehensive Synthetic v2.4.0 — Run 2** | 30 corrected CSVs — `ERG_CSV_Generator_v2_4_corrected.py` (23 Jun 2026) | 30/41 PASS combined — G3/G6/G7/A1 generator defects outstanding; zero API bugs identified | ⚠️ CONDITIONAL |

## Quick Start

### Local Installation (Conda)

    git clone https://github.com/AI-Fairness-com/erg-analysis-api.git
    cd erg-analysis-api
    conda env create -f environment.yml
    conda activate erg-analysis
    python api/app.py

### Docker Deployment

    docker build -t erg-api .
    docker run -p 8080:8080 erg-api

## Validation Status

| Validation Type | Dataset | Result | Status |
|:---|:---|:---|:---|
| **Synthetic (Internal v2.3.2 — inherited by v2.4.0)** | 12 scenarios × 5 protocols × 4 electrode types | 13/13 runs passed | ✅ PASS |
| **Technical (External)** | OculusGraphy 2020 (n=149) | 100% processing success | ✅ PASS |
| **Normative integration** | Baker et al. 2025 (N=407) | All 48 µ/σ values verified < 0.02 tolerance | ✅ PASS |
| **Sensitivity (External)** | Real pathology recordings | Planned for V3.0 | ⏳ PENDING |

See `validation/VALIDATION_REPORT_v2_4_0_FINAL.docx` for the full 41-case audit table, root cause analysis, and outstanding actions. OSF pre-registration: https://doi.org/10.17605/OSF.IO/6WA42

## Electrode Support

| Electrode | Z-Score | Traffic Light | Normative Source |
|:---|:---|:---|:---|
| Gold Foil | ✅ | GREEN / AMBER / RED | Baker et al. (2025) N=407 |
| DTL (silver thread) | ✅ | GREEN / AMBER / RED | Baker et al. (2025) N=407 |
| Contact Lens | ❌ | ⬜ UNAVAILABLE | No validated age-stratified dataset |
| Skin | ❌ | ⬜ UNAVAILABLE | No validated age-stratified dataset |

Signal processing (filtering, feature extraction, AI classification, FHIR output) runs identically for all four electrode types. Z-score classification and traffic light are restricted to Gold Foil and DTL electrodes only.

## Reference Ranges

Pipeline V2.4.0 uses **age-stratified normative reference ranges** from:

> Baker RA, Leo SM, Clowes WIN, et al. ISCEV standard full-field ERG reference limits from 407 healthy subjects, derived from transference and validation of reference data between electrode types and centres. *Documenta Ophthalmologica.* 2025;150(2):47–64. doi:10.1007/s10633-025-10009-2

- **Age strata:** ≤35y | 36–59y | ≥60y (Baker 2025 three-stratum framework)
- **Electrodes:** Silver thread (fornix) + Gold Foil (Deming regression transference, Baker Table 2)
- **Protocols:** DA 0.01, DA 3, DA 10, LA 3, LA 30 Hz (all five ISCEV 2022 standard protocols)
- **Parameters:** a-wave amplitude, a-wave implicit time, b-wave amplitude, b-wave implicit time (48 validated µ/σ values)
- **b/a ratio:** mean 2.65, SD 0.425 (normal range 1.8–3.5, DA 3 only; Chapter 9)

## Traffic Light Interpretation

| Signal | Z-Score Range | Clinical Action | Confidence |
|:---|:---|:---|:---|
| 🟢 **GREEN** | \|Z\| ≤ 2.0 | Within normal limits. No immediate action required. | 95% |
| 🟡 **AMBER** | 2.0 < \|Z\| ≤ 3.0 | Borderline abnormality. Specialist review recommended. | 85% |
| 🔴 **RED** | \|Z\| > 3.0 | Significant abnormality. Urgent review required. | 90% |
| ⬜ **UNAVAILABLE** | Electrode not supported | Manual interpretation required. | N/A |

## FHIR Output

Each pipeline run generates an HL7 FHIR R4 Observation resource:
- Top-level ERG code: **LOINC 70943-7**
- Parameter codes: custom `erg-api:` scheme (`https://github.com/AI-Fairness-com/ERG-Analysis-API/CodeSystem`)
- SNOMED CT interpretation codes: Normal (17621005), Borderline (263654007), Abnormal (442257004), Not available (410515003)

## Citation

If you use this pipeline in your research, please cite:

    @misc{tavakoli2026erg,
      author = {Tavakoli, Hamid},
      title = {ERG Analysis API: ISCEV 2022-Compliant Full-Field ERG Processing Pipeline},
      year = {2026},
      publisher = {GitHub},
      version = {2.4.0},
      url = {https://github.com/AI-Fairness-com/erg-analysis-api}
    }

For the normative reference ranges, cite:

    @article{baker2025iscev,
      author = {Baker, R.A. and Leo, S.M. and Clowes, W.I.N. et al.},
      title = {ISCEV standard full-field ERG reference limits from 407 healthy subjects},
      journal = {Documenta Ophthalmologica},
      volume = {150},
      number = {2},
      pages = {47--64},
      year = {2025},
      doi = {10.1007/s10633-025-10009-2}
    }

## License

Apache 2.0 — see [LICENSE](LICENSE) file for details.

## Contact

For questions, issues, or collaboration inquiries:

- **Email:** info@ai-fairness.com
- **GitHub Issues:** [Open an issue](https://github.com/AI-Fairness-com/erg-analysis-api/issues)

For clinical validation partnerships or dataset access inquiries, please email directly.

---

*Hands-On Electroretinography in the Age of AI — Pipeline V2.4.0 — Validation updated 23 June 2026*
