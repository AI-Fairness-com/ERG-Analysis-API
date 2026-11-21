# -*- coding: utf-8 -*-
"""
appendices.py
=============
Hands-On Electroretinography in the Age of AI, Appendices A to F

The code of the appendices, in the order of the book:

  Appendix A  Standardized ERG CSV template: the feature file for
              external validation (§A.3), written and checked
  Appendix B  HL7 FHIR R4 profile: no code here. The API builds the
              output with ERGFHIRGenerator (api/erg_v2_5_0.py); see
              docs/fhir_integration.md
  Appendix C  Sample-size calculations for Chapter 10:
              §C.1 width of the AUC confidence interval (Hanley and McNeil)
              §C.2 Table 10.2 reproduced with pmsampsize (Riley et al.)
  Appendix D  Model Card checklist: no code (Chapter 17 builds the card)
  Appendix E  TRIPOD+AI evidence table: no code
  Appendix F  Local environment: the installation checks of §F.3

Run from the repository folder:
    python chapters/Appendices/appendices.py

Repository: https://github.com/AI-Fairness-com/ERG-Analysis-API
"""

import io
import math

import pandas as pd


# ============================================================================
# Appendix A, §A.3: feature file for external validation
# ============================================================================
# Nine identifying columns, then the measured features. The four example
# rows are those printed in §A.3 for Mrs. T. (Chapter 19, case 1) and
# Ms. F. (case 3). NaN marks a feature that does not apply or could not be
# measured (Chapter 11 §11.1).

FEATURE_FILE_EXAMPLE = """\
patient_id,recording_date,age_years,sex,eye,protocol,electrode_type,device_manufacturer,center_id,a_amp_uv,a_implicit_ms,b_amp_uv,b_implicit_ms,ba_ratio
CASE01_MRS_T,2026-03-15,67,F,OD,DA 0.01,dtl_fiber,diagnosys_espion,CENTER_01,NaN,NaN,190,98,NaN
CASE01_MRS_T,2026-03-15,67,F,OD,DA 3.0,dtl_fiber,diagnosys_espion,CENTER_01,95,16.4,205,52.1,2.158
CASE03_MS_F,2026-04-10,34,F,OD,DA 0.01,dtl_fiber,diagnosys_espion,CENTER_01,NaN,NaN,NaN,NaN,NaN
CASE03_MS_F,2026-04-10,34,F,OD,DA 3.0,dtl_fiber,diagnosys_espion,CENTER_01,32,19.5,41,72,1.281
"""

IDENTIFYING_COLUMNS = ['patient_id', 'recording_date', 'age_years', 'sex',
                       'eye', 'protocol', 'electrode_type',
                       'device_manufacturer', 'center_id']
PROTOCOLS = {'DA 0.01', 'DA 3.0', 'DA 10.0', 'LA 3.0', 'LA 30 Hz'}
ELECTRODES = {'contact_lens', 'gold_foil', 'dtl_fiber', 'skin'}


def check_feature_file(df: pd.DataFrame) -> list:
    """Return a list of problems with a feature file (empty if none)."""
    problems = [f'missing column: {c}' for c in IDENTIFYING_COLUMNS
                if c not in df.columns]
    if problems:
        return problems
    bad = ~df['protocol'].isin(PROTOCOLS)
    problems += [f'row {i}: protocol {p!r}'
                 for i, p in df.loc[bad, 'protocol'].items()]
    bad = ~df['electrode_type'].isin(ELECTRODES)
    problems += [f'row {i}: electrode_type {e!r}'
                 for i, e in df.loc[bad, 'electrode_type'].items()]
    bad = ~df['eye'].isin({'OD', 'OS'})
    problems += [f'row {i}: eye {e!r}' for i, e in df.loc[bad, 'eye'].items()]
    # The b/a ratio is the b-wave amplitude over the a-wave amplitude,
    # rounded to three decimals (Chapter 9 §9.1.2).
    ratio = (df['b_amp_uv'] / df['a_amp_uv']).round(3)
    both = df['ba_ratio'].notna() & ratio.notna()
    off = both & ((df['ba_ratio'] - ratio).abs() > 0.001)
    problems += [f'row {i}: ba_ratio {r} differs from b/a {ratio[i]}'
                 for i, r in df.loc[off, 'ba_ratio'].items()]
    return problems


