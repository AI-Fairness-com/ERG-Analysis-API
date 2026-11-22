"""Chapter 16: Validation methodology.

Code from Chapter 16 of "Hands-On Electroretinography in the Age of
AI", in the order of the book: the SAP hash check, patient-level
cross-validation, center-level leakage check, AUC with confidence
intervals, calibration and Brier scores, the performance table, ComBat
harmonization and its check, and the validation report. A short
demonstration on simulated data runs at the end. Outputs go to
./outputs/validation.
"""

# SAP pre-registration hash check (Section 16.2.1)
import datetime
import hashlib


def verify_sap_hash(sap_path: str = "docs/ERG_SAP_v2.2.pdf",
                    registered_hash: str = None) -> dict:
    """
    Compute the SHA-256 hash of the SAP file and compare it with the
    registered hash. Call this at the start of every validation run.
    """
    with open(sap_path, "rb") as f:
        computed = hashlib.sha256(f.read()).hexdigest()
    match = (computed == registered_hash) if registered_hash else None
    result = {
        "sap_path": sap_path,
        "computed_hash": computed,
        "registered_hash": registered_hash,
        "hash_match": match,
        "verified_at": datetime.datetime.now().isoformat(),
    }
    if match is False:
        raise ValueError(
            "The SAP hash does not match the registered hash. Do not "
            "proceed until the difference is resolved. Any analysis "
            "run with a changed SAP must be declared as a deviation "
            "from the pre-registered plan.")
    status = "MATCH" if match else "UNREGISTERED (record hash now)"
    print(f"SAP hash check: {status} [{computed[:16]}...]")
    return result

# Five-fold stratified cross-validation (Section 16.3.1)
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


def run_stratified_cv(
        df: pd.DataFrame,
        feature_cols: list,
        label_col: str = "label",
        patient_col: str = "patient_id",
        n_splits: int = 5,
        random_state: int = 42,
        tolerance: float = 0.02) -> dict:
    """
    Five-fold stratified cross-validation with patients as groups.

    Run this on the development set only (the 90% described in
    Section 16.3.1), with one row per recording, before any
    spectrogram is extracted. Every recording of a patient goes to
    the same fold. Class proportions in each validation fold are
    compared with the whole development set. A difference larger
    than the tolerance is reported, not hidden.
    """
    X = df[feature_cols].values
    y = df[label_col].values
    groups = df[patient_col].values
    overall = {c: (y == c).mean() for c in np.unique(y)}

    splitter = StratifiedGroupKFold(
        n_splits=n_splits, shuffle=True,
        random_state=random_state)

    fold_results = []
    splits = splitter.split(X, y, groups)
    for fold_idx, (train_idx, val_idx) in enumerate(splits):
        fold = fold_idx + 1
        shared = set(groups[train_idx]) & set(groups[val_idx])
        if shared:
            raise ValueError(
                f"Data leakage: {len(shared)} patients are in "
                f"both the training and validation sets of "
                f"fold {fold}.")

        y_val = y[val_idx]
        drift = max(abs((y_val == c).mean() - p)
                    for c, p in overall.items())
        present = set(np.unique(y_val)) == set(overall)
        fold_results.append({
            "fold": fold,
            "train_idx": train_idx,
            "val_idx": val_idx,
            "n_train": len(train_idx),
            "n_val": len(val_idx),
            "max_class_drift": round(float(drift), 4),
            "all_classes_present": bool(present),
            "stratification_ok": bool(drift <= tolerance),
        })
        print(f"Fold {fold}: train={len(train_idx)}, "
              f"val={len(val_idx)}, "
              f"max class drift={drift:.3f}")

    return {
        "n_splits": n_splits,
        "random_state": random_state,
        "tolerance": tolerance,
        "fold_results": fold_results,
        "leakage_check": "PASS",
    }

# Center-level leakage prevention (Section 16.4.3)
import warnings

import pandas as pd


