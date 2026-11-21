# Chapter 10: labels, class imbalance, normalization, reference limits,
# and data splitting
# The code of Chapter 10, in the order of the book: inter-rater
# reliability (Cohen's kappa), SMOTE, patient-level stratified k-fold,
# device-relative amplitude normalization, the ReferenceLimits class
# with the Traffic Light rule of §10.4 (Equation 10.2), and the
# patient-level train/test split. The book's code defines the functions.
# The Baker et al. (2025) limits used by the API, with their 90%
# confidence intervals, are in data/samples/normative_data_baker2025.json.
# Run from the repository folder:  python chapters/ch10/chapter_10.py

from sklearn.metrics import cohen_kappa_score


def verify_inter_rater_reliability(labels_rater1: list,
                                   labels_rater2: list,
                                   min_kappa: float = 0.61) -> dict:
    """
    Compute Cohen's kappa between two raters on the same recordings.

    Raises ValueError if the two label lists differ in length or are
    empty, or if kappa is below the minimum or cannot be computed
    (for example, when both raters used one identical label).
    """
    n_total = len(labels_rater1)
    if n_total != len(labels_rater2):
        raise ValueError(
            f'Rater label lists differ in length '
            f'({n_total} vs {len(labels_rater2)}).'
        )
    if n_total == 0:
        raise ValueError('No labels supplied for inter-rater '
                         'reliability.')

    kappa = cohen_kappa_score(labels_rater1, labels_rater2)
    agreed = sum(a == b for a, b in zip(labels_rater1, labels_rater2))
    p_obs = agreed / n_total

    print('Inter-rater reliability')
    print(f'  Recordings assessed : {n_total}')
    print(f'  P_observed          : {p_obs:.3f}  '
          f'({agreed}/{n_total} agreed)')
    print(f"  Cohen's kappa       : {kappa:.3f}")
    print(f'  Minimum required    : {min_kappa:.2f}')

    # "not >=" also catches NaN, which "<" would let through.
    if not kappa >= min_kappa:
        raise ValueError(
            f'Kappa {kappa:.3f} does not meet the minimum threshold '
            f'{min_kappa:.2f}. Review the labeling protocol and '
            f'relabel before training.'
        )
    print('  Status: PASS -- training may proceed.')
    return {'kappa': kappa, 'p_observed': p_obs,
            'n_assessed': n_total}

import numpy as np
from sklearn.model_selection import StratifiedKFold
from imblearn.over_sampling import SMOTE, SMOTENC


def apply_smote(X_train: np.ndarray,
                y_train: np.ndarray,
                categorical_feature_indices: list = None,
                k_neighbors: int = 5,
                random_state: int = 42) -> tuple:
    """
    Apply SMOTE or SMOTE-NC to the training partition only.
    Returns the resampled (X_resampled, y_resampled).
    """
    # Use SMOTE-NC when any categorical features are present.
    if categorical_feature_indices:
        sampler = SMOTENC(
            categorical_features=categorical_feature_indices,
            k_neighbors=k_neighbors,
            random_state=random_state)
        n_cat = len(categorical_feature_indices)
        print(f'Applying SMOTE-NC ({n_cat} categorical features)')
    else:
        sampler = SMOTE(k_neighbors=k_neighbors,
                        random_state=random_state)
        print('Applying standard SMOTE (all numerical features)')

    labels, counts = np.unique(y_train, return_counts=True)
    counts_before = {str(k): int(n) for k, n in zip(labels, counts)}
    smallest = min(counts_before.values())
    if smallest <= k_neighbors:
        raise ValueError(
            f'The smallest class has {smallest} training '
            f'recordings; SMOTE needs more than k_neighbors '
            f'({k_neighbors}). Collect more recordings or lower '
            f'k_neighbors.'
        )
    X_res, y_res = sampler.fit_resample(X_train, y_train)
    labels, counts = np.unique(y_res, return_counts=True)
    counts_after = {str(k): int(n) for k, n in zip(labels, counts)}

    print('Class distribution before SMOTE:', counts_before)
    print('Class distribution after SMOTE: ', counts_after)
    return X_res, y_res


