# ERG Analysis API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Full-field ERG signal processing, machine learning classification, and clinical decision support API.**

This repository accompanies the textbook "**Hands-On Electroretinography in the Age of AI**
_*A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*" (Apress/Springer-Nature, forthcoming (Tavakoli 2027)).

## Version Information

**Current Version: 2.3.2** | Release Date: 18 May 2026

- **V2.3.2**: Age-stratified reference ranges (Baker et al. 2025) integrated; 15 parameter corrections; 94.5% specificity validated on 407 healthy subjects.
- **V2.3.1**: Initial ISCEV 2022 compliant release; OculusGraphy 2020 technical validation (149 files; 100% success).

See `docs/CHANGELOG.md` for complete version history.

## Overview

This project provides a complete, reproducible pipeline for:
- **ISCEV-compliant ERG filtering** (Butterworth bandpass, notch, median)
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
| `/notebooks` | Interactive Jupyter notebooks (one per chapter) |
| `/tests` | Unit tests for filters, features, and API endpoints |
| `/docs` | Documentation including CHANGELOG.md and validation reports |

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
| **Synthetic (Internal)** | 7 disease classes | 100% correct classification | ✅ PASS |
| **Technical (External)** | OculusGraphy 2020 (n=149) | 100% processing success | ✅ PASS |
| **Specificity (External)** | Baker et al. 2025 (n=407) | 94.5% GREEN rate | ✅ PASS |
| **Sensitivity (External)** | Real pathology recordings | Planned for V3.0 | ⏳ PENDING |

## Reference Ranges

Pipeline V2.3.2 uses **age-stratified reference ranges** from:

> Baker RA, Leo SM, Clowes WIN, et al. ISCEV standard full-field ERG reference limits from 407 healthy subjects, derived from transference and validation of reference data between electrode types and centres. *Documenta Ophthalmologica.* 2025;150:47–64. doi:10.1007/s10633-025-10009-2

- **Age groups:** ≤35, 36-59, ≥60 years
- **Electrodes:** Silver thread (fornix) + Gold foil (transformed)
- **Protocols:** All five ISCEV standard protocols (DA 0.01, DA 3, DA 10, LA 3, LA 30 Hz)

**Note:** b/a ratio and PhNR reference ranges are retained estimates (not in Baker 2025).

## Traffic Light Interpretation

| Signal | Z-Score Range | Clinical Action |
|:---|:---|:---|
| 🟢 **GREEN** | \|Z\| ≤ 2.0 | Within normal limits. No immediate action required. |
| 🟡 **AMBER** | 2.0 < \|Z\| ≤ 3.0 | Borderline abnormality. Specialist review recommended. |
| 🔴 **RED** | \|Z\| > 3.0 | Significant abnormality. Urgent review required. |

## Citation

If you use this pipeline in your research, please cite:

    @misc{tavakoli2026erg,
      author = {Tavakoli, Hamid},
      title = {ERG Analysis API: ISCEV 2022-Compliant Full-Field ERG Processing Pipeline},
      year = {2026},
      publisher = {GitHub},
      version = {2.3.2},
      url = {https://github.com/AI-Fairness-com/erg-analysis-api}
    }

For the reference ranges, cite:

    @article{baker2025iscev,
      author = {Baker, R.A. and Leo, S.M. and Clowes, W.I.N. et al.},
      title = {ISCEV standard full-field ERG reference limits from 407 healthy subjects},
      journal = {Documenta Ophthalmologica},
      volume = {150},
      pages = {47--64},
      year = {2025},
      doi = {10.1007/s10633-025-10009-2}
    }

## License

MIT License — see [LICENSE](LICENSE) file for details.

## Contact

For questions, issues, or collaboration inquiries:

- **Email:** info@ai-fairness.com
- **GitHub Issues:** [Open an issue](https://github.com/AI-Fairness-com/erg-analysis-api/issues)

For clinical validation partnerships or dataset access inquiries, please email directly.

---

*Hands-On Electroretinography in the Age of AI — Pipeline V2.3.2 — 18 May 2026*