def appendix_a():
    df = pd.read_csv(io.StringIO(FEATURE_FILE_EXAMPLE))
    print('Appendix A, §A.3: example feature file')
    print(df[['patient_id', 'protocol', 'a_amp_uv', 'b_amp_uv', 'ba_ratio']])
    problems = check_feature_file(df)
    print('Check:', 'no problems found' if not problems else problems)


# ============================================================================
# Appendix C, §C.1: width of the AUC confidence interval
# ============================================================================

# Half-width of the 95% CI of an AUC (Hanley and McNeil, 1982)
def auc_ci_half_width(auc: float, n_abnormal: int,
                      n_normal: int, z: float = 1.96) -> float:
    """Return z times the standard error of the AUC."""
    q1 = auc / (2 - auc)
    q2 = 2 * auc ** 2 / (1 + auc)
    var = (auc * (1 - auc)
           + (n_abnormal - 1) * (q1 - auc ** 2)
           + (n_normal - 1) * (q2 - auc ** 2))
    var /= n_abnormal * n_normal
    return z * math.sqrt(var)


def appendix_c1():
    print('Appendix C, §C.1: half-width of the 95% CI of an AUC of 0.90')
    for n in (12, 25, 50, 100):
        hw = auc_ci_half_width(0.90, n, n)
        print(f'{n:>4} per class: AUC 0.90 +/- {hw:.3f}')
    # Book output: 0.132, 0.090, 0.063, 0.044


# ============================================================================
# Appendix C, §C.2: Table 10.2 reproduced with pmsampsize
# ============================================================================
# In Colab, install the package first:  !pip install -q pmsampsize
# Locally:  pip install pmsampsize  (the package needs Python 3.12 or later)

def appendix_c2():
    print('Appendix C, §C.2: Table 10.2 with pmsampsize (Riley et al., 2020)')
    try:
        from pmsampsize.pmsampsize import pmsampsize
    except ImportError:
        print('  pmsampsize is not installed. Run this cell in Google '
              'Colab, or install it with "pip install pmsampsize" '
              '(Python 3.12 or later).')
        return
    result = pmsampsize(type='b',          # binary outcome
                        cstatistic=0.681,  # anticipated AUC
                        parameters=27,     # candidate predictors
                        prevalence=0.49,   # share of Abnormal
                        noprint=True)
    n = result['sample_size']
    abnormal = round(result['events'])
    print(f'Total {n}: {abnormal} Abnormal, {n - abnormal} Normal')
    for row in result['results_table']:
        if isinstance(row, list):
            print(f'{row[0]:<11} {row[1]:>5}')
    # Book output: Total 2308: 1131 Abnormal, 1177 Normal;
    # Criteria 1 2308, Criteria 2 670, Criteria 3 385, Final SS 2308


# ============================================================================
# Appendix F, §F.3: checking the installation
# ============================================================================
# The same checks as the three commands of §F.3:
#   python -c "import numpy, scipy, mne, matplotlib, plotly"
#   python -c "import sklearn, torch, timm, shap, imblearn"
#   python chapters/ch03/csv_walkthrough.py

def appendix_f3():
    import importlib
    print('Appendix F, §F.3: libraries the book uses')
    for name in ('numpy', 'scipy', 'mne', 'matplotlib', 'plotly',
                 'sklearn', 'torch', 'timm', 'shap', 'imblearn'):
        try:
            importlib.import_module(name)
            print(f'  {name:<11} ok')
        except ImportError:
            print(f'  {name:<11} MISSING: pip install -r requirements.txt')
    print('  Then run: python chapters/ch03/csv_walkthrough.py')


if __name__ == '__main__':
    appendix_a()
    print()
    appendix_c1()
    print()
    appendix_c2()
    print()
    appendix_f3()
