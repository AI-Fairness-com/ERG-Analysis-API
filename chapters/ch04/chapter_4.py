# Chapter 4: ERG visualization and quality-control plots
# The code of Chapter 4, in the order of the book: the annotated waveform
# plot, the spectrogram, the SNR overlay, the baseline drift check, the
# sweep screen, the interactive Plotly viewer (saved as erg_waveform.html),
# and the multifocal hexagon map. Run it in Google Colab or Jupyter; the
# two lines that start with ! download the Chapter 3 sample file.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt

# OP band: per-pass corners; two passes give about 75 to 301 Hz.
OP_BAND = [70, 320]

# Download the Chapter 3 sample file (Colab or Jupyter).
!mkdir -p data/samples
!curl -sL -o data/samples/normal_001_DA3.csv https://raw.githubusercontent.com/AI-Fairness-com/ERG-Analysis-API/main/data/samples/normal_001_DA3.csv


def load_recording_from_csv(csv_path: str) -> dict:
    """Read a standardized ERG CSV file (Chapter 3, §3.4.4) into a dictionary."""
    df = pd.read_csv(csv_path)
    t = df['time_ms'].values
    return {
        'time_ms': t,                                  # time points (ms)
        'amplitude_uv': df['amplitude_uV'].values,     # voltages (µV)
        'fs_hz': 1000 / (t[1] - t[0]),                 # sampling rate (Hz)
        'electrode_type': df['electrode_type'].iloc[0],
        'protocol': df['protocol'].iloc[0],
    }


def plot_erg_waveform(recording: dict,
                      stim_onset_ms: float = 0.0,
                      show_ops: bool = True) -> plt.Figure:
    """Draw an annotated ERG waveform (ISCEV conventions; Robson et al., 2022).

    stim_onset_ms : time of the flash in the recording (ms).
    show_ops      : add a second panel with the 75-300 Hz OP trace.
    """
    t   = recording['time_ms']
    amp = recording['amplitude_uv']
    fs  = recording['fs_hz']

    # a-wave trough: lowest point in the first 30 ms after the flash.
    a_win = np.where((t >= stim_onset_ms) & (t <= stim_onset_ms + 30))[0]
    a_i = a_win[np.argmin(amp[a_win])]
    # b-wave peak: highest point from the a-wave trough to 150 ms after the flash.
    b_win = np.where((t > t[a_i]) & (t <= stim_onset_ms + 150))[0]
    b_i = b_win[np.argmax(amp[b_win])]
    # Pre-flash baseline: mean of the 100 ms before the flash (ISCEV).
    base = amp[(t >= stim_onset_ms - 100) & (t < stim_onset_ms)].mean()

    a_amp = base - amp[a_i]           # pre-flash baseline to trough
    b_amp = amp[b_i] - amp[a_i]       # a-wave trough to b-wave peak
    a_time = t[a_i] - stim_onset_ms   # implicit times run from the flash
    b_time = t[b_i] - stim_onset_ms

    n = 2 if show_ops else 1
    fig, axes = plt.subplots(n, 1, figsize=(10, 4 * n), sharex=True,
                             squeeze=False,
                             gridspec_kw={'height_ratios': [3, 1][:n]})
    ax = axes[0, 0]

    # Main waveform, baseline, and flash.
    ax.plot(t, amp, color='#2E75B6', linewidth=1.6, label='ERG waveform')
    ax.axhline(0, color='gray', linewidth=0.7, linestyle=':')
    ax.axvline(stim_onset_ms, color='red', linewidth=1.0, linestyle='--',
               label='Flash')

    # a-wave bracket: baseline to trough.
    ax.annotate('', xy=(t[a_i], amp[a_i]), xytext=(t[a_i], base),
                arrowprops=dict(arrowstyle='<->', color='#C62828', lw=1.4))
    ax.text(t[a_i] + 4, (amp[a_i] + base) / 2,
            f'a: {a_amp:.0f} µV\nat {a_time:.1f} ms', color='#C62828')

    # b-wave bracket: a-wave trough to b-wave peak.
    ax.annotate('', xy=(t[b_i], amp[b_i]), xytext=(t[b_i], amp[a_i]),
                arrowprops=dict(arrowstyle='<->', color='#1F4E79', lw=1.4))
    ax.text(t[b_i] + 4, (amp[b_i] + amp[a_i]) / 2,
            f'b: {b_amp:.0f} µV\nat {b_time:.1f} ms', color='#1F4E79')

    ax.set_ylabel('Amplitude (µV)')
    ax.legend(loc='lower right')

    # OP panel: a 75-300 Hz band-pass filter keeps only the OPs.
    if show_ops:
        sos = butter(4, OP_BAND, btype='bandpass', fs=fs, output='sos')
        axes[1, 0].plot(t, sosfiltfilt(sos, amp), color='#2E7D32',
                        linewidth=1.2)
        axes[1, 0].axhline(0, color='gray', linewidth=0.7, linestyle=':')
        axes[1, 0].set_ylabel('OPs (µV)')

    axes[-1, 0].set_xlabel('Time (ms)')
    fig.suptitle(f"{recording['protocol']}  |  {recording['electrode_type']}  |  "
                 f"a = {a_amp:.0f} µV at {a_time:.1f} ms  |  "
                 f"b = {b_amp:.0f} µV at {b_time:.1f} ms")
    fig.tight_layout()
    return fig


