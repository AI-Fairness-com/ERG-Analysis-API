# -*- Chapter 2 -*-
"""REALISTIC ERG SIMULATION - With Project-Derived Quality Thresholds (Not an ISCEV Standard)"""
# This code requires a Jupyter notebook environment (Google Colab or local Jupyter). It will not produce interactive output if run as a plain .py script.

import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, clear_output
import ipywidgets as widgets

np.random.seed(42)

TRUE_BIOLOGICAL_SIGNAL_AMP = 893

# Format: (Name, Efficiency, PASS_threshold, WARNING_low_boundary, WARNING_high_boundary)
ELECTRODE_EFFICIENCY = {
    1: ("Contact lens", 1.00, 8.0, 4.0, 7.9),
    2: ("Gold foil",     0.56, 6.0, 3.0, 5.9),
    3: ("DTL fiber",     0.34, 4.0, 2.5, 3.9),
    4: ("Skin electrode", 0.12, 3.0, 1.5, 2.9),
}

# Generate true retinal signal
fs = 2000
pre_ms = 100
total_ms = 500
t = np.linspace(0, total_ms, int(fs * total_ms / 1000))
stim_onset = pre_ms

true_retinal_signal = np.zeros_like(t)
true_retinal_signal += -120 * np.exp(-((t - (stim_onset + 20))**2) / (2 * 8**2))
true_retinal_signal += 280 * np.exp(-((t - (stim_onset + 60))**2) / (2 * 18**2))

for t_op, a_op in zip([40, 48, 56, 64, 72], [12, 15, 18, 12, 8]):
    true_retinal_signal += a_op * np.exp(-((t - (stim_onset + t_op)) / 3)**2)

noise_cache = {}

def get_recording(noise_uV, electrode_id):
    name, efficiency, pass_th, warn_low, warn_high = ELECTRODE_EFFICIENCY[electrode_id]
    attenuated_signal = true_retinal_signal * efficiency
    
    cache_key = round(noise_uV, 1)
    if cache_key not in noise_cache:
        local_seed = int(noise_uV * 100) % 10000
        np.random.seed(local_seed)
        noise = np.random.normal(0, noise_uV, len(t))
        noise_cache[cache_key] = noise
        np.random.seed(42)
    
    recorded_signal = attenuated_signal + noise_cache[cache_key]
    return recorded_signal, attenuated_signal, efficiency, name, pass_th, warn_low, warn_high

output_plot = widgets.Output()
output_info = widgets.Output()

noise_slider = widgets.FloatSlider(
    value=30, min=0, max=250, step=5,
    description='Environmental noise (µV):',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='500px')
)

electrode_dropdown = widgets.Dropdown(
    options=[
        ('Contact lens (100% efficiency, PASS SNR ≥ 8.0, WARN 4.0-7.9)', 1),
        ('Gold foil (56% efficiency, PASS SNR ≥ 6.0, WARN 3.0-5.9)', 2),
        ('DTL fiber (34% efficiency, PASS SNR ≥ 4.0, WARN 2.5-3.9)', 3),
        ('Skin electrode (12% efficiency, PASS SNR ≥ 3.0, WARN 1.5-2.9)', 4)
    ],
    value=1,
    description='Electrode:',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='600px')
)

def update_plot(noise_uV, electrode_id):
    with output_plot:
        clear_output(wait=True)
        
        recorded_signal, attenuated_signal, efficiency, name, pass_th, warn_low, warn_high = get_recording(noise_uV, electrode_id)
        
        baseline = recorded_signal[:int(100 * fs / 1000)]
        noise_rms = np.sqrt(np.mean(baseline**2))
        
        recorded_amp = TRUE_BIOLOGICAL_SIGNAL_AMP * efficiency
        snr = recorded_amp / noise_rms
        
        if snr >= pass_th:
            quality = "PASS ✓"
            color = "lightgreen"
        elif snr >= warn_low:
            quality = "WARNING ⚠"
            color = "gold"
        else:
            quality = "FAIL ✗"
            color = "salmon"
        
        with output_info:
            clear_output(wait=True)
            print("="*60)
            print(f"ELECTRODE: {name}")
            print(f"  • Signal capture efficiency: {efficiency*100:.0f}%")
            print(f"  • Threshold(this project,§2.3: PASS ≥ {pass_th}, WARNING {warn_low}-{warn_high}, FAIL < {warn_low}")

            print(f"\nTrue retinal signal: {TRUE_BIOLOGICAL_SIGNAL_AMP} µV")
            print(f"Recorded amplitude: {recorded_amp:.0f} µV ({efficiency*100:.0f}% of true)")
            print(f"Environmental noise: {noise_uV} µV RMS (measured: {noise_rms:.1f})")
            print(f"\nSNR = {recorded_amp:.0f} / {noise_rms:.1f} = {snr:.1f}")
            print(f"\n→ RESULT: {quality}")
            print("="*60)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        ax1.plot(t, true_retinal_signal, 'g-', linewidth=1.5, alpha=0.5, label='True retinal signal')
        ax1.plot(t, recorded_signal, 'b-', linewidth=1.5, label=f'Recorded ({name})')
        ax1.axvline(stim_onset, color='red', linestyle='--', alpha=0.5, label='Flash')
        ax1.axhline(0, color='gray', linestyle=':', linewidth=0.5, alpha=0.5)
        ax1.set_ylabel('Amplitude (µV)')
        ax1.set_title(f'True Retinal Signal vs Recorded Signal')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.2)
        ax1.text(0.02, 0.95, f'SNR={snr:.1f}\n{quality}', transform=ax1.transAxes,
                fontsize=11, fontweight='bold', 
                bbox=dict(boxstyle='round', facecolor=color, alpha=0.8))
        
        ax2.plot(t, true_retinal_signal, 'g-', linewidth=1, alpha=0.5, label='True retinal')
        ax2.plot(t, attenuated_signal, 'orange', linewidth=2, label=f'After attenuation ({name})')
        ax2.fill_between(t, 0, attenuated_signal, alpha=0.3, color='orange')
        ax2.axvline(stim_onset, color='red', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Time (ms)')
        ax2.set_ylabel('Amplitude (µV)')
        ax2.set_title(f'Signal Attenuation: {efficiency*100:.0f}% of true signal remains')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.2)
        
        plt.tight_layout()
        plt.show()

widgets.interactive_output(update_plot, {'noise_uV': noise_slider, 'electrode_id': electrode_dropdown})

print("\n" + "="*70)
print("REALISTIC ERG SIMULATION - WITH PROJECT-DERIVED THRESHOLDS")
print("="*70)
print("\nKEY CONCEPT: Different electrodes capture different amounts of the true signal")
print("Contact lens: 100% | Gold: 56% | DTL: 34% | Skin: 12%")
print("\nProject-derived thresholds (§2.3) reflect these efficiency differences:")
print("  • Higher efficiency → Higher SNR required for PASS")
print("  • Lower efficiency → Lower SNR accepted for PASS")
print("\n" + "-"*70)

ui = widgets.VBox([
    widgets.HTML("<b>⚠️ Environmental Noise Level (same for all electrodes):</b>"),
    noise_slider,
    widgets.HTML("<b>🔬 Electrode Type:</b>"),
    electrode_dropdown,
    widgets.HTML("<hr>"),
    output_info,
    output_plot
])

display(ui)
update_plot(30, 1)