def verify_center_stratification(
        train_df: pd.DataFrame,
        ext_df: pd.DataFrame,
        center_col: str = "center_id") -> dict:
    """
    Check that no external validation center appears in the
    training data.

    Raises ValueError if any center is in both data frames. Warns
    if an external center does not start with the prefix EXT_.
    """
    train_centers = set(train_df[center_col].unique())
    ext_centers = set(ext_df[center_col].unique())

    overlap = train_centers & ext_centers
    if overlap:
        raise ValueError(
            f"Data leakage: {len(overlap)} center(s) appear in "
            f"both the training and external validation sets: "
            f"{sorted(overlap)}. Remove all recordings from these "
            "centers from the training set. External validation "
            "results computed with this leakage are invalid and "
            "must not be reported.")

    non_prefixed = sorted(c for c in ext_centers
                          if not str(c).startswith("EXT_"))
    if non_prefixed:
        warnings.warn(
            f"External centers {non_prefixed} do not use the "
            "EXT_ prefix. Add the prefix to prevent accidental "
            "use in training.")

    print("Center stratification: PASS")
    print(f"  Training centers : {sorted(train_centers)}")
    print(f"  External centers : {sorted(ext_centers)}")
    return {
        "status": "PASS",
        "train_centers": sorted(train_centers),
        "ext_centers": sorted(ext_centers),
        "overlap_detected": False,
    }

# AUC-ROC with 95% confidence intervals (Section 16.5.2)
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import label_binarize


def delong_auc_ci(y_true: np.ndarray,
                  y_score: np.ndarray,
                  alpha: float = 0.05) -> dict:
    """
    AUC-ROC and 95% confidence interval for one class
    (one-versus-rest).

    Uses the variance of the AUC from its structural components
    (placement values), following DeLong, DeLong and
    Clarke-Pearson (1988).

    y_true  : binary labels (0 or 1), one class against the rest.
    y_score : predicted probability of the positive class.
    """
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    n1, n0 = len(pos), len(neg)
    if n1 < 2 or n0 < 2:
        return {"auc": None, "ci_lower": None, "ci_upper": None,
                "se": None, "n_pos": n1, "n_neg": n0,
                "message": "Too few cases for an AUC interval."}

    # Placement values: for each positive case, the share of
    # negative cases it outranks (ties count one half), and the
    # reverse for each negative case.
    pv_pos = np.array([np.mean(p > neg) + 0.5 * np.mean(p == neg)
                       for p in pos])
    pv_neg = np.array([np.mean(n < pos) + 0.5 * np.mean(n == pos)
                       for n in neg])
    auc = pv_pos.mean()
    se = np.sqrt(pv_pos.var(ddof=1) / n1
                 + pv_neg.var(ddof=1) / n0)
    z = stats.norm.ppf(1 - alpha / 2)
    return {"auc": round(float(auc), 4),
            "ci_lower": round(float(max(0.0, auc - z * se)), 4),
            "ci_upper": round(float(min(1.0, auc + z * se)), 4),
            "se": round(float(se), 5),
            "n_pos": n1, "n_neg": n0}


def compute_per_class_auc(y_true: np.ndarray,
                          y_proba: np.ndarray,
                          class_names: list) -> dict:
    """
    One-versus-rest AUC with a DeLong 95% CI for each class, and
    the unweighted macro-average (point estimate only).

    For Stage 2, pass the six disease classes only. The
    macro-average is then the Stage 2 macro-AUC.
    """
    n = len(class_names)
    y_bin = label_binarize(y_true, classes=list(range(n)))
    results = {}
    for c, name in enumerate(class_names):
        r = delong_auc_ci(y_bin[:, c], y_proba[:, c])
        results[name] = r
        if r["auc"] is None:
            print(f"  {name:30s}: not computed "
                  f"({r['message']})")
        else:
            print(f"  {name:30s}: AUC={r['auc']:.4f} "
                  f"[{r['ci_lower']:.4f} to "
                  f"{r['ci_upper']:.4f}]")
    valid = [v["auc"] for v in results.values()
             if v["auc"] is not None]
    macro = round(float(np.mean(valid)), 4)
    results["macro_average"] = {"auc": macro}
    print(f"  {'Macro-average':30s}: AUC={macro:.4f}")
    return results


