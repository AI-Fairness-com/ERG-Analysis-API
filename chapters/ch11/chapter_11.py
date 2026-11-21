# Chapter 11: missing data in ERG recordings
# The code of Chapter 11, in the order of the book: sentinel and NaN
# coding with missingness indicators, imputation fitted on the training
# set only, the protocol completeness label (for example "3 of 5",
# PARTIAL), the complete-case comparison, and the missing-data
# sensitivity analysis on simulated predictions.
# Run from the repository folder:  python chapters/ch11/chapter_11.py

import numpy as np
import pandas as pd
from typing import Optional, Union

SENTINELS = (-9999.0, 9999.0)   # MNAR-physiological codes (§11.1)


def add_missing_indicators(df: pd.DataFrame,
                           features: list,
                           fill_value: Union[float, str] = 0.0,
                           reference: Optional[pd.DataFrame] = None
                           ) -> pd.DataFrame:
    """
    Add a binary indicator column for each feature, recording where
    the value was NaN, then fill the NaN with a simple value.

    fill_value=0.0 suits amplitude features. fill_value='mean' suits
    timing features and uses the mean of the reference partition.
    Pass the TRAINING partition as reference when encoding the
    validation and test partitions, so no information leaks from
    them. Sentinel codes are left out of the mean.
    """
    df = df.copy()
    source = df if reference is None else reference
    for feat in features:
        if feat not in df.columns:
            continue
        df[f'{feat}_missing'] = df[feat].isna().astype(int)
        if isinstance(fill_value, str) and fill_value == 'mean':
            valid = source[feat][~source[feat].isin(SENTINELS)]
            fill = valid.mean(skipna=True)
        else:
            fill = fill_value
        df[feat] = df[feat].fillna(fill)
    return df


# Example: amplitudes are filled with 0 and timing features with the
# training-set mean; the validation set uses the training reference.
amp_features = ['a_amp_uv', 'b_amp_uv', 'op2_amp_uv', 'op3_amp_uv',
                'op4_amp_uv', 'op_sum_uv', 'phnr_amp_uv']
time_features = ['a_implicit_ms', 'b_implicit_ms', 'op2_implicit_ms']


def encode_partition(df_part, df_train):
    out = add_missing_indicators(df_part, amp_features,
                                 fill_value=0.0)
    return add_missing_indicators(out, time_features,
                                  fill_value='mean',
                                  reference=df_train)


df_train = pd.DataFrame({'a_amp_uv': [150.0, np.nan, 170.0],
                         'a_implicit_ms': [14.5, np.nan, 9999.0]})
df_val = pd.DataFrame({'a_amp_uv': [np.nan],
                       'a_implicit_ms': [np.nan]})
df_train_enc = encode_partition(df_train, df_train)
df_val_enc = encode_partition(df_val, df_train)
print(df_val_enc)

import numpy as np
import pandas as pd
from typing import Optional


def _missing_rate(frame: pd.DataFrame, cols: list,
                  applicable: Optional[pd.DataFrame]) -> pd.Series:
    """Share of NaN per column, counted only where it applies."""
    miss = frame[cols].isna()
    if applicable is None:
        return miss.mean()
    app = applicable.loc[frame.index, cols].astype(bool)
    n_app = app.sum()
    rate = (miss & app).sum() / n_app.where(n_app > 0)
    return rate.fillna(0.0)   # never applicable: nothing to exclude


