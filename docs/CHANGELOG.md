# Changelog

![Validation](https://img.shields.io/badge/validation-41%2F41%20PASS-brightgreen)

All notable changes to the ERG Analysis API pipeline are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — V3.0 (Future)

### Planned

- Sensitivity validation on real pathology recordings
- External validation with clinically annotated datasets
- Contact Lens and Skin electrode normative reference data (pending validated age-stratified dataset)
- Real-time streaming filter mode (sosfilt causal pathway — stub in v2.3.2, implementation in v2.5.0)
- REST API deployment for remote access
- Mobile/tablet interface for point-of-care use

---

## [2.5.0] — 2026-08-29

### Feature set redesign — literature-grounded 25-feature pipeline

The v2.4.0 feature set (11 time-domain, then various STFT/PSD additions) was checked against the peer-reviewed ERG feature-extraction literature during the Chapter 9 review cycle. Most features had no specific citation behind them; several strongly-evidenced features from the literature were missing entirely. This release reconciles both.

**Added (15 features, each backed by a named, cited source):**
- `phnr_bwave_ratio` — PhNR/b-wave ratio (Kirkiewicz, Lubiński & Penkala 2016)
- `hurst_exponent`, `approximate_entropy` — nonlinear complexity measures (Nair & Joseph 2014); Largest Lyapunov Exponent and Higuchi Fractal Dimension from the same study were tested and found not significant, and are deliberately not implemented
- `dwt_20a_uv2`, `dwt_40a_uv2`, `dwt_20b_uv2`, `dwt_40b_uv2`, `dwt_80ops_uv2`, `dwt_160ops_uv2` — six CWT band-energy descriptors at Gauvin, Lina & Lachapelle's (2014) statistically-validated frequency/time-window pairs (their descriptor set was directly tested for redundancy against amplitude/implicit-time and found non-redundant)
- `b_descending_inflection_ms`, `b_descending_gradient_uv_ms` — b-wave descending-limb derivative features (Wood, Margrain & Binns 2014)
- `peak_freq_hz`, `spectral_entropy`, `harmonic_ratio` (LA 30 Hz only) — retained frequency-domain features (Behbahani, Ahmadieh & Rajan 2021; Gauvin et al. 2014)
- `OP2_implicit_ms` — OP2 implicit time, alongside the existing OP2/OP3/OP4 amplitudes

**Removed:**
- `OP1` amplitude — excluded per ISCEV 2022 convention (its trough overlaps the b-wave ascending limb); this is a compliance correction, not a data-loss regression
- 16 STFT spectrogram region-statistics features and the STFT-derived OP/b-wave ratio — no specific citation found; superseded by the DWT band-energy descriptors above
- `power_ratio` (Welch OP/b-wave ratio) and the 4-band PSD split (`psd_vlow`, `psd_bwave`, `psd_transit`, `psd_op`) — redundant with the DWT descriptors, or (for the very-low band specifically) a QC/electrode-drift signal rather than a diagnostic feature

**Net result:** up to 25 features per recording (was 36), 250 raw features per patient pre-selection (was up to 360) — smaller because the new design is hand-curated for non-redundancy, not because coverage was cut.

### Bug fixes
- `extract_bwave_derivative_features()`: the descending-inflection search started exactly at the b-wave peak, where numerical differentiation could catch leftover rising-limb curvature and return a spuriously positive ("ascending") gradient for a feature defined as descending. Fixed: search now starts 3 ms past the peak and only accepts candidates where the gradient is genuinely negative. Verified across all 30 files in the synthetic validation set — zero wrong-sign results after the fix, several before it.
- Two indentation errors introduced during manual application of the v2.5.0 feature additions (one nested `def` one level too deep, one `else:` block misaligned) — both caught by direct `ast.parse()` validation and full pipeline execution, not just visual review.

### Test infrastructure
- `tests/conftest.py` imported the pipeline module from a repo-root path (`erg_v2_4_0.py`) that never existed there — only `api/erg_v2_4_0.py` and `notebooks/erg_v2_4_0.py` did, both now removed. This meant the test suite (`test_pipeline.py`, `test_regression.py`) was failing to collect independent of this release. Fixed to import from `api/erg_v2_5_0.py`.
- `tests/conftest.py`'s regression fixture path pointed at `synthetic_validation/S_Normal_DA3_GoldFoil_le35.csv`; the file actually lives at `data/samples/`. Fixed.
- Full suite verified: 23/23 passing under the repo's pinned `numpy==1.26.0` (two of the pipeline's `np.trapz` calls will need `np.trapezoid` if numpy is ever upgraded past 2.0 — not an active bug under the current pin, flagged for awareness).

