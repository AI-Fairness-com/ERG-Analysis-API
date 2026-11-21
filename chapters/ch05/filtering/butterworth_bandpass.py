# Chapter 5, §5.3.1: Butterworth band-pass filter, run forward and backward
# Run from the repository folder:
#     python chapters/ch05/filtering/butterworth_bandpass.py

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