def exclude_high_missingness_features(
        df_train: pd.DataFrame,
        df_val: pd.DataFrame,
        df_test: pd.DataFrame,
        label_col: str = 'label',
        threshold_global: float = 0.40,
        threshold_class: float = 0.40,
        applicable: Optional[pd.DataFrame] = None) -> tuple:
    """
    Remove features missing in more than the threshold share of the
    training data, overall or within any class.

    applicable: optional boolean DataFrame aligned with df_train that
    is False where a feature does not apply by design (for example,
    the PhNR on a DA recording); those cells are ignored.
    Returns (df_train, df_val, df_test, excluded_features).
    """
    feature_cols = [c for c in df_train.columns
                    if c != label_col and '_missing' not in c]
    to_exclude = set()

    # Overall missingness
    rate = _missing_rate(df_train, feature_cols, applicable)
    overall = rate[rate > threshold_global].index.tolist()
    to_exclude.update(overall)
    if overall:
        print(f'Excluded overall (> {threshold_global:.0%}): '
              f'{overall}')

    # Missingness within each class
    for cls in df_train[label_col].unique():
        sub = df_train[df_train[label_col] == cls]
        rate = _missing_rate(sub, feature_cols, applicable)
        excl = rate[rate > threshold_class].index.tolist()
        if excl:
            print(f'  Class {cls}: excluded {excl}')
            to_exclude.update(excl)

    # Drop the matching indicator columns too
    to_exclude.update(f'{f}_missing' for f in list(to_exclude)
                      if f'{f}_missing' in df_train.columns)

    drop = sorted(to_exclude)
    df_train = df_train.drop(columns=drop, errors='ignore')
    df_val = df_val.drop(columns=drop, errors='ignore')
    df_test = df_test.drop(columns=drop, errors='ignore')
    print(f'Total columns excluded: {len(drop)}')
    return df_train, df_val, df_test, drop

ISCEV_PROTOCOLS = ['DA 0.01', 'DA 3.0', 'DA 10.0',
                   'LA 3.0', 'LA 30 Hz']


def compute_protocol_completeness(present_protocols: list,
                                  passed_qc: list) -> dict:
    """
    Count the ISCEV protocols that are present and usable, and build
    the Layer 1 completeness label. A usable protocol is present and
    not flagged Fail (Chapter 2). The label never changes the Traffic
    Light zones or the class probabilities.

    present_protocols : protocol names present for the patient.
    passed_qc         : protocols not flagged Fail.
    """
    usable = [p for p in ISCEV_PROTOCOLS
              if p in present_protocols and p in passed_qc]
    missing = [p for p in ISCEV_PROTOCOLS
               if p not in present_protocols]
    failed = [p for p in ISCEV_PROTOCOLS
              if p in present_protocols and p not in passed_qc]
    n_total = len(ISCEV_PROTOCOLS)

    return {
        'n_usable':           len(usable),
        'n_total':            n_total,
        'completeness_label': f'{len(usable)} of {n_total}',
        'layer1_flag':        ('COMPLETE' if len(usable) == n_total
                               else 'PARTIAL'),
        'missing_protocols':  missing,
        'failed_protocols':   failed,
    }


print(compute_protocol_completeness(
    ['DA 3.0', 'LA 3.0', 'LA 30 Hz', 'DA 0.01'],
    ['DA 3.0', 'LA 3.0', 'LA 30 Hz']))

import numpy as np
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge


def mice_impute(X_train: np.ndarray,
                X_val: np.ndarray,
                X_test: np.ndarray,
                n_imputations: int = 20,
                max_iter: int = 10,
                random_state: int = 42) -> list:
    """
    Multiple imputation by chained equations (MICE).

    Each imputer is FITTED on the training data only and then applied
    to all three partitions, so no information leaks from validation
    or test data. sample_posterior=True draws each filled value from
    the predictive distribution, so the n_imputations datasets
    differ. At least 20 datasets may be preferable to five
    (Sterne et al., 2009).
    Returns a list of (X_train_imp, X_val_imp, X_test_imp) tuples.
    """
    imputed_sets = []
    for seed in range(random_state, random_state + n_imputations):
        imp = IterativeImputer(
            estimator=BayesianRidge(),
            sample_posterior=True,
            max_iter=max_iter,
            random_state=seed,
            initial_strategy='mean',
            imputation_order='ascending',  # most complete first
        )
        imp.fit(X_train)                   # training data only
        imputed_sets.append((imp.transform(X_train),
                             imp.transform(X_val),
                             imp.transform(X_test)))
    print(f'MICE complete: {n_imputations} imputed datasets.')
    return imputed_sets


