# Chapter 7: frequency and time-frequency analysis of the ERG
# The code of Chapter 7, in the order of the book: the FFT of one sweep,
# the Welch PSD, the worked FFT comparison of a normal and an advanced RP
# response, the continuous wavelet transform, and the DWT decomposition.
# Run from the repository folder:  python chapters/ch07/chapter_7.py

# ── FFT of a single ERG sweep ──────────────────────────────────────────────
import numpy as np
import matplotlib.pyplot as plt


def compute_fft(signal_uv: np.ndarray,
                fs_hz: float) -> dict:
    """
    Compute the single-sided amplitude spectrum of a real ERG signal.
    Returns: freqs (Hz array), amplitude (µV array), power (µV² array).
    """
    N = len(signal_uv)

    # Apply a Hamming window to reduce spectral leakage
    window = np.hamming(N)
    windowed = signal_uv * window

    # rfft returns N//2+1 complex values
    fft_vals = np.fft.rfft(windowed, n=N)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs_hz)   # frequency axis in Hz

    # Single-sided amplitude: multiply by 2/sum(window) for correct
    # coherent-gain scaling (except DC and Nyquist bins, which are not doubled)
    amplitude = (2.0 / window.sum()) * np.abs(fft_vals)
    amplitude[0] /= 2                  # DC component: do not double
    if N % 2 == 0:
        amplitude[-1] /= 2             # Nyquist bin: do not double

    power = amplitude ** 2             # power spectrum (µV²)

    return {'freqs': freqs, 'amplitude': amplitude, 'power': power}


# ── Plot the amplitude spectrum ────────────────────────────────────────────
def plot_fft(fft_result: dict, title: str = 'ERG Amplitude Spectrum'):
    freqs = fft_result['freqs']
    amp = fft_result['amplitude']

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(freqs, amp, color='#2E75B6', lw=1.6)

    # Shade the three diagnostic frequency bands
    ax.axvspan(0.3, 20, alpha=0.10, color='blue',
               label='a-wave/b-wave band (0.3-20 Hz)')
    ax.axvspan(30, 75, alpha=0.08, color='gray',
               label='Transition (30–75 Hz)')
    ax.axvspan(75, 300, alpha=0.10, color='orange',
               label='OP band (75–300 Hz)')
    ax.set_xlabel('Frequency (Hz)', fontsize=11)
    ax.set_ylabel('Amplitude (µV)', fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 320)
    plt.tight_layout()
    plt.show()

# ── Welch PSD for multi-sweep averaged ERG ─────────────────────────────────
import numpy as np
from scipy.signal import welch
from scipy.integrate import trapezoid


