"""
conftest.py — ERG Analysis API v2.5.0 test configuration
=========================================================
Stubs Google Colab and ipywidgets before the pipeline module is imported.
The pipeline is structured as a single-file notebook (Cells 1-10); Cell 10
contains Colab-specific UI code that cannot run outside Colab.  This conftest
intercepts those imports so pytest can load Cells 1-9 cleanly.

Place this file at:  tests/conftest.py
Run tests from repo root with:  pytest tests/ -v
"""

import sys
import types
import pathlib
import unittest.mock as mock
import pytest


# ---------------------------------------------------------------------------
# 1. Stub Colab / widget dependencies before anything else imports them
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "google",
    "google.colab",
    "ipywidgets",
    "IPython",
    "IPython.display",
    "skimage",
    "skimage.transform",
]
for _mod in _STUB_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = mock.MagicMock()


# ---------------------------------------------------------------------------
# 2. Make the repo root importable so `import erg_v2_4_0` works
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# 3. Import the pipeline module once and cache on the pytest session
# ---------------------------------------------------------------------------
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("erg_v2_5_0", _REPO_ROOT / "api" / "erg_v2_5_0.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["erg_v2_5_0"] = _mod


# ---------------------------------------------------------------------------
# 4. Session-scoped fixtures shared by both test files
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def pipeline_module():
    """Return the imported erg_v2_5_0 module."""
    return _mod


@pytest.fixture(scope="session")
def s01_csv_path():
    """Absolute path to the locked regression fixture CSV."""
    p = _REPO_ROOT / "data" / "samples" / "S_Normal_DA3_GoldFoil_le35.csv"
    assert p.exists(), f"Regression fixture not found: {p}"
    return str(p)


@pytest.fixture(scope="session")
def s01_result(pipeline_module, s01_csv_path):
    """
    Run the full pipeline on S01 once per session and return the result dict.
    Keys used in tests:
        result['features']         — extracted waveform features
        result['z_scores']         — Z-score dict from Layer 2
        result['traffic_light']    — traffic light dict from Layer 1
        result['fhir']             — FHIR Observation dict
        result['audit']            — audit result dict from ERGAudit
    """
    mod = pipeline_module
    import numpy as np

    PRE_MS   = 50.0
    FS_HZ    = 2000.0
    PROTOCOL = "DA 3"
    ELECTRODE = "gold_foil"
    AGE_GROUP = "≤35y"

    time_ms, signal_uv, fs_hz, metadata = mod.load_erg_csv(s01_csv_path)

    flash_onset_sample   = int(PRE_MS * fs_hz / 1000)
    prestimulus_samples  = flash_onset_sample
    pre_stim             = signal_uv[:prestimulus_samples]
    noise_rms            = float(np.sqrt(np.mean(pre_stim ** 2)))

    auditor      = mod.ERGAudit()
    audit_result = auditor.run_full_audit(
        signal_uv, fs_hz,
        electrode_type=ELECTRODE,
        prestimulus_samples=prestimulus_samples,
        age_group=AGE_GROUP,
    )

    filt_obj                     = mod.ERGFilter()
    filtered_signal, filter_log  = filt_obj.run_filter_pipeline(
        signal_uv, fs_hz,
        apply_notch=False, notch_hz=50.0,
        hardware_cutoff_hz=None,
        user_confirmed_notch=False,
    )

    extractor = mod.ERGFeatureExtractor()
    features  = extractor.extract_all_features(
        signal=filtered_signal,
        fs_hz=fs_hz,
        protocol=PROTOCOL,
        flash_onset_sample=flash_onset_sample,
        flash_duration_ms=0.0,
        op_signal=None,
        noise_rms_uv=noise_rms,
    )

    report_gen  = mod.ERGReportGenerator()
    full_report = report_gen.generate_full_report(
        features=features,
        audit_results=audit_result,
        electrode_type=ELECTRODE,
        protocol=PROTOCOL,
        age_years=AGE_GROUP,
        filtered_signal=filtered_signal,
        time_ms=time_ms,
        filter_log=filter_log,
        processing_time_ms=0.0,
    )

    fhir_gen    = mod.ERGFHIRGenerator()
    fhir_obs    = fhir_gen.generate_observation(
        report_id=full_report["layer_4_technical_audit"]["report_id"],
        patient_id="S01-TEST",
        traffic_light=full_report["layer_1_traffic_light"],
        features=features,
        z_scores=full_report["layer_2_clinical_summary"]["z_scores"],
        audit_results=audit_result,
        electrode_type=ELECTRODE,
        protocol=PROTOCOL,
    )

    return {
        "features":      features,
        "z_scores":      full_report["layer_2_clinical_summary"]["z_scores"],
        "traffic_light": full_report["layer_1_traffic_light"],
        "fhir":          fhir_obs,
        "audit":         audit_result,
        "full_report":   full_report,
    }
