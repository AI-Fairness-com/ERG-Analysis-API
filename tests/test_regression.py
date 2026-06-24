"""
tests/test_regression.py
========================
Tier 2 Step 2.3 — Non-regression baseline tests.
8 tests anchored to the locked S01 fixture:
  S_Normal_DA3_GoldFoil_le35.csv  (seed 1, DA 3, Gold Foil, ≤35y)

These tests lock the pipeline's numerical output so that any change to
filtering, feature extraction, Z-score computation, FHIR generation, or
the normative JSON immediately surfaces as a regression failure.

Expected Z-score values are taken from the Run 2 (22 Jun 2026) audit table,
confirmed in the VALIDATION_REPORT_v2_4_0_COMPLETE.docx.
  T-REG-01  a_amp Z = −1.20 ± 0.10
  T-REG-02  b_amp Z = −0.13 ± 0.10
  T-REG-03  b_it  Z = +0.50 ± 0.10
  T-REG-04  B/A   Z = −1.58 ± 0.10
  T-REG-05  traffic light = GREEN
  T-REG-06  FHIR status   = final
  T-REG-07  FHIR performer contains v2.4.0
  T-REG-08  PhNR absent for DA 3 protocol

Run from repo root:
    pytest tests/test_regression.py -v
"""

import math
import pytest


# ---------------------------------------------------------------------------
# T-REG-01  a-wave amplitude Z-score
# ---------------------------------------------------------------------------
def test_T_REG_01_a_amp_z_score(s01_result):
    """
    T-REG-01: S01 a-wave amplitude Z-score = −1.20 ± 0.10.
    Locks the a-wave amplitude extraction and Baker DA3 ≤35y a_amp norms.
    """
    Z = s01_result["z_scores"].get("a_wave_amplitude")
    assert Z is not None and not math.isnan(Z), "a_wave_amplitude Z-score missing"
    assert abs(Z - (-1.20)) <= 0.10, (
        f"T-REG-01 FAIL: a_amp Z = {Z:.3f}, expected −1.20 ± 0.10"
    )


# ---------------------------------------------------------------------------
# T-REG-02  b-wave amplitude Z-score
# ---------------------------------------------------------------------------
def test_T_REG_02_b_amp_z_score(s01_result):
    """
    T-REG-02: S01 b-wave amplitude Z-score = −0.13 ± 0.10.
    Locks the b-wave amplitude extraction and Baker DA3 ≤35y b_amp norms.
    """
    Z = s01_result["z_scores"].get("b_wave_amplitude")
    assert Z is not None and not math.isnan(Z), "b_wave_amplitude Z-score missing"
    assert abs(Z - (-0.13)) <= 0.10, (
        f"T-REG-02 FAIL: b_amp Z = {Z:.3f}, expected −0.13 ± 0.10"
    )


# ---------------------------------------------------------------------------
# T-REG-03  b-wave implicit time Z-score
# ---------------------------------------------------------------------------
def test_T_REG_03_b_it_z_score(s01_result):
    """
    T-REG-03: S01 b-wave implicit time Z-score = +0.50 ± 0.10.
    Locks the b-IT extraction and Baker DA3 ≤35y b_imp norms.
    """
    Z = s01_result["z_scores"].get("b_wave_implicit_time")
    assert Z is not None and not math.isnan(Z), "b_wave_implicit_time Z-score missing"
    assert abs(Z - 0.50) <= 0.10, (
        f"T-REG-03 FAIL: b_it Z = {Z:.3f}, expected +0.50 ± 0.10"
    )


# ---------------------------------------------------------------------------
# T-REG-04  B/A ratio Z-score
# ---------------------------------------------------------------------------
def test_T_REG_04_ba_ratio_z_score(s01_result):
    """
    T-REG-04: S01 B/A ratio Z-score = −1.58 ± 0.10.
    Locks the B/A ratio computation (mean=2.65, SD=0.425, DA 3 only).
    """
    Z = s01_result["z_scores"].get("ba_ratio")
    assert Z is not None and not math.isnan(Z), "ba_ratio Z-score missing"
    assert abs(Z - (-1.58)) <= 0.10, (
        f"T-REG-04 FAIL: B/A Z = {Z:.3f}, expected −1.58 ± 0.10"
    )


# ---------------------------------------------------------------------------
# T-REG-05  Traffic light GREEN
# ---------------------------------------------------------------------------
def test_T_REG_05_traffic_light_GREEN(s01_result):
    """
    T-REG-05: S01 overall traffic light = GREEN.
    All four Z-scores are within |Z| ≤ 2.0 so the signal must be GREEN.
    """
    signal = s01_result["traffic_light"]["signal"]
    assert signal == "GREEN", (
        f"T-REG-05 FAIL: expected GREEN, got {signal!r}"
    )


# ---------------------------------------------------------------------------
# T-REG-06  FHIR status = final
# ---------------------------------------------------------------------------
def test_T_REG_06_fhir_status_final(s01_result):
    """
    T-REG-06: FHIR Observation status must be 'final'.
    Locks the FHIR generation Cell 9 status field.
    """
    status = s01_result["fhir"].get("status")
    assert status == "final", (
        f"T-REG-06 FAIL: FHIR status = {status!r}, expected 'final'"
    )


# ---------------------------------------------------------------------------
# T-REG-07  FHIR performer contains v2.4.0
# ---------------------------------------------------------------------------
def test_T_REG_07_fhir_performer_contains_version(s01_result):
    """
    T-REG-07: The FHIR performer display string must contain 'v2.4.0'.
    Locks the pipeline version string in the FHIR output.
    """
    performers = s01_result["fhir"].get("performer", [])
    displays   = [p.get("display", "") for p in performers]
    combined   = " ".join(displays)
    assert "2.4.0" in combined, (
        f"T-REG-07 FAIL: 'v2.4.0' not found in FHIR performer. "
        f"Performer displays: {displays}"
    )


# ---------------------------------------------------------------------------
# T-REG-08  PhNR absent for DA 3
# ---------------------------------------------------------------------------
def test_T_REG_08_phnr_absent_for_DA3(s01_result):
    """
    T-REG-08: DA 3 is a scotopic protocol; PhNR extraction is only defined
    for LA 3.  The S01 result must either have no 'phnr_amp_uv' key in
    features, or the value must be NaN/None — never a numeric value.
    """
    feat    = s01_result["features"]
    phnr    = feat.get("phnr_amp_uv")

    is_absent  = phnr is None
    is_nan     = phnr is not None and isinstance(phnr, float) and math.isnan(phnr)

    assert is_absent or is_nan, (
        f"T-REG-08 FAIL: DA 3 should have no PhNR value, "
        f"but phnr_amp_uv = {phnr}"
    )
