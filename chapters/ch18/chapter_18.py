"""Chapter 18: Longitudinal monitoring of a patient's ERG record.

Code from Chapter 18 of "Hands-On Electroretinography in the Age of
AI": the LongitudinalPatientRecord class of Section 18.5. It imports
the mixed-effects model (longitudinal_lme.py) and the difference plot
(difference_plot.py) from this folder, and the version comparison
from chapters/ch17/chapter_17.py. A short demonstration on simulated
visits runs at the end. Outputs go to ./outputs/longitudinal.
"""
# Make this folder and chapters/ch17 importable
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(_HERE), str(_HERE.parent / 'ch17')]

# LongitudinalPatientRecord class (Section 18.5)
import json
import os

import pandas as pd

from chapter_17 import compare_version_stamps   # Section 17.3.3
from longitudinal_lme import fit_longitudinal_lme, predict_next_visit
from difference_plot import plot_difference_plot

# Severity order of the four Chapter 17 flags, least to most severe.
FLAG_ORDER = ["VERSION_IDENTICAL", "VERSION_PATCH_CHANGE",
              "VERSION_MINOR_CHANGE", "VERSION_MAJOR_CHANGE"]

# Published mean annual change in the RP cone 30 Hz flicker
# amplitude (%).
PUBLISHED_RP_RATES = {
    "Berson (2007), untreated": -10.0,
    "Sandberg et al. (2008), USH2A": -13.2,
}


class LongitudinalPatientRecord:
    """
    A patient's recording history and the longitudinal methods of
    Chapter 18. Each archive file is the Layer 4 audit record of one
    visit: recording_date, version_stamp, signal_quality, snr,
    snr_threshold, and one numeric field per ERG parameter.
    """

    def __init__(self, patient_id: str, archive_dir: str, norm_ref):
        self.patient_id = patient_id
        self.norm_ref = norm_ref         # NormativeReference, Ch. 15
        self.history = self._load_archive(archive_dir)

    def _load_archive(self, archive_dir: str) -> pd.DataFrame:
        folder = os.path.join(archive_dir, self.patient_id)
        if not os.path.isdir(folder):
            return pd.DataFrame()
        records = []
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                with open(os.path.join(folder, name)) as f:
                    records.append(json.load(f))
        df = pd.DataFrame(records)
        if not df.empty:
            df["recording_date"] = pd.to_datetime(
                df["recording_date"])
            df = df.sort_values("recording_date")
            df = df.reset_index(drop=True)
        return df

    def usable_history(self):
        """Return (usable visits, exclusion notes) after the signal
        quality check of Chapter 2."""
        if self.history.empty:
            return self.history, []
        bad = self.history["signal_quality"] == "FAIL"
        notes = [f"Visit {r.recording_date:%Y-%m-%d}: excluded from "
                 f"progression analysis (signal quality failure, "
                 f"SNR {r.snr}, threshold {r.snr_threshold})."
                 for r in self.history[bad].itertuples()]
        return self.history[~bad].reset_index(drop=True), notes

    def check_version_stamps(self, current_stamp: dict) -> dict:
        """Compare the new stamp with every archived stamp
        (Section 18.5.1)."""
        if self.history.empty:
            return {"overall_flag": "NO_PRIOR_REPORTS",
                    "per_visit": []}
        per_visit = []
        for row in self.history.itertuples():
            result = compare_version_stamps(row.version_stamp,
                                            current_stamp)
            per_visit.append({
                "visit": f"{row.recording_date:%Y-%m-%d}",
                "flag": result["flag"]})
        worst = max((v["flag"] for v in per_visit),
                    key=FLAG_ORDER.index)
        return {"overall_flag": worst, "per_visit": per_visit}

    def _has_cor(self, electrode, protocol, param):
        return (electrode, protocol, param) in self.norm_ref.cor

    def apply_cor_flags(self, current_values: dict, age: float,
                        electrode: str, protocol: str) -> dict:
        """Flag each parameter that has a Chapter 15 CoR against the
        previous usable visit (Section 18.3.1). Parameters without a
        CoR, such as the PhNR amplitude, are not flagged."""
        usable, _ = self.usable_history()
        if usable.empty:
            return {}
        previous = usable.iloc[-1]
        flags = {}
        for param, value in current_values.items():
            if not self._has_cor(electrode, protocol, param):
                continue
            if pd.isna(previous.get(param)):
                continue
            flags[param] = self.norm_ref.compare(
                float(previous[param]), float(value), age,
                electrode, protocol, param)
        return flags

    def observed_annual_change(self, param: str,
                               current_value: float,
                               current_date: str):
        """Observed yearly change in an amplitude (%), first usable
        visit to the new visit, for comparison with published
        rates."""
        usable, _ = self.usable_history()
        if usable.empty:
            return None
        start = usable["recording_date"].iloc[0]
        years = (pd.Timestamp(current_date) - start).days / 365.25
        return self.norm_ref.annual_percent_change(
            float(usable[param].iloc[0]), current_value, years)

    def difference_plots(self, current_values: dict,
                         current_date: str, age: float,
                         electrode: str, protocol: str) -> dict:
        """Difference plot for every parameter with a Chapter 15 CoR
        and at least three usable values (Section 18.5.3)."""
        usable, _ = self.usable_history()
        group = self.norm_ref.age_group(age)
        plots = {}
        for param, value in current_values.items():
            if not self._has_cor(electrode, protocol, param):
                continue
            if param not in usable or len(usable) < 2:
                continue
            kind = self.norm_ref.limits.get_limits(
                electrode, protocol, group, param)["kind"]
            past = usable[["recording_date", param]].dropna()
            visits = pd.concat([
                past.set_axis(["date", "value"], axis=1),
                pd.DataFrame({"date": [pd.Timestamp(current_date)],
                              "value": [value]})],
                ignore_index=True)
            if len(visits) < 3:
                continue
            cor = self.norm_ref.cor[(electrode, protocol, param)]
            plots[param] = plot_difference_plot(
                visits, cor, kind, param, self.patient_id)
        return plots

    def generate_progression_summary(
            self, current_values: dict, current_stamp: dict,
            current_date: str, age: float, electrode: str,
            protocol: str, rp_parameter: str = None,
            cohort: pd.DataFrame = None,
            next_visit_years: float = None) -> dict:
        """Assemble the six parts of the Layer 3 progression
        summary (Section 18.5.4). rp_parameter names the 30 Hz
        flicker amplitude when the diagnosis is retinitis
        pigmentosa."""
        usable, notes = self.usable_history()
        summary = {
            "patient_id": self.patient_id,
            "n_prior_visits": len(usable),
            "exclusions": notes,
            "version_check": self.check_version_stamps(
                current_stamp),
            "visit_pair_flags": self.apply_cor_flags(
                current_values, age, electrode, protocol),
            "observed_annual_change_pct": None,
            "published_rates_pct": None,
            "trajectory": None,
            "difference_plots": self.difference_plots(
                current_values, current_date, age, electrode,
                protocol),
        }
        has_rp = rp_parameter in current_values
        if has_rp and len(usable) >= 1:
            summary["observed_annual_change_pct"] = \
                self.observed_annual_change(
                    rp_parameter, current_values[rp_parameter],
                    current_date)
            summary["published_rates_pct"] = PUBLISHED_RP_RATES
        if cohort is not None and has_rp:
            fit = fit_longitudinal_lme(cohort, rp_parameter)
            mine = fit["patients"].get(self.patient_id)
            if mine is not None:
                trajectory = {
                    "slope_pct_per_year": mine["slope_pct_per_year"],
                    "slope_ci95_pct": mine["slope_ci95_pct"],
                    "n_visits": len(usable) + 1,
                }
                if next_visit_years is not None:
                    trajectory["next_visit"] = predict_next_visit(
                        fit, self.patient_id, next_visit_years)
                summary["trajectory"] = trajectory
        return summary