def pool_predictions(proba_list: list) -> np.ndarray:
    """Average predicted probabilities across imputed datasets."""
    return np.mean(np.stack(proba_list, axis=0), axis=0)

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def _per_class_auc(y: np.ndarray, proba: np.ndarray) -> dict:
    """
    One-vs-rest AUC for each class. Returns NaN when a class, or
    all other classes together, has no recording in y.
    """
    out = {}
    for c in range(proba.shape[1]):
        pos = (y == c)
        if pos.sum() == 0 or pos.sum() == len(y):
            out[c] = np.nan
        else:
            out[c] = roc_auc_score(pos, proba[:, c])
    return out


def sensitivity_analysis_missing_data(df_test: pd.DataFrame,
                                      y_pred_proba: np.ndarray,
                                      label_col: str = 'label',
                                      auc_threshold: float = 0.05
                                      ) -> dict:
    """
    Compare per-class AUC on the full test set and on its
    complete-case subset (Sterne et al., 2009).

    Labels must be integers 0 to K-1, matching the columns of
    y_pred_proba. A recording is complete-case when none of its
    _missing indicators (§11.2.1) equals 1. MNAR indicators end in
    _absent_physiological, so physiological absences stay in.
    """
    ind_cols = [c for c in df_test.columns
                if c.endswith('_missing')]
    if ind_cols:
        is_cc = (df_test[ind_cols] == 0).all(axis=1).to_numpy()
    else:
        is_cc = np.ones(len(df_test), dtype=bool)

    y_true = df_test[label_col].to_numpy()
    auc_all = _per_class_auc(y_true, y_pred_proba)
    auc_cc = _per_class_auc(y_true[is_cc], y_pred_proba[is_cc])

    classes = [c for c in auc_all
               if not np.isnan(auc_all[c])
               and not np.isnan(auc_cc[c])]
    not_eval = [c for c in auc_all if c not in classes]
    diffs = {c: abs(auc_all[c] - auc_cc[c]) for c in classes}
    n_cc = {c: int((y_true[is_cc] == c).sum()) for c in auc_all}

    too_big = any(d > auc_threshold for d in diffs.values())
    if not classes or not_eval or too_big:
        flag = 'INVESTIGATE'
    else:
        flag = 'PASS'

    max_diff = max(diffs.values(), default=float('nan'))
    print(f'Complete-case recordings: {int(is_cc.sum())} '
          f'of {len(y_true)}')
    print(f'Largest per-class AUC difference: {max_diff:.4f} '
          f'[{flag}]')
    return {
        'per_class_auc_all': {c: round(a, 4)
                              for c, a in auc_all.items()},
        'per_class_auc_cc': {c: round(a, 4)
                             for c, a in auc_cc.items()},
        'per_class_abs_diff': {c: round(d, 4)
                               for c, d in diffs.items()},
        'n_cc_per_class': n_cc,
        'classes_not_evaluable': not_eval,
        'n_complete_case': int(is_cc.sum()),
        'n_total': len(y_true),
        'sensitivity_flag': flag,
    }


# Example: three classes with simulated predictions.
rng = np.random.default_rng(0)
n = 300
y = rng.integers(0, 3, n)
proba = rng.dirichlet(np.ones(3), n)
proba[np.arange(n), y] += 0.5
proba /= proba.sum(axis=1, keepdims=True)
lost = (rng.random(n) < 0.2).astype(int)     # MAR or MCAR
absent = (rng.random(n) < 0.1).astype(int)   # MNAR
df = pd.DataFrame({'label': y,
                   'phnr_amp_uv_missing': lost,
                   'b_wave_absent_physiological': absent})
result = sensitivity_analysis_missing_data(df, proba)
print(result['n_cc_per_class'], result['classes_not_evaluable'])