# Example: the flash in the Chapter 3 sample is at 100 ms.
recording = load_recording_from_csv('data/samples/normal_001_DA3.csv')
fig = plot_erg_waveform(recording, stim_onset_ms=100)
plt.show()

# Expected title on the figure:
# DA 3.0  |  DTL_fiber  |  a = 146 µV at 16.5 ms  |  b = 458 µV at 60.5 ms

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft


def plot_erg_spectrogram(recording: dict,
                         stim_onset_ms: float = 0.0,
                         fmax_hz: float = 300.0,
                         nperseg: int = 64,
                         noverlap: int = 32) -> plt.Figure:
    """Draw an STFT spectrogram of an ERG recording.

    stim_onset_ms : time of the flash in the recording (ms).
    fmax_hz       : highest frequency shown (Hz).
    nperseg       : window length in samples (64 = 32 ms at 2,000 Hz).
    noverlap      : samples shared by neighboring windows (32 = 50%).
    """
    t   = recording['time_ms']
    amp = recording['amplitude_uv']
    fs  = recording['fs_hz']

    # STFT with a Hamming window (Albasu et al., 2024).
    freqs, t_win, Z = stft(amp, fs=fs, window='hamming',
                           nperseg=nperseg, noverlap=noverlap)

    # Window times in ms, measured from the flash.
    t_ms = t_win * 1000 + t[0] - stim_onset_ms

    # Strength in decibels (dB), relative to the mean before the flash.
    power_db = 20 * np.log10(np.abs(Z) + 1e-12)
    before = t_ms < 0
    if before.any():
        power_db -= power_db[:, before].mean(axis=1, keepdims=True)

    keep = freqs <= fmax_hz + fs / nperseg   # one row past fmax_hz fills the top
    fig, ax = plt.subplots(figsize=(10, 4.5))
    mesh = ax.pcolormesh(t_ms, freqs[keep], power_db[keep],
                         shading='gouraud', cmap='magma')
    ax.axvline(0, color='white', linewidth=1.0, linestyle=':', label='Flash')
    ax.axhline(75, color='cyan', linewidth=0.8, linestyle='--',
               label='75 Hz (lower edge of the OP band)')
    fig.colorbar(mesh, ax=ax, label='Strength (dB above the pre-flash level)')
    ax.set_xlabel('Time after the flash (ms)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_ylim(0, fmax_hz)
    ax.legend(loc='upper right')
    ax.set_title(f"STFT spectrogram  |  {recording['protocol']}  |  "
                 f"window {nperseg} samples, overlap {noverlap}")
    fig.tight_layout()
    return fig


# Example, using the recording loaded in §4.1.4 (flash at 100 ms).
fig = plot_erg_spectrogram(recording, stim_onset_ms=100)
plt.show()

# Pass and Warning thresholds for each electrode type (Table 2.3).
SNR_THRESHOLDS = {
    'contact_lens': {'pass': 8.0, 'warn': 4.0},
    'gold_foil':    {'pass': 6.0, 'warn': 3.0},
    'dtl_fiber':    {'pass': 4.0, 'warn': 2.5},
    'skin':         {'pass': 3.0, 'warn': 2.0},
}


def add_snr_overlay(ax, recording: dict, stim_onset_ms: float = 0.0) -> dict:
    """Add the noise band and the quality badge to a waveform axis.

    The SNR is the b-wave amplitude (a-wave trough to b-wave peak) divided
    by the peak-to-peak noise in the 100 ms before the flash (§2.2.1).
    """
    t   = recording['time_ms']
    amp = recording['amplitude_uv']

    # Noise: the range of the signal in the 100 ms before the flash.
    base = amp[(t >= stim_onset_ms - 100) & (t < stim_onset_ms)]
    noise_lo, noise_hi = base.min(), base.max()
    noise_pp = noise_hi - noise_lo
    ax.axhspan(noise_lo, noise_hi, color='orange', alpha=0.2,
               label=f'Noise band ({noise_pp:.1f} µV peak to peak)')

    # a-wave trough and b-wave peak, as in plot_erg_waveform().
    a_win = np.where((t >= stim_onset_ms) & (t <= stim_onset_ms + 30))[0]
    a_i = a_win[np.argmin(amp[a_win])]
    b_win = np.where((t > t[a_i]) & (t <= stim_onset_ms + 150))[0]
    b_i = b_win[np.argmax(amp[b_win])]
    snr = (amp[b_i] - amp[a_i]) / noise_pp
    snr_db = 20 * np.log10(snr)

    # Electrode name in the file, for example 'DTL_fiber' -> 'dtl_fiber'.
    key = recording['electrode_type'].lower().replace(' ', '_')
    thr = SNR_THRESHOLDS[key]        # an unknown electrode type stops here
    flag = ('PASS' if snr >= thr['pass'] else
            'WARNING' if snr >= thr['warn'] else 'FAIL')
    badge_color = {'PASS': '#2E7D32', 'WARNING': '#F9A825',
                   'FAIL': '#C62828'}[flag]

    ax.text(0.02, 0.97, f'Quality: {flag}   SNR: {snr:.1f}  ({snr_db:.1f} dB)',
            transform=ax.transAxes, va='top', color='white',
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.35', facecolor=badge_color))
    ax.legend(loc='lower right')
    return {'snr': snr, 'snr_db': snr_db, 'flag': flag,
            'noise_pp_uv': noise_pp}


# Example: add the overlay to the waveform plot from §4.1.4.
fig = plot_erg_waveform(recording, stim_onset_ms=100, show_ops=False)
result = add_snr_overlay(fig.axes[0], recording, stim_onset_ms=100)
print(f"SNR {result['snr']:.1f} ({result['snr_db']:.1f} dB), "
      f"{result['flag']}, noise {result['noise_pp_uv']:.1f} µV peak to peak")
plt.show()

# Expected output:
# SNR 15.7 (23.9 dB), PASS, noise 29.3 µV peak to peak

def check_baseline_drift(recording: dict, stim_onset_ms: float = 0.0,
                         limit_pct: float = 10.0, ax=None) -> dict:
    """Measure baseline drift per second as a share of the b-wave (§2.5.1).

    A straight line is fitted to the 100 ms before the flash. Its slope,
    in µV per second, is divided by the b-wave amplitude.
    """
    t   = recording['time_ms']
    amp = recording['amplitude_uv']

    # Straight-line fit to the 100 ms before the flash.
    pre = (t >= stim_onset_ms - 100) & (t < stim_onset_ms)
    slope_per_ms, offset = np.polyfit(t[pre], amp[pre], 1)
    drift_per_s = abs(slope_per_ms) * 1000          # µV per second

    # b-wave amplitude, as in plot_erg_waveform().
    a_win = np.where((t >= stim_onset_ms) & (t <= stim_onset_ms + 30))[0]
    a_i = a_win[np.argmin(amp[a_win])]
    b_win = np.where((t > t[a_i]) & (t <= stim_onset_ms + 150))[0]
    b_amp = amp[b_win].max() - amp[a_i]

    drift_pct = 100 * drift_per_s / b_amp
    within_limit = drift_pct <= limit_pct

    if ax is not None:
        ax.plot(t[pre], amp[pre], color='gray', linewidth=1.0,
                label='Signal before the flash')
        ax.plot(t[pre], slope_per_ms * t[pre] + offset, color='#E65100',
                linewidth=2.0, label='Fitted straight line')
        ax.set_xlabel('Time (ms)')
        ax.set_ylabel('Amplitude (µV)')
        ax.set_title(f'Drift {drift_per_s:.0f} µV/s = {drift_pct:.1f}% of the '
                     f'b-wave per second  |  limit {limit_pct:.0f}%')
        ax.legend()

    return {'drift_uv_per_s': drift_per_s, 'drift_pct_of_b_wave': drift_pct,
            'within_limit': bool(within_limit)}


# Example, using the recording loaded in §4.1.4.
fig, ax = plt.subplots(figsize=(8, 3.5))
drift = check_baseline_drift(recording, stim_onset_ms=100, ax=ax)
print(f"Drift {drift['drift_uv_per_s']:.1f} µV/s, "
      f"{drift['drift_pct_of_b_wave']:.1f}% of the b-wave per second, "
      f"within limit: {drift['within_limit']}")
plt.show()

# Expected output:
# Drift 9.3 µV/s, 2.0% of the b-wave per second, within limit: True

# Blink ceilings for each electrode type, in µV (Chapter 6, §6.2.1).
BLINK_CEILING_UV = {'contact_lens': 1600, 'gold_foil': 900,
                    'dtl_fiber': 540, 'skin': 200}


def screen_sweeps(sweeps: np.ndarray, electrode_type: str, ax=None) -> dict:
    """Flag sweeps above the blink ceiling and give the Chapter 2 result.

    sweeps : array with one row per sweep (µV), before averaging.
    """
    key = electrode_type.lower().replace(' ', '_')
    ceiling = BLINK_CEILING_UV[key]       # an unknown electrode type stops here

    pk2pk = sweeps.max(axis=1) - sweeps.min(axis=1)
    rejected = pk2pk > ceiling
    share = float(100 * rejected.mean())

    # Chapter 2 rule for the share of rejected sweeps (§2.5).
    result = ('PASS' if share <= 20 else
              'WARNING' if share <= 40 else 'FAIL')

    if ax is not None:
        n = np.arange(1, len(pk2pk) + 1)
        ax.scatter(n, pk2pk, c=np.where(rejected, '#C62828', '#2E7D32'), s=30)
        ax.axhline(ceiling, color='red', linestyle='--', linewidth=0.9,
                   label=f'Blink ceiling ({ceiling} µV)')
        ax.set_xlabel('Sweep number')
        ax.set_ylabel('Peak-to-peak amplitude (µV)')
        ax.set_title(f'{rejected.sum()} of {len(pk2pk)} sweeps rejected '
                     f'({share:.0f}%)  |  {result}')
        ax.legend()

    return {'rejected_sweeps': (np.where(rejected)[0] + 1).tolist(),
            'share_rejected_pct': share, 'result': result}


# Example: 20 simulated sweeps made from the §4.1.4 recording, each with its
# own noise; sweeps 6 and 15 carry a large slow wave, as a blink would add.
rng = np.random.default_rng(1)
t = recording['time_ms']
sweeps = recording['amplitude_uv'] + rng.normal(0, 15, (20, t.size))
blink = 700 * np.exp(-0.5 * ((t - 300) / 60) ** 2)
sweeps[[5, 14]] += blink

fig, ax = plt.subplots(figsize=(8, 3.5))
screen = screen_sweeps(sweeps, recording['electrode_type'], ax=ax)
print(screen)
plt.show()

# Expected output:
# {'rejected_sweeps': [6, 15], 'share_rejected_pct': 10.0, 'result': 'PASS'}

import plotly.graph_objects as go
from scipy.signal import butter, sosfiltfilt


def build_interactive_waveform(recording: dict,
                               stim_onset_ms: float = 0.0) -> go.Figure:
    """Build an interactive ERG waveform viewer with Plotly.

    The waveform shows its time and amplitude on hover. The OP trace
    (75-300 Hz) is hidden at first and can be shown from the legend.
    """
    t   = recording['time_ms'] - stim_onset_ms        # time from the flash
    amp = recording['amplitude_uv']
    fs  = recording['fs_hz']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=amp, mode='lines', name=recording['protocol'],
        line=dict(color='#2E75B6', width=2),
        hovertemplate='Time: %{x:.1f} ms<br>Amplitude: %{y:.1f} µV<extra></extra>'))

    sos = butter(4, [70, 320], btype='bandpass', fs=fs, output='sos')
    fig.add_trace(go.Scatter(
        x=t, y=sosfiltfilt(sos, amp), mode='lines', name='OPs (75-300 Hz)',
        line=dict(color='#2E7D32', width=1.2), visible='legendonly',
        hovertemplate='Time: %{x:.1f} ms<br>OPs: %{y:.1f} µV<extra></extra>'))

    fig.add_vline(x=0, line_dash='dash', line_color='red',
                  annotation_text='Flash', annotation_position='top right')
    fig.update_layout(
        title=f"ERG  |  {recording['protocol']}  |  "
              f"{recording['electrode_type']} electrode",
        xaxis_title='Time after the flash (ms)',
        yaxis_title='Amplitude (µV)',
        plot_bgcolor='white', height=480)
    return fig


