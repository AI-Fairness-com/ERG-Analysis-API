# Chapter 5: notch filter and mains interference detector
# Run from the repository folder:
#     python chapters/ch05/filtering/notch_filter.py

import numpy as np
from scipy.signal import sosfiltfilt

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