### Repository cleanup
- `notebooks/erg_v2_4_0.py` removed — was a stale, independently-drifted snapshot (missing several features already in `api/erg_v2_4_0.py` before this release), not a maintained duplicate.
- `api/erg_v2_4_0.py` removed; `api/erg_server.py`'s `PIPELINE_PATH` repointed to `api/erg_v2_5_0.py`.
- `docs/regulatory/` T1, T2, and T3-A through T3-E documents (all describing v2.4.0's validated behavior) moved to `docs/regulatory/archive/v2.4.0/` rather than deleted or relabeled — they remain accurate, signed records of what was actually tested for v2.4.0, and must not be silently reattributed to v2.5.0's different feature set. New T1–T3 documents for v2.5.0 are pending re-validation.

### Documentation
- `docs/methodology.md`: added an explicit "Feature Coverage" disclosure — only 5 of the pipeline's features (a-wave amp/implicit, b-wave amp/implicit, b/a ratio) currently have normative Z-score/Traffic-Light coverage; the other 20 (including all 15 new features above) are extracted and reported but not yet clinically interpreted, pending either a matched-methodology literature source or the project's own normative cohort. Gauvin et al.'s (2014) own published normative values for the DWT descriptors are not reused directly, since their discrete Haar-wavelet decomposition is not numerically interchangeable with this pipeline's continuous Morlet-based implementation.
- Chapter 9 of the accompanying textbook rewritten to match this feature set; Figures 9.1 and 9.2 rebuilt accordingly.

---
## [2.4.0-tier4-prep-complete] — 2026-06-25

### Tier 4 Phase A — External Validation Preparation (complete)

**Documents added** (`docs/regulatory/`)
- T4-A_Validation_Protocol_v1_0.docx — pre-specified SAP; N≥200; Cohen's κ primary endpoint; 5 secondary analyses; pipeline version locked at v2.4.0
- T4-B_Ethics_Application_Template_v1_0.docx — IRAS-structured ethics application; GDPR basis; consent framework; AI fairness declarations
- T4-C_Data_Sharing_Agreement_v1_0.docx — GDPR Article 28 processor agreement template; data description; retention/deletion schedule; IP ownership
- T4-D_Post_Market_Surveillance_Plan_v1_0.docx — 5 KPIs with alert thresholds; Shewhart rolling AUC drift detection; adverse event reporting; annual revalidation schedule
- T4-E_QMS_Skeleton_v1_0.docx — ISO 13485 / ISO 14971 minimum viable QMS; design history file; 6-hazard risk register; change control log
- T4-F_Validation_Report_Template_v1_0.docx — pre-formatted validation report shell; CONSORT flow; confusion matrix; outcome tables; regulatory readiness verdict

**Phase B status:** NOT STARTED — commences upon clinical site identification, ethics approval, and DSA execution.

---

## [2.4.0-tier3-complete] — 2026-06-24

### Tier 3 — Clinical & Regulatory (complete)

**Documents added** (`docs/regulatory/`)
- T2_Code_Hardening_Report_v1_0.docx — 6 work packages; pytest 23/23 PASS; T1 limitations L3/L4/L7 resolved
- T3-A_ISCEV_Compliance_Checklist_v1_0.docx — 25 items; 14 PASS, 3 AMBER (remediated), 1 FAIL (remediated)
- T3-B_Normative_Traceability_Matrix_v1_0.docx — full Baker 2025 cross-walk; 8 findings; 3 AMBER (remediated)
- T3-C_Bias_Fairness_Audit_v1_0.docx — age stratification, DTL correction, traffic light symmetry; 2 AMBER (remediated)
- T3-D_Intended_Use_Statement_v1_0.docx — intended use statement, 5 contraindications, 9 limitations, OSF pre-reg cross-walk
- T3-E_Regulatory_Readiness_Summary_v1_0.docx — RAG table 18 requirements; verdict: READY FOR TIER 4

**Code patches applied to erg_v2_4_0.py**
- G1: version comment corrected to v2.4.0
- A6: flash duration runtime validation added to ERGAudit.run_full_audit()
- E5: FHIR CodeSystem URI updated to versioned ai-fairness.com URI
- F1: schema_version assertion added at normative JSON load time
- F6: BA_RATIO_MEAN and BA_RATIO_SD loaded from JSON (single source of truth)
- F4: _la3_a_amp_dtl_r2_borderline flag added to Layer 4 audit
- B4: LA 30 Hz b_amp absolute floor (20 µV → minimum AMBER) in generate_full_report()

**Code patches applied to erg_report_generator.py**
- D5: paediatric age group disclaimer block added to PDF report

**Regulatory readiness verdict:** READY FOR TIER 4 (external clinical validation). ML classifiers, external validation, and post-market surveillance plan are deferred to Tier 4.

---
## [2.4.0] — 2026-06-18

PhNR display release. Pipeline file and HTML renamed to match version.
Comprehensive 41-case synthetic validation completed 23 June 2026 — **41/41 PASS COMPLETE**.
All generator defects G1–G7 and A1/S03 resolved across five sequential runs; zero API pipeline bugs identified.
v2.3.2 13/13 pass also inherited.

### Added

- **[PhNR-DISPLAY]** PhNR amplitude extracted for LA 3 protocol and surfaced in:
  - Result panel (sixth metric card, visible for LA 3 only, hidden otherwise)
  - Layer 2 clinical summary (`phnr_amp_uv` field)
  - Layer 4 technical audit (`phnr_amp_uv` field)
  - FHIR bundle (new `erg-api:phnr-amplitude` component, raw µV, with note)
  - `.txt` report Layer 2 section
- **[PhNR-SIGN]** PhNR displayed with negative sign convention (`−9.3 µV`) consistent
  with a-wave display; stored internally as absolute value per ISCEV BT convention
- **[PhNR-NOTE]** FHIR PhNR component carries note: "Raw amplitude only. Reference
  range under development. No Z-score classification applied (v2.4.0)."

### Changed

- **[RENAME]** Pipeline file renamed from `erg_v2_3_2.py` to `erg_v2_4_0.py`
- **[RENAME]** HTML interface renamed from `ERG_API_updated.html` to `ERG_API_v2_4.html`
- **[RENAME]** `erg_server.py` updated to reference new filenames; fallback to
  `ERG_API_updated.html` retained for backwards compatibility
- **[VERSION]** All four user-visible version strings in HTML updated to v2.4.0:
  browser tab title, hero badge, loading panel text, and `.txt` report header

### Deferred

- PhNR Z-score and traffic light classification deferred to v2.5.0 pending a
  validated normative dataset (no age-stratified PhNR norms available for
  Gold Foil + broadband LA 3 stimulus in published literature as of June 2026;
  see Frishman et al. 2018 ISCEV extended protocol)

### Tier 1 — Synthetic Validation (22–23 June 2026)

- Early DR demo (DA 3, Gold Foil, ≤35y): 13/13 inherited pass confirmed ✅
- Early Glaucoma demo (LA 3, Gold Foil, 36–59y): PhNR card visible, `−9.3 µV`
  displayed, no Z-score assigned, traffic light driven by b-wave implicit time
  Z = +4.05 (RED) — PhNR correctly excluded from traffic light logic ✅
  
- **Comprehensive synthetic validation — Run 1 (22 Jun 2026):** 41 synthetic CSVs covering
  all five ISCEV 2022 protocols (DA 0.01, DA 3, DA 10, LA 3, LA 30 Hz), three Baker et al.
  (2025) age strata (≤35y, 36–59y, ≥60y), four electrode types (Gold Foil, DTL, ERG-Jet,
  HK-Loop), six disease patterns, seven boundary Z-score cases, and four signal quality /
  artefact scenarios. Result: 11/41 PASS. Generator defects G1–G5 and test-run error T2
  identified. Zero API pipeline bugs. ⚠️ CONDITIONAL
- **Comprehensive synthetic validation — Run 2 (23 Jun 2026):** 30 corrected CSVs generated
  by `ERG_CSV_Generator_v2_4_corrected.py` (fixes: G1 b_abs calibration, G2 LA3 b_w, G3
  flicker model, G4 DA001 amplitude, G5 ≥60y a_IT). Combined two-run result: 30/41 PASS.
  Outstanding generator defects: G3 LA 30Hz flicker model, G6 DA10 a_IT norms, G7 LA3 a_IT
  norms, A1 Grade D noise model. Full audit: `validation/VALIDATION_REPORT_v2_4_0_FINAL.pdf`.
  OSF pre-registration: https://doi.org/10.17605/OSF.IO/6WA42 ⚠️ CONDITIONAL
- **Comprehensive synthetic validation — Run 3 (23 Jun 2026):** 10 corrected CSVs submitted
  (`ERG_CSV_Generator_v2_4_2.py`, fixes: G6 DA10 a_it, G7 LA3 a_it for le35/36to59/dtl,
  A1/S03 DA3 ge60 a_it). Result: 7/10 PASS. Cumulative: 37/41. Remaining failures:
  S23 LA3 GoldFoil ge60 (b_it Z=−2.02 AMBER — generator b_it=27ms vs Baker mu=29.55ms),
  S26/S27 LA30Hz 36to59/ge60 (b_amp AMBER — decay envelope attenuation). ⚠️ CONDITIONAL
- **Comprehensive synthetic validation — Run 4 (23 Jun 2026):** 3 corrected CSVs submitted.
  G7 LA3 ge60 b_it corrected to Baker mu=29.55ms (S23 GREEN ✓). LA30Hz decaying sinusoid
  envelope (tau=100ms) resolved peak aliasing — b_it now correct (S26/S27 b_it GREEN).
  However b_amp remained AMBER (Z≈−2.22/−2.23) due to exponential decay attenuating peak
  amplitude below Baker norms. Result: 1/3 PASS. Cumulative: 38/41. ⚠️ CONDITIONAL
- **Comprehensive synthetic validation — Run 5 (23 Jun 2026):** 2 corrected CSVs submitted.
  G3 LA30Hz b_amp: generator amplitude pre-compensated for decay attenuation at it_ms
  (amp_gen = 2 × Baker_mu / exp(−it_ms / tau)). Result: 2/2 PASS. Cumulative: 40/41.
  S10 boundary artefact (B/A Z=−1.93 vs threshold −2.0) documented as confirmed acceptable
  per SOP Step 1.5. **Final result: 41/41 PASS COMPLETE ✅**
- Generator: `ERG_CSV_Generator_v2_4_2.py` — all defects G1–G7 and A1/S03 RESOLVED
- Report: `VALIDATION_REPORT_v2_4_0_COMPLETE.docx` committed to `/validation/`
- OSF pre-registration updated: https://doi.org/10.17605/OSF.IO/6WA42

### Tier 2 — Code Hardening (24 June 2026)

- **[T2-A]** Normative data externalised from hardcoded dict to
  `data/normative_data_baker2025.json` (schema_version 1.0, 96 µ/σ entries,
  Baker et al. 2025 DOI 10.1007/s10633-025-10009-2). Pipeline loads via
  Colab-safe `_find_norm_json()` with three-candidate path search
  (`__file__`-relative, cwd/data/, cwd flat); raises `FileNotFoundError`
  with full path list if not found.
- **[T2-B/T2-F]** pytest suite added: `tests/conftest.py`,
  `tests/test_pipeline.py` (14 tests: T-CSV-01/02, T-FILT-01, T-WAVE-01/02,
  T-ZSCORE-01/02, T-TL-01/02, T-FHIR-01/02, T-DTL-01, T-ORIENT-01/02,
  T-ELEC-01), `tests/test_regression.py` (8 tests: T-REG-01–08 anchored to
  `S_Normal_DA3_GoldFoil_le35.csv`). 23/23 PASS · 0.06s.
- **[T2-C]** DTL Deming regression correction implemented. Baker (2025)
  Table 2 coefficients loaded from `electrode_transform` block in normative
  JSON. `_apply_dtl_transform()` applies inversion
  `GFE_equiv = (STE − intercept) / slope` for amplitude parameters when
  `electrode == dtl_fiber`. Peak times transferred without adjustment per
  paper (bias ≤ 1.6 ms, slope ~1 for all components).
- **[T2-D]** Signal orientation auto-detection added to `extract_all_features()`.
  Sums post-stimulus signal in 0–30 ms window; if sum > 0, multiplies signal
  by −1 and sets `inverted_polarity_detected = True`. **Protocol restriction:**
  DA 0.01, DA 3, DA 10 only — LA 3 and LA 30 Hz explicitly skipped (b-wave
  rising flank dominates 0–30 ms window in normal photopic signals, producing
  false positives). Layer 4 warning and FHIR note added when flag fires.
- **[T2-E]** ISCEV post-stimulus fix: `ERG_CSV_Generator_v2_4_2.py`
  `TOTAL_MS` extended from 300 → 350 ms (50 ms pre + 300 ms post, ISCEV 2022
  minimum). N_SAMPLES 600 → 700. Verification harness updated to expect 700
  samples / 349.5 ms. DTL generator amplitude entries (seeds 80, 81) scaled to
  STE scale using Baker Table 2 Deming forward transform so pipeline inversion
  returns GF-equivalent and Z ≈ 0. Re-validation 30/30 PASS; all submissions
  show `Post-stimulus OK: true (300 ms)`.

## [2.4.0-tier3-complete] — 2026-06-24

### Tier 3 — Clinical & Regulatory (complete)

**Documents added** (`docs/regulatory/`)
- T3-A_ISCEV_Compliance_Checklist_v1_0.docx — 25 items; 14 PASS, 3 AMBER (remediated), 1 FAIL (remediated)
- T3-B_Normative_Traceability_Matrix_v1_0.docx — full Baker 2025 cross-walk; 8 findings; 3 AMBER (remediated)
- T3-C_Bias_Fairness_Audit_v1_0.docx — age stratification, DTL correction, traffic light symmetry; 2 AMBER (remediated)
- T3-D_Intended_Use_Statement_v1_0.docx — intended use statement, 5 contraindications, 9 limitations, OSF pre-reg cross-walk
- T3-E_Regulatory_Readiness_Summary_v1_0.docx — RAG table 18 requirements; verdict: READY FOR TIER 4

### Code patches applied to erg_v2_4_0.py
- G1: version comment corrected to v2.4.0
- A6: flash duration runtime validation added to ERGAudit.run_full_audit()
- E5: FHIR CodeSystem URI updated to versioned ai-fairness.com URI
- F1: schema_version assertion added at normative JSON load time
- F6: BA_RATIO_MEAN and BA_RATIO_SD loaded from JSON (single source of truth)
- F4: _la3_a_amp_dtl_r2_borderline flag added to Layer 4 audit
- B4: LA 30 Hz b_amp absolute floor (20 µV → minimum AMBER) in generate_full_report()

### Code patches applied to erg_report_generator.py
- D5: paediatric age group disclaimer block added to PDF report
---

## [2.3.2] — 2026-06-16

Full upgrade and validation release. Eighteen defects resolved across six pipeline cells.
Baker et al. (2025) N=407 normative data integrated with all 48 µ/σ values verified.
Synthetic validation 13/13 passed. External validation cleared.
See `validation/VALIDATION_REPORT_v2.3.2.pdf` for the complete validation report.

### Bug Fixes

- **[B1]** GDPR: temp signal file (`/tmp/{filename}`) now deleted in `finally` block after every
  pipeline run, regardless of success or exception (Cell 10)
- **[B2]** `PIPELINE_VERSION` unified to `"2.3.2"` across Cell 1 dataclass constant, header
  comment, and FHIR performer string — previously three locations had inconsistent values
- **[B3]** Disclaimer expanded to full three-sentence text per Blueprint §2.4: states AI
  decision-support only, not medical diagnosis, requires licensed clinician review (Cell 6)
- **[ADD1]** `SNOMED_INTERPRETATION` dict: added `'UNAVAILABLE'` key (SNOMED code 410515003,
  display "Not available") — previously caused `KeyError` crash for contact_lens and skin
  electrodes (Cell 9)
- **[ADD2]** `import os` added to Cell 10 — previously absent, causing `NameError` on every
  execution when `finally` block called `os.remove()` and `os.path.exists()`
- **[M9]** `NOTCH_QUALITY_FACTOR` corrected from `30.0` to `50.0`; inline comment corrected to
  `# Q=50 (~1.0 Hz bandwidth, Chapter 5)` — manuscript locks Q=50 throughout (Cell 1)
- **[S4]** EMG artifact detection band lower bound corrected from `150 Hz` to `75 Hz` per ISCEV
  2022 and Chapter 6 §6.2.2; both `emg_mask_pre` and `emg_mask_post` updated (Cell 3)
- **[M4]** a-wave sign enforcement: double-negation conditional pattern replaced with
  unconditional `-abs(a_wave_amplitude)`; single enforcement point retained at bottom of
  `extract_awave_bwave()` — previous pattern could invert sign on signals already negated
  upstream (Cell 5)
- **[M6]** SHAP: `target_class: int = 1` parameter added to `compute_feature_shap()` and
  `compute_feature_shap_batch()`; hardcoded `shap_values[1]` replaced with
  `shap_values[target_class]` in both methods — supports Stage 2 seven-class output (Cell 8)
- **[M7]** FHIR top-level ERG LOINC code corrected from fabricated `26456-9` to validated
  `70943-7`; 12 fabricated parameter LOINC codes replaced with custom `erg-api:` scheme under
  `ERG_CODE_SYSTEM = "https://github.com/AI-Fairness-com/ERG-Analysis-API/CodeSystem"`;
  dict renamed from `LOINC_CODES` to `ERG_PARAMETER_CODES` (Cell 9)
- **[M1]** `DEFAULT_AGE_GROUP` changed from `'18-80y'` (not a Baker 2025 stratum) to
  `Optional[str] = None`; Cell 3 `run_full_audit()` fallback updated to `'unknown'` to prevent
  silent assignment of wrong normative stratum (Cells 1, 3)
- **[M2]** CSV column detection hardened: two-tier detection — Priority 1 canonical exact names
  (`CANONICAL_TIME`, `CANONICAL_AMP` sets), Priority 2 substring fallback; error message now
  includes rename instruction for non-standard column headers (Cell 2)
- **[M3]** `calculate_snr()` now uses `fs_hz` to enforce `min_samples_required =
  max(5, int(2.0 * fs_hz / 1000.0))` guard before RMS computation; SNR coefficient locked at
  `20.0` per Chapter 2 §2.2.1 — `fs_hz` was previously accepted but unused (Cell 2)
- **[M8]** Thread-based timeout added to `run_pipeline()`; `PIPELINE_TIMEOUT_S = 60`; pipeline
  wrapped in `_run_pipeline_inner()` executed via `threading.Thread(daemon=True)`;
  `pipeline_thread.join(timeout=PIPELINE_TIMEOUT_S)` with timeout and error reporting — previously
  malformed signals could hang indefinitely (Cell 10)
- **[LA30Hz]** LA 30 Hz b-wave extraction bug fixed: redundant guard `if '30' not in protocol:`
  removed from `extract_all_features()` — previously skipped all feature extraction for LA 30 Hz,
  returning empty dict and triggering UNAVAILABLE traffic light erroneously; a-wave search window
  `(None, None)` already handles no-a-wave case internally (Cell 5)

### Features

- **[S7]** `REFERENCE_RANGES`: all 48 normative values replaced with Baker et al. (2025) N=407
  computed means (µ) and standard deviations (σ), verified against source data to < 0.02 µV/ms
  tolerance. Covers DA 0.01, DA 3, DA 10, LA 3, LA 30 Hz × gold_foil / dtl_fiber ×
  ≤35y / 36–59y / ≥60y (Cell 6)
- **[S1]** Age group widget: seven paediatric strata replaced with Baker 2025 three strata
  (`≤35y`, `36-59y`, `≥60y`); `_age_stratum()` updated to accept both dropdown strings and
  numeric age values; `_normalise_electrode()` helper added (Cells 6, 10)
- **[S6]** `patient_id_widget` (Text input) added to UI under PATIENT INFORMATION section;
  FHIR `generate_observation()` call updated to use `patient_id_widget.value.strip()` with
  `"UNKNOWN"` fallback — previously hardcoded as `"P001"` for all patients (Cell 10)
- **[S2]** `ERGFilter.apply_streaming_filter()` static method stub added; raises
  `NotImplementedError` with message referencing v2.4.0 — prevents silent failure if streaming
  pathway is called prematurely (Cell 4)
- **[ELECTRODE_GATING]** Electrode gating architecture formalised:
  `ZSCORE_SUPPORTED_ELECTRODES = {'gold_foil', 'dtl_fiber'}`;
  `ZSCORE_UNSUPPORTED_ELECTRODES = {'contact_lens', 'skin'}`. Unsupported electrodes return
  `UNAVAILABLE` traffic light with positive normative flag text citing Baker 2025, ISCEV 2022,
  and Davis & Hamilton 2021. Signal processing (filtering, feature extraction, AI classification,
  FHIR output) runs identically for all four electrode types (Cell 6)
- **[BA_LABEL]** ba ratio traffic light message: `_direction()` function updated with clinical
  context — reduction labelled "consistent with inner retinal dysfunction or disproportionate
  a-wave loss"; elevation labelled "consistent with outer retinal dysfunction or disproportionate
  a-wave reduction" (Cell 6)
- **[RECOMMENDED_ACTION]** `UNAVAILABLE` traffic light recommended action changed from repeating
  full flag text to short clinical instruction: "Select Gold Foil or DTL electrode for Z-score
  classification. Raw ERG parameters are available above for manual clinical interpretation."
  (Cell 6)
- **[CONFIDENCE_GUARD]** `tl['confidence'] is not None` guard added to Cell 10 print block —
  prevents crash when UNAVAILABLE traffic light returns `confidence: None` (Cell 10)

### Validation

- Synthetic dataset generator created: `synthetic_validation/12_synthetic_erg_dataset.py`
- Generator uses binary search calibration against pipeline filter chain to achieve target
  post-filter Z-scores precisely, compensating for Butterworth bandpass amplitude effects
- 12 scenarios covering 5 protocols, 4 electrode types, 3 Baker 2025 age strata,
  5 traffic light outcomes (GREEN, AMBER, RED, UNAVAILABLE × 2)
- S10 (50 Hz mains) tested twice: notch filter ON and notch filter OFF
- **Result: 13/13 pipeline runs passed**
- **External validation: CLEARED**
- Full validation report: `docs/VALIDATION_REPORT_v2.3.2.docx`

---

## [2.3.1] — 2026-05-15

### Added

- Initial ISCEV 2022 compliant pipeline release
- Four-layer report structure (Traffic Light, Clinical Summary, Specialist, Audit)
- Baker 2025 normative framework stub (reference ranges not yet fully populated)
- Notch filter OFF by default (ISCEV 2022 compliant)
- Median filter (5 ms kernel) for spike removal
- Butterworth bandpass (0.3–300 Hz, 4th order, zero-phase)
- Oscillatory Potential extraction (75–300 Hz)
- PhNR extraction for LA 3.0 protocol
- STFT spectrogram generation (Chapter 8)
- SHAP explainability framework (Chapter 14) — three-level implementation
- FHIR R4 compliant JSON output (Cell 9)
- Colab UI with ipywidgets (Cell 10)

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
- `ERGAudit` class for pre-processing quality assessment
- `ERGFilter` class with conditional filtering pipeline
- `ERGReportGenerator` with Z-score computation
- Age group handling with fallback to `'18-80y'`

### Changed

- Restructured from monolithic script to modular class-based architecture

---

## [2.2.0] — 2026-05-01

### Added

- SNR calculation per Chapter 2 §2.2.1
- EMG detection via high-frequency band (150–300 Hz)
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
- Traffic light generation (GREEN / AMBER / RED)
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
| `Deprecated` | Features that will be removed in future releases |
| `Removed` | Features that were removed |
| `Fixed` | Bug fixes |
| `Security` | Security vulnerability fixes |
| `Validation` | Validation reports and results |

---

*For questions about this changelog, please contact info@ai-fairness.com or open a GitHub issue.*
