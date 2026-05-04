# ERG Analysis API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Full-field ERG signal processing, machine learning classification, and clinical decision support API.**

This repository accompanies the textbook "**Hands-On Electroretinography in the Age of AI**
_*A Practical Guide from Clinical Fundamentals to Intelligent Decision Support*" (Apress/Springer-Nature, forthcoming (Tavakoli 2027)).

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

## Quick Start

### Local Installation (Conda)

```bash
git clone https://github.com/AI-Fairness-com/erg-analysis-api.git
cd erg-analysis-api
conda env create -f environment.yml
conda activate erg-analysis
python api/app.py
