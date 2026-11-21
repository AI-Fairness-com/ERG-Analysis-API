# Chapter 8: STFT spectrograms for deep learning
# The code of Chapter 8, in the order of the book: the project-wide STFT
# configuration and spectrogram generator, the global statistics for
# classical models, the conversion to PyTorch tensors for the ViT, and
# the signal and spectrogram augmentations. The book's code defines the
# functions; the commented lines show how they are called.
# Run from the repository folder:  python chapters/ch08/chapter_8.py

import numpy as np
from scipy.signal import stft
from skimage.transform import resize

# ── Project-wide STFT configuration ────────────────────────────
# Every setting is stored here, so each spectrogram can be reproduced.
STFT_CONFIG = {
    'window'   : 'hamming',    # Albasu et al. (2024); see §8.3.3
    'nperseg'  : 64,           # 32 ms window at 2000 Hz
    'noverlap' : 32,           # 50% overlap, 16 ms hop (§8.2.3)
    'fs'       : 2000.0,       # Hz; must match the recording
    'fmin_hz'  : 0.0,          # lower edge of the frequency crop
    'fmax_hz'  : 300.0,        # ISCEV upper cutoff
    'output_h' : 224,          # output image height (pixels)
    'output_w' : 224,          # output image width (pixels)
    'norm'     : 'db_zscore',  # normalization strategy
}


def generate_erg_spectrogram(signal_uv:   np.ndarray,
                             config:      dict = None,
                             return_axes: bool = False) -> np.ndarray:
    """
    Generate a normalized 2-D spectrogram from a filtered ERG sweep.

    Parameters
    ----------
    signal_uv   : 1-D filtered ERG array in µV (output of Chapter 5).
    config      : STFT configuration dict. Defaults to STFT_CONFIG.
    return_axes : If True, also return (freqs, times) for axis labels.

    Returns
    -------
    S_norm : 2-D float32 array, shape (output_h, output_w). Values lie
             in [0, 1] for norm = 'db_zscore' or 'minmax';
             norm = 'none' returns dB values.
    """
    cfg = config or STFT_CONFIG
    fs = cfg['fs']

    # ── Step 1: Compute the STFT ───────────────────────────────
    freqs, times, Zxx = stft(signal_uv,
                             fs=fs,
                             window=cfg['window'],
                             nperseg=cfg['nperseg'],
                             noverlap=cfg['noverlap'])

    # ── Step 2: Convert to power in dB ─────────────────────────
    # |STFT|^2 is the power spectrogram (Equation 8.1).
    power = np.abs(Zxx) ** 2
    S_db = 10 * np.log10(power + 1e-12)    # epsilon avoids log(0)

    # ── Step 3: Crop to the clinical frequency range ───────────
    fmask = (freqs >= cfg['fmin_hz']) & (freqs <= cfg['fmax_hz'])
    S_db = S_db[fmask, :]
    freqs = freqs[fmask]

    # ── Step 4: Normalization ──────────────────────────────────
    # 'db_zscore' gives each recording the same mean and spread,
    # so only the pattern is kept, not the absolute level.
    if cfg['norm'] == 'db_zscore':
        mu = S_db.mean()
        sigma = S_db.std() + 1e-8
        S_n = (S_db - mu) / sigma
        # Clip at ±3 standard deviations, then rescale to [0, 1]
        S_n = np.clip(S_n, -3, 3)
        S_n = (S_n + 3) / 6.0
    elif cfg['norm'] == 'minmax':
        lo, hi = S_db.min(), S_db.max()
        S_n = (S_db - lo) / (hi - lo + 1e-8)
    elif cfg['norm'] == 'none':
        # Keep the dB values, so the absolute level is preserved.
        # Used only for the optional summary statistics of §8.4.2,
        # never for the Vision Transformer input.
        S_n = S_db
    else:
        raise ValueError(f'Unknown normalization: {cfg["norm"]}')

    # ── Step 5: Resize to the fixed output size (bicubic) ──────
    S_norm = resize(S_n,
                    (cfg['output_h'], cfg['output_w']),
                    order=3,               # bicubic
                    anti_aliasing=True,
                    preserve_range=True).astype(np.float32)

    if return_axes:
        return S_norm, freqs, times
    return S_norm

import numpy as np

def spectrogram_global_stats(S_db: np.ndarray) -> np.ndarray:
    """
    Extract the four Albasu et al. (2024) summary statistics
    (max, min, median, mean intensity) from a spectrogram.
    Computed once over the full spectrogram, not per band or region
    (Albasu et al., 2024, Section 3.2.2).

    S_db : (H, W) spectrogram in dB, from generate_erg_spectrogram()
           with norm = 'none'. A z-score normalized image is not
           suitable, because its mean and maximum are nearly the
           same for every recording.

    Returns
    -------
    np.ndarray of shape (4,): [bmax, bmin, bmedian, bmean].
    """
    return np.array([S_db.max(), S_db.min(),
                     np.median(S_db), S_db.mean()],
                    dtype=np.float32)

