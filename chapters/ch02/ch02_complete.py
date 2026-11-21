# Chapter 2: how electrode type and noise change the SNR and the quality flag
"""
An interactive look at signal quality.

The code builds a simulated dark-adapted 3.0 (DA 3.0) ERG, scales it for
each electrode type, adds noise, and measures the SNR as defined in
Section 2.2.1. It then applies this project's SNR thresholds (Table 2.3).
The waveform is illustrative, not a patient recording.
Run it in Google Colab or Jupyter: the slider and menu need a notebook.
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, clear_output

# --------------------------------------------------------------
# Electrode types: relative amplitude and SNR thresholds
# --------------------------------------------------------------
# Relative amplitude: mean dark-adapted b-wave as a share of the contact
# lens electrode, from one comparison in the same eyes
# (Esakowitz, Kriss and Shawkat, 1993; Chapter 1, Fig. 1.4).
# Thresholds: this project's own choice (Table 2.3).
# Format: (name, relative amplitude, Pass from, Warning from)
ELECTRODES = {
    1: ("Contact lens",   1.00, 8.0, 4.0),
    2: ("Gold foil",      0.56, 6.0, 3.0),
    3: ("DTL fiber",      0.46, 4.0, 2.5),
    4: ("Skin electrode", 0.12, 3.0, 2.0),
}

# --------------------------------------------------------------
# Simulated DA 3.0 response for a contact lens electrode
# --------------------------------------------------------------
# 100 ms of baseline before the flash (Section 2.2.1), then 400 ms after it,
# sampled at 2000 samples per second.
fs = 2000
pre_ms = 100
t = np.arange(-pre_ms, 400, 1000 / fs)   # time in ms; the flash is at 0


def bump(x, center_ms, width_ms):
    """A smooth bell-shaped curve centered on center_ms."""
    return np.exp(-0.5 * ((x - center_ms) / width_ms) ** 2)


# a-wave trough near 20 ms, b-wave peak near 60 ms, small OPs on the rise.
# The sizes give a b-wave amplitude (a-wave trough to b-wave peak) close to
# the 471 µV mean recorded with a contact lens electrode by
# Esakowitz, Kriss and Shawkat (1993).
true_response = (-150.0 * bump(t, 20.0, 8.0)
                 + 320.0 * bump(t, 60.0, 18.0))
for t_op, a_op in zip([40, 48, 56, 64], [12, 15, 15, 10]):
    ripple = np.cos(2 * np.pi * (t - t_op) / 7.0)   # about 140 Hz
    true_response += a_op * bump(t, t_op, 2.0) * ripple


# Signal and noise must be measured over the same frequency range
# (Section 2.2.2). The a- and b-waves contain frequencies up to about
# 32 Hz (Chapter 1, Section 1.3.1), so a 50 Hz low-pass filter keeps them.
LOWPASS = butter(4, 50.0, btype="low", fs=fs, output="sos")


def measure_snr(recording):
    """SNR = (b-wave peak - a-wave trough) / peak-to-peak baseline noise."""
    recording = sosfiltfilt(LOWPASS, recording)
    baseline = recording[t < 0]
    noise_pp = baseline.max() - baseline.min()
    after = (t >= 0) & (t <= 150)
    a_trough = recording[after & (t <= 40)].min()
    b_peak = recording[after & (t > 20)].max()
    return (b_peak - a_trough), noise_pp


def quality_flag(snr, pass_from, warn_from):
    if snr >= pass_from:
        return "PASS"
    if snr >= warn_from:
        return "WARNING"
    return "FAIL"


def simulate(noise_uv, electrode_id, seed=1):
    name, rel_amp, pass_from, warn_from = ELECTRODES[electrode_id]
    rng = np.random.default_rng(seed)
    clean = true_response * rel_amp
    recording = clean + rng.normal(0.0, noise_uv, t.size)
    amplitude, noise_pp = measure_snr(recording)
    snr = amplitude / noise_pp
    return name, clean, recording, amplitude, noise_pp, snr, \
        quality_flag(snr, pass_from, warn_from), pass_from, warn_from


# --------------------------------------------------------------
# Interactive controls: noise slider and electrode menu
# --------------------------------------------------------------
noise_slider = widgets.FloatSlider(
    value=40, min=1, max=300, step=1,
    description="Added noise (µV RMS):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width="450px"))
electrode_menu = widgets.Dropdown(
    options=[(ELECTRODES[k][0], k) for k in ELECTRODES], value=1,
    description="Electrode:", style={"description_width": "initial"})
output = widgets.Output()

COLORS = {"PASS": "lightgreen", "WARNING": "gold", "FAIL": "salmon"}


def update(change=None):
    (name, clean, recording, amplitude, noise_pp, snr, flag,
     pass_from, warn_from) = simulate(noise_slider.value, electrode_menu.value)
    with output:
        clear_output(wait=True)
        print(f"Electrode:          {name}")
        print(f"Measured amplitude: {amplitude:.0f} µV "
              "(a-wave trough to b-wave peak)")
        print(f"Noise before flash: {noise_pp:.1f} µV peak to peak")
        print(f"SNR:                {snr:.1f}")
        print(f"Thresholds:         Pass ≥ {pass_from}, "
              f"Warning {warn_from} to "
              f"{pass_from - 0.1:.1f}, Fail < {warn_from}  (Table 2.3)")
        print(f"Quality flag:       {flag}")

        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.axvspan(t[0], 0, color="gray", alpha=0.15,
                   label="Baseline used for noise (100 ms)")
        ax.plot(t, recording, color="steelblue", lw=1.0,
                label=f"Recorded ({name})")
        ax.plot(t, clean, color="darkorange", lw=2.0,
                label="Response without noise")
        ax.axvline(0, color="red", ls="--", lw=1.0, label="Flash")
        ax.set_xlabel("Time after flash (ms)")
        ax.set_ylabel("Amplitude (µV)")
        ax.set_title(f"SNR = {snr:.1f}: {flag}",
                     backgroundcolor=COLORS[flag])
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.show()


noise_slider.observe(update, names="value")
electrode_menu.observe(update, names="value")
display(widgets.VBox([noise_slider, electrode_menu, output]))
update()
