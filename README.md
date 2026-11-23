# ERG Analysis API

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](api/runtime.txt)

Companion code for the book **Hands-On Electroretinography in the Age of AI: A Practical Guide from Clinical Fundamentals to Intelligent Decision Support** by Hamid Tavakoli (Apress, forthcoming).

The repository holds the code of every chapter, a pipeline that processes ISCEV 2022 full-field ERG recordings, and a small web application that turns a recording into a four-layer clinical report with a Traffic Light result.

> **Research and teaching use only.** This code and the hosted demonstration accompany the book. They are not a medical device, have not been validated on patients, and must not be used for clinical decisions about a patient. The disease classifier is a pre-registered target and has not been trained or validated on patient data. Read [DISCLAIMER.md](DISCLAIMER.md) before use.

## What is in the repository

| Folder or file | Contents | Book |
|:---|:---|:---|
| `chapters/` | The code of each chapter, `ch01/` to `ch19/`, plus `Appendices/` | Chapters 1 to 19 |
| `api/` | Flask web application, pipeline (`erg_v2_5_0.py`), PDF report generator | Chapter 19 |
| `data/samples/` | Simulated DA 3.0 recording, EDF example, Baker et al. (2025) reference limits | Chapter 3, §3.6 |
| `examples/` | Nine clinical case notebooks, `case01` to `case09`, one for each case study of Chapter 19 | Chapter 19 |
| `tests/` | Automated tests of the pipeline, the Traffic Light zones and the FHIR output | |
| `docs/` | Methodology, thresholds, FHIR integration, validation plan, change log | |
| `requirements.txt` | Python libraries, with the versions the project was tested with | Appendix F |

## Getting started

**Google Colab** needs no installation and is the simplest start (Chapter 3 §3.3.1). Each chapter script and case notebook runs there after cloning the repository.

**On your own computer** (Appendix F), install Python 3 and Git, then:

```bash
git clone https://github.com/AI-Fairness-com/ERG-Analysis-API.git
cd ERG-Analysis-API
python3 -m venv erg_env
source erg_env/bin/activate        # Windows: erg_env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

The tested Python version is named in `api/runtime.txt` (Python 3.12). The decision-tree figure of Chapter 12 also needs the Graphviz program (`brew install graphviz` on macOS; it is already on Colab).

**Run the API locally** (Mode B, Chapter 19 §19.10.2):

```bash
cd api
python erg_server.py
```

Open http://localhost:8080 for the upload form; http://localhost:8080/api/v1/health reports whether the server is running. Set the `PORT` environment variable to use another port.

**Run the tests:**

```bash
python -m pytest tests
```

**Hosted version** (Mode A): https://erg-analysis-api-1.onrender.com

## Input

The API processes one file format, the Standardized ERG CSV of Appendix A: one recording (one protocol, one eye, one session) per file. The electrode type is required and has no default; a file without it halts with an `ELECTRODE_UNKNOWN` error report (Chapter 19 §19.9.2).

## The Traffic Light

Each ERG parameter is compared with the age-specific reference limits of Baker et al. (2025) for silver thread (DTL fiber) electrodes, and with the 90% confidence intervals of those limits (Chapter 10 §10.4, Equation 10.2):

| Zone | Amplitude | Implicit time |
|:---|:---|:---|
| GREEN | within the limits | within the limits |
| AMBER | below the lower limit, within its confidence interval | above the upper limit, within its confidence interval |
| RED | below the confidence interval of the lower limit, or not recordable | above the confidence interval of the upper limit, or not recordable |
| ATYPICAL DIRECTION | above the upper limit | below the lower limit |

The most severe zone sets the composite result. Gold foil amplitudes are converted to silver thread equivalents first (Baker et al., 2025, Table 2). Contact lens and skin recordings receive no zone, because no reference limits are held for them. The b/a ratio, the oscillatory potentials and the PhNR are reported as measured values without a zone.

Age strata: 35 years or younger, 36 to 59 years, 60 years or older. Protocols: DA 0.01, DA 3.0, DA 10.0, LA 3.0 and LA 30 Hz.

## Output

- **Layer 1:** Traffic Light, with the mandatory disclaimer (Chapter 1 §1.7.4)
- **Layer 2:** clinical summary with the zone of every parameter
- **Layer 3:** specialist report
- **Layer 4:** technical audit with the version stamp
- **PDF report** and an **HL7 FHIR R4 Bundle** (LOINC panel 79894-2, Appendix B)

## Citation

Please cite the book and the reference limits:

> Tavakoli, H. *Hands-On Electroretinography in the Age of AI: A Practical Guide from Clinical Fundamentals to Intelligent Decision Support.* Apress (forthcoming).

> Baker RA, Leo SM, Clowes WIN, et al. ISCEV standard full-field ERG reference limits from 407 healthy subjects, derived from transference and validation of reference data between electrode types and centres. *Documenta Ophthalmologica.* 2025;150(2):47–64. https://doi.org/10.1007/s10633-025-10009-2

Pre-registration of the validation study: https://doi.org/10.17605/OSF.IO/6WA42

## License and contact

Apache License 2.0, see [LICENSE](LICENSE). Maintained by AI Fairness CIO (UK registered charity no. 1218464).

Questions and collaboration: hello@ai-fairness.com, or [open an issue](https://github.com/AI-Fairness-com/ERG-Analysis-API/issues).
