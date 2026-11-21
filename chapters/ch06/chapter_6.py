# Chapter 6: artifact detection and rejection
# The code of Chapter 6, in the order of the book: blink detection, EMG
# detection, electrode movement detection, the combined sweep screener,
# the Wiener filter, and the worked example on 20 simulated sweeps.
# Run from the repository folder:  python chapters/ch06/chapter_6.py

# ── Blink detection: amplitude ceiling for each electrode type ────────
import numpy as np

# Blink ceilings in µV (§6.2.1); Chapter 4 uses the same values (§4.3.3).
BLINK_CEILING_UV = {'contact_lens': 1600, 'gold_foil': 900,
                    'dtl_fiber': 540, 'skin': 200}


def detect_blink(sweep_uv: np.ndarray, electrode_type: str) -> dict:
    """Flag a sweep whose peak-to-peak amplitude exceeds the blink ceiling."""
    ceiling = BLINK_CEILING_UV[electrode_type.lower().replace(' ', '_')]
    ptp = float(np.ptp(sweep_uv))          # highest minus lowest point (µV)
    flagged = ptp > ceiling
    return {'flagged': flagged, 'peak_to_peak_uv': ptp,
            'reason': (f'peak-to-peak {ptp:.0f} µV > ceiling {ceiling} µV'
                       if flagged else 'none')}

# ── EMG artifact detection ────────────────────────────────────────────────
import numpy as np
from scipy.signal import welch


def op_band_level(segment: np.ndarray,
                  fs_hz: float,
                  op_band_hz: tuple = (75, 300)) -> float:
    """
    Root of the mean Welch PSD over the OP band for one signal segment.
    Used only as a relative measure, so absolute units do not matter.
    """
    if len(segment) < 8:
        return 0.0
    f, psd = welch(segment, fs=fs_hz, nperseg=min(64, len(segment)))
    mask = (f >= op_band_hz[0]) & (f <= op_band_hz[1])
    return float(np.sqrt(np.mean(psd[mask]))) if mask.any() else 0.0


def emg_reference_level(sweeps: np.ndarray,
                        fs_hz: float,
                        pre_samples: int,
                        op_band_hz: tuple = (75, 300),
                        min_sweeps: int = 5):
    """
    Median post-stimulus OP-band level across all sweeps of a recording.
    Genuine OPs are time-locked and present in every sweep, so they are
    carried by the median; random EMG bursts are not.
    Returns None when fewer than min_sweeps sweeps are available.
    """
    if len(sweeps) < min_sweeps:
        return None
    levels = [op_band_level(s[pre_samples:], fs_hz, op_band_hz)
              for s in sweeps]
    return float(np.median(levels))


def detect_emg(sweep_uv: np.ndarray,
               fs_hz: float,
               pre_samples: int,
               reference_level,
               op_band_hz: tuple = (75, 300),
               threshold_db: float = 6.0) -> dict:
    """
    Detect EMG contamination in the oscillatory potential band.
    Compares the post-stimulus OP-band level of this sweep with the median
    level across the sweeps of the same recording (reference_level).
    Returns: flagged (bool), excess_db (float), reason (str).
    """
    # Guard: no reference (too few sweeps) or a silent reference
    if reference_level is None or reference_level < 1e-9:
        return {'flagged': False, 'excess_db': 0.0,
                'reason': 'not assessed: too few sweeps or no OP band energy'}

    level = op_band_level(sweep_uv[pre_samples:], fs_hz, op_band_hz)
    excess_db = 20 * np.log10(max(level, 1e-12) / reference_level)
    flagged = bool(excess_db > threshold_db)

    return {
        'flagged': flagged,
        'excess_db': float(excess_db),
        'reason': (f'post-stimulus OP band {excess_db:.1f} dB above '
                   f'sweep median') if flagged else 'none'
    }

