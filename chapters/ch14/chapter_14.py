"""Chapter 14: Explainable AI, SHAP and calibration.

Code from Chapter 14 of "Hands-On Electroretinography in the Age of
AI", in the order of the book: TreeSHAP for the Random Forest (Level
1), SHAP on the 330 time-frequency cells of the ViT (Level 2), the
region summary, the plain-language narratives (Levels 1 and 3), ViT
calibration with the Brier Score check, and the report block. A short
demonstration on simulated data runs at the end. Outputs go to
./outputs/shap.
"""

# Level 1 tutorial: TreeSHAP for the Random Forest of Chapter 12
import os
import numpy as np
import shap
import matplotlib.pyplot as plt


def compute_feature_shap(pipeline, X, sample_idx, feature_names,
                         output_dir='outputs/shap'):
    """
    Explain one recording with exact TreeSHAP values. The pipeline
    holds a 'preprocessor' step and a Random Forest 'classifier'.
    The values explain the model output before calibration.
    """
    os.makedirs(output_dir, exist_ok=True)
    prep = pipeline.named_steps['preprocessor']
    forest = pipeline.named_steps['classifier']
    x = prep.transform(X[sample_idx:sample_idx + 1])

    explainer = shap.TreeExplainer(forest)
    sv = np.asarray(explainer.shap_values(x))
    proba = forest.predict_proba(x)[0]
    k = int(np.argmax(proba))                  # predicted class
    # Newer shap: (1, features, classes); older: list of classes
    values = sv[0, :, k] if sv.shape[-1] == len(proba) else sv[k, 0]
    base = float(np.ravel(explainer.expected_value)[k])

    # Local accuracy: base value plus contributions equals the output
    if not np.isclose(base + values.sum(), proba[k], atol=1e-6):
        raise ValueError('SHAP values do not add up to the output')

    explanation = shap.Explanation(values=values, base_values=base,
                                   data=x[0],
                                   feature_names=feature_names)
    shap.plots.waterfall(explanation, max_display=15, show=False)
    path = os.path.join(output_dir, f'waterfall_{sample_idx}.png')
    plt.savefig(path, dpi=220, bbox_inches='tight')
    plt.close()
    return {'class_index': k, 'base_value': base,
            'output': float(proba[k]), 'shap_values': values}

# Level 2: SHAP on the 330 real time-frequency cells
import os
import numpy as np
import torch
import torch.nn as nn
import shap
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from skimage.transform import resize

# Teal for negative, dark midpoint, coral for positive (Figure 14.2)
SHAP_CMAP = LinearSegmentedColormap.from_list(
    'shap_signed', ['#4ecdc4', '#16213e', '#e76f51'])
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def resize_matrix(n_in, n_out):
    """The Chapter 8 bicubic resize along one axis, as a matrix."""
    eye = np.eye(n_in)
    cols = [resize(eye[:, [k]], (n_out, 1), order=3, clip=False,
                   anti_aliasing=True, preserve_range=True)[:, 0]
            for k in range(n_in)]
    return np.stack(cols, axis=1)              # shape (n_out, n_in)


class CellModel(nn.Module):
    """
    The ViT Small with the fixed Chapter 8 enlargement in front:
    10 x 33 grid -> 224 x 224 -> three copied channels -> ImageNet
    normalization. Predictions are unchanged; the players become
    the 330 real time-frequency cells.
    """
    def __init__(self, vit, n_f=10, n_t=33, size=224):
        super().__init__()
        self.vit = vit
        self.register_buffer('rh', torch.tensor(
            resize_matrix(n_f, size), dtype=torch.float32))
        self.register_buffer('rw', torch.tensor(
            resize_matrix(n_t, size), dtype=torch.float32))
        self.register_buffer('mean', torch.tensor(
            IMAGENET_MEAN).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor(
            IMAGENET_STD).view(1, 3, 1, 1))

    def forward(self, cells):                  # (N, 1, 10, 33)
        img = self.rh @ cells @ self.rw.T      # (N, 1, 224, 224)
        # skimage clips the result to the input range, so clip too
        lo = cells.amin(dim=(2, 3), keepdim=True)
        hi = cells.amax(dim=(2, 3), keepdim=True)
        img = torch.maximum(torch.minimum(img, hi), lo)
        img = img.repeat(1, 3, 1, 1)
        return self.vit((img - self.mean) / self.std)


