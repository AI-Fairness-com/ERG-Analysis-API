"""
tests/test_pipeline.py — core pipeline tests.
T-CSV-01/02, T-FILT-01, T-WAVE-01/02, T-LIM-01 to 05 (reference-limit
zones, Chapter 10 §10.4 and the Chapter 19 tables), T-FHIR-01 to 05,
T-GF-01 (gold foil conversion), T-ORIENT-01/02, T-ELEC-01.
"""
import math, pytest


class TestCSVLoading:
    def test_T_CSV_01_canonical_column_names(self, pipeline_module, s01_csv_path):
        mod = pipeline_module
        time_ms, signal_uv, fs_hz, metadata = mod.load_erg_csv(s01_csv_path)
        assert len(time_ms) > 0 and len(signal_uv) > 0
        assert len(time_ms) == len(signal_uv) and fs_hz > 0

    def test_T_CSV_02_fallback_column_detection(self, pipeline_module, tmp_path):
        import pandas as pd, numpy as np
        mod = pipeline_module
        t = np.arange(0, 300, 0.5)
        df = pd.DataFrame({"recording_time_ms": t, "signal_amplitude_uV": np.zeros(len(t))})
        p = tmp_path / "fallback.csv"; df.to_csv(p, index=False)
        try:
            time_ms, _, _, _ = mod.load_erg_csv(str(p))
            assert len(time_ms) > 0
        except Exception as e:
            assert "rename" in str(e).lower() or "column" in str(e).lower()


class TestFiltering:
    def test_T_FILT_01_bandpass_preserves_30Hz(self, pipeline_module):
        import numpy as np
        mod = pipeline_module
        fs = 2000.0; t = np.arange(0, 1.0, 1.0/fs)
        sig = np.sin(2*math.pi*30.0*t)*100
        filtered, _ = mod.run_filter_pipeline(sig.copy(), fs, apply_notch=False,
                                                    notch_hz=50.0, hardware_cutoff_hz=None,
                                                    user_confirmed_notch=False)
        ratio = float((filtered**2).mean()**0.5) / float((sig**2).mean()**0.5)
        assert ratio >= 0.80, f"T-FILT-01: 30Hz attenuated by {(1-ratio)*100:.1f}%"


class TestWaveformExtraction:
    def test_T_WAVE_01_a_wave_amplitude_detected(self, s01_result):
        a = s01_result["features"].get("a_amp_uv")
        assert a is not None and not math.isnan(a) and a > 0, f"T-WAVE-01: a={a}"

    def test_T_WAVE_02_b_wave_peak_follows_a_wave_trough(self, s01_result):
        f = s01_result["features"]
        a_it = f.get("a_implicit_ms"); b_it = f.get("b_implicit_ms")
        assert a_it is not None and b_it is not None and b_it > a_it


