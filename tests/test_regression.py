"""
tests/test_regression.py
========================
Non-regression baseline tests, anchored to the locked S01 fixture:
  S_Normal_DA3_GoldFoil_le35.csv  (seed 1, DA 3.0, <=35y)
The fixture was generated on the silver thread amplitude scale, so it is
analysed as a DTL fiber recording against the Baker et al. (2025) limits.

These tests lock the pipeline's numerical output so that any change to
filtering, feature extraction, zone assignment, FHIR generation, or the
normative file immediately surfaces as a regression failure.
  T-REG-01  a-wave amplitude = 137.7 uV ± 1.0, zone GREEN
  T-REG-02  b-wave amplitude = 281.1 uV ± 1.0, zone GREEN
  T-REG-03  b-wave implicit time = 51.0 ms ± 0.5, zone GREEN
  T-REG-04  b/a ratio = 2.05 ± 0.05, not zoned
  T-REG-05  composite traffic light = GREEN
  T-REG-06  FHIR status   = final
  T-REG-07  FHIR version stamp contains the pipeline version
  T-REG-08  PhNR absent for DA 3.0 protocol

Run from repo root:
    pytest tests/test_regression.py -v
"""

import math
import pytest


def _row(s01_result, parameter):
    return next(r for r in s01_result["parameter_zones"] if r["parameter"] == parameter)


@pytest.mark.parametrize("test_id, parameter, expected, tolerance, zone", [
    ("T-REG-01", "a_amp",    137.7, 1.0,  "GREEN"),
    ("T-REG-02", "b_amp",    281.1, 1.0,  "GREEN"),
    ("T-REG-03", "b_imp",     51.0, 0.5,  "GREEN"),
    ("T-REG-04", "ba_ratio",   2.05, 0.05, "NOT ZONED"),
])
def test_T_REG_01_to_04_values_and_zones(s01_result, test_id, parameter,
                                         expected, tolerance, zone):
    row = _row(s01_result, parameter)
    assert abs(row["value"] - expected) <= tolerance, (
        f"{test_id} FAIL: {parameter} = {row['value']}, expected {expected} ± {tolerance}")
    assert row["zone"] == zone, f"{test_id} FAIL: zone {row['zone']!r}, expected {zone!r}"


# ---------------------------------------------------------------------------
# T-REG-05  composite traffic light = GREEN
# ---------------------------------------------------------------------------
def test_T_REG_05_traffic_light_GREEN(s01_result):
    """T-REG-05: every zoned S01 value is within the <=35y limits."""
    signal = s01_result["traffic_light"]["signal"]
    assert signal == "GREEN", f"T-REG-05 FAIL: expected GREEN, got {signal!r}"


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
# T-REG-07  FHIR version stamp contains the pipeline version
# ---------------------------------------------------------------------------
def test_T_REG_07_fhir_version_stamp_contains_version(pipeline_module, s01_result):
    """
    T-REG-07: The version-stamp extension of the FHIR Observation must
    carry the pipeline version (CONFIG.PIPELINE_VERSION) as api_version,
    so every output can be traced (Appendix B §B.1, Chapter 17 §17.3.3).
    """
    version = pipeline_module.CONFIG.PIPELINE_VERSION
    stamp = next((e for e in s01_result["fhir"].get("extension", [])
                  if e["url"].endswith("/version-stamp")), None)
    assert stamp is not None, "T-REG-07 FAIL: version-stamp extension missing"
    parts = {p["url"]: p["valueString"] for p in stamp["extension"]}
    assert parts.get("api_version") == version, (
        f"T-REG-07 FAIL: api_version {parts.get('api_version')!r}, expected {version!r}"
    )
    assert set(parts) == {"api_version", "model_weights_hash",
                          "config_hash", "normative_ref_version"}


# ---------------------------------------------------------------------------
# T-REG-08  PhNR absent for DA 3.0
# ---------------------------------------------------------------------------
def test_T_REG_08_phnr_absent_for_DA3(s01_result):
    """
    T-REG-08: DA 3.0 is a scotopic protocol; PhNR extraction is only defined
    for LA 3.  The S01 result must either have no 'phnr_amp_uv' key in
    features, or the value must be NaN/None — never a numeric value.
    """
    feat    = s01_result["features"]
    phnr    = feat.get("phnr_amp_uv")

    is_absent  = phnr is None
    is_nan     = phnr is not None and isinstance(phnr, float) and math.isnan(phnr)

    assert is_absent or is_nan, (
        f"T-REG-08 FAIL: DA 3.0 should have no PhNR value, "
        f"but phnr_amp_uv = {phnr}"
    )