def bootstrap_macro_auc_ci(y_true: np.ndarray,
                           y_proba: np.ndarray,
                           patient_ids: np.ndarray,
                           n_boot: int = 2000,
                           alpha: float = 0.05,
                           random_state: int = 42) -> dict:
    """
    95% CI for the macro-averaged AUC by patient-level bootstrap.

    Whole patients are resampled with replacement, so all
    recordings of a patient stay together. The percentile
    interval is returned.
    """
    rng = np.random.default_rng(random_state)
    classes = list(range(y_proba.shape[1]))
    patients = np.unique(patient_ids)
    rows_of = {p: np.where(patient_ids == p)[0] for p in patients}
    values = []
    for _ in range(n_boot):
        drawn = rng.choice(patients, size=len(patients),
                           replace=True)
        idx = np.concatenate([rows_of[p] for p in drawn])
        y_b, p_b = y_true[idx], y_proba[idx]
        if len(np.unique(y_b)) < len(classes):
            continue  # a class is missing from this resample
        y_bin = label_binarize(y_b, classes=classes)
        values.append(np.mean(
            [roc_auc_score(y_bin[:, c], p_b[:, c])
             for c in classes]))
    lo, hi = np.percentile(values, [100 * alpha / 2,
                                    100 * (1 - alpha / 2)])
    return {"macro_auc_ci_lower": round(float(lo), 4),
            "macro_auc_ci_upper": round(float(hi), 4),
            "n_valid_resamples": len(values)}

# Calibration plots and Brier score per class (Section 16.5.3)
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
from sklearn.preprocessing import label_binarize


def compute_calibration_metrics(
        y_true: np.ndarray,
        y_proba_cal: np.ndarray,
        class_names: list,
        n_bins: int = 10,
        output_dir: str = "outputs/validation") -> dict:
    """
    Calibration curve and Brier score for each class.

    y_proba_cal holds the calibrated probabilities from Chapter 14:
    Platt scaling for Stage 1 and temperature scaling for Stage 2.
    Each class is compared with its own frequency-only reference,
    p * (1 - p), where p is the share of recordings in that class.
    A class passes when its Brier score is below that reference.
    """
    os.makedirs(output_dir, exist_ok=True)
    n = len(class_names)
    y_bin = label_binarize(y_true, classes=list(range(n)))

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes_flat = axes.flatten()
    brier, reference, flags = {}, {}, {}

    for c, name in enumerate(class_names):
        p = float(y_bin[:, c].mean())
        brier[name] = round(float(brier_score_loss(
            y_bin[:, c], y_proba_cal[:, c])), 4)
        reference[name] = round(p * (1 - p), 4)
        flags[name] = ("PASS" if brier[name] < reference[name]
                       else "CALIBRATION_WARNING")

        frac_pos, mean_pred = calibration_curve(
            y_bin[:, c], y_proba_cal[:, c],
            n_bins=n_bins, strategy="uniform")
        ax = axes_flat[c]
        ax.plot([0, 1], [0, 1], "--", color="#CCCCCC",
                linewidth=1)
        ax.plot(mean_pred, frac_pos, "o-", color="#2E75B6",
                linewidth=2, markersize=6)
        ax.set_title(f"{name}\nBrier={brier[name]:.3f} "
                     f"(reference {reference[name]:.3f}) "
                     f"{flags[name]}",
                     fontsize=10, fontweight="bold")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Fraction of positives")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    for ax in axes_flat[n:]:
        ax.axis("off")
    plt.suptitle("Per-Class Calibration Plots (After Calibration)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/calibration_plots.png", dpi=220,
                bbox_inches="tight")
    plt.close()

    failed = [k for k, f in flags.items() if f != "PASS"]
    if failed:
        warnings.warn(
            "CALIBRATION_WARNING: the Brier score is not below "
            f"the frequency-only reference for {failed}. Withhold "
            "the probabilities of these classes from clinical "
            "reports until the calibration is repeated on a "
            "larger calibration set.")
    print(f"Brier scores : {brier}")
    print(f"References   : {reference}")
    return {"per_class": brier,
            "reference": reference,
            "class_flags": flags,
            "audit_flag": ("CALIBRATION_WARNING" if failed
                           else "PASS")}

# Per-class metrics and the performance table (Section 16.5.4)
import os

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss
from sklearn.preprocessing import label_binarize

# Requires delong_auc_ci() and bootstrap_macro_auc_ci() from
# Section 16.5.2 in the same session.

NAMES = ["sensitivity", "specificity", "ppv", "npv"]