def stratified_kfold_split(X: np.ndarray,
                           y: np.ndarray,
                           patient_ids: np.ndarray,
                           confidence: np.ndarray = None,
                           n_splits: int = 5,
                           random_state: int = 42):
    """
    Stratified k-fold iterator with patient-level integrity.
    Yields (fold, train_idx, val_idx) for each fold. All recordings
    from one patient appear in exactly one fold.

    confidence : optional array with 'High' or 'Standard' for each
        recording (Section 10.1.3). Training folds keep both levels;
        validation folds keep High Confidence recordings only.
    """
    if confidence is not None:
        confidence = np.asarray(confidence)
        if len(confidence) != len(y):
            raise ValueError('confidence must have one entry per '
                             'recording.')

    # One label per patient. All recordings of a patient must share
    # one class label (§10.1.4); recordings with changed labels are
    # excluded as Uncertain before this function is called.
    unique_patients = np.unique(patient_ids)
    patient_labels = np.array([
        y[patient_ids == pid][0] for pid in unique_patients
    ])

    # Refuse to split if any patient carries more than one label.
    for pid, label in zip(unique_patients, patient_labels):
        if np.any(y[patient_ids == pid] != label):
            raise ValueError(
                f'Patient {pid} has more than one class label; '
                f'resolve the label conflict before splitting.'
            )

    # Every class needs at least n_splits patients, or some folds
    # will contain no patient from that class.
    classes, n_per_class = np.unique(patient_labels,
                                     return_counts=True)
    for cls, n_pat in zip(classes, n_per_class):
        if n_pat < n_splits:
            raise ValueError(
                f'Class {cls} has {n_pat} patients, fewer than '
                f'n_splits ({n_splits}).'
            )

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                          random_state=random_state)
    splits = skf.split(unique_patients, patient_labels)

    for fold, (train_pt_idx, val_pt_idx) in enumerate(splits):
        train_patients = unique_patients[train_pt_idx]
        val_patients = unique_patients[val_pt_idx]

        train_idx = np.where(np.isin(patient_ids, train_patients))[0]
        val_idx = np.where(np.isin(patient_ids, val_patients))[0]

        # Validation folds keep High Confidence labels only.
        if confidence is not None:
            val_idx = val_idx[confidence[val_idx] == 'High']
            missing = set(classes) - set(y[val_idx])
            if missing:
                raise ValueError(
                    f'Fold {fold}: no High Confidence validation '
                    f'recording for class(es) '
                    f'{sorted(str(c) for c in missing)}.'
                )

        # Verify zero patient overlap between training and validation.
        overlap = (set(patient_ids[train_idx])
                   & set(patient_ids[val_idx]))
        assert not overlap, f'Fold {fold}: patient leak: {overlap}'

        yield fold, train_idx, val_idx

from typing import Optional

# Method 3 reference b-wave amplitudes (µV): a 150 µV contact lens
# scale times the dark-adapted ratios of Esakowitz, Kriss and
# Shawkat (1993): gold foil 56%, DTL 46%, skin 12% (Chapter 1).
PROJECT_REFERENCE_BWAVE = {
    'contact_lens': 150.0,
    'gold_foil':     84.0,
    'dtl':           69.0,
    'skin':          18.0,
}


