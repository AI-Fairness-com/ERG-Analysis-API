# ── Step 4: Extract the time and amplitude arrays ──────────────────
time_ms   = df['time_ms'].values          # NumPy array of time points
amplitude = df['amplitude_uV'].values     # NumPy array of voltage values

# ── Step 5: Print basic signal properties ──────────────────────────
fs = 1000 / (time_ms[1] - time_ms[0])    # Sampling rate in Hz
duration_ms = time_ms[-1] - time_ms[0]   # Total recording duration
pre_stim_end = 100                        # Pre-stimulus baseline: 0–100 ms

pre_mask  = time_ms < pre_stim_end
noise_rms = np.sqrt(np.mean(amplitude[pre_mask]**2))
snr = (amplitude.max() - amplitude.min()) / noise_rms

print(f'Sampling rate   : {fs:.0f} Hz')
print(f'Duration        : {duration_ms:.0f} ms')
print(f'Amplitude range : {amplitude.min():.1f} to {amplitude.max():.1f} µV')
print(f'Noise RMS       : {noise_rms:.1f} µV')
print(f'SNR (approx.)   : {snr:.1f}')
print(f'Quality flag    : {"PASS" if snr >= 4 else "WARNING" if snr >= 2.5 else "FAIL"}')

# Expected output for a normal DTL recording:
# Sampling rate   : 2000 Hz
# Duration        : 500 ms
# Amplitude range : -145.3 to 312.8 µV
# Noise RMS       : 6.2 µV
# SNR (approx.)   : 73.9
# Quality flag    : PASS
