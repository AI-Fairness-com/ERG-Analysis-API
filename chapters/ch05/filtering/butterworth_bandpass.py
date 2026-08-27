# -*- coding: utf-8 -*-
"""
Chapter 5: ERG-Specific Filtering
Butterworth Bandpass Filter for ERG Signals (ISCEV Standard)

This script demonstrates the 4th-order Butterworth bandpass filter
with zero-phase filtering for full-field ERG signals.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, sosfreqz

# ISCEV Standard Parameters
FS_HZ = 1000                    # Sampling rate (Hz)
LOWCUT_HZ = 0.3                 # High-pass cutoff (preserves PhNR)
HIGHCUT_HZ = 300                # Low-pass cutoff (preserves OPs)
ORDER = 4                       # 4th-order Butterworth

def design_bandpass_filter(lowcut, highcut, fs, order):
    """
    Design a Butterworth bandpass filter.
    Returns SOS (second-order sections) for numerical stability.
    """
    nyquist = fs / 2
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='bandpass', output='sos')
    return sos

def apply_bandpass_filter(signal, fs, lowcut=LOWCUT_HZ, highcut=HIGHCUT_HZ, order=ORDER):
    """
    Apply zero-phase Butterworth bandpass filter to ERG signal.
    Uses sosfiltfilt (forward-backward) to preserve implicit times.
    """
    sos = design_bandpass_filter(lowcut, highcut, fs, order)
    return sosfiltfilt(sos, signal)

def plot_filter_response(sos, fs, lowcut, highcut):
    """
    Plot the frequency response of the filter.
    """
    w, h = sosfreqz(sos, worN=4096, fs=fs)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.semilogx(w, 20 * np.log10(np.abs(h) + 1e-12), color='#2E75B6', lw=1.8)
    ax.axvline(lowcut, color='red', ls='--', lw=1.0, label=f'High-pass: {lowcut} Hz')
    ax.axvline(highcut, color='green', ls='--', lw=1.0, label=f'Low-pass: {highcut} Hz')
    ax.axhline(-3, color='gray', ls=':', lw=0.8, label='-3 dB (half-power)')
    ax.set_xlim(0.05, fs/2)
    ax.set_ylim(-80, 5)
    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude (dB)')
    ax.set_title('4th-Order Butterworth Bandpass Filter (ISCEV Standard)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    # Design filter
    sos = design_bandpass_filter(LOWCUT_HZ, HIGHCUT_HZ, FS_HZ, ORDER)
    
    # Plot frequency response
    plot_filter_response(sos, FS_HZ, LOWCUT_HZ, HIGHCUT_HZ)
    
    # Generate synthetic test signal
    t = np.arange(0, 0.25, 1/FS_HZ)  # 250 ms duration
    synthetic_erg = np.sin(2 * np.pi * 10 * t) + 0.5 * np.sin(2 * np.pi * 100 * t)
    
    # Apply filter
    filtered = apply_bandpass_filter(synthetic_erg, FS_HZ)
    
    print(f"Filter designed successfully.")
    print(f"Passband: {LOWCUT_HZ} - {HIGHCUT_HZ} Hz")
    print(f"Filter order: {ORDER}")
    print(f"Sampling rate: {FS_HZ} Hz")