# cfg = dict(STFT_CONFIG, norm='none')
# S_db = generate_erg_spectrogram(signal_uv, config=cfg)
# feature_vector = spectrogram_global_stats(S_db)  # 4-element vector

import torch
import numpy as np

def spectrogram_to_tensor(S_norm: np.ndarray,
                          channels: int = 3,
                          imagenet_norm: bool = True
                          ) -> torch.Tensor:
    """
    Convert a normalized spectrogram array to a PyTorch image tensor.

    Parameters
    ----------
    S_norm        : (H, W) float32 array, values in [0, 1].
    channels      : 3 for pre-trained ViT/CNN (channel replication);
                    1 for scratch-trained single-channel models.
    imagenet_norm : If True, apply ImageNet mean/std normalization.
                    True for pre-trained models; False for scratch.
    """
    # Stack to a (C, H, W) tensor
    if channels == 3:
        t = torch.from_numpy(S_norm).unsqueeze(0).repeat(3, 1, 1)
    elif channels == 1:
        t = torch.from_numpy(S_norm).unsqueeze(0)
    else:
        raise ValueError(f'channels must be 1 or 3, got {channels}')

    # ImageNet normalization (mean and std of each channel).
    # The 3 replicated channels are identical, but each one is
    # normalized with its own ImageNet mean and std.
    if imagenet_norm and channels == 3:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        t = (t - mean) / std

    return t   # shape (C, H, W)

def batch_to_tensor(spectrograms: list,
                    channels: int = 3,
                    imagenet_norm: bool = True) -> torch.Tensor:
    """Convert a list of (H, W) spectrograms to (N, C, H, W)."""
    tensors = [spectrogram_to_tensor(S, channels, imagenet_norm)
               for S in spectrograms]
    return torch.stack(tensors)   # (N, C, H, W)

# ── Confirm the tensor shape before feeding it to the ViT ──────
# S = generate_erg_spectrogram(filtered_sweep)  # (224, 224) float32
# t = spectrogram_to_tensor(S, channels=3)      # (3, 224, 224)
# batch = batch_to_tensor([S1, S2, S3])         # (3, 3, 224, 224)
# model(batch)                                  # ViT forward pass

import numpy as np


def augment_erg_signal(signal_uv: np.ndarray,
                       noise_frac_range: tuple = (0.01, 0.05),
                       rng: np.random.Generator = None) -> np.ndarray:
    """
    Apply Gaussian noise injection to a raw ERG signal, before the
    STFT and spectrogram normalization (§8.4.1). The noise range
    follows Chen et al. (2026).
    signal_uv : 1D float32 array, raw ERG signal in microvolts.
    Returns the augmented signal, same shape as the input.
    """
    rng = rng or np.random.default_rng()
    sig = signal_uv.astype(np.float32)
    # Gaussian noise injection: sigma set relative to this recording's
    # own standard deviation, simulating realistic sensor noise
    # (Chen et al., 2026).
    noise_frac = rng.uniform(*noise_frac_range)
    sigma = noise_frac * sig.std()
    return sig + rng.normal(0, sigma, sig.shape).astype(np.float32)


def augment_spectrogram(S_norm: np.ndarray,
                        time_mask_max: int = 30,
                        freq_mask_max: int = 20,
                        fill_value: float = 0.5,
                        rng: np.random.Generator = None
                        ) -> np.ndarray:
    """
    Apply SpecAugment time and frequency masking (Park et al.,
    2019) to an already-normalized ERG spectrogram. Gaussian noise
    is added earlier, to the raw signal, by augment_erg_signal().
    S_norm     : (H, W) float32 spectrogram, values in [0, 1].
    fill_value : value written into masked regions; 0.5 is the
                 mean level after db_zscore normalization (§8.4.1).
    Returns the augmented spectrogram with the same shape.
    """
    rng = rng or np.random.default_rng()
    S = S_norm.copy()
    H, W = S.shape
    # Time masking: 0 to time_mask_max neighboring columns
    t_mask = int(rng.integers(0, time_mask_max + 1))
    if t_mask > 0:
        t0 = int(rng.integers(0, W - t_mask + 1))
        S[:, t0 : t0 + t_mask] = fill_value
    # Frequency masking: 0 to freq_mask_max neighboring rows
    f_mask = int(rng.integers(0, freq_mask_max + 1))
    if f_mask > 0:
        f0 = int(rng.integers(0, H - f_mask + 1))
        S[f0 : f0 + f_mask, :] = fill_value
    return S