def class_metrics(y_c: np.ndarray, pred_c: np.ndarray) -> dict:
    """Sensitivity, specificity, PPV and NPV for one class."""
    tp = int(((y_c == 1) & (pred_c == 1)).sum())
    fn = int(((y_c == 1) & (pred_c == 0)).sum())
    fp = int(((y_c == 0) & (pred_c == 1)).sum())
    tn = int(((y_c == 0) & (pred_c == 0)).sum())

    def ratio(a, b):
        return a / b if b > 0 else np.nan

    return {"sensitivity": ratio(tp, tp + fn),
            "specificity": ratio(tn, tn + fp),
            "ppv": ratio(tp, tp + fp),
            "npv": ratio(tn, tn + fn)}


def bootstrap_metrics(y_bin, pred_bin, patient_ids,
                      n_boot=2000, alpha=0.05, random_state=42):
    """
    Point estimates and percentile bootstrap CIs for each column
    of y_bin (one column per class) and for the column mean
    (macro). Whole patients are resampled with replacement.
    """
    rng = np.random.default_rng(random_state)
    k = y_bin.shape[1]
    patients = np.unique(patient_ids)
    rows_of = {p: np.where(patient_ids == p)[0] for p in patients}

    def all_metrics(idx):
        per = [class_metrics(y_bin[idx, c], pred_bin[idx, c])
               for c in range(k)]
        per.append({m: np.nanmean([r[m] for r in per])
                    for m in NAMES})
        return per                      # k classes, then macro

    point = all_metrics(np.arange(len(patient_ids)))
    draws = [{m: [] for m in NAMES} for _ in range(k + 1)]
    for _ in range(n_boot):
        drawn = rng.choice(patients, size=len(patients),
                           replace=True)
        idx = np.concatenate([rows_of[p] for p in drawn])
        for c, r in enumerate(all_metrics(idx)):
            for m in NAMES:
                draws[c][m].append(r[m])

    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    out = []
    for c in range(k + 1):
        out.append({m: (point[c][m],
                        *np.nanpercentile(draws[c][m], q))
                    for m in NAMES})
    return out


def fmt(p, lo, hi):
    return f"{p:.3f} ({lo:.3f} to {hi:.3f})"


def table_row(name, ci, auc, brier):
    row = {"Disease Class": name}
    for m, label in zip(NAMES, ["Sensitivity", "Specificity",
                                "PPV", "NPV"]):
        row[f"{label} (95% CI)"] = fmt(*ci[m])
    row["AUC-ROC (95% CI)"] = auc
    row["Brier Score"] = f"{brier:.3f}"
    return row


def build_performance_table(
        s1_true, s1_proba, s1_threshold, s1_ids,
        y_true, y_proba, patient_ids, class_names, brier,
        output_dir="outputs/validation", n_boot=2000):
    """
    Integrated table: one Stage 1 row, one row for each of the
    six Stage 2 disease classes, and a Stage 2 macro-average row.

    Stage 1: s1_true is 1 for Abnormal, s1_proba is the calibrated
    probability of Abnormal, and s1_threshold is the operating
    point. Stage 2: brier maps each class name to its Brier score
    (Section 16.5.3). The predicted class is the most probable.
    """
    os.makedirs(output_dir, exist_ok=True)
    rows = []

    pred1 = (s1_proba >= s1_threshold).astype(int)
    ci1 = bootstrap_metrics(s1_true[:, None], pred1[:, None],
                            s1_ids, n_boot)[0]
    a = delong_auc_ci(s1_true, s1_proba)
    auc1 = (f"{a['auc']:.3f} ({a['ci_lower']:.3f} to "
            f"{a['ci_upper']:.3f})")
    rows.append(table_row("Stage 1 (Abnormal vs Normal)", ci1,
                          auc1, brier_score_loss(s1_true,
                                                 s1_proba)))

    k = len(class_names)
    y_bin = label_binarize(y_true, classes=list(range(k)))
    pred_bin = label_binarize(y_proba.argmax(axis=1),
                              classes=list(range(k)))
    ci2 = bootstrap_metrics(y_bin, pred_bin, patient_ids, n_boot)
    aucs = []
    for c, name in enumerate(class_names):
        a = delong_auc_ci(y_bin[:, c], y_proba[:, c])
        aucs.append(a["auc"])
        auc = ("not computed" if a["auc"] is None else
               f"{a['auc']:.3f} ({a['ci_lower']:.3f} to "
               f"{a['ci_upper']:.3f})")
        rows.append(table_row(name, ci2[c], auc, brier[name]))

    m = bootstrap_macro_auc_ci(y_true, y_proba, patient_ids,
                               n_boot)
    macro_auc = fmt(np.mean([v for v in aucs if v is not None]),
                    m["macro_auc_ci_lower"],
                    m["macro_auc_ci_upper"])
    macro_brier = np.mean([brier[n] for n in class_names])
    rows.append(table_row("Macro-average (Stage 2)", ci2[k],
                          macro_auc, macro_brier))

    table = pd.DataFrame(rows)
    table.to_csv(f"{output_dir}/performance_table.csv",
                 index=False)
    return table

