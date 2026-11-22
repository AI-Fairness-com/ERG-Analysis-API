"""Synthetic CSV generator for the internal validation of ERG Analysis API v2.5.0.

Writes Standardized ERG CSV files (Appendix A) and a manifest of the
results the book's rules require for each file. The expected zones are
worked out here from the Baker et al. (2025) limits in
data/samples/normative_data_baker2025.json with Equation 10.2 of
Chapter 10, independently of the pipeline code.

Usage (from the repository root):
    python synthetic_validation/ERG_CSV_Generator_v2_5_0.py
Output: synthetic_validation/v2_5_0/csv/*.csv and manifest.json

All recordings are simulated. They test the code and say nothing about
any patient.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'synthetic_validation' / 'v2_5_0'
NORM = json.loads((ROOT / 'data' / 'samples' /
                   'normative_data_baker2025.json').read_text())
LIMITS, TRANSFORM = NORM['limits'], NORM['electrode_transform']['transform']

FS = 2000.0            # Hz (Chapter 5: 2000 Hz)
PRESTIM_MS = 100.0     # flash 100 ms into each file (Chapter 3)
POST_MS = 400.0
PROTOCOLS = ['DA 0.01', 'DA 3.0', 'DA 10.0', 'LA 3.0', 'LA 30 Hz']
STRATA = {'le35': '≤35y', '36to59': '36-59y', 'ge60': '≥60y'}
ELECTRODE_CSV = {'dtl_fiber': 'DTL_fiber', 'gold_foil': 'gold_foil',
                 'contact_lens': 'contact_lens', 'skin': 'skin'}
# Chapter 2, Table 2.3: Pass at or above, Fail below
SNR_TABLE = {'contact_lens': (8.0, 4.0), 'gold_foil': (6.0, 3.0),
             'dtl_fiber': (4.0, 2.5), 'skin': (3.0, 2.0)}
ZONE_RANK = {'GREEN': 0, 'ATYPICAL DIRECTION': 1, 'AMBER': 2, 'RED': 3}
COLOURS = set(ZONE_RANK)
HAS_A = {'DA 3.0', 'DA 10.0', 'LA 3.0'}
RESOLUTION_MS = 1000.0 / FS          # 0.5 ms


# ── Book rule (Chapter 10, Equation 10.2) ────────────────────────────────
def limits(protocol, param, stratum):
    v = LIMITS[protocol][param][stratum]
    return v['lower'], v['lower_ci'][0], v['upper'], v['upper_ci'][1]


def zone(protocol, param, stratum, x):
    L, L_lo, U, U_hi = limits(protocol, param, stratum)
    if param.endswith('amp'):
        if x > U:
            return 'ATYPICAL DIRECTION'
        return 'GREEN' if x >= L else ('AMBER' if x >= L_lo else 'RED')
    if x < L:
        return 'ATYPICAL DIRECTION'
    return 'GREEN' if x <= U else ('AMBER' if x <= U_hi else 'RED')


def target(protocol, param, stratum, want):
    """A value well inside the wanted zone, or None if the zone is too
    narrow to hit from a waveform (it is then covered by unit tests)."""
    L, L_lo, U, U_hi = limits(protocol, param, stratum)
    amp = param.endswith('amp')
    if want == 'GREEN':
        v = (L + U) / 2
    elif want == 'ATYPICAL DIRECTION':
        v = U * 1.25 if amp else L - max(2.0, 0.15 * L)
    elif want == 'AMBER':
        lo, hi = (L_lo, L) if amp else (U, U_hi)
        width = hi - lo
        if (amp and width < max(4.0, 0.06 * L)) or (not amp and width < 2.0):
            return None
        v = (lo + hi) / 2
    else:  # RED
        v = L_lo * 0.6 if amp else U_hi + max(3.0, 0.08 * U_hi)
    if not amp:
        v = round(v / RESOLUTION_MS) * RESOLUTION_MS
    return round(v, 1)


def to_gold_foil(protocol, param, st_value):
    t = TRANSFORM[protocol][param]
    return round((st_value - t['intercept']) / t['slope'], 1)


# ── Waveforms ────────────────────────────────────────────────────────────
def _rise(t, t0, t1, y0, y1):
    """From (t0, y0) to (t1, y1): slow start, steep finish, so the end
    point is a sharp extremum that noise and filtering cannot move."""
    s = np.clip((t - t0) / (t1 - t0), 0, 1)
    return y0 + (y1 - y0) * (1 - np.cos(np.pi * s / 2))


def transient(t, a_amp, a_time, b_amp, b_time):
    """Flash ERG with a-wave trough -a_amp at a_time and b-wave peak
    b_amp above the trough at b_time (times in ms from the flash)."""
    y = np.zeros_like(t)
    if a_amp:
        on = max(a_time * 0.35, 2.0)
        peak = b_amp - a_amp
        y = np.where((t >= on) & (t < a_time),
                     _rise(t, on, a_time, 0.0, -a_amp), y)
        y = np.where((t >= a_time) & (t < b_time),
                     -a_amp + (peak + a_amp) * np.clip(
                         (t - a_time) / (b_time - a_time), 0, 1), y)
    else:
        on = b_time * 0.35
        peak = b_amp
        y = np.where((t >= on) & (t < b_time), _rise(t, on, b_time, 0.0, peak), y)
    tail = t >= b_time
    tau = 0.6 * b_time + 15
    y = np.where(tail, peak * np.exp(-(t - b_time) / tau), y)
    return y


def flicker(t, amp, latency, hz=30.0):
    """Steady-state 30 Hz flicker: trough-to-peak amp, peak at latency."""
    cycle = 1000.0 / hz
    y = (amp / 2) * np.cos(2 * np.pi * (t - latency) / cycle)
    return np.where(t >= 0, y * np.clip(t / 40.0, 0, 1), 0.0)


def measure_clean(t, y, protocol):
    """True values of the noise-free waveform, by the book's definitions:
    a-wave baseline to trough, b-wave trough to peak (ISCEV 2022), times
    from the flash; flicker trough to peak of a steady-state cycle."""
    out = {}
    if protocol == 'LA 30 Hz':
        cycle = 1000.0 / 30.0
        m = (t >= 300) & (t < 300 + cycle)
        out['b_amp'] = round(float(y[m].max() - y[m].min()), 1)
        out['b_imp'] = round(float(t[m][np.argmax(y[m])] % cycle), 1)
        return out
    if protocol in HAS_A:
        m = (t >= 5) & (t <= 40)
        i = int(np.argmin(y[m]))
        out['a_amp'] = round(float(-y[m][i]), 1)
        out['a_imp'] = round(float(t[m][i]), 1)
        ref, start = float(y[m][i]), float(t[m][i])
    else:
        ref, start = 0.0, 20.0
    m = (t >= start) & (t <= 150)
    j = int(np.argmax(y[m]))
    out['b_amp'] = round(float(y[m][j] - ref), 1)
    out['b_imp'] = round(float(t[m][j]), 1)
    return out


def make_csv(name, protocol, electrode, values, snr=80.0, seed=0,
             invert=False, mains_uv=0.0, flash_shift_ms=0.0, csv_electrode=None):
    """Write one CSV; return its file name and the true values measured
    on the noise-free waveform (these, not the targets, set the expected
    zones)."""
    rng = np.random.default_rng(seed)
    t_file = np.arange(0, PRESTIM_MS + POST_MS, 1000.0 / FS)
    t = t_file - PRESTIM_MS - flash_shift_ms
    def build(v):
        if protocol == 'LA 30 Hz':
            return flicker(t, v['b_amp'], v['b_imp'])
        y = transient(t, v.get('a_amp', 0.0), v.get('a_imp', 0.0),
                      v['b_amp'], v['b_imp'])
        return gaussian_filter1d(y, sigma=1.0 * FS / 1000.0)

    # Smoothing moves the extremes a little; correct the inputs so the
    # noise-free waveform lands on the target values.
    v_in = dict(values)
    for _ in range(4):
        clean = build(v_in)
        true = measure_clean(t, clean, protocol)
        for p, want in values.items():
            if p.endswith('imp'):
                v_in[p] += want - true[p]
            else:
                v_in[p] *= want / true[p] if true[p] else 1.0
    noise_rms = values['b_amp'] / snr
    sig = clean + rng.normal(0, noise_rms, t.size)
    if mains_uv:
        sig = sig + mains_uv * np.sin(2 * np.pi * 50.0 * t_file / 1000.0)
    if invert:
        sig = -sig
    df = pd.DataFrame({
        'time_ms': np.round(t_file, 2), 'amplitude_uV': np.round(sig, 3),
        'protocol': protocol, 'eye': 'OD',
        'electrode_type': (ELECTRODE_CSV.get(electrode, '')
                           if csv_electrode is None else csv_electrode),
        'patient_id': 'SYN-' + name})
    path = OUT / 'csv' / f'{name}.csv'
    df.to_csv(path, index=False)
    return path.name, true


# ── Cases ────────────────────────────────────────────────────────────────
def params(protocol):
    return (['a_amp', 'a_imp', 'b_amp', 'b_imp'] if protocol in HAS_A
            else ['b_amp', 'b_imp'])


def zone_case(protocol, stratum, want):
    """Values and expected zones for one protocol and age group."""
    values, expected, skipped = {}, {}, []
    for p in params(protocol):
        v = target(protocol, p, stratum, want)
        if v is None:
            skipped.append(p)
            v = target(protocol, p, stratum, 'GREEN')
        values[p] = v
        expected[p] = zone(protocol, p, stratum, v)
    return values, expected, skipped


def composite(zones):
    zs = [z for z in zones.values() if z in COLOURS]
    return max(zs, key=ZONE_RANK.get) if zs else 'UNAVAILABLE'


def main():
    (OUT / 'csv').mkdir(parents=True, exist_ok=True)
    cases, seed = [], 100

    def add(case_id, group, protocol, electrode, stratum, values, expected,
            proves, form=None, expect=None, zoned=True, **kw):
        """expected: dict of parameters to check. With zoned=True the
        zones are recomputed from the true values (gold foil amplitudes
        converted first); other dicts are used as given."""
        nonlocal seed
        seed += 1
        csv, true = make_csv(case_id, protocol, electrode, values, seed=seed, **kw)
        if zoned and expected:
            expected = {}
            for p in params(protocol):
                x = true[p]
                if electrode == 'gold_foil' and p.endswith('amp') and TRANSFORM[protocol].get(p):
                    t = TRANSFORM[protocol][p]
                    x = round(t['slope'] * x + t['intercept'], 1)
                expected[p] = zone(protocol, p, stratum, x)
        cases.append({
            'id': case_id, 'group': group, 'file': csv, 'proves': proves,
            'form': {'protocol': protocol, 'age_group': STRATA[stratum],
                     'electrode_type': electrode,
                     'pre_stimulus_ms': str(PRESTIM_MS),
                     'flash_duration_ms': '1.0', **(form or {})},
            'true_values': true,
            'expected': {'zones': expected,
                         'composite': composite(expected) if expected else None,
                         **(expect or {})}})
        return expected

    tag = {'DA 0.01': 'DA001', 'DA 3.0': 'DA3', 'DA 10.0': 'DA10',
           'LA 3.0': 'LA3', 'LA 30 Hz': 'LA30'}

    # A. Normal baseline: 5 protocols x 3 age groups, DTL, all GREEN
    for pr in PROTOCOLS:
        for st in STRATA:
            v, e, _ = zone_case(pr, st, 'GREEN')
            add(f'A_{tag[pr]}_{st}_GREEN', 'A baseline', pr, 'dtl_fiber', st,
                v, e, f'{pr}, {STRATA[st]}: right limits chosen, all GREEN',
                expect={'snr_status': 'PASS'})

    # B. Zones at <=35y: AMBER, RED, ATYPICAL DIRECTION for each protocol
    for pr in PROTOCOLS:
        for want in ('AMBER', 'RED', 'ATYPICAL DIRECTION'):
            v, e, skipped = zone_case(pr, 'le35', want)
            note = (f' ({", ".join(skipped)} kept GREEN: zone narrower than '
                    'waveform resolution; covered by unit tests)'
                    if skipped else '')
            add(f'B_{tag[pr]}_le35_{want.split()[0]}', 'B zones', pr,
                'dtl_fiber', 'le35', v, e,
                f'{pr}: Equation 10.2 gives {want}{note}')

    # C. Gold foil: amplitudes converted with Baker Table 2 before zoning
    for pr in PROTOCOLS:
        v_st, e, _ = zone_case(pr, 'le35', 'GREEN')
        v_gf = dict(v_st)
        for p in ('a_amp', 'b_amp'):
            if p in v_gf and TRANSFORM[pr].get(p):
                v_gf[p] = to_gold_foil(pr, p, v_st[p])
        add(f'C_{tag[pr]}_le35_goldfoil', 'C gold foil', pr, 'gold_foil',
            'le35', v_gf, e,
            f'{pr}: gold foil amplitude converted to the silver thread '
            'value before zoning (GREEN)')
    # one case where the conversion changes the zone
    pr, st = 'DA 3.0', 'le35'
    v_st, _, _ = zone_case(pr, st, 'GREEN')
    L, L_lo, U, U_hi = limits(pr, 'b_amp', st)
    st_b = round((L_lo + L) / 2, 1)                 # AMBER after conversion
    gf_b = to_gold_foil(pr, 'b_amp', st_b)
    La, _, Ua, _ = limits(pr, 'a_amp', st)
    st_a = round(La + 0.2 * (Ua - La), 1)
    v_gf = dict(v_st, b_amp=gf_b, a_amp=to_gold_foil(pr, 'a_amp', st_a))
    e = {p: zone(pr, p, st, x) for p, x in
         dict(v_st, b_amp=st_b, a_amp=st_a).items()}
    add('C_DA3_le35_goldfoil_changes_zone', 'C gold foil', pr, 'gold_foil', st,
        v_gf, e, f'DA 3.0 b-wave {gf_b} µV gold foil is GREEN as a raw value '
        f'({zone(pr, "b_amp", st, gf_b)}) but {st_b} µV silver thread '
        'equivalent is AMBER: conversion must happen before zoning')

    # D. Contact lens and skin: no limits held, zones UNAVAILABLE
    for el in ('contact_lens', 'skin'):
        v, _, _ = zone_case('DA 3.0', 'le35', 'GREEN')
        add(f'D_DA3_le35_{el}', 'D no limits', 'DA 3.0', el, 'le35', v,
            {p: 'UNAVAILABLE' for p in params('DA 3.0')},
            f'{el}: no reference limits held, Traffic Light UNAVAILABLE',
            expect={'composite': 'UNAVAILABLE', 'snr_status': 'PASS'},
            zoned=False)

    # E. Signal quality: Warning and Fail SNR for each electrode (DA 3.0)
    for el, (pass_at, fail_below) in SNR_TABLE.items():
        for status, snr in (('WARNING', (pass_at + fail_below) / 2),
                            ('FAIL', fail_below * 0.6)):
            v, e, _ = zone_case('DA 3.0', 'le35', 'GREEN')
            exp = {'snr_band': status, 'snr_electrode': el}
            if status == 'FAIL':
                exp['traffic_light_withheld'] = True    # Chapter 2 §2.5
            add(f'E_DA3_le35_{el}_{status}', 'E signal quality', 'DA 3.0', el,
                'le35', v, {}, f'{el}: SNR {snr:.1f} gives {status} '
                f'(Pass ≥ {pass_at}, Fail < {fail_below}); a Fail recording '
                'gets no Traffic Light' if status == 'FAIL' else
                f'{el}: SNR {snr:.1f} gives {status} (Pass ≥ {pass_at}, '
                f'Fail < {fail_below})', snr=snr, expect=exp)

    # F. Safe failure and special recordings
    v, e, _ = zone_case('DA 3.0', 'le35', 'GREEN')
    add('F_DA3_blank_electrode', 'F special', 'DA 3.0', 'dtl_fiber', 'le35',
        v, {}, 'Electrode blank on the form and in the CSV: HALT with '
        'ELECTRODE_UNKNOWN before any processing (Chapter 19 §19.9.2)',
        form={'electrode_type': ''}, csv_electrode='',
        expect={'http_status': 400, 'error': 'ELECTRODE_UNKNOWN'})
    add('F_DA3_electrode_from_csv', 'F special', 'DA 3.0', 'dtl_fiber',
        'le35', v, e, 'Electrode blank on the form but given in the CSV: '
        'read from the CSV (Appendix A), normal GREEN report',
        form={'electrode_type': ''})
    add('F_DA3_inverted_polarity', 'F special', 'DA 3.0', 'dtl_fiber', 'le35',
        v, e, 'Recording stored upside down: polarity check flips it, '
        'zones as normal', invert=True,
        expect={'inverted_polarity_detected': True})
    add('F_DA3_mains_50Hz_no_notch', 'F special', 'DA 3.0', 'dtl_fiber',
        'le35', v, {}, '50 Hz hum present: detected and reported; no notch '
        'filter without the user\'s consent (Chapter 5). Zones not checked: '
        'uncorrected hum is expected to disturb the timing', mains_uv=15.0,
        expect={'mains_detected': True})
    add('F_DA3_mains_50Hz_notch_consent', 'F special', 'DA 3.0', 'dtl_fiber',
        'le35', v, e, '50 Hz hum with notch requested and consented: notch '
        'applied and logged', mains_uv=15.0,
        form={'apply_notch': 'true', 'notch_consent': 'true'},
        expect={'mains_detected': True})
    add('F_DA3_long_flash_4ms', 'F special', 'DA 3.0', 'dtl_fiber', 'le35',
        v, e, '4 ms flash: implicit times measured from the flash midpoint '
        '(Chapter 9 §9.1.1), so the zones match the true times',
        form={'flash_duration_ms': '4.0'}, flash_shift_ms=2.0)

    manifest = {'generator': 'ERG_CSV_Generator_v2_5_0.py',
                'pipeline_target': '2.5.0',
                'normative_source': NORM['citation'] if 'citation' in NORM else 'Baker et al. (2025)',
                'n_files': len(cases), 'cases': cases}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1,
                                                  ensure_ascii=False))
    print(f'{len(cases)} CSV files and manifest.json written to {OUT}')


if __name__ == '__main__':
    main()
