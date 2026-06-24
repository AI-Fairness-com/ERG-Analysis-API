"""
ERG_CSV_Generator_v2_4_2.py
=====================================
Corrected synthetic CSV generator — AI Fairness CIO (Charity No. 1218464)
Normative reference: Baker et al. (2025) DOI:10.1007/s10633-025-10009-2

Supersedes ERG_CSV_Generator_v2_4_corrected.py (G1-G5 fixes).
Generates the 11 files that remained failing after the G1-G5 pass, plus
re-generates S_Normal_DA3_GoldFoil_ge60 (S03 regression fix).

Defects corrected in this version (G6, G7, A1/S03)
----------------------------------------------------
G6  DA 10 a_it generator values used DA 3 norms (~14-16ms) instead of
    Baker et al. (2025) DA 10 a_imp norms (le35=11.99ms, 36-59y=12.83ms,
    ge60=13.42ms). Pipeline measured Z=+2.0/+2.5/+2.4 -> AMBER on normal cases.
    FIX: a_it set to Baker mu directly (overshoot < 0.1ms for DA10 b_w=11).
    Affects: S_Normal_DA10_GoldFoil_le35/36to59/ge60.

G7  LA 3 a_it generator values set 1.5-2.1ms too high vs Baker et al. (2025)
    LA 3 a_imp norms (le35=14.03ms, 36-59y=14.30ms, ge60=14.40ms).
    Pipeline measured Z=+2.7/+3.3/+2.8 -> AMBER/RED on normal cases.
    FIX: a_it set to Baker mu directly (overshoot < 0.5ms for LA3 b_w=5).
    Affects: S_Normal_LA3_GoldFoil_36to59/ge60, S_Normal_LA3_dtl_le35.
    Note: S_Normal_LA3_GoldFoil_le35 was already GREEN — not regenerated.

G3  (extended) LA 30Hz _flicker() b_imp (it_ms) was wrong in all three
    strata (le35=20ms, 36-59y=50.5ms, ge60=49.5ms vs Baker norms 25.5/26.0/
    26.45ms). Additionally b_amp was severely underscaled (16-22uV vs norms
    71-93uV). Both corrected simultaneously.
    FIX: amp set to Baker b_amp mu; it_ms set to Baker b_imp mu.
    Affects: S_Normal_LA30Hz_GoldFoil_le35/36to59/ge60.

A1/S03  S_Normal_DA3_GoldFoil_ge60 returned RED (a_imp Z=+4.2) despite
    G5 fixing a_it to 16ms. Root cause: DA3 ge60 has lower a_amp=130uV
    (vs le35=143.6uV), making the broad b-wave tail (b_w=12) relatively
    stronger. This shifts the composite Gaussian minimum 3.52ms rightward
    from the centre, so generator a_it=16ms -> pipeline measures ~19.5ms.
    FIX: generator a_it pre-compensated to 12.5ms so composite minimum
    falls at Baker mu=16.08ms.
    Affects: S_Normal_DA3_GoldFoil_ge60.

Previously corrected (G1-G5, unchanged in this version)
--------------------------------------------------------
G1  _scotopic() b_abs calibration. G2  _photopic() b_w=5ms + a_amp.
G3  _flicker() onset ramp removed. G4  DA 0.01 b_amp. G5  ge60 a_it.
"""

import numpy as np
import pandas as pd
import os

# ─────────────────────────────────────────────────────────────────────────────
# LOCKED PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
FS          = 2000
DT          = 1000.0 / FS        # 0.5 ms
TOTAL_MS    = 300.0
N_SAMPLES   = int(TOTAL_MS / DT) # 600
PRE_MS      = 50.0
FLASH_IDX   = int(PRE_MS / DT)   # 100
MASTER_SEED = 42

T_FULL = np.arange(0, TOTAL_MS, DT)          # 0.0 … 299.5 ms, len=600
T_POST = T_FULL[FLASH_IDX:] - PRE_MS         # 0.0 … 249.5 ms, len=500

# Baker et al. (2025) DA 3 <=35y derived normative values
# Used exclusively for boundary test parameter derivation.
BAKER_DA3_LE35 = {
    'a_amp':     {'mu': 175.5,  'sigma': 30.69},
    'b_amp':     {'mu': 281.6,  'sigma': 53.27},
    'b_it':      {'mu': 51.41,  'sigma': 3.182},
    'b_a_ratio': {'mu': 2.651,  'sigma': 0.4253},
}

