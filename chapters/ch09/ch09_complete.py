"""
Chapter 9 ERG Feature Extraction Pipeline
Assembled from ERG_Chapter9_Final_13.docx code blocks for Colab testing
and repo integration. Free-function design, matching the canonical
chapters/ch09/feature_extraction_and_selection_pipeline.py and
api/erg_v2_5_0.py (both rebuilt to this same design 2026-09-07).
All 28 features across the four families in Sections 9.1-9.4; feature
count varies by protocol (25-27), since the PhNR family (Section 9.2,
LA 3.0 only) and the harmonic ratio (Section 9.4, LA 30 Hz only) never
co-occur on the same recording. No Section 9.5 feature-selection code
is included here (single-recording scope only, matching this file's
original intent) -- see feature_extraction_and_selection_pipeline.py
for the full patient-matrix + 4-method selection pipeline.
"""
import numpy as np
from typing import Dict, Any
from scipy.signal import find_peaks, welch
from numpy.lib.stride_tricks import sliding_window_view
import pywt

FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS = 1.0
# ISCEV 2022 flash-duration constants -- kept separate deliberately:
# ISCEV_FLASH_MAX_DURATION_MS is the absolute ceiling ISCEV allows for any
# stimulus flash. FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS is the (much lower)
# duration above which ISCEV requires implicit time to be measured from the
# flash midpoint rather than flash onset. These answer different questions
# and must not share one constant.
ISCEV_FLASH_MAX_DURATION_MS = 5.0
FS_HZ = 2000.0  # pipeline sampling rate (Chapter 3)


def extract_a_wave(signal_uv:    np.ndarray,
                   time_ms:      np.ndarray,
                   protocol:     str,
                   hardware_lowpass_hz: float = 300.0,
                   flash_duration_ms: float = 0.0,
                   search_start: float = 5.0,
                   search_end:   float = 40.0) -> dict:
    """Extract a-wave amplitude and implicit time from a broadband ERG sweep.

    Parameters
    ----------
    signal_uv : np.ndarray
        1-D broadband-filtered ERG in µV (t = 0 at stimulus onset).
    time_ms : np.ndarray
        Corresponding time axis in ms.
    protocol : str
        ISCEV protocol string ('DA 0.01', 'DA 3.0', 'DA 10.0',
        'LA 3.0', 'LA 30 Hz').
    hardware_lowpass_hz : float
        Hardware low-pass cutoff for this recording (Chapter 5 metadata).
        Used only to set a_wave_mar_technical when no a-wave is detected.
    flash_duration_ms : float
        Stimulus flash duration in ms. Per ISCEV 2022, flashes longer than
        FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS (1 ms) require implicit time
        to be measured from the flash midpoint rather than flash onset.
    search_start, search_end : float
        Post-stimulus search window in ms.

    Returns
    -------
    dict with keys: a_amp_uv (float or NaN), a_implicit_ms (float or NaN),
                    a_wave_mar_technical (bool, only meaningful when NaN),
                    flash_midpoint_correction_applied (bool),
                    flash_midpoint_correction_ms (float).

    Notes
    -----
    DA 0.01 and LA 30 Hz do not generate a measurable a-wave; NaN is
    returned immediately for these protocols. LA 3.0 does have a
    scorable a-wave (ISCEV 2022: measured baseline-to-trough alongside
    DA 3.0 and DA 10.0) and is no longer excluded here.
    Amplitude is reported as absolute value (ISCEV 2022: baseline-to-trough).
    When no a-wave is detected, hardware_lowpass_hz is compared against a
    protocol-specific threshold (30 Hz dark-adapted, 35 Hz LA 3.0 -- this
    project's own convention, margined above the measured human a-b wave
    frequency ceiling of Chen, Zheng and Lei, 2013) to distinguish a
    MAR-technical absence from a MNAR-physiological one.
    """
    correction_ms = (flash_duration_ms / 2.0
                     if flash_duration_ms >= FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS
                     else 0.0)
    correction_applied = correction_ms > 0.0

    if protocol.strip().upper() in ('DA 0.01', 'LA 30 HZ'):
        return {'a_amp_uv': np.nan, 'a_implicit_ms': np.nan}

    lowpass_threshold = 35.0 if protocol.strip().upper() == 'LA 3.0' else 30.0

    mask = (time_ms >= search_start) & (time_ms <= search_end)
    if not mask.any():
        return {'a_amp_uv': np.nan, 'a_implicit_ms': np.nan,
                'a_wave_mar_technical': hardware_lowpass_hz < lowpass_threshold}

    window_amp  = signal_uv[mask]
    window_time = time_ms[mask]
    a_local_idx = int(np.argmin(window_amp))
    a_amp_raw   = float(window_amp[a_local_idx])
    a_time      = float(window_time[a_local_idx]) - correction_ms

    # a-wave must be a negative deflection
    if a_amp_raw >= 0:
        return {'a_amp_uv': np.nan, 'a_implicit_ms': np.nan,
                'a_wave_mar_technical': hardware_lowpass_hz < lowpass_threshold}

    baseline_mask = time_ms < 0
    baseline_mean = float(signal_uv[baseline_mask].mean()) if baseline_mask.any() else 0.0
    a_amp_uv      = abs(a_amp_raw - baseline_mean)

    return {'a_amp_uv': round(a_amp_uv, 2), 'a_implicit_ms': round(a_time, 2),
            'flash_midpoint_correction_applied': correction_applied,
            'flash_midpoint_correction_ms': correction_ms}


