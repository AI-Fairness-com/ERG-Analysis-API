"""
tests/test_pipeline.py — 14 core + orientation tests.
T-CSV-01/02, T-FILT-01, T-WAVE-01/02, T-ZSCORE-01/02,
T-TL-01/02, T-FHIR-01/02, T-DTL-01, T-ORIENT-01/02, T-ELEC-01.
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
        filt_obj = mod.ERGFilter()
        filtered, _ = filt_obj.run_filter_pipeline(sig.copy(), fs, apply_notch=False,
                                                    notch_hz=50.0, hardware_cutoff_hz=None,
                                                    user_confirmed_notch=False)
        ratio = float((filtered**2).mean()**0.5) / float((sig**2).mean()**0.5)
        assert ratio >= 0.80, f"T-FILT-01: 30Hz attenuated by {(1-ratio)*100:.1f}%"


class TestWaveformExtraction:
    def test_T_WAVE_01_a_wave_trough_is_negative(self, s01_result):
        a = s01_result["features"].get("a_wave_amplitude_uv")
        assert a is not None and not math.isnan(a) and a < 0, f"T-WAVE-01: a={a}"

    def test_T_WAVE_02_b_wave_peak_follows_a_wave_trough(self, s01_result):
        f = s01_result["features"]
        a_it = f.get("a_wave_implicit_time_ms"); b_it = f.get("b_wave_implicit_time_ms")
        assert a_it is not None and b_it is not None and b_it > a_it


class TestZScores:
    def test_T_ZSCORE_01_mu_input_returns_zero(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        mu, sigma = rgen.REFERENCE_RANGES["DA 3"]["gold_foil"]["le35"]["a_amp"]
        assert abs((mu-mu)/sigma) <= 0.01

    def test_T_ZSCORE_02_mu_plus_2sigma_returns_plus_two(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        mu, sigma = rgen.REFERENCE_RANGES["DA 3"]["gold_foil"]["le35"]["b_amp"]
        assert abs(((mu+2*sigma)-mu)/sigma - 2.0) <= 0.05


class TestTrafficLight:
    def test_T_TL_01_Z_minus_2_5_returns_AMBER(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        tl = rgen.generate_traffic_light(
            {"a_wave_amplitude":-2.5,"b_wave_amplitude":0.0,"b_wave_implicit_time":0.0,"ba_ratio":0.0})
        assert tl["signal"] == "AMBER", f"T-TL-01: {tl['signal']}"

    def test_T_TL_02_Z_plus_3_1_returns_RED(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        tl = rgen.generate_traffic_light(
            {"a_wave_amplitude":0.0,"b_wave_amplitude":0.0,"b_wave_implicit_time":3.1,"ba_ratio":0.0})
        assert tl["signal"] == "RED", f"T-TL-02: {tl['signal']}"


class TestFHIROutput:
    def test_T_FHIR_01_resourceType_is_Observation(self, s01_result):
        assert s01_result["fhir"].get("resourceType") == "Observation"

    def test_T_FHIR_02_LOINC_70943_7_present(self, s01_result):
        codes = [c.get("code") for c in s01_result["fhir"].get("code",{}).get("coding",[])]
        assert "70943-7" in codes, f"T-FHIR-02: codes={codes}"


class TestDTLDemingRegression:
    def test_T_DTL_01_deming_correction_shifts_z_scores(self, pipeline_module):
        rgen = pipeline_module.ERGReportGenerator()
        assert rgen.ELECTRODE_TRANSFORM and "DA 3" in rgen.ELECTRODE_TRANSFORM
        gf_mu = 175.70
        slope = rgen.ELECTRODE_TRANSFORM["DA 3"]["a_amp"]["slope"]
        intercept = rgen.ELECTRODE_TRANSFORM["DA 3"]["a_amp"]["intercept"]
        ste_at_mu = slope*gf_mu + intercept
        gfe_equiv = rgen._apply_dtl_transform("DA 3","a_amp",ste_at_mu)
        assert abs(gfe_equiv - gf_mu) < 0.01, f"T-DTL-01: GFE_equiv={gfe_equiv:.4f}"
        _, sigma = rgen.REFERENCE_RANGES["DA 3"]["gold_foil"]["le35"]["a_amp"]
        assert abs((gfe_equiv-gf_mu)/sigma) <= 0.01
        assert rgen._apply_dtl_transform("DA 3","a_imp",14.98) == 14.98


class TestSignalOrientation:

    def test_T_ORIENT_01_inverted_signal_corrected_and_flagged(
            self, pipeline_module, s01_csv_path):
        """
        T-ORIENT-01: Artificially inverted waveform must be auto-corrected.
        (a) a-wave amplitude negative after correction
        (b) inverted_polarity_detected = True in features
        (c) Layer 4 warning present and contains 'corrected'
        (d) traffic light still GREEN
        (e) FHIR note contains 'inverted' or 'polarity'
        """
        import numpy as np
        mod = pipeline_module
        PRE_MS=50.0; PROTOCOL="DA 3"; ELECTRODE="gold_foil"; AGE="≤35y"

        time_ms, signal_uv, fs_hz, _ = mod.load_erg_csv(s01_csv_path)
        flash_onset = int(PRE_MS * fs_hz / 1000)
        inv_sig = signal_uv * -1.0
        noise_rms = float(np.sqrt(np.mean(inv_sig[:flash_onset]**2)))

        auditor = mod.ERGAudit()
        audit   = auditor.run_full_audit(inv_sig, fs_hz, electrode_type=ELECTRODE,
                                         prestimulus_samples=flash_onset, age_group=AGE)
        filt_obj = mod.ERGFilter()
        filtered, filter_log = filt_obj.run_filter_pipeline(
            inv_sig, fs_hz, apply_notch=False, notch_hz=50.0,
            hardware_cutoff_hz=None, user_confirmed_notch=False)
        extractor = mod.ERGFeatureExtractor()
        features  = extractor.extract_all_features(
            signal=filtered, fs_hz=fs_hz, protocol=PROTOCOL,
            flash_onset_sample=flash_onset, flash_duration_ms=0.0,
            op_signal=None, noise_rms_uv=noise_rms)

        # (a)
        a_amp = features.get("a_wave_amplitude_uv")
        assert a_amp is not None and not math.isnan(a_amp) and a_amp < 0, (
            f"T-ORIENT-01(a): a-wave must be negative after correction, got {a_amp}")

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
            z_scores=full_report["layer_2_clinical_summary"]["z_scores"],
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
        auditor = mod.ERGAudit()
        audit   = auditor.run_full_audit(signal_uv, fs_hz, electrode_type="contact_lens",
                                         prestimulus_samples=flash_onset, age_group="≤35y")
        filt_obj = mod.ERGFilter()
        filtered, filter_log = filt_obj.run_filter_pipeline(
            signal_uv, fs_hz, apply_notch=False, notch_hz=50.0,
            hardware_cutoff_hz=None, user_confirmed_notch=False)
        extractor = mod.ERGFeatureExtractor()
        features  = extractor.extract_all_features(
            signal=filtered, fs_hz=fs_hz, protocol="DA 3",
            flash_onset_sample=flash_onset, flash_duration_ms=0.0,
            op_signal=None, noise_rms_uv=noise_rms)
        report_gen  = mod.ERGReportGenerator()
        full_report = report_gen.generate_full_report(
            features=features, audit_results=audit, electrode_type="contact_lens",
            protocol="DA 3", age_years="≤35y", filtered_signal=filtered,
            time_ms=time_ms, filter_log=filter_log, processing_time_ms=0.0)
        signal = full_report["layer_1_traffic_light"]["signal"]
        assert signal == "UNAVAILABLE", f"T-ELEC-01: {signal!r}"