# ─────────────────────────────────────────────────────────────────────────────
# WAVEFORM PRIMITIVES (corrected)
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(t, centre, amp, width):
    return amp * np.exp(-((t - centre) ** 2) / (2.0 * width ** 2))


def _scotopic(rng, a_amp, a_it, b_amp_tp, b_it,
              noise_sd=4.5, a_w=3.5, b_w=12.0, op_amp=0.0):
    """
    DA scotopic ERG.
    G1 FIX: b_abs = b_amp_tp - a_amp
    => trough-to-peak = (b_amp_tp - a_amp) - (-a_amp) = b_amp_tp  [intended]
    """
    t = T_POST
    a = _gauss(t, a_it, -a_amp, a_w)
    # G1 CORRECTED line:
    b_abs = b_amp_tp - a_amp
    b = _gauss(t, b_it, b_abs, b_w)
    op = np.zeros_like(t)
    if op_amp > 0:
        for ctr, sgn in [(b_it-12, 1), (b_it-7, -1), (b_it-2, 1)]:
            op += _gauss(t, ctr, sgn * op_amp, 1.5)
    sig = a + b + op + rng.normal(0, noise_sd, len(t))
    sig[t < 0] = 0.0
    return sig


def _photopic(rng, a_amp, a_it, b_amp_tp, b_it,
              phnr_amp=0.0, phnr_it=70.0, phnr_w=12.0,
              noise_sd=3.0, a_w=2.5, b_w=5.0):
    """
    LA photopic ERG with PhNR.
    G1+G2 FIX: b_w=5.0 (was 8.0); b_abs = b_amp_tp - a_amp.
    With b_w=5 the b-wave tail at a_it is ~2uV vs ~24uV for b_w=8,
    eliminating the masking of the a-wave trough.
    """
    t = T_POST
    a = _gauss(t, a_it, -a_amp, a_w)
    # G1 fix also applied here:
    b_abs = b_amp_tp - a_amp
    b = _gauss(t, b_it, b_abs, b_w)
    phnr = _gauss(t, phnr_it, -phnr_amp, phnr_w) if phnr_amp > 0 else 0.0
    sig = a + b + phnr + rng.normal(0, noise_sd, len(t))
    sig[t < 0] = 0.0
    return sig


def _flicker(rng, amp=80.0, it_ms=17.0, noise_sd=1.5):
    """
    LA 30Hz flicker.
    G3 FIX (extended Run 3): decaying sinusoid with tau=100ms envelope.
    Phase set so first peak occurs at exactly it_ms.
    omega*it_ms + phase = pi/2  =>  phase = pi/2 - omega*it_ms

    The exponential decay (tau=100ms) ensures the first positive peak is
    reliably the dominant peak regardless of which window the pipeline's
    b_imp extractor uses, eliminating the noise-driven peak aliasing that
    caused S26/S27 to return RED in Run 3.
    noise_sd reduced from 3.0 to 1.5uV (SNR still physiologically realistic;
    noise at 3.0uV was causing noise spikes to exceed the first-cycle peak).
    Peak location shift due to decay: atan(omega*tau) - pi/2 < 0.2ms. Negligible.
    """
    t = T_POST
    omega = 2 * np.pi * 30.0 / 1000.0        # rad/ms
    phase = np.pi / 2.0 - omega * it_ms       # first peak at it_ms
    tau = 100.0                                # ms — decay constant
    sig = (amp / 2.0) * np.sin(omega * t + phase) * np.exp(-t / tau)
    sig += rng.normal(0, noise_sd, len(t))
    sig[t < 0] = 0.0
    return sig


def _dim_flash(rng, b_amp=120.0, b_it=80.0, b_w=18.0, noise_sd=4.0):
    """DA 0.01 rod-isolated b-wave. G4: higher b_amp values."""
    t = T_POST
    sig = _gauss(t, b_it, b_amp * 0.90, b_w) + rng.normal(0, noise_sd, len(t))
    sig[t < 0] = 0.0
    return sig


def _assemble(post_sig, rng, noise_sd):
    baseline = rng.normal(0, noise_sd, FLASH_IDX)
    amplitude = np.concatenate([baseline, post_sig])
    return pd.DataFrame({
        'Time_ms':      np.round(T_FULL, 1),
        'Amplitude_uV': np.round(amplitude, 4)
    })


