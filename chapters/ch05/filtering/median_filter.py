# Chapter 5: median filter for high-frequency spike suppression
# The function is used by complete_filter_pipeline.py.

import numpy as np

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