def compute_spectrogram_shap(vit, cells, background, class_idx,
                             class_name, output_dir='outputs/shap'):
    """
    Signed SHAP map on the 10 x 33 grid for one recording.
    cells: tensor (1, 1, 10, 33) from the Chapter 8 pipeline before
    resizing; background: tensor (20, 1, 10, 33) from the training
    set. Returns the grid scaled to [-1, 1]; positive pushes toward
    class_idx.
    """
    os.makedirs(output_dir, exist_ok=True)
    model = CellModel(vit).eval()
    explainer = shap.GradientExplainer(model, background)
    sv = explainer.shap_values(cells)
    # Older shap: list with one array per class; newer: class last
    sv = sv[class_idx] if isinstance(sv, list) else sv[..., class_idx]
    grid = np.asarray(sv)[0, 0]                # (10, 33)
    grid = grid / (np.abs(grid).max() + 1e-12)

    # Enlarge for display only, with the same resize as the model
    rh, rw = model.rh.cpu().numpy(), model.rw.cpu().numpy()
    spec = np.clip(rh @ cells[0, 0].cpu().numpy() @ rw.T, 0, 1)
    shown = np.clip(rh @ grid @ rw.T, -1, 1)
    heat = SHAP_CMAP((shown + 1) / 2)[..., :3]
    weight = 0.85 * np.abs(shown)[..., None]   # color up to 85%
    gray = np.repeat(spec[..., None], 3, axis=2)
    overlay = np.clip((1 - weight) * gray + weight * heat, 0, 1)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(overlay, origin='lower', aspect='auto',
              extent=[-100, 412, 0, 312.5])
    ax.set_xlabel('Time after the flash (ms)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title(f'SHAP overlay: {class_name}')
    name = class_name.replace(' ', '_')
    fig.savefig(f'{output_dir}/saliency_{name}.png', dpi=220,
                bbox_inches='tight')
    plt.close(fig)
    return grid

# Region-level summary of the SHAP grid
import numpy as np

# Windows in Hz and in ms after the flash (project conventions,
# from the components of Chapters 8 and 9)
REGIONS = {
    'b_wave_band':   ((0, 30), (20, 60)),
    'phnr_band':     ((0, 30), (60, 200)),
    'op_burst_band': ((75, 300), (15, 70)),
    'prestim_noise': ((0, 300), (-100, 0)),
}


def summarize_saliency_regions(grid, fs=2000.0, nperseg=64,
                               noverlap=32, pre_stimulus_ms=100.0):
    """
    Mean positive SHAP value of the cells in each named region,
    scaled so that the largest region equals 1. A cell belongs to a
    region when its center frequency and center time fall inside.
    """
    n_f, n_t = grid.shape
    freqs = np.arange(n_f) * fs / nperseg               # Hz
    hop_ms = (nperseg - noverlap) / fs * 1000.0
    times = np.arange(n_t) * hop_ms - pre_stimulus_ms   # ms

    results = {}
    for name, ((f0, f1), (t0, t1)) in REGIONS.items():
        rows = (freqs >= f0) & (freqs < f1)
        cols = (times >= t0) & (times < t1)
        block = grid[np.ix_(rows, cols)]
        results[name] = float(np.clip(block, 0, None).mean())

    top = max(results.values()) or 1.0
    return {k: round(v / top, 3) for k, v in results.items()}

# Level 1 tutorial: plain-language narrative from SHAP values
import numpy as np

# Size bands of Table 14.1 (project conventions, config-API)
DOMINANT_MIN = 0.20
SIGNIFICANT_MIN = 0.10
SUPPORTING_MIN = 0.05

# Key: (feature name, 'high' or 'low' against the training mean).
# Value: (phrase, fragment that says what the feature measures).
SENTENCE_MAP = {
    ('op2_implicit_ms', 'high'): (
        'The delay in OP2 implicit time',
        'Oscillatory potentials are conventionally associated with '
        'inner retinal activity (Robson et al., 2022).'),
    ('dwt_80ops_uv2', 'low'): (
        'The reduction in oscillatory potential wavelet energy',
        'This feature measures the energy of the response near '
        '80 Hz in the oscillatory potential time window.'),
    ('phnr_amp_uv', 'low'): (
        'The reduction in PhNR amplitude',
        'The photopic negative response is conventionally '
        'associated with retinal ganglion cell activity '
        '(Frishman et al., 2018).'),
    ('b_implicit_ms', 'high'): (
        'The delay in b-wave implicit time',
        'The b-wave is conventionally associated with bipolar cell '
        'activity (Robson et al., 2022).'),
    ('op2_amp_uv', 'low'): (
        'The reduction in OP2 amplitude',
        'OP2 is the second peak of the oscillatory potentials in the '
        'filtered response.'),
    ('ba_ratio', 'low'): (
        'The reduction in the b/a amplitude ratio',
        'The ratio compares the b-wave with the a-wave in the same '
        'response.'),
    ('a_amp_uv', 'low'): (
        'The reduction in a-wave amplitude',
        'The a-wave is conventionally associated with photoreceptor '
        'activity (Robson et al., 2022).'),
}

# Plain names for the 28 features of Chapter 9, so that no code
# name reaches a clinician
FEATURE_LABELS = {
    'a_amp_uv': 'a-wave amplitude',
    'a_implicit_ms': 'a-wave implicit time',
    'b_amp_uv': 'b-wave amplitude',
    'b_implicit_ms': 'b-wave implicit time',
    'ba_ratio': 'b/a amplitude ratio',
    'op2_amp_uv': 'OP2 amplitude',
    'op3_amp_uv': 'OP3 amplitude',
    'op4_amp_uv': 'OP4 amplitude',
    'op_sum_uv': 'summed oscillatory potential amplitude',
    'op2_implicit_ms': 'OP2 implicit time',
    'phnr_amp_uv': 'PhNR amplitude',
    'phnr_bwave_ratio': 'PhNR to b-wave ratio',
    'hurst_exponent': 'Hurst exponent of the waveform',
    'approximate_entropy':
        'waveform complexity (approximate entropy)',
    'dwt_20a_uv2': 'a-wave wavelet energy near 20 Hz',
    'dwt_40a_uv2': 'a-wave wavelet energy near 40 Hz',
    'dwt_20b_uv2': 'b-wave wavelet energy near 20 Hz',
    'dwt_40b_uv2': 'b-wave wavelet energy near 40 Hz',
    'dwt_80ops_uv2':
        'oscillatory potential wavelet energy near 80 Hz',
    'dwt_160ops_uv2':
        'oscillatory potential wavelet energy near 160 Hz',
    'b_descending_gradient_uv_ms': 'b-wave falling slope',
    'b_descending_inflection_ms': 'b-wave falling-limb turning point',
    'b_ascending_gradient_uv_ms': 'b-wave rising slope',
    'b_ascending_inflection_ms': 'b-wave rising-limb turning point',
    'a_descending_inflection_ms': 'a-wave falling-limb turning point',
    'peak_freq_hz': 'dominant frequency',
    'spectral_entropy': 'spread of energy across frequencies',
    'harmonic_ratio': 'flicker harmonic ratio',
}


def _label(name):
    return FEATURE_LABELS.get(name, name.replace('_', ' '))


def plain_language_shap(shap_values, feature_values, feature_names,
                        feature_means, predicted_class):
    """
    Turn the SHAP values of one recording into a short narrative.
    Features that pushed toward the predicted class are named as
    contributors; strong features that pushed away are listed apart.
    """
    total = float(np.sum(np.abs(shap_values))) + 1e-12
    sentences, supporting, against = [], [], []

    for i in np.argsort(-np.abs(shap_values)):   # largest first
        sv, name = float(shap_values[i]), feature_names[i]
        size = abs(sv)
        if size < SUPPORTING_MIN:
            break                                # the rest are small
        if sv < 0:
            if size >= SIGNIFICANT_MIN:
                against.append(_label(name))
            continue
        # PhNR is stored as a negative value, so its sign is flipped
        sign = -1.0 if name == 'phnr_amp_uv' else 1.0
        high = sign * feature_values[i] > sign * feature_means[i]
        entry = SENTENCE_MAP.get((name, 'high' if high else 'low'))
        if size < SIGNIFICANT_MIN or entry is None:
            supporting.append(_label(name))
            continue
        phrase, fragment = entry
        rank = ('the dominant' if size >= DOMINANT_MIN
                else 'a significant')
        share = size / total * 100
        sentences.append(
            f'{phrase} was {rank} contributor to the '
            f'{predicted_class} classification ({share:.0f}% of '
            f'the total attribution). {fragment}')

    if supporting:
        sentences.append('Supporting contributors: '
                         + ', '.join(supporting[:3]) + '.')
    if against:
        sentences.append('Findings that argued against the '
                         f'{predicted_class} classification: '
                         + ', '.join(against[:3]) + '.')
    if not sentences:
        return ('No single feature contributed strongly to this '
                'classification. Please refer to the waterfall chart '
                'in the Specialist Report.')
    return ' '.join(sentences)

# Level 3: plain-language narrative from the saliency regions
# Keys match summarize_saliency_regions(). Associations follow the
# ISCEV standard (Robson et al., 2022) and the ISCEV PhNR protocol
# (Frishman et al., 2018).
REGION_SENTENCE_MAP = {
    'b_wave_band': (
        'the b-wave region',
        'conventionally associated with bipolar cell activity'),
    'phnr_band': (
        'the photopic negative response region',
        'conventionally associated with retinal ganglion cell '
        'activity'),
    'op_burst_band': (
        'the oscillatory potential region',
        'conventionally associated with inner retinal activity'),
}

ARTIFACT_SENTENCE = (
    'The model also gave substantial weight to the pre-stimulus '
    'interval, which contains no retinal response. This may indicate '
    'baseline noise or an artifact, and the recording quality should '
    'be checked before this result is relied upon.')


def plain_language_regions(region_summary, predicted_class,
                           min_norm=0.5, max_regions=3):
    """
    Turn the normalized region summary into a narrative for the
    Layer 2 Clinical Summary. Regions at or above min_norm are named
    in descending order, up to max_regions. The narrative reports
    where the model placed weight, not that a change is present.
    """
    ranked = sorted(region_summary.items(), key=lambda kv: -kv[1])
    named = [name for name, value in ranked
             if name in REGION_SENTENCE_MAP and value >= min_norm]
    sentences = []
    for i, name in enumerate(named[:max_regions]):
        region, association = REGION_SENTENCE_MAP[name]
        if i == 0:
            sentences.append(
                f'The classification as {predicted_class} placed the '
                f'most weight on {region} ({association}).')
        else:
            sentences.append(
                f'The model also weighted {region} ({association}).')
    if not sentences:
        sentences.append(
            f'The classification as {predicted_class} was not '
            'dominated by any single named region of the response. '
            'Please refer to the saliency overlay in the Specialist '
            'Report.')
    if region_summary.get('prestim_noise', 0.0) >= min_norm:
        sentences.append(ARTIFACT_SENTENCE)
    return ' '.join(sentences)

# Calibration of the ViT Small output and the Brier Score check
import warnings
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, log_softmax, softmax


def _platt(z, y):
    """Fit p = sigmoid(A * z + B) by maximum likelihood."""
    def nll(params):
        a, b = params
        p = np.clip(expit(a * z + b), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    return minimize(nll, x0=[1.0, 0.0], method='Nelder-Mead').x


def _temperature(logits, y):
    """Fit one temperature T by maximum likelihood (Guo et al.)."""
    def nll(t):
        logp = log_softmax(logits / t, axis=1)
        return -np.mean(logp[np.arange(len(y)), y])
    return minimize_scalar(nll, bounds=(0.05, 20.0),
                           method='bounded').x


def calibrate_vit_output(logits_val, y_val, logits_test, y_test,
                         class_names):
    """
    Stage 1 (two classes): Platt scaling on the logit difference.
    Stage 2 (six classes): temperature scaling. Both are fitted on
    the validation partition and checked on the test set.
    """
    if logits_val.shape[1] == 2:
        a, b = _platt(logits_val[:, 1] - logits_val[:, 0], y_val)
        p1 = expit(a * (logits_test[:, 1] - logits_test[:, 0]) + b)
        proba = np.column_stack([1 - p1, p1])
        params = {'A': round(float(a), 5), 'B': round(float(b), 5)}
    else:
        t = _temperature(logits_val, y_val)
        proba = softmax(logits_test / t, axis=1)
        params = {'T': round(float(t), 5)}

    # Brier Score of each class against its p(1 - p) reference
    brier, flags = {}, {}
    for c, name in enumerate(class_names):
        y_bin = (y_test == c).astype(float)
        freq = y_bin.mean()
        brier[name] = float(np.mean((proba[:, c] - y_bin) ** 2))
        passed = brier[name] < freq * (1 - freq)
        flags[name] = 'PASS' if passed else 'CALIBRATION_WARNING'

    failed = [n for n, f in flags.items() if f != 'PASS']
    if failed:
        warnings.warn('No better than the frequency-only reference: '
                      + ', '.join(failed) + '. Their probabilities '
                      'are withheld from Layers 1 and 2.')
    return {'calibrated_proba': proba, 'parameters': params,
            'brier_per_class': brier, 'class_flags': flags,
            'suppressed_classes': failed,
            'layer4_audit_flag': 'CALIBRATION_WARNING' if failed
            else 'PASS'}

# Integration: one report block for the deployed route
def generate_shap_report_block(vit, cells, background, class_idx,
                               class_name, probability,
                               output_dir='outputs/shap'):
    """
    Run Levels 2 and 3 for one recording. probability is the
    calibrated value from calibrate_vit_output(). Attributions are
    always kept for Layer 4; the clinical layers show them only
    when the Traffic Light is not Green (Section 14.1.3).
    """
    grid = compute_spectrogram_shap(vit, cells, background,
                                    class_idx, class_name, output_dir)
    regions = summarize_saliency_regions(grid)
    name = class_name.replace(' ', '_')
    return {
        'predicted_class': class_name,
        'layer2_narrative': plain_language_regions(regions,
                                                   class_name),
        'layer3_saliency_path': f'{output_dir}/saliency_{name}.png',
        'layer3_region_summary': regions,
        'layer4_attribution': {'calibrated_probability': probability,
                               'region_scores': regions,
                               'shap_grid': grid.round(4).tolist()},
    }


# ── Demonstration on simulated data ──────────────────────────────────
# The book applies these functions to the Random Forest of Chapter 12
# and the ViT Small of Chapter 13. The block below runs each function
# once on simulated data, so that the script runs on its own. The ViT
# here is untrained, so its map and narrative mean nothing clinically;
# load your trained checkpoint (models/vit_best.pt) in its place.
if __name__ == '__main__':
    import timm
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(42)
    names = ['a_amp_uv', 'b_amp_uv', 'op_sum_uv', 'a_implicit_ms',
             'b_implicit_ms', 'ba_ratio']
    y = rng.integers(0, 2, 120)
    X = rng.normal([150, 300, 60, 15, 50, 2.0],
                   [25, 50, 12, 1, 4, 0.3], (120, 6))
    X[:, 1] -= 80 * y                    # class 1 has a smaller b-wave
    pipe = Pipeline([('preprocessor', StandardScaler()),
                     ('classifier', RandomForestClassifier(
                         n_estimators=100, random_state=42))]).fit(X, y)

    # Level 1: TreeSHAP waterfall and plain-language narrative
    res = compute_feature_shap(pipe, X, 0, names)
    x0 = pipe.named_steps['preprocessor'].transform(X[:1])[0]
    print(plain_language_shap(res['shap_values'], x0, names,
                              np.zeros(len(names)), 'Abnormal'))

    # Calibration of simulated Stage 1 logits and the Brier Score check
    y_val, y_test = rng.integers(0, 2, 200), rng.integers(0, 2, 200)
    logits_val = rng.normal(0, 1, (200, 2))
    logits_val[:, 1] += 2 * y_val
    logits_test = rng.normal(0, 1, (200, 2))
    logits_test[:, 1] += 2 * y_test
    cal = calibrate_vit_output(logits_val, y_val, logits_test, y_test,
                               ['Normal', 'Abnormal'])
    print(cal['parameters'], cal['class_flags'])

    # Levels 2 and 3: SHAP grid, regions and narrative on the ViT
    vit = timm.create_model('vit_small_r26_s32_224', pretrained=False,
                            num_classes=2).eval()
    cells = torch.rand(1, 1, 10, 33)
    background = torch.rand(20, 1, 10, 33)
    block = generate_shap_report_block(
        vit, cells, background, 1, 'Abnormal',
        float(cal['calibrated_proba'][0, 1]))
    print(block['layer2_narrative'])
    print('Saliency figure:', block['layer3_saliency_path'])