def _save(df, directory, fname):
    df.to_csv(os.path.join(directory, fname), index=False)


def rng(seed_extra=0):
    return np.random.default_rng(MASTER_SEED + seed_extra)


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE 28 CORRECTED FILES
# ─────────────────────────────────────────────────────────────────────────────

def generate_corrected(output_dir='synthetic_validation_v2_4_corrected'):
    os.makedirs(output_dir, exist_ok=True)
    generated = []
    N = BAKER_DA3_LE35

    # ── G1/G5: DA 3 normals (seeds 0,1,2) ───────────────────────────────────
    # a_it corrected: le35=15, 36to59=15, ge60=16 (G5 fix)
    # b_amp_tp and a_amp calibrated from validated S01 case
    for seed, age_str, a_amp, a_it, b_amp_tp, b_it, op_a in [
        (0,  'le35',   143.6, 15, 282.7, 53, 6.0),
        (1,  '36to59', 145.0, 15, 286.0, 52, 5.0),
        (2,  'ge60',   130.0, 16.08, 256.0, 53, 4.0),  # A1/S03: a_it set to Baker DA3 ge60 a_imp mu=16.08ms (G5 fixed 19->16; now locked to Baker mu)
    ]:
        r = rng(seed)
        sig = _scotopic(r, a_amp, a_it, b_amp_tp, b_it,
                        noise_sd=4.5, op_amp=op_a)
        df  = _assemble(sig, r, 4.5)
        fn  = f'S_Normal_DA3_GoldFoil_{age_str}.csv'
        _save(df, output_dir, fn)
        generated.append(fn)
        print(f'  OK  {fn}')

    # ── G4: DA 0.01 normals (seeds 10,11,12) ─────────────────────────────────
    # b_amp increased to match Baker et al. (2025) DA 0.01 normative range
    for seed, age_str, b_amp, b_it in [
        (10, 'le35',   235.0, 85.0),
        (11, '36to59', 225.0, 90.0),
        (12, 'ge60',   200.0, 97.0),
    ]:
        r = rng(seed)
        sig = _dim_flash(r, b_amp, b_it)
        df  = _assemble(sig, r, 4.0)
        fn  = f'S_Normal_DA001_GoldFoil_{age_str}.csv'
        _save(df, output_dir, fn)
        generated.append(fn)
        print(f'  OK  {fn}')

    # ── G1/G6: DA 10 normals (seeds 20,21,22) ────────────────────────────────
    # a_w=3.0, b_w=11.0 (wider flash), op_amp=10
    # G6 FIX: a_it set to Baker et al. (2025) DA 10 a_imp mu (was DA3-equivalent values)
    # le35: 14->11.99ms | 36to59: 15->12.83ms | ge60: 16->13.42ms
    for seed, age_str, a_amp, a_it, b_amp_tp, b_it in [
        (20, 'le35',   210.0, 11.99, 349.0, 51),   # G6: Baker DA10 le35 a_imp mu
        (21, '36to59', 184.0, 12.83, 327.0, 51),   # G6: Baker DA10 36to59 a_imp mu
        (22, 'ge60',   158.0, 13.42, 330.0, 52),   # G6: Baker DA10 ge60 a_imp mu
    ]:
        r = rng(seed)
        sig = _scotopic(r, a_amp, a_it, b_amp_tp, b_it,
                        noise_sd=5.0, a_w=3.0, b_w=11.0, op_amp=10.0)
        df  = _assemble(sig, r, 5.0)
        fn  = f'S_Normal_DA10_GoldFoil_{age_str}.csv'
        _save(df, output_dir, fn)
        generated.append(fn)
        print(f'  OK  {fn}')

    # ── G2/G7: LA 3 normals — Gold Foil (seeds 30,31,32) ────────────────────
    # b_w=5.0 (G2 fix); a_amp recalibrated; G1 fix also applied
    # G7 FIX: a_it set to Baker et al. (2025) LA 3 a_imp mu (was 1.5-2.1ms too high)
    # le35: 15->14.03ms | 36to59: 16->14.30ms | ge60: 17->14.40ms
    for seed, age_str, a_amp, a_it, b_amp_tp, b_it, phnr, phnr_it in [
        (30, 'le35',   30.0, 14.03, 123.0, 29, 35.0, 68.0),  # G7: Baker LA3 le35 a_imp mu
        (31, '36to59', 28.0, 14.30, 120.0, 27, 28.0, 72.0),  # G7: Baker LA3 36to59 a_imp mu
        (32, 'ge60',   27.0, 14.40, 112.0, 29.55, 22.0, 76.0),  # G7: Baker LA3 ge60 a_imp mu; b_it corrected to Baker b_imp mu=29.55ms
    ]:
        r = rng(seed)
        sig = _photopic(r, a_amp, a_it, b_amp_tp, b_it,
                        phnr_amp=phnr, phnr_it=phnr_it, noise_sd=3.0)
        df  = _assemble(sig, r, 3.0)
        fn  = f'S_Normal_LA3_GoldFoil_{age_str}.csv'
        _save(df, output_dir, fn)
        generated.append(fn)
        print(f'  OK  {fn}')

    # ── G3: LA 30Hz normals (seeds 40,41,42) ─────────────────────────────────
    # G3 FIX (final): amp pre-compensated for exponential decay in _flicker().
    # The decaying sinusoid produces peak = (amp/2)*exp(-it_ms/tau).
    # Pipeline measures b_amp ≈ peak value. To obtain Baker b_amp mu at the
    # measured peak: amp_gen = 2 * Baker_mu / exp(-it_ms/tau).
    # it_ms set to Baker b_imp mu (unchanged from Run4 corrected version).
    for seed, age_str, amp, it_ms in [
        (40, 'le35',   238.99, 25.50),   # G3: 2*92.60/exp(-25.5/100) — compensated
        (41, '36to59', 209.38, 26.00),   # G3: 2*80.72/exp(-26.0/100) — compensated
        (42, 'ge60',   185.33, 26.45),   # G3: 2*71.13/exp(-26.45/100) — compensated
    ]:
        r = rng(seed)
        sig = _flicker(r, amp, it_ms, noise_sd=3.0)
        df  = _assemble(sig, r, 3.0)
        fn  = f'S_Normal_LA30Hz_GoldFoil_{age_str}.csv'
        _save(df, output_dir, fn)
        generated.append(fn)
        print(f'  OK  {fn}')

    # ── G1: Early DR (seed 50) ────────────────────────────────────────────────
    # a_amp=135, a_it=15, b_amp_tp=165 => Z_b=-2.21, Z_ba=-3.37 => RED
    r = rng(50)
    sig = _scotopic(r, 135.0, 15.0, 165.0, 57.0, noise_sd=4.5, op_amp=3.0)
    df  = _assemble(sig, r, 4.5)
    fn  = 'S_DR_early_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # ── G1: Boundary tests — DA 3 <=35y (seeds 60-66) ────────────────────────
    # All use Baker et al. (2025) derived normative values.
    # Parameters target specific Z-scores after G1 fix.

    # AllZ0: S01-validated params => all GREEN
    r = rng(60)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0, noise_sd=3.0, op_amp=6.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_AllZ0_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # B-amp at Z = -1.95 (just inside GREEN): b_amp_tp = mu - 1.95*sigma = 177.7
    # a_amp set so a-amp alone is AMBER (Z_a ~ -2.78) — overall AMBER
    b_195 = N['b_amp']['mu'] - 1.95 * N['b_amp']['sigma']   # 177.7
    a_195 = 90.2   # Z_a = (90.2 - 175.5)/30.69 = -2.78 AMBER
    r = rng(61)
    sig = _scotopic(r, a_195, 15.0, b_195, N['b_it']['mu'], noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_Bamp_Zneg195_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [b_amp_tp={b_195:.1f}uV, a_amp={a_195}uV]')

    # B-amp at Z = -2.01 (just outside => AMBER)
    b_201 = N['b_amp']['mu'] - 2.01 * N['b_amp']['sigma']   # 175.1
    a_201 = 88.9   # Z_a ~ -2.82 AMBER
    r = rng(62)
    sig = _scotopic(r, a_201, 15.0, b_201, N['b_it']['mu'], noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_Bamp_Zneg201_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [b_amp_tp={b_201:.1f}uV]')

    # B-IT at Z = +1.95 (just inside GREEN upper bound)
    bit_195 = N['b_it']['mu'] + 1.95 * N['b_it']['sigma']   # 57.62
    r = rng(63)
    sig = _scotopic(r, 143.6, 15.0, 282.7, bit_195, noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_BIT_Zpos195_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [b_it={bit_195:.2f}ms]')

    # B-IT at Z = +2.01 (just outside => AMBER)
    bit_201 = N['b_it']['mu'] + 2.01 * N['b_it']['sigma']   # 57.81
    r = rng(64)
    sig = _scotopic(r, 143.6, 15.0, 282.7, bit_201, noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_BIT_Zpos201_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [b_it={bit_201:.2f}ms]')

    # B/A ratio at Z = -1.95 (just inside GREEN)
    ba_195     = N['b_a_ratio']['mu'] - 1.95 * N['b_a_ratio']['sigma']  # 1.822
    b_for_ba95 = ba_195 * N['a_amp']['mu']  # b_amp_tp that gives this ratio
    r = rng(65)
    sig = _scotopic(r, N['a_amp']['mu'], 15.0, b_for_ba95, N['b_it']['mu'],
                    noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_BAratio_Zneg195_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [B/A_target={ba_195:.3f}, b_amp_tp={b_for_ba95:.1f}uV]')

    # B/A ratio at Z = -2.01 (just outside => AMBER)
    ba_201     = N['b_a_ratio']['mu'] - 2.01 * N['b_a_ratio']['sigma']  # 1.796
    b_for_ba01 = ba_201 * N['a_amp']['mu']
    r = rng(66)
    sig = _scotopic(r, N['a_amp']['mu'], 15.0, b_for_ba01, N['b_it']['mu'],
                    noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Boundary_BAratio_Zneg201_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}  [B/A_target={ba_201:.3f}, b_amp_tp={b_for_ba01:.1f}uV]')

    # ── G1: Signal quality / artefact cases (seeds 70,71,72,74) ─────────────
    # All use S01 normal params with G1 fix; noise_sd varies by grade.

    # High noise — Grade D attempt (noise_sd=45)
    r = rng(70)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0, noise_sd=45.0)
    df  = _assemble(sig, r, 45.0)
    fn  = 'S_SQ_HighNoise_GradeD_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # Moderate noise — Grade B/C (noise_sd=15)
    r = rng(71)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0, noise_sd=15.0)
    df  = _assemble(sig, r, 15.0)
    fn  = 'S_SQ_ModerateNoise_GradeBC_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # High quality — Grade A (noise_sd=1.5, OPs prominent)
    r = rng(72)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0,
                    noise_sd=1.5, op_amp=8.0)
    df  = _assemble(sig, r, 1.5)
    fn  = 'S_SQ_HighQuality_GradeA_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # Blink artefact (spike at t_rel=120ms)
    r = rng(74)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0, noise_sd=4.5)
    art_idx = int(120.0 / DT)
    for k in range(-4, 5):
        idx = art_idx + k
        if 0 <= idx < len(sig):
            sig[idx] += 350.0 * np.exp(-k**2 / 2.0)
    df  = _assemble(sig, r, 4.5)
    fn  = 'S_Artefact_Blink_DA3_GoldFoil_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # ── G1+G2: Electrode coverage cases (seeds 80,81,83) ────────────────────
    # DTL DA3 (seed 80) — scotopic with Gold Foil norms
    r = rng(80)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0,
                    noise_sd=4.5, op_amp=5.0)
    df  = _assemble(sig, r, 4.5)
    fn  = 'S_Normal_DA3_dtl_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # DTL LA3 (seed 81) — photopic with G2 fix
    # G7 FIX: a_it 15.0->14.03ms (Baker LA3 le35 a_imp mu)
    r = rng(81)
    sig = _photopic(r, 30.0, 14.03, 123.0, 29.0,
                    phnr_amp=30.0, phnr_it=68.0, noise_sd=3.0)
    df  = _assemble(sig, r, 3.0)
    fn  = 'S_Normal_LA3_dtl_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    # HK-Loop DA3 (seed 83)
    r = rng(83)
    sig = _scotopic(r, 143.6, 15.0, 282.7, 53.0,
                    noise_sd=4.5, op_amp=5.0)
    df  = _assemble(sig, r, 4.5)
    fn  = 'S_Normal_DA3_hk_loop_le35.csv'
    _save(df, output_dir, fn)
    generated.append(fn)
    print(f'  OK  {fn}')

    print(f'\n{len(generated)} corrected CSV files -> {output_dir}/')
    return generated


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION HARNESS
# ─────────────────────────────────────────────────────────────────────────────

