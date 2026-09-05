# -*- coding: utf-8 -*-
"""
Chapter 5: ERG-Specific Filtering
Complete Filter Pipeline: Median + Notch + Butterworth Bandpass

This script assembles all three filters into a single pipeline function
that processes ERG recordings in the correct order and with proper
parameter handling.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, sosfreqz, iirnotch, tf2sos, medfilt, welch

# ============================================================================
# Individual Filter Functions (imported or redefined for completeness)
# ============================================================================

def apply_median_filter(signal_uv, kernel_samples=5):
    """Remove spikes using median filter. Kernel must be odd."""
    if kernel_samples % 2 == 0:
        kernel_samples += 1
    return medfilt(signal_uv, kernel_size=kernel_samples)

def design_butterworth_bandpass(highpass_hz, lowpass_hz, fs_hz, order=4):
    """Design Butterworth bandpass filter using SOS format."""
    nyquist = fs_hz / 2.0
    low = highpass_hz / nyquist
    high = lowpass_hz / nyquist
    if high >= 1.0:
        raise ValueError(f'Low-pass cutoff {lowpass_hz} Hz exceeds Nyquist ({nyquist} Hz)')
    sos = butter(order, [low, high], btype='bandpass', output='sos')
    return sos

def apply_bandpass_filter(signal_uv, fs_hz, highpass_hz=0.3, lowpass_hz=300.0, order=4):
    """Apply zero-phase Butterworth bandpass filter."""
    sos = design_butterworth_bandpass(highpass_hz, lowpass_hz, fs_hz, order)
    return sosfiltfilt(sos, signal_uv)

def design_notch_filter(notch_hz, quality_factor, fs_hz):
    """Design IIR notch filter."""
    b, a = iirnotch(notch_hz, quality_factor, fs=fs_hz)
    return tf2sos(b, a)

def apply_notch_filter(signal_uv, fs_hz, notch_hz=50.0, quality_factor=30.0):
    """Apply zero-phase notch filter."""
    sos = design_notch_filter(notch_hz, quality_factor, fs_hz)
    return sosfiltfilt(sos, signal_uv)

def detect_mains_interference(signal_uv, fs_hz, notch_hz=50.0, threshold_db=6.0):
    """Detect if mains interference is present."""
    freqs, psd = welch(signal_uv, fs=fs_hz, nperseg=min(1024, len(signal_uv)))
    idx = int(np.argmin(np.abs(freqs - notch_hz)))
    p_notch = 10 * np.log10(psd[idx] + 1e-30)
    left_start = max(0, idx - 5)
    right_end = min(len(psd), idx + 6)
    shoulder = np.concatenate([psd[left_start:idx], psd[idx+1:right_end]])
    p_shoulder = 10 * np.log10(np.mean(shoulder) + 1e-30)
    return (p_notch - p_shoulder) > threshold_db

# ============================================================================
# Complete Pipeline Function
# ============================================================================

def apply_erg_filter_pipeline(recording, apply_median=True, apply_notch=False,
                               notch_hz=50.0, highpass_hz=0.3, lowpass_hz=300.0,
                               filter_order=4, notch_q=30.0):
    """
    Apply the complete ERG filter pipeline in the correct sequence:
    1. Median filter (spike removal) - must come first
    2. Notch filter (mains interference) - OFF by default (ISCEV 2022: "Such
       filters should not be used"); applied only if the caller explicitly
       passes apply_notch=True, which is the deliberate action ISCEV's
       guidance implies is needed before overriding the default.
    3. Butterworth bandpass (ISCEV 0.3-300 Hz or hardware-limited)

    Parameters:
    recording : dict - Must contain 'amplitude_uv' and 'fs_hz' keys.
                Optional: 'hardware_lowpass_hz', 'hardware_highpass_hz',
                'prestimulus_uv' (used for the ISCEV pre-stimulus baseline
                duration check below; omit to skip that check).
    apply_median : bool - Whether to apply median filter
    apply_notch : bool - Off by default per ISCEV 2022 guidance. Caller
                  must explicitly pass True to apply a notch filter.
    notch_hz : float - Mains frequency (50.0 or 60.0 Hz)
    highpass_hz : float - Butterworth high-pass cutoff (default 0.3, ISCEV target)
    lowpass_hz : float - Butterworth low-pass cutoff (default 300.0, ISCEV target)
    filter_order : int - Butterworth filter order (default 4)
    notch_q : float - Notch filter quality factor (default 30.0)
    
    Returns:
    dict - Original recording with added keys:
           'filtered_uv' : filtered signal array
           'filter_log' : list of processing steps
           'hw_cutoff_ok' : bool, whether hardware allows full low-pass band
           'hw_highpass_ok' : bool, whether hardware allows full high-pass band
           'iscev_compliance' : dict of compliance flags (sampling_rate_ok,
                                 prestimulus_ok, bandwidth_ok, notch_applied)
           'notch_applied' : bool, whether a notch filter was actually applied
           'mains_detected' : bool, whether mains interference was detected
                               (independent of whether notch was applied)
    """
    # Extract signal and parameters
    sig = recording['amplitude_uv'].copy()
    fs = recording['fs_hz']
    hw_lp = recording.get('hardware_lowpass_hz', 300.0)
    hw_hp = recording.get('hardware_highpass_hz', 0.3)

    log = []

    # ISCEV 2022: digitize at >= 1 kHz per channel
    iscev_sampling_compliant = fs >= 1000.0
    if not iscev_sampling_compliant:
        log.append(f'WARNING: Sampling rate {fs} Hz is below ISCEV minimum 1000 Hz. '
                    'Implicit time measurements may be unreliable.')

    # ISCEV 2022: stored records need >= 20 ms pre-stimulus baseline
    prestimulus_samples_needed = int(0.020 * fs)
    has_prestimulus = len(recording.get('prestimulus_uv', [])) >= prestimulus_samples_needed
    if not has_prestimulus:
        log.append('WARNING: Pre-stimulus baseline < 20 ms (ISCEV minimum). '
                    'Filter transient may affect early waveform features.')

    # Check hardware bandwidth constraint (low-pass side)
    hw_cutoff_ok = hw_lp >= lowpass_hz
    effective_lp = min(lowpass_hz, hw_lp * 0.95)

    if not hw_cutoff_ok:
        log.append(f'WARNING: hardware cutoff {hw_lp} Hz < requested {lowpass_hz} Hz. '
                   f'Software low-pass set to {effective_lp:.1f} Hz. '
                   f'OP features may be unreliable.')

    # Check hardware bandwidth constraint (high-pass side)
    hw_highpass_ok = hw_hp <= highpass_hz
    effective_hp = max(highpass_hz, hw_hp * 1.05)

    if not hw_highpass_ok:
        log.append(f'WARNING: hardware high-pass {hw_hp} Hz > requested {highpass_hz} Hz. '
                   f'Software high-pass set to {effective_hp:.1f} Hz. '
                   f'PhNR features may be unreliable.')

    # Step 1: Median filter (spike removal)
    if apply_median:
        sig = apply_median_filter(sig, kernel_samples=5)
        log.append('Median filter applied: kernel=5 samples (5 ms at 1000 Hz)')

    # Step 2: Notch filter (mains interference) -- OFF by default (ISCEV 2022)
    mains_detected = detect_mains_interference(sig, fs, notch_hz)
    if mains_detected:
        log.append(f'Detection: {notch_hz} Hz mains interference present. '
                     'ISCEV 2022 advises against notch filters due to waveform distortion.')

    notch_applied = False
    if apply_notch:
        sig = apply_notch_filter(sig, fs, notch_hz, notch_q)
        notch_applied = True
        log.append(f'NOTCH APPLIED: {notch_hz} Hz, Q={notch_q} (caller overrode ISCEV default). '
                     'Output waveform may be distorted.')
    else:
        log.append('Notch filter: OFF (ISCEV 2022 compliant default)')
        if mains_detected:
            log.append(f'  -> {notch_hz} Hz interference remains in signal; '
                         'consider post-acquisition removal if clinically justified.')

    # Step 3: Butterworth bandpass
    sig = apply_bandpass_filter(sig, fs, effective_hp, effective_lp, filter_order)
    log.append(f'Butterworth bandpass: order={filter_order}, {effective_hp:.1f}-{effective_lp:.1f} Hz '
               f'(zero-phase, sosfiltfilt)')

    # Return enriched recording
    result = recording.copy()
    result['filtered_uv'] = sig
    result['filter_log'] = log
    result['hw_cutoff_ok'] = hw_cutoff_ok
    result['hw_highpass_ok'] = hw_highpass_ok
    result['notch_applied'] = notch_applied
    result['mains_detected'] = mains_detected
    result['iscev_compliance'] = {
        'sampling_rate_ok': iscev_sampling_compliant,
        'prestimulus_ok': has_prestimulus,
        'bandwidth_ok': hw_cutoff_ok and hw_highpass_ok,
        'notch_applied': notch_applied,
        'notch_iscev_compliant': not notch_applied,
    }

    return result


def plot_before_after(recording, fs_hz, protocol_name='ERG'):
    """
    Create a side-by-side comparison of raw and filtered waveforms.
    
    Parameters:
    recording : dict - Must contain 'amplitude_uv' and 'filtered_uv'
    fs_hz : float - Sampling rate
    protocol_name : str - Name of the ERG protocol (for title)
    """
    t = np.arange(len(recording['amplitude_uv'])) / fs_hz
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    
    # Raw signal
    axes[0].plot(t, recording['amplitude_uv'], color='red', lw=0.8)
    axes[0].set_ylabel('Amplitude (µV)')
    axes[0].set_title(f'{protocol_name} - Raw Signal (Unfiltered)')
    axes[0].grid(True, alpha=0.3)
    
    # Filtered signal
    axes[1].plot(t, recording['filtered_uv'], color='#2E75B6', lw=0.8)
    axes[1].set_xlabel('Time (ms)')
    axes[1].set_ylabel('Amplitude (µV)')
    axes[1].set_title(f'{protocol_name} - After Filter Pipeline')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    

# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Create a synthetic test recording
    FS_HZ = 1000
    DURATION_MS = 250
    t = np.arange(0, DURATION_MS / 1000, 1/FS_HZ)
    
    # Simulated ERG waveform
    clean_erg = 2.0 * np.exp(-((t - 0.025) / 0.008)**2) - \
                 1.5 * np.exp(-((t - 0.015) / 0.005)**2)  # Simple a/b-wave shape
    
    # Add noise: 50 Hz hum + spike + broadband noise
    noise_50hz = 0.3 * np.sin(2 * np.pi * 50 * t)
    spike = np.zeros_like(t)
    spike_idx = int(0.08 * FS_HZ)
    if spike_idx < len(spike):
        spike[spike_idx] = 3.0
    broadband_noise = 0.1 * np.random.randn(len(t))
    
    noisy_signal = clean_erg + noise_50hz + spike + broadband_noise
    
    # Create recording dictionary (matching Chapter 3 format)
    recording = {
        'amplitude_uv': noisy_signal,
        'fs_hz': FS_HZ,
        'hardware_lowpass_hz': 300.0,
        'patient_id': 'TEST001',
        'protocol': 'DA 3.0'
    }
    
    # Apply pipeline
    filtered_recording = apply_erg_filter_pipeline(
        recording,
        apply_median=True,
        apply_notch=None,  # Auto-detect
        notch_hz=50.0,
        highpass_hz=0.3,
        lowpass_hz=300.0,
        filter_order=4,
        notch_q=30.0
    )
    
    # Print filter log
    print("=" * 60)
    print("FILTER PIPELINE LOG")
    print("=" * 60)
    for step in filtered_recording['filter_log']:
        print(f"  {step}")
    print("=" * 60)
    
    # Plot before/after
    plot_before_after(filtered_recording, FS_HZ, 'DA 3.0 (Synthetic)')
    
    # Verify that filtered signal is same length as input
    assert len(filtered_recording['filtered_uv']) == len(recording['amplitude_uv'])
    print(f"\nVerification passed: filtered signal length = {len(filtered_recording['filtered_uv'])} samples")
