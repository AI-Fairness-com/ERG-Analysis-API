"""Chapter 15: Normative data, transference and serial change.

Code from Chapter 15 of "Hands-On Electroretinography in the Age of
AI", in the order of the book: the transference checks (verification
of published limits, electrode conversion) and the NormativeReference
class (Traffic Light zones and change detection with the coefficient
of repeatability). A short demonstration runs at the end; it uses the
ReferenceLimits class of chapters/ch10/chapter_10.py.
"""

# Transference checks (Section 15.3)
import numpy as np


def verify_limits(values, lower, upper, max_outside=0.10, min_n=20):
    """
    Check that published limits suit local healthy people.
    values: one parameter in local healthy subjects; lower, upper:
    the source limits; max_outside: share allowed outside them;
    min_n: the smallest local sample accepted.
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < min_n:
        raise ValueError(
            f'{len(values)} subjects provided, {min_n} required.')
    outside = float(np.mean((values < lower) | (values > upper)))
    return {
        'n_subjects': int(len(values)),
        'proportion_outside': round(outside, 3),
        'status': 'PASS' if outside < max_outside else 'FAIL',
    }


def fit_electrode_conversion(source, target, min_r2=0.7,
                             simple_r2=0.95):
    """
    Fit the straight-line conversion from one electrode to another.
    source, target: paired values of one parameter, recorded with
    both electrodes in the same subjects. Simple linear regression
    is used when r2 >= simple_r2; otherwise Deming regression,
    which allows for error in both electrodes.
    """
    x = np.asarray(source, dtype=float)
    y = np.asarray(target, dtype=float)
    keep = ~(np.isnan(x) | np.isnan(y))
    x, y = x[keep], y[keep]
    if len(x) < 3:
        raise ValueError('At least 3 paired recordings are required.')
    r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
    if r2 >= simple_r2:
        method = 'simple linear'
        slope, intercept = np.polyfit(x, y, 1)
    else:
        method = 'Deming'
        sxx = np.var(x, ddof=1)
        syy = np.var(y, ddof=1)
        sxy = np.cov(x, y, ddof=1)[0, 1]
        root = np.sqrt((syy - sxx) ** 2 + 4 * sxy ** 2)
        slope = (syy - sxx + root) / (2 * sxy)
        intercept = y.mean() - slope * x.mean()
    return {
        'n_pairs': int(len(x)),
        'method': method,
        'slope': round(float(slope), 4),
        'intercept': round(float(intercept), 3),
        'r_squared': round(r2, 3),
        'status': 'ACCEPT' if r2 >= min_r2 else 'REJECT',
    }


def convert_values(values, slope, intercept):
    """Convert values from the source to the target electrode."""
    return slope * np.asarray(values, dtype=float) + intercept

# NormativeReference: reference limits and change detection
import numpy as np


class NormativeReference:
    """
    Single interface between the ERG feature vector and the report
    layers. limits: a ReferenceLimits object (Chapter 10, Section
    10.4) holding the Baker et al. (2025) percentile limits.
    cor: dict mapping (electrode, protocol, parameter) to the
    coefficient of repeatability, in log10 units for amplitudes and
    in milliseconds for implicit times.
    """

    AGE_GROUPS = ('le35', '36to59', 'ge60')

    def __init__(self, limits, cor=None):
        self.limits = limits
        self.cor = dict(cor or {})

    @staticmethod
    def age_group(age):
        """Return the Baker et al. (2025) age group for an age."""
        if age < 0:
            raise ValueError('Age must not be negative.')
        if age <= 35:
            return 'le35'
        if age < 60:
            return '36to59'
        return 'ge60'

    def classify(self, x, age, electrode, protocol, parameter):
        """Assign a Traffic Light zone to one measurement."""
        group = self.age_group(age)
        result = self.limits.classify(x, electrode, protocol, group,
                                      parameter)
        result['age_group'] = group
        return result

    def compare(self, x_prior, x_current, age, electrode, protocol,
                parameter):
        """
        Compare two serial recordings with the CoR (Section 15.5).
        Amplitudes are compared on the log10 scale and reported as
        percent change; implicit times are compared in milliseconds.
        """
        key = (electrode, protocol, parameter)
        if key not in self.cor:
            raise KeyError(f'No CoR registered for {key}.')
        cor = float(self.cor[key])
        group = self.age_group(age)
        kind = self.limits.get_limits(electrode, protocol, group,
                                      parameter)['kind']
        if kind == 'amplitude':
            if x_prior <= 0 or x_current <= 0:
                raise ValueError('Amplitudes must be positive.')
            change = float(np.log10(x_current / x_prior))
            percent = round((10 ** change - 1) * 100, 1)
            worse = change < 0
            bounds = ((10 ** -cor - 1) * 100, (10 ** cor - 1) * 100)
        else:
            change = float(x_current - x_prior)
            percent = None
            worse = change > 0
            bounds = (-cor, cor)
        if abs(change) < cor:
            zone = 'NO_CHANGE'
        elif worse:
            zone = 'SIGNIFICANT_PROGRESSION'
        else:
            zone = 'SIGNIFICANT_IMPROVEMENT'
        return {
            'parameter': parameter,
            'kind': kind,
            'change': round(change, 4),
            'percent_change': percent,
            'cor': cor,
            'cor_bounds': tuple(round(b, 1) for b in bounds),
            'change_zone': zone,
        }

    @staticmethod
    def annual_percent_change(x_prior, x_current, years):
        """
        Average yearly change in an amplitude, as a percent of the
        remaining amplitude, for comparison with published rates.
        """
        if x_prior <= 0 or x_current <= 0 or years <= 0:
            raise ValueError('Amplitudes and years must be positive.')
        rate = (x_current / x_prior) ** (1 / years) - 1
        return round(rate * 100, 1)


# ── Demonstration ────────────────────────────────────────────────────
# Runs each function once. The reference limits are the Baker et al.
# (2025) values in data/samples/normative_data_baker2025.json, read into
# the ReferenceLimits class of Chapter 10. The CoR is the Knickelbein
# et al. (2021) example of Table 15.3. Healthy and paired values are
# simulated. Run from the repository root or from chapters/ch15.
if __name__ == '__main__':
    import importlib.util
    import json
    import pandas as pd
    from pathlib import Path

    here = Path(__file__).resolve().parent
    root = here.parents[1]
    spec = importlib.util.spec_from_file_location(
        'chapter_10', root / 'chapters' / 'ch10' / 'chapter_10.py')
    ch10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch10)

    norm = json.loads((root / 'data' / 'samples' /
                       'normative_data_baker2025.json').read_text())
    rows = []
    for protocol, params in norm['limits'].items():
        for parameter, groups in params.items():
            for group, v in groups.items():
                rows.append({
                    'electrode': 'dtl', 'protocol': protocol,
                    'age_group': group, 'parameter': parameter,
                    'kind': norm['parameters'][parameter]['kind'],
                    'lower': v['lower'],
                    'lower_ci_low': v['lower_ci'][0],
                    'lower_ci_high': v['lower_ci'][1],
                    'upper': v['upper'],
                    'upper_ci_low': v['upper_ci'][0],
                    'upper_ci_high': v['upper_ci'][1]})
    limits = ch10.ReferenceLimits(pd.DataFrame(rows))

    rng = np.random.default_rng(42)
    # Transference: 30 simulated local healthy subjects, DA 3.0 b-wave
    lim = limits.get_limits('dtl', 'DA 3.0', '36to59', 'b_amp')
    local = rng.normal(270, 45, 30)
    print('Verification:', verify_limits(local, lim['lower'],
                                         lim['upper']))
    # Cross-electrode conversion from 25 simulated paired recordings
    gold = rng.normal(250, 50, 25)
    silver = 0.8 * gold + 10 + rng.normal(0, 8, 25)
    conv = fit_electrode_conversion(gold, silver)
    print('Conversion:', conv)
    print('Gold foil 240 uV as silver thread:',
          round(float(convert_values(240, conv['slope'],
                                     conv['intercept'])), 1), 'uV')

    # Zone and serial change for a 45-year-old, DA 3.0 b-wave amplitude
    ref = NormativeReference(limits,
                             cor={('dtl', 'DA 3.0', 'b_amp'): 0.216})
    print(ref.classify(150.0, 45, 'dtl', 'DA 3.0', 'b_amp'))
    for current in (140.0, 100.0, 300.0):
        r = ref.compare(180.0, current, 45, 'dtl', 'DA 3.0', 'b_amp')
        print(f"180 -> {current:.0f} uV: {r['percent_change']}% "
              f"{r['change_zone']}  (CoR bounds {r['cor_bounds']}%)")
    print('Annual change:',
          NormativeReference.annual_percent_change(180, 100, 3), '%')