# ComBat batch effect harmonization (Section 16.6.1)
# Requires: pip install neuroCombat
import numpy as np
import pandas as pd

AGE_CODES = {"le35": 0, "36to59": 1, "ge60": 2}

# neuroCombat still calls np.int, which NumPy removed in 1.24.
if not hasattr(np, "int"):
    np.int = int


def harmonize_features(feature_matrix: np.ndarray,
                       batch_labels: np.ndarray,
                       covariates: pd.DataFrame,
                       ref_batch: str = None) -> np.ndarray:
    """
    Remove batch effects from a feature matrix with ComBat.

    feature_matrix : array of shape (n_samples, n_features).
    batch_labels   : device or site label for every sample.
    covariates     : columns age_strata (le35, 36to59, ge60) and
                     sex (M, F). Disease labels are never used.
    ref_batch      : if given, the samples of this batch stay
                     unchanged and the other batches are adjusted
                     toward it.
    """
    try:
        from neuroCombat import neuroCombat
    except ImportError:
        raise ImportError(
            "Install neuroCombat with: pip install neuroCombat")

    ages = covariates["age_strata"].map(AGE_CODES)
    covars = pd.DataFrame({
        "batch": np.asarray(batch_labels),
        "age_strata": ages.values,
        "sex": covariates["sex"].map({"M": 0, "F": 1}).values,
    })
    result = neuroCombat(dat=feature_matrix.T,  # features x samples
                         covars=covars,
                         batch_col="batch",
                         categorical_cols=["age_strata", "sex"],
                         ref_batch=ref_batch)
    return result["data"].T


def harmonize_training_and_external(train_X, train_batch,
                                    train_cov, ext_X, ext_cov):
    """
    Step 1: harmonize the training devices to each other, using
    the training data only. The model is trained on train_X_h.
    Step 2: pool the harmonized training features (one batch,
    TRAIN) with the raw external features (one batch, EXT) and
    adjust EXT toward TRAIN. The training features do not change,
    so the frozen model sees the same data. No labels are used
    in either step.
    """
    train_X_h = harmonize_features(train_X, train_batch,
                                   train_cov)

    pooled_X = np.vstack([train_X_h, ext_X])
    pooled_batch = np.array(["TRAIN"] * len(train_X_h)
                            + ["EXT"] * len(ext_X))
    pooled_cov = pd.concat([train_cov, ext_cov],
                           ignore_index=True)
    pooled_h = harmonize_features(pooled_X, pooled_batch,
                                  pooled_cov, ref_batch="TRAIN")
    return train_X_h, pooled_h[len(train_X_h):]

# Harmonization check: Levene test and MMD (Section 16.6.2)
from itertools import combinations

import numpy as np
from scipy import stats


def mmd(x: np.ndarray, y: np.ndarray, bw: float) -> float:
    """Squared MMD between two 1-D samples, Gaussian kernel."""
    def k(a, b):
        return np.exp(-(a[:, None] - b[None, :]) ** 2
                      / (2 * bw ** 2))
    return float(k(x, x).mean() + k(y, y).mean()
                 - 2 * k(x, y).mean())


