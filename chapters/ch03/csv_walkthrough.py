# Chapter 3, §3.6: load, measure, and plot the sample ERG recording
# Run from the repository folder:  python chapters/ch03/csv_walkthrough.py
# This is the code of §3.6. It prints the first rows of the sample file,
# the signal properties and the SNR, and saves a plot of the waveform
# (the installation check of Appendix F, §F.3).

# ── Step 1: Import the required libraries ──────────────────────────
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── Step 2: Load the ERG CSV file ──────────────────────────────────
df = pd.read_csv('data/samples/normal_001_DA3.csv')

# ── Step 3: Display the first few rows to confirm it loaded correctly
print(df.head())

# Expected output:
#    time_ms  amplitude_uV protocol eye electrode_type patient_id
# 0      0.0         -8.77   DA 3.0  OD      DTL_fiber       P001
# 1      0.5         -5.74   DA 3.0  OD      DTL_fiber       P001
# 2      1.0          2.41   DA 3.0  OD      DTL_fiber       P001
# 3      1.5         -3.21   DA 3.0  OD      DTL_fiber       P001
# 4      2.0          3.22   DA 3.0  OD      DTL_fiber       P001

# ── Step 4: Extract the time and amplitude arrays ──────────────────
time_ms   = df['time_ms'].values          # NumPy array of time points
amplitude = df['amplitude_uV'].values     # NumPy array of voltage values

# ── Step 5: Print basic signal properties and the SNR (Chapter 2) ──
fs = 1000 / (time_ms[1] - time_ms[0])     # Sampling rate in Hz
duration_ms = time_ms[-1] - time_ms[0]    # Total recording duration
pre_stim_end = 100                        # Flash at 100 ms; baseline 0–100 ms

# Noise: peak to peak in the 100 ms before the flash (§2.2.1)
baseline = amplitude[time_ms < pre_stim_end]
noise_pp = baseline.max() - baseline.min()

# a-wave trough: lowest point in the first 30 ms after the flash
a_win = (time_ms >= pre_stim_end) & (time_ms <= pre_stim_end + 30)
a_idx = np.argmin(amplitude[a_win])
a_time, a_amp = time_ms[a_win][a_idx], amplitude[a_win][a_idx]

# b-wave peak: highest point from the a-wave trough to 150 ms after the flash
b_win = (time_ms > a_time) & (time_ms <= pre_stim_end + 150)
b_idx = np.argmax(amplitude[b_win])
b_time, b_amp = time_ms[b_win][b_idx], amplitude[b_win][b_idx]

b_wave = b_amp - a_amp                    # a-wave trough to b-wave peak
snr = b_wave / noise_pp

# DTL fiber thresholds (Table 2.3): Pass >= 4, Warning 2.5 to 3.9, Fail < 2.5
flag = 'PASS' if snr >= 4 else 'WARNING' if snr >= 2.5 else 'FAIL'

print(f'Sampling rate   : {fs:.0f} Hz')
print(f'Duration        : {duration_ms:.0f} ms')
print(f'a-wave trough   : {a_amp:.1f} µV at {a_time - pre_stim_end:.1f} ms')
print(f'b-wave peak     : {b_amp:.1f} µV at {b_time - pre_stim_end:.1f} ms')
print(f'b-wave amplitude: {b_wave:.1f} µV')
print(f'Noise (p-p)     : {noise_pp:.1f} µV')
print(f'SNR             : {snr:.1f}')
print(f'Quality flag    : {flag}')

# Expected output:
# Sampling rate   : 2000 Hz
# Duration        : 500 ms
# a-wave trough   : -145.3 µV at 16.5 ms
# b-wave peak     : 312.8 µV at 60.5 ms
# b-wave amplitude: 458.1 µV
# Noise (p-p)     : 29.3 µV
# SNR             : 15.7
# Quality flag    : PASS

# ── Step 6: Plot the annotated ERG waveform ────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))

# Shade the baseline window used for the noise measurement
ax.axvspan(0, pre_stim_end, alpha=0.10, color='gray',
           label='Baseline before the flash (noise window)')

# Plot the ERG waveform
ax.plot(time_ms, amplitude, color='#2E75B6', linewidth=1.6,
        label='ERG waveform (simulated, DA 3.0, DTL fiber)')

# Mark the flash
ax.axvline(pre_stim_end, color='red', linewidth=1.2,
           linestyle='--', label='Flash (t = 100 ms)')

# Annotate the a-wave trough and b-wave peak found in Step 5
ax.annotate(f'a-wave\n{a_amp:.0f} µV at {a_time - pre_stim_end:.1f} ms',
            xy=(a_time, a_amp), xytext=(a_time + 40, a_amp + 20),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=10, color='black')
ax.annotate(f'b-wave\n{b_amp:.0f} µV at {b_time - pre_stim_end:.1f} ms',
            xy=(b_time, b_amp), xytext=(b_time + 60, b_amp - 40),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=10, color='black')

# Reference zero line
ax.axhline(0, color='gray', linewidth=0.6, linestyle=':')

# Labels and title (the flag is the one computed in Step 5)
ax.set_xlabel('Time (ms)', fontsize=12)
ax.set_ylabel('Amplitude (µV)', fontsize=12)
ax.set_title(f'Simulated ERG | DA 3.0 | DTL fiber | '
             f'SNR = {snr:.1f} ({flag})', fontsize=12)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig('ch03_erg_waveform.png', dpi=150)   # saved for Appendix F §F.3
print('Plot saved as ch03_erg_waveform.png')
plt.show()

# ── Step 7: The sample is already in the standardized CSV template ──
# No conversion is needed. Files from other systems are first
# converted to this template (§3.4.4).