def extract_b_wave(signal_uv:  np.ndarray,
                   time_ms:    np.ndarray,
                   protocol:   str,
                   a_time_ms:  float = np.nan,
                   flash_duration_ms: float = 0.0,
                   search_end: float = 150.0) -> dict:
    """Extract b-wave amplitude (trough-to-peak, ISCEV 2022) and implicit time.

    Parameters
    ----------
    signal_uv : np.ndarray
        Broadband-filtered ERG in µV.
    time_ms : np.ndarray
        Time axis in ms.
    protocol : str
        ISCEV protocol string.
    a_time_ms : float
        a-wave implicit time (ms), already flash-midpoint corrected if
        applicable. Pass np.nan for DA 0.01 (no a-wave); the
        baseline-to-peak convention is then used.
    flash_duration_ms : float
        Stimulus flash duration in ms. Per ISCEV 2022, flashes longer than
        FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS (1 ms) require implicit time
        to be measured from the flash midpoint rather than flash onset.
    search_end : float
        End of b-wave search window in ms post-stimulus.

    Returns
    -------
    dict with keys: b_amp_uv (float or NaN), b_implicit_ms (float or NaN),
                    flash_midpoint_correction_applied (bool),
                    flash_midpoint_correction_ms (float).
    """
    correction_ms = (flash_duration_ms / 2.0
                     if flash_duration_ms >= FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS
                     else 0.0)
    correction_applied = correction_ms > 0.0

    b_search_start = 20.0 if np.isnan(a_time_ms) else a_time_ms

    mask = (time_ms >= b_search_start) & (time_ms <= search_end)
    if not mask.any():
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}

    window_amp  = signal_uv[mask]
    window_time = time_ms[mask]
    b_local_idx = int(np.argmax(window_amp))
    b_amp_raw   = float(window_amp[b_local_idx])
    b_time      = float(window_time[b_local_idx]) - correction_ms

    if b_amp_raw <= 0:
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}

    if np.isnan(a_time_ms):
        # DA 0.01: baseline-to-peak
        baseline_mask   = time_ms < 0
        reference_level = float(signal_uv[baseline_mask].mean()) if baseline_mask.any() else 0.0
    else:
        # All other protocols: a-wave trough-to-peak (ISCEV 2022)
        a_idx           = int(np.argmin(np.abs(time_ms - a_time_ms)))
        reference_level = float(signal_uv[a_idx])

    b_amp_uv = b_amp_raw - reference_level
    if b_amp_uv <= 0:
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}

    return {'b_amp_uv': round(b_amp_uv, 2), 'b_implicit_ms': round(b_time, 2),
            'flash_midpoint_correction_applied': correction_applied,
            'flash_midpoint_correction_ms': correction_ms}


def compute_ba_ratio(b_amp_uv: float, a_amp_uv: float) -> float:
    """Compute the b/a amplitude ratio.

    Returns NaN if either component is missing or if a_amp_uv is zero.
    A ratio < 1.0 is a negative ERG (diagnostic hallmark of complete CSNB).
    """
    if np.isnan(b_amp_uv) or np.isnan(a_amp_uv) or a_amp_uv == 0:
        return np.nan
    return round(b_amp_uv / a_amp_uv, 3)


