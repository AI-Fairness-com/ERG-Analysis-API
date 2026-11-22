"""
Exact-boundary and rule tests for v2.5.0 (synthetic validation companion).

The CSV set in synthetic_validation/ checks the whole API with values well
inside each zone, because a waveform cannot hit a limit to 0.1 uV. These
tests feed numbers straight into the rules, at the limits themselves:

  T-BND-01  Equation 10.2 at L, L_lo, U and U_hi, for every protocol,
            parameter and age group in the normative file (Chapter 10)
  T-SNR-01  Table 2.3 Pass/Warning/Fail boundaries for the four electrodes
            (Chapter 2)
  T-MED-01  Median filter of 5 samples removes a 1-sample spike and keeps
            a 3-sample one (Chapter 5)
  T-QF-01   A recording with a Fail SNR gets no Traffic Light (Chapter 2)
  T-NR-01   A wave coded as not recordable is RED (Chapter 11)
"""
import json
import pathlib

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).parent.parent
NORM = json.loads((ROOT / "data" / "samples" /
                   "normative_data_baker2025.json").read_text())
CASES = [(pr, p, st) for pr, ps in NORM["limits"].items()
         for p, sts in ps.items() for st in sts]


@pytest.mark.parametrize("protocol,param,stratum", CASES)
def test_T_BND_01_equation_10_2_at_every_limit(pipeline_module, protocol,
                                               param, stratum):
    lim = pipeline_module.ERGReportGenerator().get_limits(protocol, param, stratum)
    L, U = lim["lower"], lim["upper"]
    L_lo, U_hi = lim["lower_ci"][0], lim["upper_ci"][1]
    kind = NORM["parameters"][param]["kind"]
    zone = lambda x: pipeline_module.classify_against_limits(x, lim, kind)["zone"]
    assert zone(L) == "GREEN" and zone(U) == "GREEN"
    if kind == "amplitude":
        assert zone(U + 0.1) == "ATYPICAL DIRECTION"
        assert zone(L_lo) == ("AMBER" if L_lo < L else "GREEN")
        assert zone(L_lo - 0.1) == "RED"
    else:
        assert zone(L - 0.1) == "ATYPICAL DIRECTION"
        assert zone(U_hi) == ("AMBER" if U_hi > U else "GREEN")
        assert zone(U_hi + 0.1) == "RED"


@pytest.mark.parametrize("electrode,pass_at,fail_below", [
    ("contact_lens", 8.0, 4.0), ("gold_foil", 6.0, 3.0),
    ("dtl_fiber", 4.0, 2.5), ("skin", 3.0, 2.0)])
def test_T_SNR_01_table_2_3_boundaries(pipeline_module, electrode, pass_at,
                                       fail_below):
    status = lambda s: pipeline_module.CONFIG.get_electrode_snr_status(electrode, s)[0]
    assert status(pass_at) == "PASS"
    assert status(pass_at - 0.1) == "WARNING"
    assert status(fail_below) == "WARNING"
    assert status(fail_below - 0.1) == "FAIL"


def test_T_MED_01_median_kernel_is_5_samples(pipeline_module):
    assert pipeline_module.CONFIG.MEDIAN_KERNEL_SAMPLES == 5
    x = np.zeros(200)
    x[50] = 100.0                      # one-sample spike: removed
    x[120:123] = 100.0                 # three-sample spike: passes through
    y = pipeline_module.apply_median_filter(x, 2000.0)
    assert y[50] == 0.0
    assert y[121] == 100.0


def test_T_QF_01_fail_recording_gets_no_traffic_light(pipeline_module):
    rgen = pipeline_module.ERGReportGenerator()
    features = {"a_amp_uv": 60.0, "a_implicit_ms": 15.0,
                "b_amp_uv": 100.0, "b_implicit_ms": 50.0}
    audit = {"snr": {"linear": 1.8, "electrode_type": "dtl_fiber",
                     "status": "FAIL"}}
    report = rgen.generate_full_report(
        features=features, audit_results=audit, electrode_type="dtl_fiber",
        protocol="DA 3.0", age_years=30, filtered_signal=np.zeros(10),
        time_ms=np.arange(10.0), filter_log=[], processing_time_ms=1.0)
    tl = report["layer_1_traffic_light"]
    assert tl["signal"] not in ("GREEN", "AMBER", "RED", "ATYPICAL DIRECTION")
    assert tl.get("quality_fail") is True
    assert "Signal quality FAIL" in tl["message"]


def test_T_NR_01_not_recordable_is_red(pipeline_module):
    rows = pipeline_module.ERGReportGenerator().classify_parameters(
        {"b_amp_uv": -9999.0, "b_implicit_ms": 9999.0},
        "dtl_fiber", "DA 0.01", 30)
    zones = {r["parameter"]: r for r in rows}
    assert zones["b_amp"]["zone"] == "RED" and zones["b_amp"]["not_recordable"]
    assert zones["b_imp"]["zone"] == "RED" and zones["b_imp"]["not_recordable"]