def compute_welch_psd(sweeps_uv: np.ndarray,
                      fs_hz: float,
                      nperseg: int = None) -> dict:
    """
    Compute the Welch PSD from a stack of ERG sweeps.
    sweeps_uv : shape (n_sweeps, n_samples), accepted sweeps after artifact
                rejection.
    Returns: freqs (Hz), psd (µV²/Hz), band_power dict.
    """
    n_sw, n_samp = sweeps_uv.shape

    # Average the sweeps first to improve SNR, then compute PSD on the average
    avg = sweeps_uv.mean(axis=0)

    # Default segment: 250 ms (500 samples at 2000 Hz), giving 4 Hz frequency
    # bins and 3 overlapping segments for a 500 ms epoch
    seg = nperseg or min(int(0.25 * fs_hz), n_samp)
    freqs, psd = welch(avg, fs=fs_hz, nperseg=seg,
                       noverlap=seg // 2, window='hann')

    # Integrate power in each diagnostic band (trapezoid rule)
    def band_power(f1, f2):
        mask = (freqs >= f1) & (freqs <= f2)
        return float(trapezoid(psd[mask], freqs[mask]))

    bands = {
        'total_0_300': band_power(0.3, 300),
        'bwave_0_20': band_power(0.3, 20),
        'op_75_300': band_power(75, 300),
        'phnr_11hz': band_power(7.8, 15.9),
        'transition_30_75': band_power(30, 75),
    }

    # Power ratio: OP band relative to total power (candidate DR feature)
    total = bands['total_0_300'] + 1e-12
    bands['op_power_ratio'] = bands['op_75_300'] / total
    bands['bwave_power_ratio'] = bands['bwave_0_20'] / total

    return {'freqs': freqs, 'psd': psd, 'band_power': bands}

# ── Worked example: FFT comparison of normal vs. advanced RP ────────────────
import numpy as np
import matplotlib.pyplot as plt

# Build a simplified synthetic normal DA 3.0 sweep. The amplitudes are
# illustrative, not measured. The a-wave trough (about -157 µV) and the
# b-wave (about +353 µV, measured from the a-wave trough as in the ISCEV
# Standard) lie within the Baker et al. (2025) silver thread DA 3 limits
# for the youngest age group. OP implicit times follow Dimopoulos et al.
# (2014), 0.38 log stimulus; each crest is about half the reported
# trough-to-peak amplitude. This single-Gaussian construction does not
# reproduce the combined-signal targeting used for Figure 7.1.
fs = 2000
epoch = 500       # ms
pre = 100         # ms pre-stimulus
N = int(fs * epoch / 1000)
t_ms = np.linspace(0, epoch, N)

# Normal ERG: a-wave, b-wave and four OP wavelets
normal = np.zeros(N)
normal += -170 * np.exp(-((t_ms - (pre + 18))**2) / (2 * 6**2))   # a-wave
normal += 190 * np.exp(-((t_ms - (pre + 57))**2) / (2 * 20**2))   # b-wave

# Four OP wavelets (implicit time in ms post-stimulus, crest amplitude in µV)
for op_t, op_a in [(18.1, 6.4), (24.8, 13.8), (31.2, 11.8), (37.3, 12.0)]:
    normal += (op_a * np.sin(2 * np.pi * 150 * (t_ms - (pre + op_t)) / 1000)
               * np.exp(-((t_ms - (pre + op_t))**2) / (2 * 5**2)))

normal += np.random.default_rng(0).normal(0, 5, N)   # noise floor
# Advanced RP: about 2% of the normal signal, plus noise
rp = normal * 0.02 + np.random.default_rng(1).normal(0, 6, N)

# Compute FFT for both
fft_normal = compute_fft(normal, fs)
fft_rp     = compute_fft(rp,     fs)

# Plot side by side
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
for ax, res, label, col in zip(
        axes,
        [fft_normal, fft_rp],
        ['Normal DA 3.0', 'Advanced RP DA 3.0'],
        ['#2E75B6', '#C62828']):
    ax.plot(res['freqs'], res['amplitude'], color=col, lw=1.5)
    ax.axvspan(0.3, 20,  alpha=0.10, color='blue')
    ax.axvspan(75, 300,  alpha=0.10, color='orange')
    ax.set_xlim(0, 320)
    ax.set_xlabel('Frequency (Hz)', fontsize=11)
    ax.set_title(label, fontsize=12)
    ax.grid(True, alpha=0.3)
axes[0].set_ylabel('Amplitude (µV)', fontsize=11)
fig.suptitle('FFT Amplitude Spectrum: Normal vs. Advanced RP', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.show()

# Print band powers for both
for label, fft_r in [('Normal', fft_normal), ('Advanced RP', fft_rp)]:
    a = fft_r['amplitude']
    f = fft_r['freqs']
    op_mask = (f >= 75) & (f <= 300)
    bw_mask = (f >= 0.3) & (f <= 20)
    bw_rms = np.sqrt(np.mean(a[bw_mask] ** 2))
    op_rms = np.sqrt(np.mean(a[op_mask] ** 2))
    print(f'{label}: a-wave/b-wave band RMS = {bw_rms:.2f} µV | '
          f'OP band RMS = {op_rms:.2f} µV')

# Expected output:
# Normal: a-wave/b-wave band RMS = 29.07 µV | OP band RMS = 0.56 µV
# Advanced RP: a-wave/b-wave band RMS = 0.73 µV | OP band RMS = 0.45 µV

# ── Continuous Wavelet Transform of an ERG sweep ──────────────────────────
import pywt
import numpy as np
import matplotlib.pyplot as plt


def compute_cwt(signal_uv: np.ndarray,
                fs_hz: float,
                wavelet: str = 'cmor1.5-1.0',
                freq_min_hz: float = 0.5,
                freq_max_hz: float = 300.0,
                n_freqs: int = 128) -> dict:
    """
    Compute the CWT scalogram of a single ERG sweep.
    wavelet     : PyWavelets CWT wavelet name.
                  'cmor1.5-1.0' = complex Morlet (bandwidth 1.5, centre 1.0)
                  'mexh'        = Mexican hat, also called Ricker (real)
                  'morl'        = Morlet (real)
    freq_min_hz : lowest frequency to analyse (Hz)
    freq_max_hz : highest frequency to analyse (Hz)
    n_freqs     : number of frequencies (scales)
    Returns a dict with 'scalogram' (power, n_freqs x n_samples),
    'freqs' (Hz) and 'times_ms'.
    Note: a wavelet at 0.5 Hz is much longer than a 500 ms record, so the
    lowest rows spread in time and are dominated by edge effects.
    """
    # Frequency axis (log-spaced), converted to CWT scales
    freqs_hz = np.logspace(np.log10(freq_min_hz),
                           np.log10(freq_max_hz), n_freqs)
    scales = pywt.frequency2scale(wavelet, freqs_hz / fs_hz)

    # Coefficients: one row per scale, one column per sample
    coeffs, _ = pywt.cwt(signal_uv, scales, wavelet,
                         sampling_period=1 / fs_hz)
    scalogram = np.abs(coeffs) ** 2            # power scalogram

    times_ms = np.arange(len(signal_uv)) * 1000.0 / fs_hz
    return {'scalogram': scalogram, 'freqs': freqs_hz, 'times_ms': times_ms}


# ── Plot the CWT scalogram ────────────────────────────────────────────────
def plot_cwt(cwt_result: dict,
             pre_ms: float = 100.0,
             title: str = 'CWT Scalogram'):
    """
    Display the CWT power scalogram as a time-frequency image.
    pre_ms : length of the pre-flash period in ms (marks the flash).
    """
    scalo = cwt_result['scalogram']
    freqs = cwt_result['freqs']
    times = cwt_result['times_ms']

    fig, ax = plt.subplots(figsize=(12, 5))
    img = ax.pcolormesh(times, freqs, 10 * np.log10(scalo + 1e-12),
                        cmap='inferno', shading='auto')
    ax.set_yscale('log')
    ax.set_ylim(freqs[0], freqs[-1])
    ax.set_yticks([1, 5, 10, 30, 75, 150, 300])
    ax.set_yticklabels(['1', '5', '10', '30', '75', '150', '300'])
    ax.axvline(pre_ms, color='cyan', lw=1.2,
               label=f'Flash ({pre_ms:.0f} ms)')
    # Mark the OP band
    ax.axhspan(75, 300, alpha=0.12, color='orange',
               label='OP band (75-300 Hz)')
    ax.set_xlabel('Time (ms)', fontsize=11)
    ax.set_ylabel('Frequency (Hz)', fontsize=11)
    ax.set_title(title, fontsize=12)
    plt.colorbar(img, ax=ax, label='Power (dB)')
    ax.legend(fontsize=9, loc='upper right')
    plt.tight_layout()
    plt.show()

# ── DWT decomposition of an ERG sweep ─────────────────────────────────────

import pywt
import numpy as np

def compute_dwt(signal_uv: np.ndarray,
                wavelet: str = 'haar',
                level: int = None) -> dict:
    """
    Compute the DWT of a single ERG sweep up to the specified level.
    wavelet : PyWavelets wavelet name (default 'haar').
    level   : decomposition depth. If None, uses the maximum useful
              level as determined by §7.4.4.
    Returns dict with:
        coeffs         : list of arrays [cA_n, cD_n, ..., cD_1] per pywt convention
        level_energies : array of energy per detail level (D1..Dn)
        approx_energy  : energy of the final approximation (cA_n)
        feature_vector : compact feature vector for ML input
    """
    max_lvl = pywt.dwt_max_level(len(signal_uv), wavelet)
    lvl = level or min(max_lvl, 6)   # cap at 6 per §7.4.4

    coeffs = pywt.wavedec(signal_uv, wavelet, level=lvl)
    # coeffs[0] = approximation at level lvl (cA_lvl)
    # coeffs[1..n] = detail coefficients at each level (cD_lvl..cD_1)

    # Energy per level: E = sum(c²) / len(c), the mean squared coefficient
    approx_energy = float(np.sum(coeffs[0]**2) / len(coeffs[0]))
    detail_energies = np.array([float(np.sum(c**2) / len(c)) for c in coeffs[1:]])

    # Compact feature vector: log-energy per level (more Gaussian distribution)
    log_energies = np.log1p(np.concatenate([[approx_energy], detail_energies]))

    # Additional statistics per level: mean abs, std, max abs
    stats = []
    for c in coeffs:
        stats.extend([float(np.mean(np.abs(c))),
                      float(np.std(c)),
                      float(np.max(np.abs(c)))])
    feature_vector = np.concatenate([log_energies, stats])

    # Explicit level labels, matching log_energies' and detail_energies'
    # actual order (pywt returns coarsest detail first, not D1..Dn)
    level_names = ['A' + str(lvl)] + ['D' + str(l) for l in range(lvl, 0, -1)]

    return {
        'coeffs': coeffs,
        'level_energies': detail_energies,
        'level_names': level_names,
        'approx_energy': approx_energy,
        'feature_vector': feature_vector,
        'n_features': len(feature_vector),
    }

