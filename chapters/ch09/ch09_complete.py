"""
Chapter 9 ERG Feature Extraction Pipeline
Assembled from ERG_Chapter9_Final_12.docx code blocks for Colab testing
and repo integration. All 28 features across the four families in
Sections 9.1-9.4, plus the Section 9.5 feature-selection scaffold notes.
"""
import numpy as np
from typing import Dict, Any
from scipy.signal import find_peaks, welch
import pywt


class ERGConfig:
    """Minimal config stub. Replace with the project's real config class."""
    ISCEV_FLASH_MAX_DURATION_MS = 5.0  # ISCEV 2022: max acceptable flash duration


class ERGFeatureExtractor:
    """
    Extracts all 28 Chapter 9 features from a single ERG recording.
    Feature count varies by protocol (25-27); see Chapter 9 Section 9.1
    for the full breakdown of why PhNR (Section 9.2, LA 3.0 only) and the
    harmonic ratio (Section 9.4, LA 30 Hz only) never co-occur.
    """

    def __init__(self, config: ERGConfig = None):
        self.config = config or ERGConfig()

    def extract_awave_bwave(self, signal: np.ndarray, fs_hz: float,
                            protocol: str = 'DA 3',
                            flash_onset_sample: int = 0,
                            flash_duration_ms: float = 1.0) -> Dict[str, Any]:

        # Protocol-specific search windows
        if protocol == 'DA 0.01':
            a_wave_window_ms = (None, None)
            b_wave_window_ms = (40, 130)
        elif protocol == 'DA 3':
            a_wave_window_ms = (10, 35)
            b_wave_window_ms = (30, 100)
        elif protocol == 'DA 10':
            a_wave_window_ms = (8, 30)
            b_wave_window_ms = (25, 95)
        elif protocol == 'LA 3':
            a_wave_window_ms = (12, 28)
            b_wave_window_ms = (25, 60)
        elif protocol == 'LA 30 Hz':
            a_wave_window_ms = (None, None)
            b_wave_window_ms = (20, 60)
        else:
            a_wave_window_ms = (10, 35)
            b_wave_window_ms = (30, 100)

        if a_wave_window_ms[0] is None:
            a_wave_amplitude = np.nan
            a_wave_implicit_ms = np.nan
            b_start = flash_onset_sample + int(b_wave_window_ms[0] * fs_hz / 1000)
            b_end = flash_onset_sample + int(b_wave_window_ms[1] * fs_hz / 1000)
            b_start = max(0, min(b_start, len(signal)-1))
            b_end = max(b_start+1, min(b_end, len(signal)))
        else:
            a_start = flash_onset_sample + int(a_wave_window_ms[0] * fs_hz / 1000)
            a_end = flash_onset_sample + int(a_wave_window_ms[1] * fs_hz / 1000)
            a_start = max(0, min(a_start, len(signal)-1))
            a_end = max(a_start+1, min(a_end, len(signal)))

            a_segment = signal[a_start:a_end]
            if len(a_segment) > 0:
                a_trough_idx_local = np.argmin(a_segment)
                a_trough_idx = a_start + a_trough_idx_local
                a_wave_amplitude = signal[a_trough_idx]
                a_wave_implicit_samples = a_trough_idx - flash_onset_sample
                a_wave_implicit_ms = a_wave_implicit_samples * 1000.0 / fs_hz
            else:
                a_wave_amplitude = np.nan
                a_wave_implicit_ms = np.nan

            # b-wave search must start AFTER the a-wave trough
            if not np.isnan(a_wave_implicit_ms):
                b_start_abs = max(a_trough_idx + int(2 * fs_hz / 1000),
                                  flash_onset_sample + int(b_wave_window_ms[0] * fs_hz / 1000))
            else:
                b_start_abs = flash_onset_sample + int(b_wave_window_ms[0] * fs_hz / 1000)

            b_end_abs = flash_onset_sample + int(b_wave_window_ms[1] * fs_hz / 1000)
            b_start = max(0, min(b_start_abs, len(signal)-1))
            b_end = max(b_start+1, min(b_end_abs, len(signal)))

        b_segment = signal[b_start:b_end]
        if len(b_segment) > 0:
            b_peak_idx_local = np.argmax(b_segment)
            b_peak_idx = b_start + b_peak_idx_local
            b_wave_raw = signal[b_peak_idx]
            b_wave_amplitude = b_wave_raw - a_wave_amplitude if not np.isnan(a_wave_amplitude) else b_wave_raw
            if b_wave_amplitude < 0:
                b_wave_amplitude = -b_wave_amplitude
            b_wave_implicit_samples = b_peak_idx - flash_onset_sample
            b_wave_implicit_ms = b_wave_implicit_samples * 1000.0 / fs_hz
        else:
            b_wave_amplitude = np.nan
            b_wave_implicit_ms = np.nan

        # a-wave amplitude is always reported negative , enforced once, here
        if not np.isnan(a_wave_amplitude):
            a_wave_amplitude = -abs(a_wave_amplitude)
        ba_ratio = (b_wave_amplitude / abs(a_wave_amplitude)
                    if a_wave_amplitude != 0 and not np.isnan(a_wave_amplitude) else np.nan)

        correction_applied = False
        correction_ms = 0.0
        if flash_duration_ms >= self.config.ISCEV_FLASH_MAX_DURATION_MS:
            correction_ms = flash_duration_ms / 2.0
            a_wave_implicit_ms = a_wave_implicit_ms - correction_ms if not np.isnan(a_wave_implicit_ms) else np.nan
            b_wave_implicit_ms = b_wave_implicit_ms - correction_ms if not np.isnan(b_wave_implicit_ms) else np.nan
            correction_applied = True

        return {
            'a_wave_amplitude_uv': round(float(a_wave_amplitude), 1) if not np.isnan(a_wave_amplitude) else np.nan,
            'a_wave_implicit_time_ms': round(float(a_wave_implicit_ms), 1) if not np.isnan(a_wave_implicit_ms) else np.nan,
            'b_wave_amplitude_uv': round(float(b_wave_amplitude), 1) if not np.isnan(b_wave_amplitude) else np.nan,
            'b_wave_implicit_time_ms': round(float(b_wave_implicit_ms), 1) if not np.isnan(b_wave_implicit_ms) else np.nan,
            'ba_ratio': round(float(ba_ratio), 2) if not np.isnan(ba_ratio) else np.nan,
            'flash_midpoint_correction_applied': correction_applied,
            'flash_midpoint_correction_ms': correction_ms,
        }

    def extract_oscillatory_potentials(self, signal: np.ndarray, fs_hz: float,
                                        flash_onset_sample: int = 0) -> Dict[str, Any]:
        """
        Extract Oscillatory Potentials OP2-OP4 from the 75-300 Hz filtered signal.
        OP1 is not extracted: its trough overlaps the b-wave ascending limb and
        ISCEV 2022 does not use this OP1–OP4 numbering scheme.
        """
        op_windows = {
            'OP2': (20, 28),
            'OP3': (28, 38),
            'OP4': (38, 65),
        }

        ops = {}
        op2_implicit_ms = np.nan

        for op_name, (start_ms, end_ms) in op_windows.items():
            start_idx = flash_onset_sample + int(start_ms * fs_hz / 1000)
            end_idx = flash_onset_sample + int(end_ms * fs_hz / 1000)
            start_idx = max(0, min(start_idx, len(signal)-1))
            end_idx = max(start_idx+1, min(end_idx, len(signal)))
            segment = signal[start_idx:end_idx]

            if len(segment) > 0:
                peaks, _ = find_peaks(segment, height=0, prominence=0.5)
                if len(peaks) > 0:
                    peak_idx_local = peaks[np.argmax(segment[peaks])]
                    peak_amplitude = segment[peak_idx_local]
                    trough_idx_local = np.argmin(segment[:peak_idx_local+1]) if peak_idx_local > 0 else 0
                    trough_amplitude = segment[trough_idx_local]
                    op_amplitude = peak_amplitude - trough_amplitude
                    if op_name == 'OP2':
                        op2_implicit_ms = (start_idx + peak_idx_local - flash_onset_sample) * 1000.0 / fs_hz
                else:
                    op_amplitude = 0.0
            else:
                op_amplitude = 0.0

            ops[op_name] = round(float(op_amplitude), 1)

        ops['OP_sum_uv'] = ops.get('OP2', 0) + ops.get('OP3', 0) + ops.get('OP4', 0)
        ops['OP2_implicit_ms'] = round(float(op2_implicit_ms), 2) if not np.isnan(op2_implicit_ms) else np.nan
        return ops

    def extract_phnr(self, signal: np.ndarray, fs_hz: float,
                     b_wave_implicit_time_ms: float,
                     flash_onset_sample: int = 0,
                     noise_rms_uv: float = 1.0) -> Dict[str, Any]:
        """
        PhNR is reported as a SIGNED value relative to baseline. The expected
        physiological PhNR is negative-going (Frishman et al., 2018;\n 
      Prencipe et al., 2020); a positive value is flagged via 'phnr_polarity_atypical'
       as a data-quality signal, not presented as an alternate normal state.
        """
        search_start_ms = max(60.0, b_wave_implicit_time_ms + 10.0)
        search_end_ms = 200.0

        start_idx = flash_onset_sample + int(search_start_ms * fs_hz / 1000)
        end_idx = flash_onset_sample + int(search_end_ms * fs_hz / 1000)
        start_idx = max(0, min(start_idx, len(signal)-1))
        end_idx = max(start_idx+1, min(end_idx, len(signal)))
        segment = signal[start_idx:end_idx]

        if len(segment) > 0:
            seg_min = float(np.min(segment))
            seg_max = float(np.max(segment))
            if abs(seg_min) >= abs(seg_max):
                phnr_signed = seg_min       # trough dominates: typical
            else:
                phnr_signed = seg_max       # peak dominates: atypical

            phnr_magnitude = abs(phnr_signed)
            if phnr_magnitude < 2.0 * noise_rms_uv:
                return {'phnr_amp_uv': np.nan, 'phnr_polarity_atypical': False}

            return {
                'phnr_amp_uv': round(phnr_signed, 1),
                'phnr_polarity_atypical': bool(phnr_signed > 0),
            }
        else:
            return {'phnr_amp_uv': np.nan, 'phnr_polarity_atypical': False}

    def extract_nonlinear_features(self, signal: np.ndarray) -> Dict[str, Any]:
        """
      Hurst Exponent and Approximate Entropy of the broadband signal.
               Both measures are significantly lower (p<0.05) in CSNB, RP, and
              cone-rod dystrophy vs. healthy controls (Nair and Joseph, 2014a).
            """
        x = np.asarray(signal, dtype=float)
        n = len(x)

        # Hurst exponent via detrended-difference scaling
        if n < 20:
            hurst = np.nan
        else:
            lags = range(2, n // 2)
            tau = np.array([np.std(x[lag:] - x[:-lag]) for lag in lags])
            valid = tau > 0
            if valid.sum() < 2:
                hurst = np.nan
            else:
                log_lags = np.log(np.array(list(lags))[valid])
                log_tau = np.log(tau[valid])
                slope, _ = np.polyfit(log_lags, log_tau, 1)
                hurst = float(slope * 2.0)

   
     # Approximate entropy (Pincus, 1991; m=2, r=0.15*SD per Nair and Joseph, 2014a)

        def _phi(m, r):
            z = np.array([x[i:i + m] for i in range(n - m + 1)])
            d = np.abs(z[:, None, :] - z[None, :, :]).max(axis=2)
            c = (d <= r).sum(axis=1) / (n - m + 1)
            return np.sum(np.log(c)) / (n - m + 1)

        if n < 10:
            apen = np.nan
        else:
            r = 0.15 * np.std(x)
            apen = float(_phi(2, r) - _phi(3, r)) if r > 0 else np.nan

        return {
            'hurst_exponent': round(hurst, 4) if not np.isnan(hurst) else np.nan,
            'approximate_entropy': round(apen, 4) if not np.isnan(apen) else np.nan,
        }

    def extract_dwt_band_energies(self, signal: np.ndarray, fs_hz: float,
                                   flash_onset_sample: int = 0,
                                   wavelet: str = 'morl') -> Dict[str, Any]:
        """
              CWT band-energy descriptors at the six statistically-validated
             frequency/time-window pairs: 20/40 Hz over the a-wave window, 20/40 Hz
            over the b-wave window, and 80/160 Hz over the OP window
           (Gauvin, Lina and Lachapelle, 2014).
        """
        x = np.asarray(signal, dtype=float)
        n = len(x)
        t_ms = (np.arange(n) - flash_onset_sample) * 1000.0 / fs_hz
        dt = 1.0 / fs_hz
        central_freq = pywt.central_frequency(wavelet)

        descriptors = {
            'dwt_20a_uv2': (20.0, (5.0, 30.0)),
            'dwt_40a_uv2': (40.0, (5.0, 30.0)),
            'dwt_20b_uv2': (20.0, (20.0, 70.0)),
            'dwt_40b_uv2': (40.0, (20.0, 70.0)),
            'dwt_80ops_uv2': (80.0, (10.0, 45.0)),
            'dwt_160ops_uv2': (160.0, (10.0, 45.0)),
        }

        out = {}
        for key, (target_freq_hz, window_ms) in descriptors.items():
            scale = central_freq * fs_hz / target_freq_hz
            coeffs, _ = pywt.cwt(x, [scale], wavelet, sampling_period=dt)
            mag = np.abs(coeffs[0])
            mask = (t_ms >= window_ms[0]) & (t_ms <= window_ms[1])
            out[key] = round(float(np.sum(mag[mask] ** 2)), 2) if mask.any() else np.nan
        return out

    def extract_bwave_derivative_features(self, signal: np.ndarray, fs_hz: float,
                                           b_wave_implicit_time_ms: float,
                                           flash_onset_sample: int = 0,
                                           search_end_ms: float = 150.0) -> Dict[str, Any]:
        """
        b-wave ascending- and descending-limb inflection points (2nd-derivative
        zero crossings), implicit time and gradient. Both limbs reached
        statistical significance in the source study (descending: p<0.001 time,
        p=0.033 gradient; ascending: p<0.001 time, p=0.005 gradient)
        (Wood, Margrain and Binns, 2014).
        """
        empty = {'b_ascending_inflection_ms': np.nan, 'b_ascending_gradient_uv_ms': np.nan,
                 'b_descending_inflection_ms': np.nan, 'b_descending_gradient_uv_ms': np.nan}
        if np.isnan(b_wave_implicit_time_ms):
            return empty

        t_ms = (np.arange(len(signal)) - flash_onset_sample) * 1000.0 / fs_hz

        asc_mask = (t_ms >= 0.0) & (t_ms <= b_wave_implicit_time_ms - 1.0)
        asc_result = {'b_ascending_inflection_ms': np.nan, 'b_ascending_gradient_uv_ms': np.nan}
        if asc_mask.sum() >= 5:
            seg_t = t_ms[asc_mask]
            seg_x = np.asarray(signal)[asc_mask]
            d1 = np.gradient(seg_x, seg_t)
            d2 = np.gradient(d1, seg_t)
            sign_changes = np.where(np.diff(np.sign(d2)))[0]
            candidates = [i for i in sign_changes if d1[i] > 0]
            if candidates:
                idx = candidates[-1]
                asc_result = {
                    'b_ascending_inflection_ms': round(float(seg_t[idx]), 2),
                    'b_ascending_gradient_uv_ms': round(float(d1[idx]), 2),
                }

        desc_mask = (t_ms >= b_wave_implicit_time_ms + 3.0) & (t_ms <= search_end_ms)
        desc_result = {'b_descending_inflection_ms': np.nan, 'b_descending_gradient_uv_ms': np.nan}
        if desc_mask.sum() >= 5:
            seg_t = t_ms[desc_mask]
            seg_x = np.asarray(signal)[desc_mask]
            d1 = np.gradient(seg_x, seg_t)
            d2 = np.gradient(d1, seg_t)
            sign_changes = np.where(np.diff(np.sign(d2)))[0]
            candidates = [i for i in sign_changes if d1[i] < 0]
            if candidates:
                idx = candidates[0]
                desc_result = {
                    'b_descending_inflection_ms': round(float(seg_t[idx]), 2),
                    'b_descending_gradient_uv_ms': round(float(d1[idx]), 2),
                }

        return {**asc_result, **desc_result}

    def extract_awave_descending_inflection(self, signal: np.ndarray, fs_hz: float,
                                              a_wave_implicit_time_ms: float,
                                              b_wave_implicit_time_ms: float,
                                              flash_onset_sample: int = 0) -> Dict[str, Any]:
        """
        a-wave descending-limb inflection point, implicit time only. Gradient at
        this point was NOT significant in the source study (p = 0.097) and is
        deliberately not extracted; implicit time was significant (p < 0.001,
        AUC 0.68) (Wood, Margrain and Binns, 2014).
        """
        if np.isnan(a_wave_implicit_time_ms) or np.isnan(b_wave_implicit_time_ms):
            return {'a_descending_inflection_ms': np.nan}

        t_ms = (np.arange(len(signal)) - flash_onset_sample) * 1000.0 / fs_hz
        mask = (t_ms >= a_wave_implicit_time_ms + 1.0) & (t_ms <= b_wave_implicit_time_ms - 1.0)
        if mask.sum() < 5:
            return {'a_descending_inflection_ms': np.nan}

        seg_t = t_ms[mask]
        seg_x = np.asarray(signal)[mask]
        d1 = np.gradient(seg_x, seg_t)
        d2 = np.gradient(d1, seg_t)
        sign_changes = np.where(np.diff(np.sign(d2)))[0]
        if len(sign_changes) == 0:
            return {'a_descending_inflection_ms': np.nan}

        idx = sign_changes[0]
        return {'a_descending_inflection_ms': round(float(seg_t[idx]), 2)}

    def extract_frequency_domain_features(self, signal: np.ndarray, fs_hz: float,
                                           protocol: str = 'DA 3',
                                           fmin: float = 0.0, fmax: float = 300.0,
                                           fundamental_hz: float = 30.0,
                                           n_harmonics: int = 3,
                                           bw_hz: float = 2.0) -> Dict[str, Any]:
        """
        Peak PSD frequency and spectral entropy on the broadband signal for
        every protocol. Harmonic ratio (LA 30 Hz only).
        """
        freqs, psd = welch(signal, fs=fs_hz, nperseg=min(256, len(signal)))
        mask = (freqs >= fmin) & (freqs <= fmax)
        freqs_m, psd_m = freqs[mask], psd[mask]

        if len(psd_m) == 0 or np.sum(psd_m) == 0:
            out = {'peak_freq_hz': np.nan, 'spectral_entropy': np.nan}
        else:
            peak_freq = float(freqs_m[np.argmax(psd_m)])
            p_norm = psd_m / np.sum(psd_m)
            p_norm = p_norm[p_norm > 0]
            entropy = float(-np.sum(p_norm * np.log(p_norm)) / np.log(len(p_norm))) if len(p_norm) > 1 else np.nan
            out = {'peak_freq_hz': round(peak_freq, 2), 'spectral_entropy': round(entropy, 4)}

        if protocol.upper().replace(' ', '') in ('LA30HZ', 'LA30'):
            total_power = np.sum(psd)
            if total_power > 0:
                harmonic_power = 0.0
                for k in range(1, n_harmonics + 1):
                    f0 = fundamental_hz * k
                    hmask = (freqs >= f0 - bw_hz) & (freqs <= f0 + bw_hz)
                    harmonic_power += np.sum(psd[hmask])
                out['harmonic_ratio'] = round(float(harmonic_power / total_power), 4)
            else:
                out['harmonic_ratio'] = np.nan

        return out

    def extract_all_features(self, signal: np.ndarray, fs_hz: float,
                             protocol: str = 'DA 3',
                             flash_onset_sample: int = 0,
                             flash_duration_ms: float = 1.0,
                             op_signal: np.ndarray = None,
                             noise_rms_uv: float = 1.0) -> Dict[str, Any]:

        features = {'protocol': protocol}

        # §9.1: a-wave, b-wave, b/a ratio
        features.update(self.extract_awave_bwave(signal, fs_hz, protocol,
                                                  flash_onset_sample, flash_duration_ms))

        # §9.1: oscillatory potentials, computed only when a dedicated
        # OP-isolated (75-300 Hz) signal is supplied; there is no fallback
        # to the broadband signal. Without op_signal, OP extraction is
        # skipped entirely and the key is simply absent from the output.
        if op_signal is not None:
            features['oscillatory_potentials'] = self.extract_oscillatory_potentials(
                op_signal, fs_hz, flash_onset_sample)

        # §9.2: PhNR family, LA 3.0 only
        if protocol == 'LA 3':
            b_it = features.get('b_wave_implicit_time_ms', np.nan)
            if not np.isnan(b_it):
                features.update(self.extract_phnr(signal, fs_hz, b_it,
                                                   flash_onset_sample, noise_rms_uv))
                b_amp = features.get('b_wave_amplitude_uv', np.nan)
                phnr_amp = features.get('phnr_amp_uv', np.nan)
                if not np.isnan(b_amp) and b_amp != 0 and not np.isnan(phnr_amp):
                    features['phnr_bwave_ratio'] = round(float(phnr_amp / b_amp), 4)
                else:
                    features['phnr_bwave_ratio'] = np.nan
            else:
                features['phnr_amp_uv'] = np.nan
                features['phnr_polarity_atypical'] = False
                features['phnr_bwave_ratio'] = np.nan

        # §9.3: nonlinear, DWT bands, b-wave and a-wave derivative features (all protocols)
        features.update(self.extract_nonlinear_features(signal))
        features.update(self.extract_dwt_band_energies(signal, fs_hz, flash_onset_sample))
        a_implicit = features.get('a_wave_implicit_time_ms', np.nan)
        b_implicit = features.get('b_wave_implicit_time_ms', np.nan)
        features.update(self.extract_bwave_derivative_features(
            signal, fs_hz, b_implicit, flash_onset_sample))
        features.update(self.extract_awave_descending_inflection(
            signal, fs_hz, a_implicit, b_implicit, flash_onset_sample))

        # §9.4: frequency-domain
        features.update(self.extract_frequency_domain_features(signal, fs_hz, protocol))

        return features

# ---------------------------------------------------------------------------
# Self-test: confirms the pipeline runs on every protocol and that Section
# 9.3 (nonlinear/DWT/derivative features) fires on ALL protocols, not just
# LA 3 -- this was the specific bug fixed during the Chapter 9 review.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    fs_hz = 2000.0
    t = np.arange(0, 0.3, 1 / fs_hz)
    # Synthetic biphasic ERG-like waveform: a-wave trough ~15ms, b-wave peak ~50ms
    signal = (-50 * np.exp(-((t - 0.015) ** 2) / (2 * 0.006 ** 2))
              + 120 * np.exp(-((t - 0.050) ** 2) / (2 * 0.020 ** 2)))
    op_signal = signal + 5 * np.sin(2 * np.pi * 100 * t) * np.exp(-((t - 0.03) ** 2) / (2 * 0.02 ** 2))

    extractor = ERGFeatureExtractor()

    protocols = ['DA 0.01', 'DA 3', 'DA 10', 'LA 3', 'LA 30 Hz']
    expected_counts = {'DA 0.01': 25, 'DA 3': 25, 'DA 10': 25, 'LA 3': 27, 'LA 30 Hz': 26}

    print(f"{'Protocol':10s} {'#Features':10s} {'Has NLTF?':10s} {'Has PhNR?':10s} {'Has FreqDom?':12s}")
    print("-" * 60)
    for protocol in protocols:
        feats = extractor.extract_all_features(
            signal, fs_hz, protocol=protocol, flash_onset_sample=0,
            flash_duration_ms=1.0, op_signal=op_signal, noise_rms_uv=1.0)
        # Count diagnostic feature keys: flatten the nested oscillatory_potentials
        # dict (5 keys) into the tally, and exclude non-feature bookkeeping keys.
        bookkeeping = {'protocol', 'flash_midpoint_correction_applied',
                        'flash_midpoint_correction_ms', 'phnr_polarity_atypical'}
        feature_keys = [k for k in feats if k not in bookkeeping and k != 'oscillatory_potentials']
        if 'oscillatory_potentials' in feats:
            feature_keys += list(feats['oscillatory_potentials'].keys())
        has_nltf = 'hurst_exponent' in feats or 'b_ascending_inflection_ms' in feats
        has_phnr = 'phnr_amp_uv' in feats
        has_freq = 'peak_frequency_hz' in feats or 'spectral_entropy' in feats
        print(f"{protocol:10s} {len(feature_keys):<10d} {str(has_nltf):10s} {str(has_phnr):10s} {str(has_freq):12s}")

    print("\nSample output for protocol='DA 3' (should include Section 9.3 keys):")
    sample = extractor.extract_all_features(signal, fs_hz, protocol='DA 3',
                                             flash_onset_sample=0, op_signal=op_signal)
    for k, v in sample.items():
        print(f"  {k}: {v}")
