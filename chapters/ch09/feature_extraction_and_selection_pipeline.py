# Chapter 9: feature extraction and selection pipeline
# The functions of Chapter 9 without the worked examples: every feature
# extractor, the four selection methods, select_features() (§9.5.5), and
# extract_all_features(). Import them, or run this file from the
# repository folder to extract the features of the Chapter 3 sample:
#     python chapters/ch09/feature_extraction_and_selection_pipeline.py

import numpy as np
from typing import Dict, Any
from scipy.signal import find_peaks

FS_HZ = 2000.0  # sampling rate used in this book's examples (Hz)

# Two ISCEV flash-duration constants (Robson et al., 2022):
ISCEV_FLASH_MAX_DURATION_MS = 5.0             # p. 168: longest flash
FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS = 1.0  # p. 174: shorter is
                                              # treated as instant


def noise_peak_to_peak(signal_uv: np.ndarray,
                       time_ms: np.ndarray,
                       window_ms: float = 100.0) -> float:
    """Peak-to-peak noise in the window before the flash.

    Noise is measured peak to peak, as in Chapter 2.
    """
    pre = signal_uv[(time_ms >= -window_ms) & (time_ms < 0)]
    return float(pre.max() - pre.min()) if pre.size >= 2 else np.nan


def flash_correction_ms(flash_duration_ms: float) -> float:
    """Half the flash duration for flashes of 1 ms or longer."""
    if flash_duration_ms >= FLASH_MIDPOINT_CORRECTION_THRESHOLD_MS:
        return flash_duration_ms / 2.0
    return 0.0


def extract_a_wave(signal_uv: np.ndarray,
                   time_ms: np.ndarray,
                   protocol: str,
                   hardware_lowpass_hz: float = 300.0,
                   flash_duration_ms: float = 0.0,
                   search_start: float = 5.0,
                   search_end: float = 40.0) -> Dict[str, Any]:
    """Extract a-wave amplitude and implicit time (broadband sweep).

    The a-wave is not scored for DA 0.01 and LA 30 Hz, so NaN is
    returned for these protocols. For DA 3.0, DA 10.0, and LA 3.0,
    the amplitude is measured from the average pre-flash baseline to
    the a-wave trough (Robson et al., 2022, p. 174).

    When no a-wave is found, hardware_lowpass_hz is compared with a
    project threshold (30 Hz dark-adapted, 35 Hz LA 3.0). A lower
    setting marks a technical cause rather than a physiological one.
    The thresholds lie above the mean upper frequency of the a-b
    complex, 25.35 +/- 3.77 Hz dark-adapted and 32.47 +/- 3.68 Hz
    light-adapted (Chen, Zheng and Lei, 2013; 16 eyes of 8 adults).
    """
    corr = flash_correction_ms(flash_duration_ms)
    proto = protocol.strip().upper()
    if proto in ('DA 0.01', 'LA 30 HZ'):
        return {'a_amp_uv': np.nan, 'a_implicit_ms': np.nan}

    lowpass_threshold = 35.0 if proto == 'LA 3.0' else 30.0
    missing = {'a_amp_uv': np.nan, 'a_implicit_ms': np.nan,
               'a_wave_mar_technical':
                   hardware_lowpass_hz < lowpass_threshold}

    mask = (time_ms >= search_start) & (time_ms <= search_end)
    if not mask.any():
        return missing
    window_amp = signal_uv[mask]
    window_time = time_ms[mask]
    i = int(np.argmin(window_amp))
    a_amp_raw = float(window_amp[i])
    a_time = float(window_time[i]) - corr

    pre = time_ms < 0
    baseline = float(signal_uv[pre].mean()) if pre.any() else 0.0
    if a_amp_raw >= baseline:   # trough must fall below baseline
        return missing

    return {'a_amp_uv': round(abs(a_amp_raw - baseline), 2),
            'a_implicit_ms': round(a_time, 2),
            'flash_midpoint_correction_ms': corr}