# ── Demonstration on simulated visits ────────────────────────────────
# A patient with retinitis pigmentosa has four archived visits (one
# failed the signal quality check) and a new visit today. The limits
# are the Baker et al. (2025) values read into the Chapter 10 class;
# the CoR values are illustrative, not published figures for the
# 30 Hz flicker. The cohort for the mixed-effects model is simulated.
if __name__ == '__main__':
    import importlib.util
    import tempfile

    import numpy as np

    root = _HERE.parents[1]

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ch10 = load('chapter_10', root / 'chapters/ch10/chapter_10.py')
    ch15 = load('chapter_15', root / 'chapters/ch15/chapter_15.py')
    norm = json.loads((root / 'data/samples/'
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
    ref = ch15.NormativeReference(
        ch10.ReferenceLimits(pd.DataFrame(rows)),
        cor={('dtl', 'LA 30 Hz', 'b_amp'): 0.10,
             ('dtl', 'LA 30 Hz', 'b_imp'): 2.0})

    stamp = {'api_version': '1.0.0', 'model_weights_hash': 'aaa',
             'config_hash': 'bbb', 'normative_ref_version': 'Baker2025_v1'}
    archive = Path(tempfile.mkdtemp()) / 'P001'
    archive.mkdir()
    for date, amp, imp, quality in [('2022-03-01', 60.0, 30.0, 'PASS'),
                                    ('2023-03-01', 54.0, 30.5, 'PASS'),
                                    ('2023-09-01', 30.0, 31.0, 'FAIL'),
                                    ('2024-03-01', 48.0, 31.0, 'PASS')]:
        (archive / f'{date}.json').write_text(json.dumps({
            'recording_date': date, 'version_stamp': stamp,
            'signal_quality': quality, 'snr': 9.0 if quality == 'PASS'
            else 2.1, 'snr_threshold': 3.0,
            'b_amp': amp, 'b_imp': imp}))

    rng = np.random.default_rng(42)
    cohort = []
    # P001: its usable visits and today's visit; others simulated
    for t, amp in [(0.0, 60.0), (1.0, 54.0), (2.0, 48.0), (3.0, 42.0)]:
        cohort.append({'patient_id': 'P001', 'time_years': t,
                       'amplitude_uv': amp})
    times = [0.0, 1.0, 2.0, 3.0]
    for i in range(1, 30):
        pid = f'C{i:03d}'
        start = 60 * np.exp(rng.normal(0, 0.3))
        slope = rng.normal(-0.11, 0.05)
        for t in times:
            cohort.append({'patient_id': pid, 'time_years': t,
                           'amplitude_uv': start * np.exp(
                               slope * t + rng.normal(0, 0.05))})
    cohort = pd.DataFrame(cohort)

    record = LongitudinalPatientRecord('P001', str(archive.parent), ref)
    summary = record.generate_progression_summary(
        current_values={'b_amp': 42.0, 'b_imp': 32.5},
        current_stamp=dict(stamp, api_version='1.0.1'),
        current_date='2025-03-01', age=45, electrode='dtl',
        protocol='LA 30 Hz', rp_parameter='b_amp', cohort=cohort,
        next_visit_years=4.0)
    print(json.dumps(summary, indent=2, default=str))
