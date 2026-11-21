# Chapter 1: create, save, load and measure a sample ERG
"""
A first look at ERG data in Python.

The code builds a simulated dark-adapted 3.0 (DA 3.0) ERG, saves it as a
CSV file, loads it back, and measures the a-wave and b-wave with the ISCEV
conventions described in Section 1.3.2. The waveform is illustrative, not a
patient recording. No programming experience is needed to run it.
"""

import numpy as np                 # numerical arrays and maths
import matplotlib.pyplot as plt    # plotting

# --------------------------------------------------------------
# STEP 1: Build a simulated DA 3.0 waveform
# --------------------------------------------------------------
print("Step 1: Building a simulated DA 3.0 ERG...")

# Time runs from 20 ms before the flash to 300 ms after it, every 0.5 ms
# (a sampling rate of 2000 samples per second). ISCEV asks for at least
# 20 ms of pre-flash baseline and at least 300 ms of record.
time_ms = np.arange(-20.0, 300.5, 0.5)


def bump(t, center_ms, width_ms):
    """A smooth bell-shaped curve centered on center_ms."""
    return np.exp(-0.5 * ((t - center_ms) / width_ms) ** 2)


# a-wave: a negative dip with its trough near 15 ms
a_wave = -170.0 * bump(time_ms, 15.0, 4.0)

# b-wave: a larger positive wave with its peak near 52 ms
b_wave = 150.0 * bump(time_ms, 52.0, 15.0)

# Oscillatory potentials: fast ripples (about 150 Hz) on the rising b-wave
ops = 12.0 * bump(time_ms, 30.0, 7.0) * np.sin(2 * np.pi * 150.0 * time_ms / 1000.0)

# A little random noise, as in a real recording
rng = np.random.default_rng(seed=42)
noise = rng.normal(0.0, 1.0, time_ms.size)

amplitude_uv = a_wave + b_wave + ops + noise

# --------------------------------------------------------------
# STEP 2: Save the waveform as a CSV file
# --------------------------------------------------------------
print("Step 2: Saving the waveform to sample_erg_da3.csv...")

data_to_save = np.column_stack((time_ms, amplitude_uv))
np.savetxt("sample_erg_da3.csv", data_to_save, delimiter=",",
           header="Time_ms,Amplitude_uV", comments="", fmt="%.3f")

# --------------------------------------------------------------
# STEP 3: Load the CSV file, as for a real recording
# --------------------------------------------------------------
print("Step 3: Loading the CSV file...")

data = np.loadtxt("sample_erg_da3.csv", delimiter=",", skiprows=1)
t = data[:, 0]   # time in milliseconds
v = data[:, 1]   # amplitude in microvolts
print(f"Loaded {t.size} samples")

# --------------------------------------------------------------
# STEP 4: Measure the a-wave and b-wave (ISCEV conventions)
# --------------------------------------------------------------
print("Step 4: Measuring the a-wave and b-wave...")

# Baseline: the average of the samples before the flash
baseline_uv = v[t < 0].mean()

# a-wave trough: the lowest point between 0 and 30 ms
a_window = (t >= 0) & (t <= 30)
a_index = np.flatnonzero(a_window)[np.argmin(v[a_window])]
a_time_ms = t[a_index]
a_amplitude_uv = baseline_uv - v[a_index]      # baseline to trough

# b-wave peak: the highest point between the a-wave trough and 120 ms
b_window = (t > a_time_ms) & (t <= 120)
b_index = np.flatnonzero(b_window)[np.argmax(v[b_window])]
b_time_ms = t[b_index]
b_amplitude_uv = v[b_index] - v[a_index]       # a-wave trough to b-wave peak

ba_ratio = b_amplitude_uv / a_amplitude_uv

# --------------------------------------------------------------
# STEP 5: Plot the waveform with the two measurement points
# --------------------------------------------------------------
print("Step 5: Plotting the waveform...")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t, v, color="steelblue", linewidth=1.8, label="Simulated DA 3.0 ERG")
ax.axhline(baseline_uv, color="gray", linewidth=0.8, linestyle="--")
ax.axvline(0, color="gray", linewidth=0.8, linestyle=":")
ax.plot(a_time_ms, v[a_index], "o", color="darkred")
ax.plot(b_time_ms, v[b_index], "o", color="darkgreen")
ax.annotate("a-wave trough", xy=(a_time_ms, v[a_index]),
            xytext=(a_time_ms + 25, v[a_index] - 10),
            arrowprops=dict(arrowstyle="->"), fontsize=12)
ax.annotate("b-wave peak", xy=(b_time_ms, v[b_index]),
            xytext=(b_time_ms + 25, v[b_index] + 10),
            arrowprops=dict(arrowstyle="->"), fontsize=12)
ax.set_xlabel("Time after the flash (ms)")
ax.set_ylabel("Amplitude (µV)")
ax.set_title("Simulated DA 3.0 ERG with a-wave and b-wave")
ax.legend(loc="upper right")
plt.tight_layout()
plt.show()

# --------------------------------------------------------------
# STEP 6: Print the measurements
# --------------------------------------------------------------
print(f"a-wave: {a_amplitude_uv:.1f} µV at {a_time_ms:.1f} ms")
print(f"b-wave: {b_amplitude_uv:.1f} µV at {b_time_ms:.1f} ms")
print(f"b/a ratio: {ba_ratio:.2f}")
