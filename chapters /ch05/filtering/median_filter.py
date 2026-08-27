# -*- coding: utf-8 -*-
"""
Chapter 5: ERG-Specific Filtering
Median Filter for High-Frequency Spike Noise Removal

This script demonstrates the median filter for removing isolated
high-amplitude spikes (e.g., electrode static, blink artifacts)
without distorting the underlying ERG waveform.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import medfilt

def apply_median_filter(signal_uv, kernel_samples=5):
    """
    Remove high-amplitude short-duration spikes using a median filter.
    
    The median filter replaces each sample with the median value of
    its neighbors within the kernel window. Spikes narrower than the
    kernel are eliminated; smooth ERG features wider than the kernel
    are preserved with minimal distortion.
    
    Parameters:
    signal_uv : ndarray - ERG signal in microvolts
    kernel_samples : int - Window size (must be odd). 
                     Default 5 samples = 5 ms at 1000 Hz sampling.
    
    Returns:
    filtered : ndarray - Median-filtered signal
    """
    # Ensure kernel length is odd (required by scipy.signal.medfilt)
    if kernel_samples % 2 == 0:
        kernel_samples += 1
        print(f"Warning: kernel_samples must be odd. Changed to {kernel_samples}")
    
    return medfilt(signal_uv, kernel_size=kernel_samples)

def create_test_signal_with_spike(fs_hz, duration_ms=250):
    """
    Create a synthetic ERG-like signal with an isolated spike artifact.
    
    Parameters:
    fs_hz : int - Sampling rate in Hz
    duration_ms : int - Signal duration in milliseconds
    
    Returns:
    t : ndarray - Time axis in seconds
    clean : ndarray - Clean ERG-like signal
    noisy : ndarray - Signal with added spike artifact
    """
    t = np.arange(0, duration_ms / 1000, 1/fs_hz)
    
    # ERG-like waveform (simplified: combination of low-frequency sine waves)
    clean = np.sin(2 * np.pi * 8 * t) + 0.3 * np.sin(2 * np.pi * 25 * t)
    
    # Add a single high-amplitude spike at 80 ms
    noisy = clean.copy()
    spike_idx = int(0.08 * fs_hz)  # 80 ms position
    if spike_idx < len(noisy):
        noisy[spike_idx] += 5.0  # 5 µV spike
    
    return t, clean, noisy

def visualize_median_filter_effect(noisy_signal, filtered_signal, fs_hz):
    """
    Create a before/after plot showing spike removal.
    """
    t = np.arange(len(noisy_signal)) / fs_hz
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    
    # Before filtering
    axes[0].plot(t, noisy_signal, color='red', lw=1.0)
    axes[0].set_ylabel('Amplitude (µV)')
    axes[0].set_title('Before Median Filter: Spike Artifact Present')
    axes[0].grid(True, alpha=0.3)
    
    # After filtering
    axes[1].plot(t, filtered_signal, color='#2E75B6', lw=1.0)
    axes[1].set_xlabel('Time (ms)')
    axes[1].set_ylabel('Amplitude (µV)')
    axes[1].set_title('After Median Filter: Spike Removed, Waveform Preserved')
    axes[1].grid(True, alpha=0.3)
    
    # Mark the spike location on the top plot
    spike_idx = np.argmax(np.abs(noisy_signal - filtered_signal))
    if spike_idx < len(noisy_signal):
        axes[0].axvline(t[spike_idx], color='purple', ls='--', lw=0.8, alpha=0.7)
        axes[0].text(t[spike_idx], max(noisy_signal) * 0.9, 'Spike', 
                     color='purple', fontsize=8, ha='center')
    
    plt.tight_layout()
    plt.show()

def compare_kernel_sizes(signal_uv, fs_hz, kernels=[3, 5, 7, 11]):
    """
    Compare the effect of different median filter kernel sizes.
    """
    t = np.arange(len(signal_uv)) / fs_hz
    
    fig, axes = plt.subplots(len(kernels), 1, figsize=(12, 8), sharex=True)
    
    for i, kernel in enumerate(kernels):
        filtered = apply_median_filter(signal_uv, kernel)
        axes[i].plot(t, filtered, color='#2E75B6', lw=1.0)
        axes[i].set_ylabel(f'Kernel = {kernel}')
        axes[i].grid(True, alpha=0.3)
        axes[i].set_ylim(-2, 6)
    
    axes[-1].set_xlabel('Time (ms)')
    axes[0].set_title('Effect of Kernel Size on Median Filter Output')
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    FS_HZ = 1000
    KERNEL = 5
    
    # Create test signal with spike
    t, clean, noisy = create_test_signal_with_spike(FS_HZ)
    
    # Apply median filter
    filtered = apply_median_filter(noisy, KERNEL)
    
    # Visualize results
    visualize_median_filter_effect(noisy, filtered, FS_HZ)
    
    # Optional: compare different kernel sizes
    # compare_kernel_sizes(noisy, FS_HZ, [3, 5, 7, 11])
    
    print(f"Median filter applied with kernel size: {KERNEL} samples")
    print(f"At {FS_HZ} Hz sampling, this equals {KERNEL} ms window duration")
    print(f"Spike removed. Waveform preserved.")