# ── Electrode movement (step change) detection ────────────────────────────
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def detect_electrode_movement(sweep_uv: np.ndarray,
                              fs_hz: float,
                              step_uv: float = 385.0,
                              smoothing_ms: float = 10.0,
                              comparison_ms: float = 20.0) -> dict:
    """
    Detect abrupt step changes caused by electrode movement or contact loss.

    The sweep is first smoothed with a short running-mean window
    (smoothing_ms) to suppress sample-to-sample noise, then compared against
    itself offset by a longer comparison window (comparison_ms) to detect a
    sustained shift in the local mean. A genuine ERG response develops
    gradually and is bounded by the a-wave's and b-wave's own amplitude;
    an electrode movement or contact-loss event produces a shift that is
    both faster and larger.

    step_uv is set per electrode type by screen_sweep(), from
    MOVEMENT_STEP_UV (§6.2.3); the default of 385 µV is the DTL fiber value.
    gold_foil=650, dtl/dtl_fiber=385, skin=144 uV; see screen_sweep());
    the default here (385 uV, the DTL value) applies only when the function
    is called directly without an electrode-specific override.

    Parameters
    ----------
    sweep_uv : np.ndarray
        Single ERG sweep in uV.
    fs_hz : float
        Sampling rate in Hz.
    step_uv : float
        Minimum change in windowed mean (uV) that constitutes a step event.
    smoothing_ms : float
        Window length (ms) of the running mean.
    comparison_ms : float
        Separation (ms) between the two means that are compared.

    Returns
    -------
    dict with keys: flagged, max_step_uv, step_time_ms, reason
    """
    smooth_n = max(2, int(smoothing_ms * fs_hz / 1000))
    comp_n = max(1, int(comparison_ms * fs_hz / 1000))
    none_found = {'flagged': False, 'max_step_uv': 0.0,
                  'step_time_ms': None, 'reason': 'none'}
    if len(sweep_uv) < smooth_n + comp_n:
        return none_found

    means = np.mean(sliding_window_view(sweep_uv, smooth_n), axis=1)
    if len(means) <= comp_n:
        return none_found

    steps = np.abs(means[comp_n:] - means[:-comp_n])
    max_step = float(np.max(steps))
    flagged = max_step > step_uv

    step_idx = int(np.argmax(steps)) + comp_n if flagged else None
    step_t = (step_idx / fs_hz * 1000) if step_idx is not None else None

    return {
        'flagged': flagged,
        'max_step_uv': max_step,
        'step_time_ms': step_t,
        'reason': (f'Step {max_step:.0f} µV > threshold {step_uv:.0f} µV '
                   f'at {step_t:.1f} ms') if flagged else 'none',
    }

# ── Combined sweep-level artifact screener ────────────────────────────
# Movement thresholds in µV, about 72% of each blink ceiling (§6.2.3)
MOVEMENT_STEP_UV = {'contact_lens': 1150, 'gold_foil': 650,
                    'dtl_fiber': 385, 'skin': 144}


def screen_sweep(sweep_uv: np.ndarray,
                 fs_hz: float,
                 pre_samples: int,
                 electrode: str = 'dtl_fiber',
                 emg_reference=None) -> dict:
    """
    Apply the three artifact detectors to a single ERG sweep.
    emg_reference is the median OP-band level of the recording, from
    emg_reference_level(); without it the EMG detector is not applied.
    Returns a combined result dict with:
        reject       : bool - True if ANY detector flagged this sweep
        flags        : list - names of triggered detectors
        blink        : dict - blink detector result
        emg          : dict - EMG detector result
        electrode_mv : dict - electrode movement detector result
    """
    key = electrode.lower().replace(' ', '_')
    if key == 'dtl':                         # short name for DTL fiber
        key = 'dtl_fiber'

    b = detect_blink(sweep_uv, key)
    e = detect_emg(sweep_uv, fs_hz, pre_samples, emg_reference)
    m = detect_electrode_movement(sweep_uv, fs_hz,
                                  step_uv=MOVEMENT_STEP_UV[key],
                                  smoothing_ms=10.0, comparison_ms=20.0)

    triggered = []
    if b['flagged']:
        triggered.append('BLINK')
    if e['flagged']:
        triggered.append('EMG')
    if m['flagged']:
        triggered.append('ELECTRODE_MOVEMENT')

    return {
        'reject':       bool(triggered),
        'flags':        triggered,
        'blink':        b,
        'emg':          e,
        'electrode_mv': m,
    }


# ── Apply screener to a stack of sweeps and compute rejection rate ─────────
def screen_all_sweeps(sweeps: np.ndarray,
                      fs_hz: float,
                      pre_samples: int,
                      electrode: str = 'dtl_fiber') -> dict:
    """
    Screen a 2-D array of sweeps (shape: n_sweeps x n_samples).
    Returns:
        accept_mask    : bool array, True = sweep passes screening
        rejection_rate : float, fraction of sweeps rejected
        quality_flag   : str, PASS / WARNING / FAIL (Chapter 2, §2.5.1)
        sweep_results  : list of per-sweep screen_sweep() dicts
    """
    # One EMG reference level for the whole recording
    emg_ref = emg_reference_level(sweeps, fs_hz, pre_samples)

    results = [screen_sweep(sweeps[i], fs_hz, pre_samples, electrode, emg_ref)
               for i in range(len(sweeps))]
    accept = np.array([not r['reject'] for r in results])
    rej_rate = float(1 - accept.mean())

    # Rejection-rate bands of Chapter 2 (§2.5.1)
    if rej_rate <= 0.20:
        q_flag = 'PASS'
    elif rej_rate <= 0.40:
        q_flag = 'WARNING'
    else:
        q_flag = 'FAIL'

    return {
        'accept_mask':    accept,
        'rejection_rate': rej_rate,
        'quality_flag':   q_flag,
        'sweep_results':  results,
    }

# ── Wiener filter for residual noise reduction (after Cerutti et al., 1987) ─
import numpy as np
from scipy.signal import periodogram, welch


