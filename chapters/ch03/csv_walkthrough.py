# ── Step 1: Import the required libraries ──────────────────────────
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── Step 2: Load the ERG CSV file ──────────────────────────────────
df = pd.read_csv('data/samples/normal_001_DA3.csv')

# ── Step 3: Display the first few rows to confirm it loaded correctly
print(df.head())

# Expected output:
#    time_ms   amplitude_uV  protocol  eye  electrode_type  patient_id
#  0    0.0          1.23     DA_3.0    OD   DTL_fiber      P001
#  1    0.5         -0.87     DA_3.0    OD   DTL_fiber      P001
#  2    1.0          2.14     DA_3.0    OD   DTL_fiber      P001
#  ...

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

# ── Step 6: Plot the annotated ERG waveform ────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))

# Shade the pre-stimulus baseline window
ax.axvspan(0, pre_stim_end, alpha=0.10, color='gray',
           label='Pre-stimulus baseline')

# Plot the ERG waveform
ax.plot(time_ms, amplitude, color='#2E75B6', linewidth=1.6,
        label='ERG waveform (DTL fiber, DA 3.0)')

# Mark stimulus onset
ax.axvline(pre_stim_end, color='red', linewidth=1.2,
           linestyle='--', label='Stimulus onset (t = 100 ms)')

# Find and annotate a-wave trough and b-wave peak
post_stim = amplitude[time_ms >= pre_stim_end]
post_time = time_ms[time_ms >= pre_stim_end]

a_idx   = np.argmin(post_stim)
b_idx   = np.argmax(post_stim)
a_time, a_amp = post_time[a_idx], post_stim[a_idx]
b_time, b_amp = post_time[b_idx], post_stim[b_idx]

ax.annotate(f'a-wave\n{a_amp:.0f} µV @ {a_time - pre_stim_end:.0f} ms',         xy=(a_time, a_amp), xytext=(a_time + 30, a_amp - 30),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=9, color='black')
ax.annotate(f'b-wave\n{b_amp:.0f} µV @ {b_time - pre_stim_end:.0f} ms',         xy=(b_time, b_amp), xytext=(b_time + 20, b_amp + 20),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=9, color='black')

# Reference zero line
ax.axhline(0, color='gray', linewidth=0.6, linestyle=':')

# Labels and formatting
ax.set_xlabel('Time (ms)', fontsize=12)
ax.set_ylabel('Amplitude (µV)', fontsize=12)
ax.set_title(
    f'ERG Recording , Normal Subject | DA 3.0 Protocol | DTL Fiber | '
    f'SNR = {snr:.1f}  ["PASS"]',
    fontsize=12)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig('chapter3_normal_waveform.png', dpi=220)
plt.show()

# ── Step 7: Save the standardized CSV (already in template format)
# No conversion needed for this sample; it is already in the
# standardized template format. For real data, use the relevant
# reader function from the erg_io module (see Chapter 4).