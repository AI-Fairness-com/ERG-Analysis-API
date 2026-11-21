# Chapter 5: complete ERG filter pipeline, the chapter's full script
# The code of Chapter 5 in the order of the book: the Butterworth
# band-pass filter, the notch filter and mains detector, the median
# filter, the complete pipeline with its ISCEV checks, and the streaming
# filter. Run from the repository folder:
#     python chapters/ch05/filtering/complete_filter_pipeline.py

import numpy as np
import pandas as pd


# load_recording_from_csv() is the loader of Chapter 4, §4.1.4, repeated
# here so that this script runs on its own.
def load_recording_from_csv(csv_path: str) -> dict:
    """Read a standardized ERG CSV file (Chapter 3, §3.4.4) into a dictionary."""
    df = pd.read_csv(csv_path)
    t = df['time_ms'].values
    return {
        'time_ms': t,                                  # time points (ms)
        'amplitude_uv': df['amplitude_uV'].values,     # voltages (µV)
        'fs_hz': 1000 / (t[1] - t[0]),                 # sampling rate (Hz)
        'electrode_type': df['electrode_type'].iloc[0],
        'protocol': df['protocol'].iloc[0],
    }


# ── Butterworth band-pass filter, run forward and backward ─────────
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, sosfreqz

ISCEV_HIGHPASS_HZ = 0.3     # target high-pass corner (ISCEV: 0.3 Hz or lower)
ISCEV_LOWPASS_HZ = 300.0    # target low-pass corner (ISCEV: 300 Hz or higher)
FILTER_ORDER = 4            # this project's choice (§5.3.1)


def per_pass_corners(highpass_hz: float, lowpass_hz: float,
                     order: int = FILTER_ORDER) -> tuple:
    """Corners for each pass, so that two passes are 3 dB down at the targets.

    Two passes double every loss in decibels, so each pass may lose only
    1.5 dB at the target corners (§5.3.1, Fig. 5.1B).
    """
    c = (10 ** 0.15 - 1) ** (1 / (2 * order))     # about 0.895 for order 4
    return highpass_hz * c, lowpass_hz / c


def design_butterworth_bandpass(highpass_hz: float, lowpass_hz: float,
                                fs_hz: float,
                                order: int = FILTER_ORDER) -> np.ndarray:
    """Design the band-pass filter as second-order sections (see box)."""
    lo, hi = per_pass_corners(highpass_hz, lowpass_hz, order)
    if hi >= fs_hz / 2:   # half the sampling rate, the Nyquist frequency
        raise ValueError(f'Low-pass corner {hi:.0f} Hz must be below half the '
                         f'sampling rate ({fs_hz / 2:.0f} Hz).')
    return butter(order, [lo, hi], btype='bandpass', fs=fs_hz, output='sos')


def apply_bandpass(signal_uv: np.ndarray, fs_hz: float,
                   highpass_hz: float = ISCEV_HIGHPASS_HZ,
                   lowpass_hz: float = ISCEV_LOWPASS_HZ,
                   order: int = FILTER_ORDER) -> np.ndarray:
    """Filter forward, then backward (sosfiltfilt): peaks keep their times."""
    sos = design_butterworth_bandpass(highpass_hz, lowpass_hz, fs_hz, order)
    return sosfiltfilt(sos, signal_uv)


def plot_filter_response(sos: np.ndarray, fs_hz: float) -> tuple:
    """Plot the two-pass gain of the filter and return its 3 dB band."""
    f = np.logspace(-2, np.log10(fs_hz / 2 * 0.999), 20000)   # log-spaced, Hz
    _, h = sosfreqz(sos, worN=f, fs=fs_hz)
    gain_db = 2 * 20 * np.log10(np.abs(h) + 1e-12)            # two passes
    inside = f[gain_db >= -3]
    low, high = inside[0], inside[-1]

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.semilogx(f, gain_db, color='#2E75B6', lw=1.8)
    ax.axhline(-3, color='gray', ls=':', label='−3 dB')
    for x in (low, high):
        ax.axvline(x, color='red', ls='--', lw=1.0)
    ax.set_ylim(-80, 5)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Gain, two passes (dB)')
    ax.set_title(f'3 dB band of the two passes: {low:.2f} to {high:.0f} Hz')
    ax.legend()
    plt.show()
    return low, high