def extract_b_wave(signal_uv: np.ndarray,
                   time_ms: np.ndarray,
                   protocol: str,
                   a_time_ms: float = np.nan,
                   flash_duration_ms: float = 0.0,
                   search_end: float = 150.0,
                   noise_pp_uv: float = None,
                   noise_multiple: float = 1.5) -> Dict[str, Any]:
    """Extract b-wave amplitude (a-wave trough to peak) and time.

    The b-wave is the highest peak after the a-wave whose prominence
    exceeds noise_multiple x noise_pp_uv, the peak-to-peak noise
    before the flash (a project convention). A b-wave smaller than
    the a-wave (an electronegative ERG) is therefore still found.
    NaN is returned when no peak qualifies, and for LA 30 Hz, which
    has no b-wave (Robson et al., 2022, p. 175).

    The amplitude is measured from the a-wave trough (Robson et al.,
    2022, p. 174). For DA 0.01, pass a_time_ms = NaN: the amplitude
    is then measured from the lowest point between the flash and the
    peak, and the search starts 20 ms after the flash (a project
    convention). If noise_pp_uv is not given, it is measured from
    the 100 ms before the flash.
    """
    if protocol.strip().upper() == 'LA 30 HZ':
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}
    if noise_pp_uv is None:
        noise_pp_uv = noise_peak_to_peak(signal_uv, time_ms)

    corr = flash_correction_ms(flash_duration_ms)
    if np.isnan(a_time_ms):
        b_start = 20.0
    else:
        b_start = a_time_ms + corr
    mask = (time_ms >= b_start) & (time_ms <= search_end)
    if not mask.any():
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}

    window_amp = signal_uv[mask]
    window_time = time_ms[mask]
    peaks, _ = find_peaks(window_amp,
                          prominence=noise_multiple * noise_pp_uv)
    if len(peaks) == 0:
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}
    i = int(peaks[np.argmax(window_amp[peaks])])
    b_peak = float(window_amp[i])
    b_peak_time = float(window_time[i])

    if np.isnan(a_time_ms):
        before = (time_ms >= 0) & (time_ms <= b_peak_time)
        reference = float(signal_uv[before].min())
    else:
        a_idx = int(np.argmin(np.abs(time_ms - (a_time_ms + corr))))
        reference = float(signal_uv[a_idx])

    b_amp_uv = b_peak - reference
    if b_amp_uv <= 0:
        return {'b_amp_uv': np.nan, 'b_implicit_ms': np.nan}
    return {'b_amp_uv': round(b_amp_uv, 2),
            'b_implicit_ms': round(b_peak_time - corr, 2),
            'flash_midpoint_correction_ms': corr}


def compute_ba_ratio(b_amp_uv: float, a_amp_uv: float) -> float:
    """Compute the b/a amplitude ratio.

    Returns NaN if either amplitude is missing or a_amp_uv is zero.
    A ratio below 1.0 marks an electronegative ERG, which has
    several genetic and acquired causes (Jiang and Mahroo, 2021).
    """
    if np.isnan(b_amp_uv) or np.isnan(a_amp_uv) or a_amp_uv == 0:
        return np.nan
    return round(b_amp_uv / a_amp_uv, 3)


def extract_oscillatory_potentials(op_signal_uv: np.ndarray,
                                   time_ms: np.ndarray,
                                   hardware_lowpass_hz: float = 300.0,
                                   min_prom_uv: float = 5.0,
                                   min_dist_ms: float = 4.0,
                                   fs: float = FS_HZ,
                                   search_start_ms: float = 15.0,
                                   noise_multiple: float = 1.5
                                   ) -> Dict[str, Any]:
    """Extract OP2, OP3, OP4 amplitudes and OP2 implicit time.

    The first peak at or after search_start_ms is OP1 and is not
    reported (Hancock and Kraft, 2008; Arias-Alvarez et al., 2024,
    Table 4). A peak counts when its prominence exceeds
    noise_multiple x the peak-to-peak noise of the OP signal in the
    100 ms before the flash (a project convention); min_prom_uv is
    used if there are no pre-flash samples. OPs are set to NaN and
    flagged as technical when the hardware low-pass is below 300 Hz
    (Robson et al., 2022, p. 171).
    """
    keys = ['op2_amp_uv', 'op3_amp_uv', 'op4_amp_uv',
            'op_sum_uv', 'op2_implicit_ms']
    op_mar_technical = hardware_lowpass_hz < 300.0
    nan_result = {k: np.nan for k in keys}
    nan_result['op_mar_technical'] = op_mar_technical
    if op_mar_technical:
        return nan_result

    post = (time_ms >= 0) & (time_ms <= 100)
    if not post.any():
        return nan_result
    post_amp = op_signal_uv[post]
    post_time = time_ms[post]

    noise_pp = noise_peak_to_peak(op_signal_uv, time_ms)
    if np.isnan(noise_pp) or noise_pp <= 0:
        prominence = min_prom_uv
    else:
        prominence = noise_multiple * noise_pp

    dist = max(1, int(min_dist_ms * fs / 1000))
    peaks, _ = find_peaks(post_amp, prominence=prominence,
                          distance=dist)
    peaks = [p for p in peaks if post_time[p] >= search_start_ms]
    if len(peaks) < 2:
        return nan_result

    results = dict(nan_result)
    op_amps = []
    # peaks[0] is OP1 and is not reported.
    for i, label in enumerate(['op2', 'op3', 'op4']):
        if i + 1 >= len(peaks):
            break
        peak_idx = peaks[i + 1]
        trough = float(post_amp[peaks[i]:peak_idx + 1].min())
        amp = float(post_amp[peak_idx]) - trough
        results[f'{label}_amp_uv'] = round(amp, 2)
        if label == 'op2':
            results['op2_implicit_ms'] = round(
                float(post_time[peak_idx]), 2)
        op_amps.append(amp)

    if len(op_amps) == 3:
        results['op_sum_uv'] = round(sum(op_amps), 2)
    return results