def extract_phnr(signal_uv:    np.ndarray,
                 time_ms:      np.ndarray,
                 b_time_ms:    float,
                 noise_rms_uv: float,
                 hardware_highpass_hz: float = 0.3,
                 search_start: float = 60.0,
                 search_end:   float = 200.0) -> dict:
    """Extract PhNR amplitude from a LA 3.0 broadband-filtered sweep.

    Parameters
    ----------
    signal_uv : np.ndarray
        LA 3.0 broadband-filtered ERG in µV.
    time_ms : np.ndarray
        Time axis in ms.
    b_time_ms : float
        b-wave implicit time (ms). PhNR search starts after this.
    noise_rms_uv : float
        Pre-stimulus noise RMS from Chapter 2 quality pipeline.
    hardware_highpass_hz : float
        Hardware high-pass cutoff for this recording (Chapter 5 metadata).
        Used only to set phnr_mar_technical when no PhNR is detected.
    search_start, search_end : float
        PhNR search window bounds in ms post-stimulus.

    Returns
    -------
    dict with keys: phnr_amp_uv (float or NaN),
                    phnr_mar_technical (bool, only meaningful when NaN).

    Notes
    -----
    PhNR must exceed 2x noise RMS to be considered reliable. This
    multiplier is this project's own convention (see Chapter 11 §11.1.2),
    not an ISCEV-specified value; no peer-reviewed automated PhNR
    detectability threshold was found during this book's review.
    When no PhNR is detected, hardware_highpass_hz is compared against
    the ISCEV-specified 0.3 Hz target (Frishman et al., 2018) to
    distinguish a MAR-technical absence from a MNAR-physiological one.
    A 5-point moving average is applied before trough detection to reduce
    false detections from noise.
    """
    effective_start = max(search_start, b_time_ms + 5.0)
    mask = (time_ms >= effective_start) & (time_ms <= search_end)
    if not mask.any():
        return {'phnr_amp_uv': np.nan,
                'phnr_mar_technical': hardware_highpass_hz > 0.3}

    win_amp = signal_uv[mask]
    if len(win_amp) >= 5:
        smoothed = np.mean(sliding_window_view(win_amp, 5), axis=1)
    else:
        smoothed = win_amp

    seg_min, seg_max = float(np.min(smoothed)), float(np.max(smoothed))
    phnr_signed = seg_min if abs(seg_min) >= abs(seg_max) else seg_max
    phnr_magnitude = abs(phnr_signed)
    if phnr_magnitude < 2.0 * noise_rms_uv:
        return {'phnr_amp_uv': np.nan, 'phnr_polarity_atypical': False,
                'phnr_mar_technical': hardware_highpass_hz > 0.3}

    return {'phnr_amp_uv': round(phnr_signed, 2),
            'phnr_polarity_atypical': bool(phnr_signed > 0)}