def normalize_amplitude(a_measured: float,
                        method: int,
                        a_calibration: Optional[float] = None,
                        norm_mean: Optional[float] = None,
                        electrode_type: Optional[str] = 'dtl'
                        ) -> dict:
    """
    Apply device-relative normalization to one ERG amplitude.

    Parameters
    ----------
    a_measured     : measured amplitude in µV.
    method         : 1, 2, or 3 (see §10.3).
    a_calibration  : calibration signal amplitude in µV (Method 1).
    norm_mean      : laboratory normative central value in µV
                     (Method 2).
    electrode_type : 'contact_lens', 'gold_foil', 'dtl' or 'skin'
                     (Method 3).

    Returns
    -------
    dict with keys: normalized_value, method_used, method_note.
    """
    if method == 1:
        if a_calibration is None or a_calibration <= 0:
            raise ValueError('Method 1 requires a valid calibration '
                             'signal amplitude.')
        norm_val = a_measured / a_calibration
        note = 'Internal calibration signal (Method 1)'

    elif method == 2:
        if norm_mean is None or norm_mean <= 0:
            raise ValueError('Method 2 requires a valid normative '
                             'mean.')
        norm_val = a_measured / norm_mean
        note = 'Laboratory normative scaling (Method 2)'

    elif method == 3:
        key = electrode_type.lower() if electrode_type else None
        if key not in PROJECT_REFERENCE_BWAVE:
            raise ValueError(
                f'Method 3 requires electrode_type to be one of '
                f'{sorted(PROJECT_REFERENCE_BWAVE)}; '
                f'got {electrode_type!r}.'
            )
        norm_val = a_measured / PROJECT_REFERENCE_BWAVE[key]
        note = (f'Electrode-amplitude hierarchy (Method 3, fallback '
                f'with increased uncertainty, electrode={key})')

    else:
        raise ValueError(f'Unknown normalization method: {method}')

    return {
        'normalized_value': norm_val,
        'method_used':      method,
        'method_note':      note,
    }

import numpy as np
import pandas as pd


class ReferenceLimits:
    """
    Store published percentile reference limits and assign Traffic
    Light zones (Equation 10.2).

    limits_df has one row per electrode, protocol, age_group and
    parameter, with these columns:
        electrode, protocol, age_group, parameter,
        kind          'amplitude' or 'implicit_time'
        lower, lower_ci_low, lower_ci_high
                      2.5th percentile and its 90% CI
        upper, upper_ci_low, upper_ci_high
                      97.5th percentile and its 90% CI
    Values are in the same units as the measurements classified.
    The kind column sets which direction is atypical: an amplitude
    above the upper limit, or an implicit time below the lower one.
    """

    KEY = ['electrode', 'protocol', 'age_group', 'parameter']
    VALUE_COLUMNS = ['lower', 'lower_ci_low', 'lower_ci_high',
                     'upper', 'upper_ci_low', 'upper_ci_high']
    KINDS = ('amplitude', 'implicit_time')

    def __init__(self, limits_df: pd.DataFrame):
        needed = self.KEY + ['kind'] + self.VALUE_COLUMNS
        missing = [c for c in needed if c not in limits_df.columns]
        if missing:
            raise ValueError(f'limits_df is missing columns: '
                             f'{missing}')
        if limits_df.duplicated(self.KEY).any():
            raise ValueError('limits_df has more than one row for '
                             'a stratum.')
        if limits_df[self.VALUE_COLUMNS].isna().any().any():
            raise ValueError('limits_df contains missing limit '
                             'values.')
        if not limits_df['kind'].isin(self.KINDS).all():
            raise ValueError(f'kind must be one of {self.KINDS}.')
        d = limits_df
        ok = ((d['lower_ci_low'] <= d['lower'])
              & (d['lower'] <= d['lower_ci_high'])
              & (d['lower'] < d['upper'])
              & (d['upper_ci_low'] <= d['upper'])
              & (d['upper'] <= d['upper_ci_high']))
        if not ok.all():
            raise ValueError('Reference limits are inconsistent: '
                             'each limit must lie inside its own '
                             'confidence interval, and lower must '
                             'be below upper.')
        self.limits = limits_df.set_index(self.KEY)

    def get_limits(self, electrode: str, protocol: str,
                   age_group: str, parameter: str) -> pd.Series:
        """Return the limits for one stratum."""
        key = (electrode, protocol, age_group, parameter)
        try:
            return self.limits.loc[key]
        except KeyError:
            raise ValueError(
                f'No reference limits for {electrode}/{protocol}/'
                f'{age_group}/{parameter}.') from None

    def classify(self, x: float, electrode: str, protocol: str,
                 age_group: str, parameter: str) -> dict:
        """Assign a Traffic Light zone to one measurement."""
        if x is None or not np.isfinite(x):
            raise ValueError(f'Measurement for {parameter} is '
                             f'missing or not finite.')
        lim = self.get_limits(electrode, protocol, age_group,
                              parameter)

        if x < lim['lower']:
            direction = 'below'
        elif x > lim['upper']:
            direction = 'above'
        else:
            direction = 'within'

        atypical = ((lim['kind'] == 'amplitude'
                     and direction == 'above')
                    or (lim['kind'] == 'implicit_time'
                        and direction == 'below'))
        in_amber = (lim['lower_ci_low'] <= x < lim['lower']
                    or lim['upper'] < x <= lim['upper_ci_high'])

        if direction == 'within':
            zone = 'GREEN'
        elif atypical:
            # Opposite to the direction in which disease usually acts.
            zone = 'ATYPICAL DIRECTION'
        elif in_amber:
            zone = 'AMBER'
        else:
            zone = 'RED'

        return {
            'parameter':     parameter,
            'x':             x,
            'lower_limit':   float(lim['lower']),
            'upper_limit':   float(lim['upper']),
            'direction':     direction,
            'traffic_light': zone,
        }