def extract_phnr(signal_uv: np.ndarray,
                 time_ms: np.ndarray,
                 b_time_ms: float,
                 noise_pp_uv: float = None,
                 hardware_highpass_hz: float = 0.3,
                 search_start: float = 60.0,
                 search_end: float = 200.0,
                 noise_multiple: float = 1.0) -> Dict[str, Any]:
    """Extract the PhNR amplitude from an LA 3.0 broadband sweep.

    The amplitude is SIGNED and measured from the baseline. A normal
    PhNR is negative (Frishman et al., 2018; Prencipe et al., 2020);
    a positive value is flagged by phnr_polarity_atypical as a data
    quality signal.

    The PhNR counts only when its size exceeds noise_multiple x the
    peak-to-peak noise before the flash (a project convention).
    If no PhNR is found, hardware_highpass_hz is compared with the
    0.3 Hz ISCEV setting (Frishman et al., 2018):
    a higher setting marks a technical cause, because it cuts the
    slow PhNR, rather than ganglion cell dysfunction.
    """
    technical = hardware_highpass_hz > 0.3
    if noise_pp_uv is None:
        noise_pp_uv = noise_peak_to_peak(signal_uv, time_ms)

    start = max(search_start, b_time_ms + 10.0)
    mask = (time_ms >= start) & (time_ms <= search_end)
    if not mask.any():
        return {'phnr_amp_uv': np.nan,
                'phnr_mar_technical': technical}

    segment = signal_uv[mask]
    seg_min = float(segment.min())
    seg_max = float(segment.max())
    if abs(seg_min) >= abs(seg_max):
        phnr = seg_min        # trough dominates: typical
    else:
        phnr = seg_max        # peak dominates: atypical

    if abs(phnr) < noise_multiple * noise_pp_uv:
        return {'phnr_amp_uv': np.nan,
                'phnr_polarity_atypical': False,
                'phnr_mar_technical': technical}

    return {'phnr_amp_uv': round(phnr, 2),
            'phnr_polarity_atypical': bool(phnr > 0)}

def hurst_rs(x: np.ndarray, min_window: int = 8) -> float:
    """Hurst exponent by rescaled-range (R/S) analysis.

    The signal is cut into windows of length n. In each window, R is
    the range of the cumulative deviations from the window mean and
    S is the standard deviation. The slope of log(mean R/S) against
    log(n) is the Hurst exponent (the method of Nair and Joseph,
    2014).
    """
    x = np.asarray(x, dtype=float)
    N = len(x)
    sizes, rs = [], []
    n = min_window
    while n <= N // 2:
        vals = []
        for start in range(0, N - n + 1, n):
            w = x[start:start + n]
            z = np.cumsum(w - w.mean())
            s = w.std()
            if s > 0:
                vals.append((z.max() - z.min()) / s)
        if vals:
            sizes.append(n)
            rs.append(np.mean(vals))
        n *= 2
    if len(sizes) < 3:
        return np.nan
    slope, _ = np.polyfit(np.log(sizes), np.log(rs), 1)
    return float(slope)