def extract_oscillatory_potentials(op_signal_uv: np.ndarray,
                                    time_ms:      np.ndarray,
                                    hardware_lowpass_hz: float = 300.0,
                                    min_prom_uv:  float = 5.0,
                                    min_dist_ms:  float = 8.0,
                                    fs:           float = FS_HZ) -> dict:
    """Extract OP2, OP3, OP4 amplitudes and OP2 implicit time.

    Uses the 75-300 Hz bandpass-filtered signal (Chapter 5 output).
    OP1 is excluded because its trough overlaps the b-wave ascending limb; ISCEV 2022 does not define an OP1-OP4 numbering scheme.
    Returns NaN for any OP that cannot be reliably identified.

    Parameters
    ----------
    op_signal_uv : np.ndarray
        OP-isolated (75-300 Hz) filtered ERG in uV.
    time_ms : np.ndarray
        Time axis in ms.
    hardware_lowpass_hz : float
        Hardware low-pass cutoff for this recording (Chapter 5 metadata).
        Used only to set op_mar_technical when no OPs are detected.
    min_prom_uv : float
        Minimum peak prominence in uV.
    min_dist_ms : float
        Minimum inter-peak distance in ms.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    dict with keys: op2_amp_uv, op3_amp_uv, op4_amp_uv,
                    op_sum_uv, op2_implicit_ms,
                    op_mar_technical (bool, only meaningful when all NaN).
    """
    op_mar_technical = hardware_lowpass_hz < 300.0
    _nan_result = {k: np.nan for k in
                   ['op2_amp_uv', 'op3_amp_uv', 'op4_amp_uv',
                    'op_sum_uv', 'op2_implicit_ms']}
    _nan_result['op_mar_technical'] = op_mar_technical

    post_mask = (time_ms >= 0) & (time_ms <= 100)
    if not post_mask.any():
        return _nan_result

    post_amp  = op_signal_uv[post_mask]
    post_time = time_ms[post_mask]
    min_dist_samples = int(min_dist_ms * fs / 1000)

    peaks, _ = find_peaks(post_amp,
                          prominence=min_prom_uv,
                          distance=max(1, min_dist_samples))

    if len(peaks) < 2:
        return _nan_result

    # OP1 excluded: first valid peak must be ≥ 25 ms post-stimulus
    valid_peaks = [p for p in peaks if post_time[p] >= 25.0]
    if len(valid_peaks) < 2:
        return _nan_result

    results  = dict(_nan_result)
    op_amps  = []
    for i, label in enumerate(['op2', 'op3', 'op4']):
        if i >= len(valid_peaks):
            break
        peak_idx   = valid_peaks[i]
        peak_amp   = float(post_amp[peak_idx])
        trough_start = valid_peaks[i - 1] if i > 0 else 0
        trough_amp   = float(post_amp[trough_start:peak_idx + 1].min())
        op_amp_tp    = peak_amp - trough_amp
        results[f'{label}_amp_uv'] = round(op_amp_tp, 2)
        if label == 'op2':
            results['op2_implicit_ms'] = round(float(post_time[peak_idx]), 2)
        op_amps.append(op_amp_tp)

    if len(op_amps) >= 2:
        results['op_sum_uv'] = round(sum(op_amps), 2)

    return results


def extract_nonlinear_features(signal: np.ndarray) -> Dict[str, Any]:
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