def check_harmonization(X_h: np.ndarray,
                        batch_labels: np.ndarray,
                        feature_names: list,
                        alpha: float = 0.05,
                        random_state: int = 42) -> dict:
    """
    Check each harmonized feature in two ways.

    Levene: the spread of the feature must not differ between
    batches (p >= alpha).
    MMD: the largest MMD between two batches must be no larger
    than the largest MMD between two random halves of one batch.
    A feature that fails either check is listed in "failed".
    """
    rng = np.random.default_rng(random_state)
    batch_labels = np.asarray(batch_labels)
    batches = np.unique(batch_labels)
    results, failed = {}, []

    for j, name in enumerate(feature_names):
        x = X_h[:, j]
        # Kernel width: median absolute deviation of the feature.
        bw = float(np.median(np.abs(x - np.median(x)))) or 1.0
        groups = {b: x[batch_labels == b] for b in batches}

        lev_p = float(stats.levene(*groups.values()).pvalue)
        between = max(mmd(groups[a], groups[b], bw)
                      for a, b in combinations(batches, 2))
        within = []
        for g in groups.values():
            g = rng.permutation(g)
            half = len(g) // 2
            within.append(mmd(g[:half], g[half:], bw))
        within = max(within)

        ok = lev_p >= alpha and between <= within
        results[name] = {"levene_p": round(lev_p, 4),
                         "mmd_between": round(between, 4),
                         "mmd_within": round(within, 4),
                         "pass": bool(ok)}
        if not ok:
            failed.append(name)

    print(f"Harmonization check: {len(failed)} of "
          f"{len(feature_names)} features failed {failed}")
    return {"per_feature": results, "failed": failed}

# Integrated validation reporting template (Section 16.7)
# Assembles the validation evidence into a Model Card-ready JSON.
import datetime
import json
import os


