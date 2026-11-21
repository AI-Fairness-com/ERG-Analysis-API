"""Chapter 19: Pipeline walkthrough on a synthetic recording.

Code from Section 19.11 of "Hands-On Electroretinography in the Age
of AI". It runs the implemented stages of the pipeline (ingestion,
signal quality, filtering, feature extraction and the four report
layers) on data/samples/normal_001_DA3.csv. Run it from the
repository root, for example in Google Colab.
"""

# ── Pipeline walkthrough on a synthetic recording (Section 19.11)
# Prerequisites: repository cloned, requirements.txt installed,
# working directory set to the repository root (for example in
# Google Colab).
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, "api")
import erg_v2_5_0 as erg

# The report generator reads the Baker et al. (2025) limits
# from data/.
os.makedirs("data", exist_ok=True)
shutil.copy("data/samples/normative_data_baker2025.json", "data/")

CSV_PATH = "data/samples/normal_001_DA3.csv"
PROTOCOL = "DA 3.0"
ELECTRODE = "dtl_fiber"
AGE_GROUP = "≤35y"          # Baker et al. (2025) stratum 1
PRESTIM_MS = 100            # the flash occurs 100 ms into this file
FLASH_MS = 1.0

# ── Stage 1: ingestion ──────────────────────────────────────────
time_ms, signal_uv, fs_hz, meta = erg.load_erg_csv(CSV_PATH)
flash_sample = int(PRESTIM_MS * fs_hz / 1000)
print(f"Stage 1: {meta['n_samples']} samples at {fs_hz:.0f} Hz")

# ── Stage 2: signal quality ─────────────────────────────────────
audit = erg.run_full_audit(
    signal_uv, fs_hz,
    electrode_type=ELECTRODE,
    prestimulus_samples=flash_sample,
    age_group="18-80y",
    flash_duration_ms=FLASH_MS)
snr = audit["snr"]
print(f"Stage 2: SNR {snr['linear']} ({snr['status']}), "
      f"quality grade {audit['quality']['grade']}")

# ── Stage 3: pre-processing ─────────────────────────────────────
filtered, filter_log = erg.run_filter_pipeline(
    signal_uv, fs_hz,
    hardware_cutoff_hz=audit["bandwidth"].get("hardware_cutoff_hz"))
print("Stage 3:", filter_log[-1])

# ── Stage 4: feature extraction ─────────────────────────────────
noise_rms_uv = float(np.sqrt(np.mean(signal_uv[:flash_sample] ** 2)))
features = erg.extract_all_features(
    filtered, fs_hz,
    protocol=PROTOCOL,
    flash_onset_sample=flash_sample,
    flash_duration_ms=FLASH_MS,
    noise_rms_uv=noise_rms_uv)
print(f"Stage 4: a-wave {features['a_amp_uv']} µV, "
      f"b-wave {features['b_amp_uv']} µV")

# ── Stages 5 and 8: normative zoning and report generation ──────
report = erg.ERGReportGenerator().generate_full_report(
    features=features,
    audit_results=audit,
    electrode_type=ELECTRODE,
    protocol=PROTOCOL,
    age_years=AGE_GROUP,
    filtered_signal=filtered,
    time_ms=time_ms,
    filter_log=filter_log,
    processing_time_ms=0.0)

layer1 = report["layer_1_traffic_light"]
print(f"Layer 1: {layer1['signal']}")
layer2 = report["layer_2_clinical_summary"]
print("Layer 2:", layer2["recommended_action"])
print("Layer 3:", report["layer_3_specialist"]["status"])
print("Layer 4:", report["layer_4_technical_audit"]["report_id"])