def extract_dwt_band_energies(signal: np.ndarray, fs_hz: float,
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



def extract_bwave_derivative_features(signal: np.ndarray, fs_hz: float,
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



def extract_awave_descending_inflection(signal: np.ndarray, fs_hz: float,
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


def extract_frequency_domain_features(signal: np.ndarray, fs_hz: float,
                                       protocol: str = 'DA 3.0',
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


def extract_all_features(signal: np.ndarray, fs_hz: float,
                         protocol: str = 'DA 3.0',
                         flash_onset_sample: int = 0,
                         flash_duration_ms: float = 0.0,
                         op_signal: np.ndarray = None,
                         noise_rms_uv: float = 1.0,
                         hardware_lowpass_hz: float = 300.0,
                         hardware_highpass_hz: float = 0.3) -> Dict[str, Any]:
    """Assemble every feature family in this chapter for one recording.

    flash_duration_ms defaults to 0.0, matching ISCEV 2022's assumption
    for a near-instantaneous xenon flashtube; pass the device's actual
    flash duration for LED-based systems to apply the ISCEV
    flash-midpoint implicit-time correction where it is needed.

    hardware_lowpass_hz and hardware_highpass_hz are Chapter 5 device
    metadata, used only to distinguish a MAR-technical absence from a
    MNAR-physiological one when the a-wave, PhNR, or OPs are not detected.
    """
    time_ms = (np.arange(len(signal)) - flash_onset_sample) * 1000.0 / fs_hz

    features = {'protocol': protocol}

    # §9.1: a-wave, b-wave, b/a ratio
    a = extract_a_wave(signal, time_ms, protocol,
                       hardware_lowpass_hz=hardware_lowpass_hz,
                       flash_duration_ms=flash_duration_ms)
    features.update(a)
    b = extract_b_wave(signal, time_ms, protocol,
                       a_time_ms=a['a_implicit_ms'],
                       flash_duration_ms=flash_duration_ms)
    features.update(b)
    features['ba_ratio'] = compute_ba_ratio(b['b_amp_uv'], a['a_amp_uv'])

    # §9.1: oscillatory potentials, computed only when a dedicated
    # OP-isolated (75-300 Hz) signal is supplied; there is no fallback
    # to the broadband signal. Without op_signal, OP extraction is
    # skipped entirely and its keys are simply absent from the output.
    if protocol.strip().upper() in ('DA 3.0', 'DA 10.0') and op_signal is not None:
        features.update(extract_oscillatory_potentials(
            op_signal, time_ms, hardware_lowpass_hz=hardware_lowpass_hz))
    else:
        for k in ['op2_amp_uv', 'op3_amp_uv', 'op4_amp_uv',
                  'op_sum_uv', 'op2_implicit_ms']:
            features[k] = np.nan
    # §9.2: PhNR family, LA 3.0 only        
    if protocol.strip().upper() == 'LA 3.0':
        b_it = features.get('b_implicit_ms', np.nan)
        if not np.isnan(b_it):
            features.update(extract_phnr(signal, time_ms, b_it, noise_rms_uv,
                                         hardware_highpass_hz=hardware_highpass_hz))
            b_amp = features.get('b_amp_uv', np.nan)
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
    features.update(extract_nonlinear_features(signal))
    features.update(extract_dwt_band_energies(signal, fs_hz, flash_onset_sample))
    a_implicit = features.get('a_implicit_ms', np.nan)
    b_implicit = features.get('b_implicit_ms', np.nan)
    features.update(extract_bwave_derivative_features(
        signal, fs_hz, b_implicit, flash_onset_sample))
    features.update(extract_awave_descending_inflection(
        signal, fs_hz, a_implicit, b_implicit, flash_onset_sample))

    # §9.4: frequency-domain
    features.update(extract_frequency_domain_features(signal, fs_hz, protocol))

    return features

# ---------------------------------------------------------------------------
# Self-test: confirms the pipeline runs on every protocol and that Section
# 9.3 (nonlinear/DWT/derivative features) fires on ALL protocols, not just
# LA 3.0 -- this was the specific bug fixed during the Chapter 9 review.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    fs_hz = 2000.0
    t = np.arange(0, 0.3, 1 / fs_hz)
    # Synthetic biphasic ERG-like waveform: a-wave trough ~15ms, b-wave peak ~50ms
    signal = (-50 * np.exp(-((t - 0.015) ** 2) / (2 * 0.006 ** 2))
              + 120 * np.exp(-((t - 0.050) ** 2) / (2 * 0.020 ** 2)))
    op_signal = signal + 5 * np.sin(2 * np.pi * 100 * (t*1000)) * np.exp(-((t - 0.03) ** 2) / (2 * 0.02 ** 2))

    protocols = ['DA 0.01', 'DA 3.0', 'DA 10.0', 'LA 3.0', 'LA 30 Hz']
    expected_counts = {'DA 0.01': 25, 'DA 3.0': 25, 'DA 10.0': 25, 'LA 3.0': 27, 'LA 30 Hz': 26}

    meta_keys = {'protocol', 'flash_midpoint_correction_applied',
                 'flash_midpoint_correction_ms', 'op_mar_technical',
                 'a_wave_mar_technical', 'phnr_mar_technical',
                 'phnr_polarity_atypical'}

    print(f"{'Protocol':10s} {'#Features':10s} {'Expected':10s} {'Has NLTF?':10s} {'Has PhNR?':10s} {'Has FreqDom?':12s}")
    print("-" * 70)
    all_pass = True
    for protocol in protocols:
        feats = extract_all_features(
            signal, fs_hz, protocol=protocol, flash_onset_sample=0,
            flash_duration_ms=1.0, op_signal=op_signal, noise_rms_uv=1.0)
        feature_keys = [k for k in feats if k not in meta_keys]
        n = len(feature_keys)
        has_nltf = 'hurst_exponent' in feats
        has_phnr = 'phnr_amp_uv' in feats and not np.isnan(feats['phnr_amp_uv'])
        has_freq = 'peak_freq_hz' in feats
        ok = (n == expected_counts[protocol])
        all_pass &= ok
        print(f"{protocol:10s} {n:<10d} {expected_counts[protocol]:<10d} {str(has_nltf):10s} {str(has_phnr):10s} {str(has_freq):12s} {'OK' if ok else 'MISMATCH'}")

    print("\nSample output for protocol='DA 3.0' (should include Section 9.3 keys):")
    sample = extract_all_features(signal, fs_hz, protocol='DA 3.0',
                                   flash_onset_sample=0, op_signal=op_signal)
    for k, v in sample.items():
        print(f"  {k}: {v}")

    print("\nALL PROTOCOL COUNTS MATCH EXPECTED" if all_pass else "\nSOME COUNTS MISMATCHED")