def build_validation_report(
        internal_cv_results: dict,   # from run_stratified_cv()
        external_auc: dict,          # from compute_per_class_auc()
        macro_auc_ci: dict,          # from bootstrap_macro_auc_ci()
        calibration: dict,  # from compute_calibration_metrics()
        harmonization: dict,         # from check_harmonization()
        sap_hash: str,
        n_batches: int,
        model_version: str = "v1.0.0",
        output_dir: str = "outputs/validation") -> dict:
    """
    Assemble a machine-readable validation report for the
    Chapter 17 Model Card and save it as validation_report.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    folds = internal_cv_results["fold_results"]
    per_class = {k: v for k, v in external_auc.items()
                 if k != "macro_average"}
    repo = "github.com/AI-Fairness-com/erg-analysis-api"

    report = {
        "model_version": model_version,
        "generated_at": datetime.datetime.now().isoformat(),
        "sap_hash_verified": sap_hash,
        "validation_standard": "TRIPOD+AI (Collins et al., 2024)",
        "preregistration_doi": "10.17605/OSF.IO/6WA42",
        "normative_reference": ("Baker et al. (2025), "
                                "DOI:10.1007/s10633-025-10009-2"),
        "primary_outcome": ("Macro-AUC-ROC, Stage 2 six-class, "
                            "external validation"),
        "internal_validation": {
            "n_splits": internal_cv_results["n_splits"],
            "leakage_check": internal_cv_results["leakage_check"],
            "max_class_drift": max(f["max_class_drift"]
                                   for f in folds),
        },
        "stage1_binary": {
            "classifier": "ViT Small, Hamming STFT",
            "calibration_method": "Platt scaling (Chapter 14)",
            "operating_point_sensitivity": 0.90,
            "auc_internal_point": "[computed from internal CV]",
            "auc_external_point": "[computed from external data]",
            "auc_external_95ci": "[DeLong method]",
            "deployment_cleared": "[True if lower CI >= 0.94]",
        },
        "stage2_multiclass": {
            "classifier": "ViT Small, Hamming STFT, 6-class",
            "calibration_method": ("Temperature scaling "
                                   "(Chapter 14)"),
            "macro_auc_internal": "[computed]",
            "macro_auc_external":
                external_auc["macro_average"]["auc"],
            "macro_auc_external_95ci": [
                macro_auc_ci["macro_auc_ci_lower"],
                macro_auc_ci["macro_auc_ci_upper"]],
            "per_class_auc": per_class,
            "brier_scores": calibration["per_class"],
            "brier_references": calibration["reference"],
            "calibration_audit_flag": calibration["audit_flag"],
            "minimum_class_sensitivity": 0.75,
            "classes_below_threshold": "[sensitivity < 0.75]",
            "deployment_cleared": "[True if lower CI >= 0.80]",
        },
        "batch_harmonization": {
            "method": "ComBat (neuroCombat), two steps (16.6.1)",
            "batch_variable": "device_manufacturer",
            "covariates_preserved": ["age_strata", "sex"],
            "n_batches": n_batches,
            "failed_features": harmonization["failed"],
        },
        "open_science": {
            "fair_principles": "Wilkinson et al. (2016)",
            "data_doi": "[OSF DOI on data release]",
            "code_repository": repo,
        },
        "performance_table_path":
            f"{output_dir}/performance_table.csv",
        "calibration_plot_path":
            f"{output_dir}/calibration_plots.png",
    }
    path = f"{output_dir}/validation_report.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Validation report saved: {path}")
    return report


# ── Demonstration on simulated data ──────────────────────────────────
# Runs each function once, on simulated recordings, labels and model
# probabilities, so that the script runs on its own. The numbers mean
# nothing clinically. In a real validation run the inputs come from
# the frozen model of Chapters 12 to 14 and the external centers.
# n_boot is lowered to 200 here to keep the run short; the book uses
# the default of 2000.
if __name__ == '__main__':
    import tempfile

    rng = np.random.default_rng(42)
    classes = ['Normal', 'RP', 'CSNB', 'Cone dystrophy',
               'Diabetic retinopathy', 'Glaucoma']
    k = len(classes)

    # SAP hash check on a stand-in file (no registered hash yet)
    with tempfile.NamedTemporaryFile(suffix='.pdf',
                                     delete=False) as tmp:
        tmp.write(b'Statistical Analysis Plan v2.1 (stand-in)')
    verify_sap_hash(tmp.name)

    # Development set: 120 patients, two eyes each, 3 training centers
    n_pat = 120
    pid = np.repeat(np.arange(n_pat), 2)
    label = np.repeat(rng.integers(0, k, n_pat), 2)
    dev = pd.DataFrame({
        'patient_id': pid, 'label': label,
        'center_id': np.repeat(rng.choice(['C01', 'C02', 'C03'],
                                          n_pat), 2),
        'b_amp_uv': rng.normal(300, 50, 2 * n_pat) - 25 * label,
        'a_amp_uv': rng.normal(150, 25, 2 * n_pat) - 10 * label})
    cv = run_stratified_cv(dev, ['b_amp_uv', 'a_amp_uv'],
                           tolerance=0.05)

    # External set: 60 patients from two external centers
    m = 60
    ext_pid = np.repeat(np.arange(1000, 1000 + m), 2)
    y_ext = np.repeat(rng.integers(0, k, m), 2)
    ext = pd.DataFrame({'center_id': np.repeat(
        rng.choice(['EXT_C04', 'EXT_C05'], m), 2)})
    verify_center_stratification(dev, ext)

    # Simulated calibrated six-class probabilities for the external set
    logits = rng.normal(0, 1, (2 * m, k))
    logits[np.arange(2 * m), y_ext] += 2.0
    proba = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    auc = compute_per_class_auc(y_ext, proba, classes)
    macro = bootstrap_macro_auc_ci(y_ext, proba, ext_pid, n_boot=200)
    cal = compute_calibration_metrics(y_ext, proba, classes)

    # Stage 1 (Abnormal vs Normal) from the same simulated set
    s1_true = (y_ext != 0).astype(int)
    s1_proba = 1 - proba[:, 0]
    table = build_performance_table(
        s1_true, s1_proba, 0.5, ext_pid, y_ext, proba, ext_pid,
        classes, cal['per_class'], n_boot=200)
    print(table.to_string(index=False))

    # ComBat: two training devices plus one external device
    def features(n, shift):
        return rng.normal([300, 150, 60], [50, 25, 12], (n, 3)) + shift

    def covariates(n):
        return pd.DataFrame({
            'age_strata': rng.choice(list(AGE_CODES), n),
            'sex': rng.choice(['M', 'F'], n)})

    train_X = np.vstack([features(60, 0), features(60, 40)])
    train_batch = np.array(['DevA'] * 60 + ['DevB'] * 60)
    train_cov = covariates(120)
    ext_X, ext_cov = features(50, -30), covariates(50)
    train_X_h, ext_X_h = harmonize_training_and_external(
        train_X, train_batch, train_cov, ext_X, ext_cov)
    harm = check_harmonization(
        np.vstack([train_X_h, ext_X_h]),
        np.array(['TRAIN'] * 120 + ['EXT'] * 50),
        ['b_amp_uv', 'a_amp_uv', 'op_sum_uv'])

    build_validation_report(cv, auc, macro, cal, harm,
                            sap_hash='[demo hash]', n_batches=3)