# Example, using the recording loaded in §4.1.4 (flash at 100 ms).
viewer = build_interactive_waveform(recording, stim_onset_ms=100)
viewer.show()

# Save as one HTML file with the Plotly code inside, so it opens offline.
viewer.write_html('erg_waveform.html', include_plotlyjs=True)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection


def plot_mferg_maps(mferg: dict, snr_limit: float = 2.5) -> plt.Figure:
    """Draw an mfERG amplitude map and a matching signal quality map.

    mferg must contain:
      density    : response density of each hexagon (nV/deg²)
      snr        : SNR of each hexagon
      centers    : list of (x, y) hexagon centers
      hex_radius : radius of each hexagon
    snr_limit : hexagons below this SNR are hatched on the amplitude map.
    """
    density = np.asarray(mferg['density'], dtype=float)
    snr = np.asarray(mferg['snr'], dtype=float)
    centers = mferg['centers']
    r = mferg['hex_radius']

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    def hexagons():
        return [RegularPolygon(c, numVertices=6, radius=r * 0.95)
                for c in centers]

    panels = [
        (axes[0], density, colormaps['viridis'],
         plt.Normalize(0, np.nanmax(density)),
         'Response density (nV/deg²)', 'Amplitude map'),
        (axes[1], snr, colormaps['RdYlGn'],
         plt.Normalize(0, max(6.0, np.nanmax(snr))),
         'SNR of each hexagon', 'Signal quality map'),
    ]
    for ax, values, cmap, norm, label, title in panels:
        patches = hexagons()
        for i, p in enumerate(patches):
            p.set_facecolor(cmap(norm(values[i])))
            p.set_edgecolor('white')
            if ax is axes[0] and snr[i] < snr_limit:
                p.set_hatch('///')      # weak signal: do not trust this value
        ax.add_collection(PatchCollection(patches, match_original=True))
        ax.autoscale_view()
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                     label=label)

    fig.suptitle('Multifocal ERG maps (show with the trace array)')
    fig.tight_layout()
    return fig


# Example with 61 simulated hexagons in five rings (illustrative values).
centers, rings = [], []
for q in range(-4, 5):
    for s in range(-4, 5):
        ring = max(abs(q), abs(s), abs(q + s))
        if ring <= 4:
            centers.append((np.sqrt(3) * (q + s / 2), 1.5 * s))
            rings.append(ring + 1)
rings = np.array(rings)
density = np.array([100, 70, 55, 45, 40])[rings - 1].astype(float)
snr = np.array([9.0, 7.0, 5.5, 4.5, 4.0])[rings - 1]
snr[[3, 40]] = 1.8          # two hexagons with weak signals
mferg = {'density': density, 'snr': snr, 'centers': centers, 'hex_radius': 1.0}

fig = plot_mferg_maps(mferg)
plt.show()
print(f'{(snr < 2.5).sum()} of {len(snr)} hexagons below the SNR limit')

# Expected output:
# 2 of 61 hexagons below the SNR limit