def approximate_entropy(x: np.ndarray, m: int = 2,
                        r_frac: float = 0.15) -> float:
    """Approximate entropy ApEn(m, r) (Pincus, 1991).

    m = 2 and r = 0.15 x SD, as in Nair and Joseph (2014).
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    r = r_frac * np.std(x)
    if n < 10 or r == 0:
        return np.nan

    def phi(k):
        z = np.array([x[i:i + k] for i in range(n - k + 1)])
        d = np.abs(z[:, None, :] - z[None, :, :]).max(axis=2)
        c = (d <= r).sum(axis=1) / (n - k + 1)
        return np.sum(np.log(c)) / (n - k + 1)

    return float(phi(m) - phi(m + 1))


def extract_nonlinear_features(signal: np.ndarray) -> Dict[str, Any]:
    """Hurst exponent and approximate entropy of the broadband
    signal. In Nair and Joseph (2014), approximate entropy was
    lower in every disease group than in controls, and the Hurst
    exponent differed between groups in both directions.
    """
    h = hurst_rs(signal)
    a = approximate_entropy(signal)
    return {
        'hurst_exponent': round(h, 4) if not np.isnan(h) else np.nan,
        'approximate_entropy':
            round(a, 4) if not np.isnan(a) else np.nan,
    }

import pywt
from fractions import Fraction
from scipy.signal import resample_poly

# Gauvin, Lina and Lachapelle (2014): 3413.33 Hz, 150 ms analyzed,
# from 20 ms before the flash to 130 ms after it.
GAUVIN_FS_HZ = 10240.0 / 3.0   # 3413.33 Hz
GAUVIN_N = 512                 # 150 ms at 3413.33 Hz
GAUVIN_START_MS = -20.0        # start, 20 ms before the flash

# (DWT level at 3413.33 Hz, window start ms, window end ms)
# Gauvin, Lina and Lachapelle (2014), Table 1
GAUVIN_DESCRIPTORS = {
    'dwt_20a_uv2':    (7, -20.0, 17.5),     # 20 Hz, a-wave
    'dwt_40a_uv2':    (6, 0.0, 17.5),       # 40 Hz, a-wave
    'dwt_20b_uv2':    (7, 17.5, 55.0),      # 20 Hz, b-wave
    'dwt_40b_uv2':    (6, 17.5, 55.0),      # 40 Hz, b-wave
    'dwt_80ops_uv2':  (5, 8.125, 55.0),     # 80 Hz, OPs
    'dwt_160ops_uv2': (4, 17.5, 40.35),     # 160 Hz, OPs
}


def extract_dwt_band_energies(signal: np.ndarray, fs_hz: float,
                              flash_onset_sample: int = 0
                              ) -> Dict[str, Any]:
    """Six Haar DWT band-energy descriptors (Gauvin, Lina and
    Lachapelle, 2014).

    The sweep is resampled to 3413.33 Hz, the rate of the original
    study (128/75 x 2000 Hz), and the 512 samples from 20 ms before
    the flash are analyzed, as in that study. DWT levels 7, 6, 5,
    and 4 then cover the 20, 40, 80, and 160 Hz bands, and the cell
    edges fall on the published window limits. Each descriptor is
    the sum of the squared detail coefficients whose centers lie
    inside its window.
    """
    ratio = Fraction(GAUVIN_FS_HZ / fs_hz).limit_denominator(1000)
    x = resample_poly(np.asarray(signal, dtype=float),
                      ratio.numerator, ratio.denominator)
    flash_ms = flash_onset_sample / fs_hz * 1000.0
    i0 = int(round((flash_ms + GAUVIN_START_MS) / 1000
                   * GAUVIN_FS_HZ))
    seg = x[i0:i0 + GAUVIN_N]
    if i0 < 0 or len(seg) < GAUVIN_N:
        return {key: np.nan for key in GAUVIN_DESCRIPTORS}

    coeffs = pywt.wavedec(seg, 'haar', level=7)
    out = {}
    for key, (level, t0, t1) in GAUVIN_DESCRIPTORS.items():
        d = coeffs[len(coeffs) - level]     # detail coefficients
        cell_ms = 2 ** level / GAUVIN_FS_HZ * 1000.0
        t_ms = GAUVIN_START_MS + (np.arange(len(d)) + 0.5) * cell_ms
        mask = (t_ms >= t0) & (t_ms <= t1)
        out[key] = round(float(np.sum(d[mask] ** 2)), 2)
    return out

def _smooth(x: np.ndarray, n: int = 7) -> np.ndarray:
    """Moving average (Wood, Margrain and Binns, 2014)."""
    return np.convolve(x, np.ones(n) / n, mode='same')


def _inflections(t: np.ndarray, x: np.ndarray, rising: bool):
    """Index of the main inflection on one edge, and the 1st
    derivative. Among the points where the 2nd derivative crosses
    zero with the expected slope sign, the steepest is taken."""
    d1 = np.gradient(x, t)
    d2 = np.gradient(d1, t)
    idx = np.where(np.diff(np.sign(d2)) != 0)[0]
    ok = [i for i in idx if (d1[i] > 0) == rising and d1[i] != 0]
    if not ok:
        return None, d1
    return max(ok, key=lambda i: abs(d1[i])), d1


def extract_bwave_derivative_features(signal: np.ndarray,
                                      fs_hz: float,
                                      b_implicit_ms: float,
                                      flash_onset_sample: int = 0,
                                      search_end_ms: float = 150.0
                                      ) -> Dict[str, Any]:
    """Time and gradient of the inflections on the rising and falling
    edges of the b-wave (Wood, Margrain and Binns, 2014).
    """
    out = {'b_ascending_inflection_ms': np.nan,
           'b_ascending_gradient_uv_ms': np.nan,
           'b_descending_inflection_ms': np.nan,
           'b_descending_gradient_uv_ms': np.nan}
    if np.isnan(b_implicit_ms):
        return out
    t = (np.arange(len(signal)) - flash_onset_sample) * 1000 / fs_hz
    x = _smooth(np.asarray(signal, dtype=float))

    # Rising edge: from the flash to just before the b-wave peak.
    m = (t >= 0.0) & (t <= b_implicit_ms - 1.0)
    if m.sum() >= 5:
        i, d1 = _inflections(t[m], x[m], rising=True)
        if i is not None:
            out['b_ascending_inflection_ms'] = round(
                float(t[m][i]), 2)
            out['b_ascending_gradient_uv_ms'] = round(float(d1[i]), 2)

    # Falling edge: from 3 ms after the peak.
    m = (t >= b_implicit_ms + 3.0) & (t <= search_end_ms)
    if m.sum() >= 5:
        i, d1 = _inflections(t[m], x[m], rising=False)
        if i is not None:
            out['b_descending_inflection_ms'] = round(
                float(t[m][i]), 2)
            out['b_descending_gradient_uv_ms'] = round(
                float(d1[i]), 2)
    return out


def extract_awave_descending_inflection(signal: np.ndarray,
                                        fs_hz: float,
                                        a_implicit_ms: float,
                                        flash_onset_sample: int = 0
                                        ) -> Dict[str, Any]:
    """Time of the inflection on the falling edge of the a-wave,
    between the flash and the a-wave trough. Its gradient was not
    significant in the source study (p = 0.097) and is not kept
    (Wood, Margrain and Binns, 2014).
    """
    if np.isnan(a_implicit_ms):
        return {'a_descending_inflection_ms': np.nan}
    t = (np.arange(len(signal)) - flash_onset_sample) * 1000 / fs_hz
    x = _smooth(np.asarray(signal, dtype=float))
    m = (t >= 0.0) & (t <= a_implicit_ms - 1.0)
    if m.sum() < 5:
        return {'a_descending_inflection_ms': np.nan}
    i, _ = _inflections(t[m], x[m], rising=False)
    if i is None:
        return {'a_descending_inflection_ms': np.nan}
    return {'a_descending_inflection_ms': round(float(t[m][i]), 2)}

from scipy.signal import welch


def extract_frequency_domain_features(signal: np.ndarray,
                                      fs_hz: float,
                                      protocol: str = 'DA 3.0',
                                      fmin: float = 0.0,
                                      fmax: float = 300.0,
                                      fundamental_hz: float = 30.0,
                                      n_harmonics: int = 3,
                                      bw_hz: float = 2.0
                                      ) -> Dict[str, Any]:
    """Peak frequency and spectral entropy of the broadband signal
    on every protocol; harmonic ratio on LA 30 Hz only.
    """
    freqs, psd = welch(signal, fs=fs_hz,
                       nperseg=min(256, len(signal)))
    band = (freqs >= fmin) & (freqs <= fmax)
    f_b, p_b = freqs[band], psd[band]
    out = {'peak_freq_hz': np.nan, 'spectral_entropy': np.nan}
    if len(p_b) > 1 and np.sum(p_b) > 0:
        out['peak_freq_hz'] = round(float(f_b[np.argmax(p_b)]), 2)
        p = p_b / np.sum(p_b)
        p = p[p > 0]
        if len(p) > 1:
            h = -np.sum(p * np.log(p)) / np.log(len(p))
            out['spectral_entropy'] = round(float(h), 4)

    if protocol.upper().replace(' ', '') in ('LA30HZ', 'LA30'):
        out['harmonic_ratio'] = np.nan
        total = np.sum(psd)
        if total > 0:
            half = max(bw_hz, float(freqs[1] - freqs[0]))
            power = 0.0
            for k in range(1, n_harmonics + 1):
                f0 = fundamental_hz * k
                m = (freqs >= f0 - half) & (freqs <= f0 + half)
                power += np.sum(psd[m])
            out['harmonic_ratio'] = round(float(power / total), 4)
    return out

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE


def select_rfe(X, y, k, seed=0, step=1):
    """Fit a Random Forest, drop the least important feature(s),
    refit, and repeat until k features remain."""
    est = RandomForestClassifier(n_estimators=200, random_state=seed,
                                 n_jobs=-1)
    rfe = RFE(est, n_features_to_select=k, step=step).fit(X, y)
    return X.columns[rfe.support_].tolist()

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif


def select_pearson(X, y, k):
    """Rank features by their strongest one-vs-rest linear link with
    the class label (|r| for each class indicator, maximum over
    classes), and keep the k highest."""
    scores = {}
    for col in X.columns:
        r = [abs(np.corrcoef(X[col], (y == c).astype(float))[0, 1])
             for c in np.unique(y)]
        scores[col] = np.nanmax(r)
    ranked = pd.Series(scores).sort_values(ascending=False)
    return ranked.index[:k].tolist()


import numpy as np
import pandas as pd
from sklearn.feature_selection import (mutual_info_classif,
                                       mutual_info_regression)


def select_mrmr(X, y, k, seed=0):
    """Greedy mRMR, difference form (Ding and Peng, 2005): at each
    step add the feature with the highest relevance I(f; y) minus
    its mean redundancy with the features already chosen."""
    relevance = pd.Series(mutual_info_classif(X, y,
                                              random_state=seed),
                          index=X.columns)
    chosen = [relevance.idxmax()]
    while len(chosen) < k:
        best, best_score = None, -np.inf
        for f in X.columns.difference(chosen):
            red = np.mean([mutual_info_regression(
                X[[c]], X[f], random_state=seed)[0] for c in chosen])
            score = relevance[f] - red
            if score > best_score:
                best, best_score = f, score
        chosen.append(best)
    return chosen

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance


def select_rf(X, y, k, seed=0):
    """Rank features by impurity-based importance of one fitted
    forest, and keep the k highest."""
    rf = RandomForestClassifier(n_estimators=300, random_state=seed,
                                n_jobs=-1).fit(X, y)
    imp = pd.Series(rf.feature_importances_, index=X.columns)
    return imp.sort_values(ascending=False).index[:k].tolist()


import pandas as pd


def select_features(X_train, y_train, k=40, min_votes=2):
    """Return (votes table, selected features). Every method sees the
    training data only. Uses select_pearson, select_mrmr, select_rfe,
    and select_rf from §9.5.1 to §9.5.4."""
    picks = {'pearson': select_pearson(X_train, y_train, k),
             'mrmr':    select_mrmr(X_train, y_train, k),
             'rfe':     select_rfe(X_train, y_train, k),
             'rf':      select_rf(X_train, y_train, k)}
    votes = pd.DataFrame({m: X_train.columns.isin(p).astype(int)
                          for m, p in picks.items()},
                         index=X_train.columns)
    votes['votes'] = votes.sum(axis=1)
    selected = votes.index[votes['votes'] >= min_votes].tolist()
    return votes.sort_values('votes', ascending=False), selected

# Usage: X_train is the coded training matrix (Chapter 11) and
# y_train the labels.
# votes, selected = select_features(X_train, y_train, k=40,
#                                   min_votes=2)

def extract_all_features(signal: np.ndarray, fs_hz: float,
                         protocol: str = 'DA 3.0',
                         flash_onset_sample: int = 0,
                         flash_duration_ms: float = 0.0,
                         op_signal: np.ndarray = None,
                         hardware_lowpass_hz: float = 300.0,
                         hardware_highpass_hz: float = 0.3
                         ) -> Dict[str, Any]:
    """Assemble every feature family of this chapter for one
    recording.

    flash_duration_ms defaults to 0.0, as for a xenon flashtube;
    pass the real duration for LED systems so that the ISCEV
    flash-midpoint correction is applied where needed.

    hardware_lowpass_hz and hardware_highpass_hz are device metadata
    (Chapter 5). They are used only to tell a technical absence
    from a physiological one when the a-wave, PhNR, or OPs are not
    found. The noise is measured peak to peak in the 100 ms before
    the flash, as in Chapter 2.
    """
    time_ms = ((np.arange(len(signal)) - flash_onset_sample)
               * 1000.0 / fs_hz)
    proto = protocol.strip().upper()
    noise_pp = noise_peak_to_peak(signal, time_ms)
    features = {'protocol': protocol}

    # §9.1: a-wave, b-wave, b/a ratio
    a = extract_a_wave(signal, time_ms, protocol,
                       hardware_lowpass_hz=hardware_lowpass_hz,
                       flash_duration_ms=flash_duration_ms)
    features.update(a)
    b = extract_b_wave(signal, time_ms, protocol,
                       a_time_ms=a['a_implicit_ms'],
                       flash_duration_ms=flash_duration_ms,
                       noise_pp_uv=noise_pp)
    features.update(b)
    features['ba_ratio'] = compute_ba_ratio(b['b_amp_uv'],
                                            a['a_amp_uv'])

    # §9.1: OPs, only on DA 3.0 and DA 10.0 and only from a separate
    # OP signal (75-300 Hz); otherwise the OP features are NaN.
    op_keys = ['op2_amp_uv', 'op3_amp_uv', 'op4_amp_uv',
               'op_sum_uv', 'op2_implicit_ms']
    if proto in ('DA 3.0', 'DA 10.0') and op_signal is not None:
        features.update(extract_oscillatory_potentials(
            op_signal, time_ms,
            hardware_lowpass_hz=hardware_lowpass_hz, fs=fs_hz))
    else:
        for k in op_keys:
            features[k] = np.nan

    # §9.2: PhNR family, LA 3.0 only
    if proto == 'LA 3.0':
        b_it = features.get('b_implicit_ms', np.nan)
        features['phnr_amp_uv'] = np.nan
        features['phnr_bwave_ratio'] = np.nan
        if not np.isnan(b_it):
            features.update(extract_phnr(
                signal, time_ms, b_it, noise_pp_uv=noise_pp,
                hardware_highpass_hz=hardware_highpass_hz))
            b_amp = features.get('b_amp_uv', np.nan)
            phnr = features.get('phnr_amp_uv', np.nan)
            if not (np.isnan(b_amp) or np.isnan(phnr)) and b_amp:
                features['phnr_bwave_ratio'] = round(
                    float(phnr / b_amp), 4)

    # §9.3: nonlinear, DWT bands, derivative features
    features.update(extract_nonlinear_features(signal))
    features.update(extract_dwt_band_energies(
        signal, fs_hz, flash_onset_sample))
    features.update(extract_bwave_derivative_features(
        signal, fs_hz, features.get('b_implicit_ms', np.nan),
        flash_onset_sample))
    features.update(extract_awave_descending_inflection(
        signal, fs_hz, features.get('a_implicit_ms', np.nan),
        flash_onset_sample))

    # §9.4: frequency-domain features
    features.update(extract_frequency_domain_features(
        signal, fs_hz, protocol))
    return features

if __name__ == '__main__':
    # Demonstration on the Chapter 3 sample (DA 3.0, flash at 100 ms).
    # The OP signal is the 75 to 300 Hz band of the recording (§9.1).
    from scipy.signal import butter, sosfiltfilt
    df = pd.read_csv('data/samples/normal_001_DA3.csv')
    signal, fs = df['amplitude_uV'].to_numpy(), 2000.0
    sos = butter(4, [75, 300], btype='band', fs=fs, output='sos')
    features = extract_all_features(signal, fs, protocol='DA 3.0',
                                    flash_onset_sample=200,
                                    op_signal=sosfiltfilt(sos, signal))
    for name, value in features.items():
        print(f'{name:30s} {value}')