# Example: the pipeline filter at this book's sampling rate of 2000 Hz.
sos = design_butterworth_bandpass(ISCEV_HIGHPASS_HZ, ISCEV_LOWPASS_HZ,
                                  fs_hz=2000)
low, high = plot_filter_response(sos, fs_hz=2000)
print(f'3 dB band of the two passes: {low:.2f} to {high:.0f} Hz')

# Expected output:
# 3 dB band of the two passes: 0.30 to 305 Hz

# ── Notch filter and mains detector ─────────────────────────────────
from scipy.signal import iirnotch, tf2sos, welch


def apply_notch_filter(signal_uv: np.ndarray, fs_hz: float,
                       notch_hz: float = 50.0,
                       quality_factor: float = 50.0) -> np.ndarray:
    """Remove a narrow band around notch_hz, forward and backward.

    notch_hz       : 50.0 in the UK and Europe, 60.0 in North America.
    quality_factor : Q; the notch is notch_hz / Q wide at -3 dB (one pass).
    Off by default in the pipeline (ISCEV: notch filters should not be used).
    """
    b, a = iirnotch(notch_hz, quality_factor, fs=fs_hz)
    return sosfiltfilt(tf2sos(b, a), signal_uv)


def detect_mains_interference(signal_uv: np.ndarray, fs_hz: float,
                              notch_hz: float = 50.0,
                              threshold_db: float = 6.0,
                              shoulder_hz: float = 5.0) -> bool:
    """Return True if the spectrum has a clear peak at the mains frequency.

    The power at notch_hz is compared with the average power within
    shoulder_hz on either side. A peak more than threshold_db above it
    counts as interference (this project's threshold).
    """
    # welch() estimates the power of the signal at each frequency.
    freqs, psd = welch(signal_uv, fs=fs_hz, nperseg=min(1024, len(signal_uv)))
    k = int(np.argmin(np.abs(freqs - notch_hz)))
    near = np.abs(freqs - notch_hz) <= shoulder_hz
    side = near & (np.arange(freqs.size) != k)      # neighbors, not the peak
    peak_db = 10 * np.log10(psd[k] + 1e-30)
    side_db = 10 * np.log10(np.mean(psd[side]) + 1e-30)
    return bool(peak_db - side_db > threshold_db)


# Example: a 2 s test signal with and without 20 µV of 50 Hz hum.
fs = 2000.0
t_s = np.arange(0, 2.0, 1 / fs)
noise = np.random.default_rng(0).normal(0, 5, t_s.size)
hum = 20 * np.sin(2 * np.pi * 50 * t_s)
print('With hum:   ', detect_mains_interference(noise + hum, fs))
print('Without hum:', detect_mains_interference(noise, fs))