import pandas as pd
from sklearn.model_selection import train_test_split


def patient_level_split(df: pd.DataFrame,
                        label_col: str = 'label',
                        patient_col: str = 'patient_id',
                        confidence_col: str = None,
                        test_frac: float = 0.10,
                        random_state: int = 42) -> tuple:
    """
    Split a feature DataFrame into a development set and a held-out
    test set, keeping each patient whole and stratifying by class.

    The 5-fold cross-validation of Section 10.2.3 then runs inside
    the development set.

    If confidence_col is given (values 'High' or 'Standard',
    Section 10.1.3), the test set keeps High Confidence recordings
    only. Standard Confidence recordings of test patients are
    dropped, not moved to the development set, so no test patient
    contributes to training.

    Returns: (df_development, df_test).
    """
    # Step 1: one label per patient.
    n_labels = df.groupby(patient_col)[label_col].nunique()
    conflicted = n_labels[n_labels > 1].index.tolist()
    if conflicted:
        raise ValueError(
            f'Patients with more than one class label: '
            f'{conflicted[:5]}. Resolve the label conflict before '
            f'splitting.'
        )
    patient_df = (
        df.groupby(patient_col)[label_col].first()
          .reset_index()
          .rename(columns={label_col: 'patient_label'})
    )

    per_class = patient_df['patient_label'].value_counts()
    too_few = per_class[per_class < 2].index.tolist()
    if too_few:
        raise ValueError(f'Classes with fewer than 2 patients '
                         f'cannot be stratified: {too_few}.')

    # Step 2: split patients into development and test.
    patients_dev, patients_test = train_test_split(
        patient_df,
        test_size=test_frac,
        stratify=patient_df['patient_label'],
        random_state=random_state,
    )

    # Step 3: map patient assignments back to recordings.
    dev_ids = set(patients_dev[patient_col])
    test_ids = set(patients_test[patient_col])
    df_dev = df[df[patient_col].isin(dev_ids)].copy()
    df_test = df[df[patient_col].isin(test_ids)].copy()

    if confidence_col is not None:
        n_before = len(df_test)
        keep = df_test[confidence_col] == 'High'
        df_test = df_test[keep].copy()
        print(f'  Test set: {n_before - len(df_test)} Standard '
              f'Confidence recordings of test patients dropped.')
        absent = set(df[label_col]) - set(df_test[label_col])
        if absent:
            raise ValueError(
                f'No High Confidence test recording for class(es) '
                f'{sorted(str(c) for c in absent)}. Review the '
                f'split before testing.'
            )

    # Step 4: verify zero leakage.
    _verify_no_leakage(df_dev, df_test, patient_col)

    print('Split complete:')
    print(f'  Development : {len(df_dev)} recordings '
          f'({len(dev_ids)} patients)')
    print(f'  Test        : {len(df_test)} recordings '
          f'({len(test_ids)} patients)')
    return df_dev, df_test


def _verify_no_leakage(df_dev, df_test, patient_col):
    """Raise if any patient appears in both partitions."""
    overlap = set(df_dev[patient_col]) & set(df_test[patient_col])
    if overlap:
        raise ValueError(f'Patient leakage detected! '
                         f'Development and test share: {overlap}')
    print('  Leakage check: PASS -- zero patient overlap across '
          'partitions.')
