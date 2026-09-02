# ERG Analysis API

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pipeline Version](https://img.shields.io/badge/pipeline-v2.5.1-lightgreen.svg)](https://github.com/AI-Fairness-com/ERG-Analysis-API/blob/main/docs/CHANGELOG.md)
![Validation](https://img.shields.io/badge/validation-41%2F41%20PASS%20(v2.4.0)-yellow)
![pytest](https://img.shields.io/badge/pytest-23%2F23%20PASS-brightgreen)
![Tier](https://img.shields.io/badge/tier-4%20prep%20complete-brightgreen)
![Version](https://img.shields.io/badge/version-v2.5.1-blue)


**Full-field ERG signal processing, machine learning classification, and clinical decision support API.**

## Project Status

| Tier | Name | Status |
|:---|:---|:---|
| **Tier 1** | Synthetic Validation | ⚠️ 41/41 PASS on v2.4.0 — pending re-validation on v2.5.0's feature set |
| **Tier 2** | Code Hardening | ✅ Complete — pytest 23/23 PASS |
| **Tier 3** | Clinical & Regulatory | ✅ Complete — T3-A through T3-E signed off |
| **Tier 4** | External Validation | 🔄 Phase A complete — clinical site TBD |
| **Tier 5** | Clinical Deployment | ⏳ Pending Tier 4 |

**Current version:** v2.5.1  
**Normative reference:** Baker et al. (2025) N=407. DOI: [10.1007/s10633-025-10009-2](https://doi.org/10.1007/s10633-025-10009-2)  
**OSF pre-registration:** [10.17605/OSF.IO/6WA42](https://doi.org/10.17605/OSF.IO/6WA42)  
**Regulatory package:** [`docs/regulatory/`](docs/regulatory/) (T2–T4 documents)  
**Charity registration:** AI Fairness CIO — Charity Commission No. 1218464

This repository accompanies the textbook "**Hands-On Electroretinography in the Age of AI**
_*A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*" (Apress/Springer-Nature, forthcoming (Tavakoli 2027)).

## Version Information

**Current Version: 2.5.1** | Release Date: 2 September 2026

- **V2.5.1**: Chapter 9 full-pixel-level review completed — 3 further features added (b-wave ascending-limb inflection time and gradient, a-wave descending-limb inflection time; Wood, Margrain & Binns 2014 found these equally significant to the already-implemented b-wave descending-limb pair), bringing the pipeline to 28 distinct features (up to 27 on a single recording, since the PhNR and harmonic-ratio bonuses never co-occur on the same protocol). One logic bug fixed: the §9.3 nonlinear/DWT/derivative feature block was nested inside the LA-3-only PhNR conditional, meaning those 13 features were silently skipped on every protocol except LA 3; now runs unconditionally on all five protocols. Several citation corrections from full-text verification: Nair & Joseph's (2014a) cohort description corrected (three groups, not four — cone-rod dystrophy and retinitis pigmentosa are the same group under two names in that study, not separate groups); Gauvin et al.'s (2014) non-redundancy claim narrowed to the two descriptor pairs actually tested, not all six; a spectral-structure claim misattributed to Behbahani, Ahmadieh & Rajan (2021) corrected to its actual source (Gauvin et al. 2014 alone); the harmonic-ratio citation (previously Pescosolido et al. 2015, found on full-text review to describe vascular flicker-light reactivity, not the flicker-ERG waveform) replaced with Fukuo et al. (2016), which directly measures flicker-ERG amplitude and implicit time against diabetic retinopathy severity. OP1 exclusion rationale corrected: ISCEV 2022 does not define an OP1–OP4 numbering scheme at all (it describes "typically three main positive peaks, often followed by a fourth"), so the numbering this pipeline uses is a wider-literature convention, not an ISCEV compliance rule. Pipeline pushed to chapters/ch09/ch09_complete.py. Synthetic validation (41/41) still pending re-run against this feature set — see Tier 1 status above.
  
- **V2.5.0**: Feature set redesigned around a literature-reviewed, citation-backed 28-feature pipeline (was 36) — 18 features added (PhNR/b-wave ratio, Hurst Exponent, Approximate Entropy, six DWT band-energy descriptors, five b/a-wave derivative features, peak frequency, spectral entropy, harmonic ratio, OP2 implicit time), OP1 removed (its trough overlaps the b-wave's ascending limb, making it unreliable to isolate), STFT region-statistics and PSD-per-band features removed (redundant or unevidenced). Pipeline file renamed erg_v2_5_0.py. See docs/CHANGELOG.md for full details.

- **V2.4.0**: PhNR amplitude extraction added for LA 3 protocol (raw µV, negative sign convention); PhNR displayed in result panel, Layer 2 clinical summary, Layer 4 technical audit, FHIR bundle, and .txt report; PhNR Z-score and traffic light classification deferred pending validated normative dataset; pipeline file renamed to `erg_v2_4_0.py`; HTML renamed to `ERG_API_v2_4.html`. Comprehensive 41-case synthetic validation completed 23 June 2026 — **41/41 PASS COMPLETE**; all generator defects G1–G7 and A1/S03 resolved in `ERG_CSV_Generator_v2_4_2.py`; zero API pipeline bugs identified. Released 18 June 2026; validation completed 23 June 2026.
  
- **V2.3.2**: 18 defects resolved (3 blocking, 2 critical, 6 significant, 5 minor, 2 additional blocking); Baker et al. (2025) N=407 normative data integrated with all 48 µ/σ values verified; electrode gating architecture (Gold Foil and DTL supported; Contact Lens and Skin UNAVAILABLE with positive flag); LA 30 Hz b-wave extraction bug fixed; synthetic validation 13/13 passed; external validation cleared. Released 16 June 2026.
  
- **V2.3.1**: Initial ISCEV 2022 compliant release; OculusGraphy 2020 technical validation (149 files; 100% success). Released May 2026.

See `docs/CHANGELOG.md` for complete version history.

## Overview

This project provides a complete, reproducible pipeline for:
- **ISCEV-compliant ERG filtering** (Butterworth bandpass, notch Q=50, median)
- **Time-frequency analysis** (STFT spectrograms, wavelet transforms)
- **Feature extraction** (time-domain, PhNR family, nonlinear & CWT time-frequency descriptors, frequency-domain — 28 features total, 25–27 per recording depending on protocol, see `docs/CHANGELOG.md` v2.5.1)`
- **Machine learning classification** (Random Forest baseline + Vision Transformer)
- **SHAP explainability** (feature-level, spectrogram-level, plain-language)
- **No-code clinical API** (four-layer report: Traffic Light + Clinical Summary + Specialist + Audit)

## Repository Structure

| Directory | Contents |
|:---|:---|
| `/chapters` | Complete Python code for all 19 textbook chapters |`
| `/api` | Flask/FastAPI application for no-code clinical decision support |
| `/data` | De-identified sample ERG recordings + normative reference data |
| `/notebooks` | Interactive Jupyter notebooks including `ERG_V2_4_0.ipynb` |
| `/tests` | Unit tests for filters, features, and API endpoints |
| `/docs` | Documentation including CHANGELOG.md and validation reports |
| `/synthetic_validation` | Synthetic dataset generator and validation manifest (v2.3.2 inherited); v2.4.0 comprehensive 41-case datasets and corrected generator |
| `/validation` | v2.4.0 validation reports — `T1_Synthetic_Validation_Report_v2_4_0_COMPLETE.docx` (23 Jun 2026, **41/41 PASS — current**); `T1_Synthetic_Validation_Report_v2_4_0_FINAL_superseded.docx` (23 Jun 2026, 30/41 conditional, superseded); `VALIDATION_REPORT_v2_4_0_comprehensive.docx` (22 Jun 2026, superseded) |
| `/synthetic_validation` | Synthetic dataset generators and validation manifests; v2.3.2 inherited (13/13); v2.4.0 comprehensive 41-case dataset — Run 1 (11/41), Run 2 (30/41), Runs 3–5 final (41/41); `ERG_CSV_Generator_v2_4_2.py` (all defects G1–G7 resolved) |

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

| Tier | Type | Dataset | Result | Status |
|:---|:---|:---|:---|:---|
| **Tier 1** | Synthetic — Internal v2.4.0 | 41 cases × 5 protocols × 3 age strata × Gold Foil + DTL | 41/41 PASS | ✅ COMPLETE |
| **Tier 1** | Synthetic — Internal v2.3.2 (inherited) | 12 scenarios × 5 protocols × 4 electrode types | 13/13 runs PASS | ✅ PASS |
| **Tier 2** | Code Hardening — pytest suite | 23 automated tests (14 pipeline + 9 regression) | 23/23 PASS | ✅ COMPLETE |
| **Tier 2** | ISCEV re-validation | 30 CSVs at 350 ms post-stimulus | 30/30 PASS | ✅ COMPLETE |
| **Tier 2** | Normative integration | Baker et al. 2025 (N=407) — 96 µ/σ values | All values verified | ✅ COMPLETE |
| **Tier 3** | Clinical & Regulatory | ISCEV audit, traceability, bias, intended use, regulatory readiness | T3-A–T3-E signed off | ✅ COMPLETE |
| **Tier 4** | External Clinical Validation | Prospective real-patient ERG (N≥200, independent site) | Phase A prep complete | 🔄 IN PROGRESS |
| **Tier 5** | Clinical Deployment | Post Tier 4 completion | — | ⏳ PENDING |

## Validation

ERG Analysis API v2.4.0 has achieved **41/41 PASS** on comprehensive 
internal synthetic validation (23 June 2026).

- 41 synthetic test cases covering all five ISCEV 2022 protocols, three 
  Baker et al. (2025) age strata, Gold Foil and DTL Fiber electrodes, 
  disease patterns, boundary cases, and signal quality scenarios
- All generator defects G1–G7 and A1/S03 resolved in 
  `ERG_CSV_Generator_v2_4_2.py`
- Zero API pipeline bugs identified
- Full report: `validation/T1_Synthetic_Validation_Report_v2_4_0_COMPLETE.docx`
- Code hardening report: `docs/regulatory/T2_Code_Hardening_Report_v1_0.docx`
- Regulatory package: `docs/regulatory/` (T3-A through T3-E)
- Pre-registration: https://doi.org/10.17605/OSF.IO/6WA42

See `validation/T1_Synthetic_Validation_Report_v2_4_0_COMPLETE.docx` for the full 41-case audit table, root cause analysis for all generator defects, and Tier 1 sign-off checklist. OSF pre-registration: https://doi.org/10.17605/OSF.IO/6WA42

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
- **Parameters:** a-wave amplitude, a-wave implicit time, b-wave amplitude, b-wave implicit time (96 validated µ/σ values across 5 protocols × 3 strata × 2 electrodes)
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
- Parameter codes: custom `erg-api:` scheme (`https://ai-fairness.com/fhir/CodeSystem/erg-api`, version: 2.4.0)
- SNOMED CT interpretation codes: Normal (17621005), Borderline (263654007), Abnormal (442257004), Not available (410515003)

## Citation

If you use this pipeline in your research, please cite:

    @misc{tavakoli2026erg,
      author = {Tavakoli, Hamid},
      title = {ERG Analysis API: ISCEV 2022-Compliant Full-Field ERG Processing Pipeline},
      year = {2026},
      publisher = {GitHub},
      version = {2.5.1},
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

*Hands-On Electroretinography in the Age of AI — Pipeline V2.4.0 — Tiers 1–3 complete; Tier 4 Phase A complete — Updated 25 June 2026*