class TestReferenceLimits:
    """Equation 10.2 and Table 10.4 of Chapter 10 §10.4, with the
    Baker et al. (2025) Tables 4 and 5 limits held in the normative file."""

    def test_T_LIM_01_amplitude_zones_at_boundaries(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        lim = rgen.get_limits("DA 3.0", "a_amp", "le35")   # 119-238, L_lo 109
        assert (lim["lower"], lim["upper"], lim["lower_ci"][0]) == (119, 238, 109)
        zone = lambda x: pipeline_module.classify_against_limits(x, lim, "amplitude")["zone"]
        assert zone(119) == "GREEN" and zone(238) == "GREEN"
        assert zone(118.9) == "AMBER" and zone(109) == "AMBER"
        assert zone(108.9) == "RED"
        assert zone(238.1) == "ATYPICAL DIRECTION"

    def test_T_LIM_02_implicit_time_zones_at_boundaries(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        lim = rgen.get_limits("DA 3.0", "a_imp", "le35")   # 13.5-16, U_hi 17
        assert (lim["lower"], lim["upper"], lim["upper_ci"][1]) == (13.5, 16, 17)
        zone = lambda x: pipeline_module.classify_against_limits(x, lim, "implicit_time")["zone"]
        assert zone(13.5) == "GREEN" and zone(16) == "GREEN"
        assert zone(16.1) == "AMBER" and zone(17) == "AMBER"
        assert zone(17.1) == "RED"
        assert zone(13.4) == "ATYPICAL DIRECTION"

    # Every zoned value of the Chapter 19 case tables (Tables 19.1 to 19.9):
    # (age group, protocol, parameter, value, zone printed in the book)
    CHAPTER_19 = [
    ("le35", "DA 0.01", "b_amp", 190, "GREEN"),
    ("le35", "DA 0.01", "b_amp", 215, "GREEN"),
    ("le35", "DA 0.01", "b_imp", 84, "GREEN"),
    ("le35", "DA 0.01", "b_imp", 98, "GREEN"),
    ("le35", "DA 10.0", "a_amp", 50, "RED"),
    ("le35", "DA 10.0", "a_amp", 140, "GREEN"),
    ("le35", "DA 10.0", "a_imp", 13.1, "GREEN"),
    ("le35", "DA 10.0", "a_imp", 14.8, "RED"),
    ("le35", "DA 10.0", "b_amp", 60, "RED"),
    ("le35", "DA 10.0", "b_amp", 110, "RED"),
    ("le35", "DA 10.0", "b_amp", 240, "GREEN"),
    ("le35", "DA 10.0", "b_imp", 55, "GREEN"),
    ("le35", "DA 10.0", "b_imp", 58, "GREEN"),
    ("le35", "DA 3.0", "a_amp", 32, "RED"),
    ("le35", "DA 3.0", "a_amp", 95, "RED"),
    ("le35", "DA 3.0", "a_amp", 150, "GREEN"),
    ("le35", "DA 3.0", "a_amp", 170, "GREEN"),
    ("le35", "DA 3.0", "a_imp", 15, "GREEN"),
    ("le35", "DA 3.0", "a_imp", 15.2, "GREEN"),
    ("le35", "DA 3.0", "a_imp", 16.4, "AMBER"),
    ("le35", "DA 3.0", "a_imp", 19.5, "RED"),
    ("le35", "DA 3.0", "b_amp", 41, "RED"),
    ("le35", "DA 3.0", "b_amp", 95, "RED"),
    ("le35", "DA 3.0", "b_amp", 205, "GREEN"),
    ("le35", "DA 3.0", "b_amp", 280, "GREEN"),
    ("le35", "DA 3.0", "b_imp", 52, "GREEN"),
    ("le35", "DA 3.0", "b_imp", 52.1, "GREEN"),
    ("le35", "DA 3.0", "b_imp", 54, "GREEN"),
    ("le35", "DA 3.0", "b_imp", 72, "RED"),
    ("le35", "LA 3.0", "a_amp", 8, "RED"),
    ("le35", "LA 3.0", "a_amp", 14, "GREEN"),
    ("le35", "LA 3.0", "a_amp", 20, "GREEN"),
    ("le35", "LA 3.0", "a_amp", 24, "GREEN"),
    ("le35", "LA 3.0", "a_imp", 14.1, "GREEN"),
    ("le35", "LA 3.0", "a_imp", 14.2, "GREEN"),
    ("le35", "LA 3.0", "a_imp", 14.8, "GREEN"),
    ("le35", "LA 3.0", "a_imp", 15.5, "GREEN"),
    ("le35", "LA 3.0", "b_amp", 40, "RED"),
    ("le35", "LA 3.0", "b_amp", 58, "AMBER"),
    ("le35", "LA 3.0", "b_amp", 60, "AMBER"),
    ("le35", "LA 3.0", "b_amp", 70, "AMBER"),
    ("le35", "LA 3.0", "b_imp", 29, "GREEN"),
    ("le35", "LA 3.0", "b_imp", 29.6, "GREEN"),
    ("le35", "LA 3.0", "b_imp", 29.8, "GREEN"),
    ("le35", "LA 3.0", "b_imp", 33, "RED"),
    ("36to59", "DA 0.01", "b_amp", 175, "GREEN"),
    ("36to59", "DA 0.01", "b_imp", 98.6, "GREEN"),
    ("36to59", "DA 10.0", "a_amp", 180, "GREEN"),
    ("36to59", "DA 10.0", "a_imp", 15.6, "AMBER"),
    ("36to59", "DA 10.0", "b_amp", 280, "GREEN"),
    ("36to59", "DA 10.0", "b_imp", 52, "GREEN"),
    ("36to59", "DA 3.0", "a_amp", 150, "GREEN"),
    ("36to59", "DA 3.0", "a_imp", 17.3, "AMBER"),
    ("36to59", "DA 3.0", "b_amp", 240, "GREEN"),
    ("36to59", "DA 3.0", "b_imp", 49.8, "GREEN"),
    ("36to59", "LA 3.0", "a_amp", 22, "GREEN"),
    ("36to59", "LA 3.0", "a_imp", 14.2, "GREEN"),
    ("36to59", "LA 3.0", "b_amp", 100, "GREEN"),
    ("36to59", "LA 3.0", "b_imp", 29.4, "GREEN"),
    ("ge60", "DA 0.01", "b_amp", 190, "GREEN"),
    ("ge60", "DA 0.01", "b_imp", 98, "GREEN"),
    ("ge60", "DA 10.0", "a_amp", 140, "GREEN"),
    ("ge60", "DA 10.0", "a_imp", 13.1, "GREEN"),
    ("ge60", "DA 10.0", "b_amp", 240, "GREEN"),
    ("ge60", "DA 10.0", "b_imp", 55, "GREEN"),
    ("ge60", "DA 3.0", "a_amp", 95, "GREEN"),
    ("ge60", "DA 3.0", "a_amp", 105, "GREEN"),
    ("ge60", "DA 3.0", "a_amp", 112, "GREEN"),
    ("ge60", "DA 3.0", "a_imp", 16.2, "GREEN"),
    ("ge60", "DA 3.0", "a_imp", 16.4, "GREEN"),
    ("ge60", "DA 3.0", "a_imp", 16.6, "GREEN"),
    ("ge60", "DA 3.0", "b_amp", 195, "GREEN"),
    ("ge60", "DA 3.0", "b_amp", 205, "GREEN"),
    ("ge60", "DA 3.0", "b_amp", 215, "GREEN"),
    ("ge60", "DA 3.0", "b_imp", 51.4, "GREEN"),
    ("ge60", "DA 3.0", "b_imp", 52.1, "GREEN"),
    ("ge60", "DA 3.0", "b_imp", 53, "GREEN"),
    ("ge60", "LA 3.0", "a_amp", 19, "GREEN"),
    ("ge60", "LA 3.0", "a_amp", 20, "GREEN"),
    ("ge60", "LA 3.0", "a_amp", 21, "GREEN"),
    ("ge60", "LA 3.0", "a_imp", 14.2, "GREEN"),
    ("ge60", "LA 3.0", "a_imp", 14.3, "GREEN"),
    ("ge60", "LA 3.0", "a_imp", 14.4, "GREEN"),
    ("ge60", "LA 3.0", "b_amp", 52, "GREEN"),
    ("ge60", "LA 3.0", "b_amp", 58, "GREEN"),
    ("ge60", "LA 3.0", "b_amp", 90, "GREEN"),
    ("ge60", "LA 3.0", "b_imp", 28.1, "GREEN"),
    ("ge60", "LA 3.0", "b_imp", 29.6, "GREEN"),
    ("ge60", "LA 3.0", "b_imp", 29.8, "GREEN"),
    ]

    def test_T_LIM_03_reproduces_chapter_19_zones(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        wrong = []
        for stratum, protocol, param, x, expected in self.CHAPTER_19:
            kind = "amplitude" if param.endswith("_amp") else "implicit_time"
            got = pipeline_module.classify_against_limits(
                x, rgen.get_limits(protocol, param, stratum), kind)["zone"]
            if got != expected:
                wrong.append((stratum, protocol, param, x, expected, got))
        assert not wrong, f"T-LIM-03: zones differ from Chapter 19: {wrong}"

    def test_T_LIM_04_composite_is_most_severe_zone(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        base = {"a_amp_uv": 150, "a_implicit_ms": 15, "b_amp_uv": 300, "b_implicit_ms": 52}
        def signal(**changes):
            rows = rgen.classify_parameters({**base, **changes}, "dtl_fiber", "DA 3.0", "≤35y")
            return rgen.composite_traffic_light(rows, "dtl_fiber")["signal"]
        assert signal() == "GREEN"
        assert signal(a_amp_uv=300) == "ATYPICAL DIRECTION"
        assert signal(a_amp_uv=300, b_amp_uv=185) == "AMBER"
        assert signal(a_amp_uv=300, b_amp_uv=185, b_implicit_ms=70) == "RED"

    def test_T_LIM_05_unzoned_parameters_reported_without_zone(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        rows = rgen.classify_parameters(
            {"b_amp_uv": 300, "b_implicit_ms": 52, "ba_ratio": 2.1}, "dtl_fiber", "DA 3.0", "≤35y")
        ba = next(r for r in rows if r["parameter"] == "ba_ratio")
        assert ba["zone"] == "NOT ZONED" and ba["value"] == 2.1


class TestFHIROutput:
    def test_T_FHIR_01_resourceType_is_Observation(self, s01_result):
        assert s01_result["fhir"].get("resourceType") == "Observation"

    def test_T_FHIR_02_LOINC_79894_2_present(self, s01_result):
        codes = [c.get("code") for c in s01_result["fhir"].get("code",{}).get("coding",[])]
        assert "79894-2" in codes, f"T-FHIR-02: codes={codes}"

    def test_T_FHIR_03_components_use_table_B1_codes(self, s01_result):
        """DA 3.0, right eye: a-wave and b-wave values carry the OD LOINC
        codes of Table B.1; the b/a ratio uses the project code system."""
        comps = s01_result["fhir"].get("component", [])
        codes = {c["code"]["coding"][0]["code"] for c in comps}
        for code in ("79773-8", "79777-9", "79781-1", "79786-0", "ba_ratio"):
            assert code in codes, f"T-FHIR-03: {code} missing; codes={sorted(codes)}"
        units = {c["code"]["coding"][0]["code"]: c["valueQuantity"]["code"] for c in comps}
        assert units["79773-8"] == "uV" and units["79777-9"] == "ms"

    def test_T_FHIR_04_extensions_use_project_base(self, s01_result):
        urls = [e["url"] for e in s01_result["fhir"].get("extension", [])]
        base = "https://ai-fairness.com/fhir/erg/StructureDefinition/"
        for name in ("iscev-protocol", "electrode-type", "version-stamp"):
            assert base + name in urls, f"T-FHIR-04: {name} missing; urls={urls}"

    def test_T_FHIR_05_bundle_holds_report_and_audit(self, s01_result):
        bundle = s01_result["fhir_bundle"]
        assert bundle["resourceType"] == "Bundle" and bundle["type"] == "collection"
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        for rt in ("Observation", "DiagnosticReport", "AuditEvent"):
            assert rt in types, f"T-FHIR-05: {rt} missing; types={types}"
        audit = next(e["resource"] for e in bundle["entry"]
                     if e["resource"]["resourceType"] == "AuditEvent")
        assert audit["type"]["code"] == "110100" and audit["outcome"] == "0"


class TestGoldFoilConversion:
    def test_T_GF_01_gold_foil_amplitude_converted_to_silver_thread(self, pipeline_module):
        """Baker et al. (2025) Table 2: ST = slope * GF + intercept for
        amplitudes; peak times and DTL fiber values are unchanged."""
        rgen = pipeline_module.ERGReportGenerator()
        model = rgen.ELECTRODE_TRANSFORM["DA 3.0"]["a_amp"]
        assert (model["slope"], model["intercept"]) == (0.56, 8.24)
        value, converted = rgen.to_silver_thread("gold_foil", "DA 3.0", "a_amp", 200.0)
        assert converted and value == round(0.56 * 200.0 + 8.24, 1)
        assert rgen.to_silver_thread("gold_foil", "DA 3.0", "a_imp", 15.0) == (15.0, False)
        assert rgen.to_silver_thread("dtl_fiber", "DA 3.0", "a_amp", 200.0) == (200.0, False)
        flicker, _ = rgen.to_silver_thread("gold_foil", "LA 30 Hz", "b_amp", 100.0)
        assert flicker == 63.5   # Table 2 legend: 100 uV gold foil -> 63.46 uV


class TestSignalOrientation:

    def test_T_ORIENT_01_inverted_signal_corrected_and_flagged(
            self, pipeline_module, s01_csv_path):
        """
        T-ORIENT-01: Artificially inverted waveform must be auto-corrected.
        (a) a-wave amplitude negative after correction
        (b) inverted_polarity_detected = True in features
        (c) Layer 4 warning present and contains 'corrected'
        (d) traffic light still GREEN (analysed as DTL fiber, like S01)
        (e) FHIR note contains 'inverted' or 'polarity'
        """
        import numpy as np
        mod = pipeline_module
        PRE_MS=50.0; PROTOCOL="DA 3.0"; ELECTRODE="dtl_fiber"; AGE="≤35y"

        time_ms, signal_uv, fs_hz, _ = mod.load_erg_csv(s01_csv_path)
        flash_onset = int(PRE_MS * fs_hz / 1000)
        inv_sig = signal_uv * -1.0
        noise_rms = float(np.sqrt(np.mean(inv_sig[:flash_onset]**2)))

        audit   = mod.run_full_audit(inv_sig, fs_hz, electrode_type=ELECTRODE,
                                         prestimulus_samples=flash_onset, age_group=AGE)
        filtered, filter_log = mod.run_filter_pipeline(
            inv_sig, fs_hz, apply_notch=False, notch_hz=50.0,
            hardware_cutoff_hz=None, user_confirmed_notch=False)
        features  = mod.extract_all_features(
            signal=filtered, fs_hz=fs_hz, protocol=PROTOCOL,
            flash_onset_sample=flash_onset, flash_duration_ms=0.0,
            op_signal=None, noise_rms_uv=noise_rms)

        # (a)
        a_amp = features.get("a_amp_uv")
        assert a_amp is not None and not math.isnan(a_amp) and a_amp > 0, (
            f"T-ORIENT-01(a): a-wave must be detected after correction (amplitude reported as a positive baseline-to-trough value), got {a_amp}")

        # (b)
        assert features.get("inverted_polarity_detected") is True, (
            "T-ORIENT-01(b): inverted_polarity_detected must be True")

        # (c) Layer 4 warning
        report_gen = mod.ERGReportGenerator()
        full_report = report_gen.generate_full_report(
            features=features, audit_results=audit, electrode_type=ELECTRODE,
            protocol=PROTOCOL, age_years=AGE, filtered_signal=filtered,
            time_ms=time_ms, filter_log=filter_log, processing_time_ms=0.0)
        l4 = full_report["layer_4_technical_audit"]
        assert l4.get("inverted_polarity_detected") is True, "T-ORIENT-01(c): flag missing L4"
        warning = l4.get("inverted_polarity_warning","")
        assert warning and "corrected" in warning.lower(), (
            f"T-ORIENT-01(c): warning missing or lacks 'corrected': {warning!r}")

        # (d) traffic light unchanged
        tl = full_report["layer_1_traffic_light"]["signal"]
        assert tl == "GREEN", f"T-ORIENT-01(d): TL={tl!r}, expected GREEN"

        # (e) FHIR note
        fhir_gen = mod.ERGFHIRGenerator()
        fhir_obs = fhir_gen.generate_observation(
            report_id=l4["report_id"], patient_id="ORIENT-TEST",
            traffic_light=full_report["layer_1_traffic_light"],
            features=features,
            audit_results=audit, electrode_type=ELECTRODE, protocol=PROTOCOL)
        note_text = " ".join(n.get("text","") for n in fhir_obs.get("note",[])).lower()
        assert "inverted" in note_text or "polarity" in note_text, (
            f"T-ORIENT-01(e): FHIR note missing polarity text. notes={fhir_obs.get('note')}")

    def test_T_ORIENT_02_normal_signal_not_flagged(self, s01_result):
        """T-ORIENT-02: Normal signal must NOT trigger inversion flag."""
        flag = s01_result["features"].get("inverted_polarity_detected")
        assert flag is False, f"T-ORIENT-02: normal signal flagged as inverted: {flag!r}"


class TestElectrodeGating:
    def test_T_ELEC_01_unsupported_electrode_returns_UNAVAILABLE(
            self, pipeline_module, s01_csv_path):
        import numpy as np
        mod = pipeline_module
        PRE_MS=50.0
        time_ms, signal_uv, fs_hz, _ = mod.load_erg_csv(s01_csv_path)
        flash_onset = int(PRE_MS*fs_hz/1000)
        noise_rms = float(np.sqrt(np.mean(signal_uv[:flash_onset]**2)))
        audit   = mod.run_full_audit(signal_uv, fs_hz, electrode_type="contact_lens",
                                         prestimulus_samples=flash_onset, age_group="≤35y")
        filtered, filter_log = mod.run_filter_pipeline(
            signal_uv, fs_hz, apply_notch=False, notch_hz=50.0,
            hardware_cutoff_hz=None, user_confirmed_notch=False)
        features  = mod.extract_all_features(
            signal=filtered, fs_hz=fs_hz, protocol="DA 3.0",
            flash_onset_sample=flash_onset, flash_duration_ms=0.0,
            op_signal=None, noise_rms_uv=noise_rms)
        report_gen  = mod.ERGReportGenerator()
        full_report = report_gen.generate_full_report(
            features=features, audit_results=audit, electrode_type="contact_lens",
            protocol="DA 3.0", age_years="≤35y", filtered_signal=filtered,
            time_ms=time_ms, filter_log=filter_log, processing_time_ms=0.0)
        signal = full_report["layer_1_traffic_light"]["signal"]
        assert signal == "UNAVAILABLE", f"T-ELEC-01: {signal!r}"
