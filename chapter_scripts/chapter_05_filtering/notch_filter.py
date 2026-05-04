# -*- coding: utf-8 -*-
"""
Chapter 5: ERG-Specific Filtering
Notch Filter for Power-Line Interference Removal

This script demonstrates the notch filter design and application
for removing 50 Hz (UK/Europe) or 60 Hz (North America) mains interference.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import iirnotch, tf2sos, sosfiltfilt, freqz, welch

def design_notch_filter(notch_hz, quality_factor, fs_hz):
    """
    Design an IIR notch filter for power-line interference removal.
    
    Parameters:
    notch_hz : float - Mains frequency (50.0 or 60.0 Hz)
    quality_factor : float - Higher Q = narrower notch (typical: 30-50)
    fs_hz : float - Sampling rate in Hz
    
    Returns:
    sos : ndarray - Second-order sections for stable filtering
    """
    b, a = iirnotch(notch_hz, quality_factor, fs=fs_hz)
    sos = tf2sos(b, a)
    return sos

def apply_notch_filter(signal_uv, fs_hz, notch_hz=50.0, quality_factor=30.0):
    """
    Apply zero-phase notch filter to remove mains interference.
    
    Parameters:
    signal_uv : ndarray - ERG signal in microvolts
    fs_hz : float - Sampling rate in Hz
    notch_hz : float - Mains frequency (50.0 or 60.0 Hz)
    quality_factor : float - Notch sharpness (higher = narrower)
    
    Returns:
    filtered : ndarray - Notch-filtered signal
    """
    sos = design_notch_filter(notch_hz, quality_factor, fs_hz)
    return sosfiltfilt(sos, signal_uv)

def detect_mains_interference(signal_uv, fs_hz, notch_hz=50.0, threshold_db=6.0):
    """
    Detect whether mains interference is present in the signal.
    
    Uses Welch's method to compute power spectral density and compares
    power at notch_frequency to surrounding noise floor.
    
    Parameters:
    signal_uv : ndarray - ERG signal in microvolts
    fs_hz : float - Sampling rate in Hz
    notch_hz : float - Mains frequency to check (50.0 or 60.0 Hz)
    threshold_db : float - Minimum peak-to-floor ratio to trigger detection
    
    Returns:
    bool : True if mains interference detected, False otherwise
    """
    freqs, psd = welch(signal_uv, fs=fs_hz, nperseg=min(1024, len(signal_uv)))
    
    # Find index of notch frequency
    idx = int(np.argmin(np.abs(freqs - notch_hz)))
    
    # Power at notch frequency
    p_notch = 10 * np.log10(psd[idx] + 1e-30)
    
    # Average power in adjacent frequencies (±5 Hz, excluding the notch bin)
    left_start = max(0, idx - 5)
    right_end = min(len(psd), idx + 6)
    shoulder = np.concatenate([psd[left_start:idx], psd[idx+1:right_end]])
    p_shoulder = 10 * np.log10(np.mean(shoulder) + 1e-30)
    
    return (p_notch - p_shoulder) > threshold_db

def plot_notch_response(sos, fs_hz, notch_hz, quality_factor):
    """
    Plot the frequency response of the notch filter.
    """
    w, h = freqz(sos, worN=5000, fs=fs_hz)
    mag_db = 20 * np.log10(np.abs(h) + 1e-12)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(w, mag_db, color='#2E75B6', lw=1.8)
    ax.axvline(notch_hz, color='red', ls='--', lw=1.0, label=f'Notch at {notch_hz} Hz')
    ax.axhline(-3, color='gray', ls=':', lw=0.8, label='-3 dB')
    ax.axhline(-40, color='gray', ls=':', lw=0.5, alpha=0.5)
    
    ax.set_xlim(notch_hz - 15, notch_hz + 15)
    ax.set_ylim(-60, 3)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude (dB)')
    ax.set_title(f'Notch Filter: {notch_hz} Hz, Q = {quality_factor}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    FS_HZ = 1000
    NOTCH_HZ = 50.0
    Q = 30.0
    
    # Design and plot filter
    sos = design_notch_filter(NOTCH_HZ, Q, FS_HZ)
    plot_notch_response(sos, FS_HZ, NOTCH_HZ, Q)
    
    # Create a test signal with 50 Hz interference
    t = np.arange(0, 0.25, 1/FS_HZ)
    clean_signal = np.sin(2 * np.pi * 10 * t)  # 10 Hz ERG-like signal
    noise_50hz = 0.5 * np.sin(2 * np.pi * 50 * t)  # 50 Hz mains hum
    noisy_signal = clean_signal + noise_50hz
    
    # Detect and filter
    detected = detect_mains_interference(noisy_signal, FS_HZ, NOTCH_HZ)
    filtered = apply_notch_filter(noisy_signal, FS_HZ, NOTCH_HZ, Q)
    
    print(f"Mains interference detected: {detected}")
    print(f"Notch filter applied at {NOTCH_HZ} Hz with Q = {Q}")