def amplitude_at(signal_uv, fs_hz, freq_hz):
    """Amplitude (µV) of one frequency, from a 1 s middle segment."""
    mid = signal_uv[len(signal_uv) // 4: len(signal_uv) // 4 + int(fs_hz)]
    spectrum = np.fft.rfft(mid) * 2 / len(mid)       # 1 Hz per bin
    return abs(spectrum[int(freq_hz)])


cleaned = apply_notch_filter(noise + hum, fs)
print(f'50 Hz amplitude before: {amplitude_at(noise + hum, fs, 50):.1f} µV, '
      f'after: {amplitude_at(cleaned, fs, 50):.1f} µV')

# Expected output:
# With hum:    True
# Without hum: False
# 50 Hz amplitude before: 20.1 µV, after: 0.6 µV

# ── Median filter for high-frequency spike suppression ──────────
from scipy.signal import medfilt

def apply_median_filter(signal_uv:np.ndarray, kernel_samples:int=5) -> np.ndarray:
    """
    Remove high-amplitude short-duration spikes using a median filter.
    kernel_samples : must be odd; 5 samples is the default, corresponding
    to 2.5 ms at this book's sampling rate of 2000 Hz (5 ms at the
    ISCEV minimum of 1000 Hz).
    This filter is applied first in the pipeline (see §5.3.4),
    before the bandpass and notch filters, to prevent spike-induced ringing.
    """
    if kernel_samples % 2 == 0:
        kernel_samples += 1  # scipy.signal.medfilt requires an odd kernel
    return medfilt(signal_uv, kernel_size=kernel_samples)

# ── Complete ERG filter pipeline (ISCEV settings: Robson et al., 2022) ──
def apply_erg_filter_pipeline(recording: dict,
                              stim_onset_ms: float = 0.0,
                              apply_median: bool = True,
                              apply_notch: bool = False,
                              notch_hz: float = 50.0,
                              hardware_highpass_hz: float = None,
                              hardware_lowpass_hz: float = None,
                              highpass_hz: float = ISCEV_HIGHPASS_HZ,
                              lowpass_hz: float = ISCEV_LOWPASS_HZ) -> dict:
    """Filter a recording in a fixed order and log every step.

    Order: 1. median filter (on by default), 2. notch filter (off by
    default; runs only if apply_notch=True), 3. Butterworth band-pass,
    forward and backward. The hardware corners are optional (§5.1.3).
    Returns a copy of the recording with filtered_uv and filter_log added.
    """
    sig = np.asarray(recording['amplitude_uv'], dtype=float).copy()
    t = recording['time_ms']
    fs = recording['fs_hz']
    log = []

    # ISCEV checks: sampling rate and pre-flash baseline (Robson et al., 2022)
    pre_ms = stim_onset_ms - t[0]
    sampling_ok = bool(fs >= 1000.0)
    prestimulus_ok = bool(pre_ms >= 20.0)
    log.append(f'Sampling rate {fs:.0f} Hz (ISCEV: 1000 Hz or higher)')
    log.append(f'Pre-flash baseline {pre_ms:.0f} ms (ISCEV: at least 20 ms)')

    # Hardware corners: the software band must lie inside them (§5.1.3)
    if hardware_lowpass_hz is not None and hardware_lowpass_hz < lowpass_hz:
        lowpass_hz = 0.95 * hardware_lowpass_hz
        log.append(f'WARNING: hardware low-pass {hardware_lowpass_hz:.0f} Hz;'
                   f' software corner set to {lowpass_hz:.0f} Hz')
    if hardware_highpass_hz is not None and hardware_highpass_hz > highpass_hz:
        highpass_hz = 1.05 * hardware_highpass_hz
        log.append(f'WARNING: hardware high-pass {hardware_highpass_hz} Hz;'
                   f' software corner set to {highpass_hz:.2f} Hz')
    bandwidth_ok = bool(highpass_hz <= 0.3 and lowpass_hz >= 300.0)

    # Step 1: median filter (spike removal, §5.3.3)
    if apply_median:
        before = sig.copy()
        sig = apply_median_filter(sig, kernel_samples=5)
        # A spike sample changed by more than 10 times the typical
        # sample-to-sample noise (a robust estimate from the median).
        d = np.diff(before)
        noise_uv = 1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(2)
        n_spikes = int(np.sum(np.abs(before - sig) > 10 * noise_uv))
        log.append(f'Median filter: 5 samples; {n_spikes} spike sample(s)'
                   ' removed')

    # Step 2: notch filter, off by default (ISCEV: should not be used)
    mains_detected = detect_mains_interference(sig, fs, notch_hz)
    if mains_detected:
        log.append(f'Mains interference detected at {notch_hz:.0f} Hz')
    if apply_notch:
        sig = apply_notch_filter(sig, fs, notch_hz)
        log.append(f'NOTCH APPLIED at {notch_hz:.0f} Hz on request;'
                   ' output flagged')
    else:
        log.append('Notch filter: not applied')

    # Step 3: Butterworth band-pass, forward and backward (§5.3.1)
    sig = apply_bandpass(sig, fs, highpass_hz, lowpass_hz)
    log.append(f'Band-pass: order 4, {highpass_hz:.2f} to {lowpass_hz:.0f}'
               ' Hz, forward and backward')

    result = dict(recording)
    result.update({
        'filtered_uv': sig,
        'filter_log': log,
        'notch_applied': apply_notch,
        'mains_detected': mains_detected,
        'iscev_checks': {'sampling_rate_ok': sampling_ok,
                         'prestimulus_ok': prestimulus_ok,
                         'bandwidth_ok': bandwidth_ok,
                         'notch_not_used': not apply_notch},
    })
    return result


# Example: the Chapter 3 sample file (flash at 100 ms), loaded with
# load_recording_from_csv() from §4.1.4. A one-sample spike and 20 µV of
# 50 Hz hum are added, so that every step has something to do.
recording = load_recording_from_csv('data/samples/normal_001_DA3.csv')
t_s = recording['time_ms'] / 1000
noisy = dict(recording)
noisy['amplitude_uv'] = (recording['amplitude_uv']
                         + 20 * np.sin(2 * np.pi * 50 * t_s))
i_spike = int(np.argmin(np.abs(recording['time_ms'] - 300)))   # at 300 ms
noisy['amplitude_uv'][i_spike] += 300

filtered = apply_erg_filter_pipeline(noisy, stim_onset_ms=100)
print('\n'.join(filtered['filter_log']))
print(filtered['iscev_checks'])

# Expected output:
# Sampling rate 2000 Hz (ISCEV: 1000 Hz or higher)
# Pre-flash baseline 100 ms (ISCEV: at least 20 ms)
# Median filter: 5 samples; 1 spike sample(s) removed
# Mains interference detected at 50 Hz
# Notch filter: not applied
# Band-pass: order 4, 0.30 to 300 Hz, forward and backward
# {'sampling_rate_ok': True, 'prestimulus_ok': True, 'bandwidth_ok': True,
#  'notch_not_used': True}

# ── Streaming mode: causal filter that keeps its state ──────────────
from scipy.signal import sosfilt


class StreamingERGFilter:
    """Causal (one-pass) band-pass filter for signals that arrive in chunks.

    For stored recordings, use apply_erg_filter_pipeline() instead (§5.3.4).
    """

    def __init__(self, fs_hz: float, highpass_hz: float = 0.3,
                 lowpass_hz: float = 300.0, order: int = FILTER_ORDER):
        # One pass only, so the ISCEV corners are used directly (§5.4.2).
        self.sos = butter(order, [highpass_hz, lowpass_hz], btype='bandpass',
                          fs=fs_hz, output='sos')
        self.reset()

    def reset(self):
        """Clear the filter state; call once at the start of a session."""
        self.state = np.zeros((self.sos.shape[0], 2))

    def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """Filter one chunk and keep the state for the next chunk."""
        filtered, self.state = sosfilt(self.sos, chunk, zi=self.state)
        return filtered


# Example: filtering in chunks of 50 samples gives the same output as
# filtering the whole recording at once, because the state is carried over.
x = recording['amplitude_uv']
stream = StreamingERGFilter(fs_hz=2000)
chunks = [stream.process_chunk(x[i:i + 50]) for i in range(0, len(x), 50)]
whole = sosfilt(stream.sos, x)
print('Same as one pass over the whole recording:',
      np.allclose(np.concatenate(chunks), whole))

# Expected output:
# Same as one pass over the whole recording: True