def wiener_denoise(sweep_uv: np.ndarray,
                   reference_uv: np.ndarray,
                   fs_hz: float,
                   pre_samples: int,
                   noise_floor: float = 1e-12) -> np.ndarray:
    """
    Apply a Wiener filter to the post-stimulus part of one ERG sweep.

    Signal PSD : periodogram of reference_uv, the average of the other
                 accepted sweeps (the stimulus-locked estimate of the signal).
    Noise PSD  : Welch PSD of this sweep's pre-stimulus baseline, assumed to
                 have the same properties after the stimulus.
    Gain       : W(f) = S_signal / (S_signal + S_noise)
    Returns the sweep (same length): pre-stimulus samples unchanged,
    post-stimulus samples filtered.
    """
    pre = sweep_uv[:pre_samples]
    post = sweep_uv[pre_samples:]
    ref_post = reference_uv[pre_samples:]

    # Both PSDs as densities (µV²/Hz) on the frequency grid of the post part
    f_post, s_sig = periodogram(ref_post, fs=fs_hz, detrend=False)
    f_pre, s_noise = welch(pre, fs=fs_hz, nperseg=min(64, len(pre)))
    s_noise = np.interp(f_post, f_pre, s_noise)

    gain = s_sig / (s_sig + s_noise + noise_floor)
    post_filt = np.fft.irfft(gain * np.fft.rfft(post), n=len(post))

    return np.concatenate([pre, post_filt])

# ── Worked example: artifact detection on a simulated 20-sweep recording ───

import numpy as np
import matplotlib.pyplot as plt

# Build 20 clean synthetic sweeps (same Gaussian model as Chapter 2)
fs    = 2000
n_sw  = 20
epoch = 500       # ms total epoch length
pre   = 100       # ms pre-stimulus
N     = int(fs * epoch / 1000)
pre_n = int(fs * pre  / 1000)
t     = np.linspace(0, epoch, N)

def clean_sweep(noise_uv=8):
    # A simplified DTL fiber-sized DA 3.0 response: by the ISCEV rules,
    # an a-wave of about 74 µV and a b-wave of about 286 µV (Fig. 6.3).
    sig = (-90 * np.exp(-((t-(pre+20))**2)/(2*8**2)) +
           210 * np.exp(-((t-(pre+60))**2)/(2*18**2)))
    return sig + np.random.normal(0, noise_uv, N)
np.random.seed(42)
sweeps = np.array([clean_sweep() for _ in range(n_sw)])

# Inject known artifacts into specific sweeps
# Sweep 3: blink (slow transient starting 200 ms and peaking 280 ms
# after the stimulus, 450 µV peak)
blink_t = (t > pre + 200) & (t < pre + 380)
sweeps[2][blink_t] += 450 * np.exp(
    -((t[blink_t] - (pre + 280)) ** 2) / (2 * 40 ** 2))

# Sweep 9: EMG burst (broadband noise from 30 to 80 ms after the stimulus,
# standard deviation 80 µV, overlapping the OP window)
emg_t = (t > pre + 30) & (t < pre + 80)
sweeps[8][emg_t] += np.random.normal(0, 80, emg_t.sum())

# Sweep 15: electrode movement (450 µV step 150 ms after the stimulus)
step_idx = int((pre + 150) * fs / 1000)
sweeps[14][step_idx:] += 450

# Run the artifact screener
result = screen_all_sweeps(sweeps, fs_hz=fs,
                            pre_samples=pre_n, electrode='dtl')
print(f'Accepted:  {result["accept_mask"].sum()}/{n_sw} sweeps')
print(f'Rejection rate: {result["rejection_rate"]*100:.1f}%')
print(f'Quality flag: {result["quality_flag"]}')
for i, r in enumerate(result['sweep_results']):
    if r['reject']:
        print(f'  Sweep {i+1:2d} REJECTED  flags={r["flags"]}')

# Expected output:
# Accepted:  17/20 sweeps
# Rejection rate: 15.0%
# Quality flag: PASS
#   Sweep  3 REJECTED  flags=['BLINK']
#   Sweep  9 REJECTED  flags=['EMG']
#   Sweep 15 REJECTED  flags=['BLINK', 'EMG', 'ELECTRODE_MOVEMENT']

# Average accepted sweeps and plot
avg_all      = np.mean(sweeps, axis=0)
avg_accepted = np.mean(sweeps[result['accept_mask']], axis=0)
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
axes[0].plot(t, avg_all,      color='firebrick', lw=1.5,
             label='All sweeps (including artifacts)')
axes[0].set_title('Average: all 20 sweeps', fontsize=11)
axes[1].plot(t, avg_accepted, color='steelblue', lw=1.8,
             label='Accepted sweeps only')
axes[1].set_title(f'Average: {result["accept_mask"].sum()} accepted sweeps', fontsize=11)
for ax in axes:
    ax.axvline(pre, color='red', lw=1, ls='-', alpha=0.7)
    ax.axhline(0, color='gray', lw=0.7, ls=':')
    ax.set_xlabel('Time (ms)'); ax.legend(fontsize=9)
axes[0].set_ylabel('Amplitude (µV)')
fig.suptitle('Effect of artifact rejection on the averaged ERG response', fontsize=12, fontweight='bold')
plt.tight_layout(); plt.show()