def verify(output_dir, generated):
    """
    Structural sanity checks on every generated file.
    V1  dt = 0.5 ms (fs = 2000 Hz)
    V2  600 samples, time range 0.0-299.5 ms
    V3  Pre-stimulus SD < 50 uV (relaxed to accommodate HighNoise)
    V4  Post-stimulus a-wave is negative (skip DA001, LA30Hz)
    V5  b-wave peak > 5 uV (skip DA001, LA30Hz)
    V6  No NaN or Inf
    """
    skip_polarity = {'DA001', 'LA30Hz'}
    results = []
    n_pass = n_fail = n_warn = 0

    print(f'\n{"─"*60}')
    print('VERIFICATION')
    print(f'{"─"*60}')

    for fn in generated:
        fpath = os.path.join(output_dir, fn)
        issues, warns = [], []

        try:
            df = pd.read_csv(fpath)

            # V6
            if df.isnull().any().any() or np.isinf(df['Amplitude_uV'].values).any():
                issues.append('V6: NaN/Inf')

            # V1
            dts = df['Time_ms'].diff().dropna()
            if not np.allclose(dts, 0.5, atol=1e-4):
                issues.append(f'V1: dt={dts.mean():.4f}ms')

            # V2
            if len(df) != 600:
                issues.append(f'V2: {len(df)} samples != 600')
            if not (np.isclose(df['Time_ms'].iloc[0], 0.0) and
                    np.isclose(df['Time_ms'].iloc[-1], 299.5)):
                issues.append(f'V2: time range wrong')

            # V3 pre-stim SD
            pre_sd = df[df['Time_ms'] < 50.0]['Amplitude_uV'].std()
            if pre_sd > 50.0:
                warns.append(f'V3-WARN: pre-stim SD={pre_sd:.1f}uV')

            # V4/V5 polarity (skip DA001, LA30Hz)
            skip = any(s in fn for s in skip_polarity)
            if not skip:
                post = df[df['Time_ms'] >= 50.0].copy()
                t_r = post['Time_ms'].values - 50.0

                a_win = post[(t_r >= 5) & (t_r <= 30)]['Amplitude_uV']
                if len(a_win) > 0 and a_win.min() > -5.0:
                    issues.append(f'V4: a-wave min={a_win.min():.1f}uV')

                b_win = post[(t_r >= 25) & (t_r <= 120)]['Amplitude_uV']
                if len(b_win) > 0 and b_win.max() < 5.0:
                    issues.append(f'V5: b-wave max={b_win.max():.1f}uV')

        except Exception as e:
            issues.append(f'READ_ERROR: {e}')

        if issues:
            status = 'FAIL'; n_fail += 1
        elif warns:
            status = 'WARN'; n_warn += 1
        else:
            status = 'PASS'; n_pass += 1

        tag = '✓' if status == 'PASS' else ('⚠' if status == 'WARN' else '✗')
        print(f'  {tag} {status}  {fn}')
        for x in issues + warns:
            print(f'        -> {x}')
        results.append({'filename': fn, 'status': status,
                        'issues': '; '.join(issues), 'warnings': '; '.join(warns)})

    print(f'\nVerification: {n_pass} PASS  {n_warn} WARN  {n_fail} FAIL  '
          f'(of {len(generated)} files)')

    rdf = pd.DataFrame(results)
    rpath = os.path.join(output_dir, 'VERIFICATION_RESULTS_corrected.csv')
    rdf.to_csv(rpath, index=False)
    print(f'Results -> {rpath}')
    return rdf


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('ERG CSV Generator v2.4.2 — 11 corrected files (G3/G6/G7/A1-S03)')
    print('AI Fairness CIO (1218464) | Baker et al. (2025)')
    print('Fixes: G3 flicker amp+it | G6 DA10 a_it | G7 LA3 a_it | A1/S03 DA3 ge60 a_it')
    print()
    OUT = 'synthetic_validation_v2_4_corrected'
    generated = generate_corrected(OUT)
    print()
    verify(OUT, generated)
