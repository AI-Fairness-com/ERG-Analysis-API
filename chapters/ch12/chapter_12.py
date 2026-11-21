"""Chapter 12: Classical machine learning models for ERG.

Code from Chapter 12 of "Hands-On Electroretinography in the Age of
AI", in the order of the book: the shared feature pipeline, random
forest, decision tree, SVM, k-NN, calibration, multiple imputation and
the saved pipeline. A simulated training set is built before the first
model so that the script runs on its own; replace it with your data.
Needs graphviz (the Python package and the system program) for the
decision-tree figure. Outputs go to ./outputs and ./models.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SENTINELS = (-9999.0, 9999.0)   # MNAR-physiological codes (Ch. 11)
AMPLITUDE_COLS = ['a_amp_uv', 'b_amp_uv', 'op2_amp_uv',
                  'op3_amp_uv', 'op4_amp_uv', 'op_sum_uv',
                  'phnr_amp_uv']
TIMING_COLS = ['a_implicit_ms', 'b_implicit_ms', 'op2_implicit_ms']


class SentinelRecoder(BaseEstimator, TransformerMixin):
    """Replace MNAR sentinel codes with a neutral value.

    Amplitudes become 0 (an absent wave has no amplitude). Timing
    features become the training-set mean of the real values. The
    absent indicator columns of Chapter 11 keep the finding. The
    means are learned from the training data only.
    """

    def __init__(self, amplitude_cols=AMPLITUDE_COLS,
                 timing_cols=TIMING_COLS):
        self.amplitude_cols = amplitude_cols
        self.timing_cols = timing_cols

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self.timing_means_ = {}
        for col in self.timing_cols:
            if col in X.columns:
                real = X[col][~X[col].isin(SENTINELS)]
                self.timing_means_[col] = real.mean(skipna=True)
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        for col in self.amplitude_cols:
            if col in X.columns:
                X[col] = X[col].mask(X[col].isin(SENTINELS), 0.0)
        for col, mean in self.timing_means_.items():
            X[col] = X[col].mask(X[col].isin(SENTINELS), mean)
        return X

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_


def build_feature_pipeline(scale=True, random_state=42,
                           sample_posterior=False):
    """Preprocessing shared by all classifiers of Chapter 12.

    Steps: (1) recode sentinel values; (2) add one indicator column
    for every feature with NaN values in the training data, and fill
    the NaN values by MICE; (3) optionally standardize. Every step
    is fitted on the data passed to fit() only, so nothing is
    learned from a validation fold. Use scale=False for tree-based
    models. sample_posterior=True draws each filled value at random,
    as multiple imputation needs (Section 12.8.1).
    """
    imputer = IterativeImputer(
        estimator=BayesianRidge(),
        sample_posterior=sample_posterior,
        max_iter=10,
        initial_strategy='mean',
        imputation_order='ascending',
        add_indicator=True,
        keep_empty_features=True,
        random_state=random_state,
    )
    return Pipeline(steps=[
        ('sentinels', SentinelRecoder()),
        ('imputer', imputer),
        ('scaler', StandardScaler() if scale else 'passthrough'),
    ]).set_output(transform='pandas')

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# build_feature_pipeline() is defined in Section 12.1.4

rf = RandomForestClassifier(
    n_estimators=250,
    criterion='gini',
    max_features='sqrt',      # sqrt(n_features) at each question
    oob_score=True,           # out-of-bag estimate (optimistic)
    class_weight='balanced',  # rare classes count more
    random_state=42,
    n_jobs=-1,                # all available CPU cores
)

clf_rf = Pipeline(steps=[
    ('preprocessor', build_feature_pipeline(scale=False)),
    ('classifier', rf),
])

# ── Simulated data so that this script runs on its own ─────────────────
# The book's code uses X_train, y_train and groups_train: the coded
# training matrix of Chapter 11, its labels, and the patient of each
# recording. Real recordings are not shipped with the repository, so the
# block below builds a small simulated set with the same columns, a few
# missing values (NaN) and absent waves (sentinel codes, Chapter 11).
# Replace it with the project's own training data.
import numpy as np
import pandas as pd

_rng = np.random.default_rng(42)
_n_patients, _per_patient = 90, 2                # two eyes per patient
groups_train = np.repeat(np.arange(_n_patients), _per_patient)
y_train = np.repeat(_rng.integers(0, 3, _n_patients), _per_patient)
_shift = np.array([0.0, -40.0, -80.0])[y_train]  # disease lowers amplitudes
_n = len(y_train)
X_train = pd.DataFrame({
    'a_amp_uv': _rng.normal(150, 25, _n) + 0.5 * _shift,
    'b_amp_uv': _rng.normal(300, 50, _n) + _shift,
    'op2_amp_uv': _rng.normal(20, 5, _n) + 0.1 * _shift,
    'op3_amp_uv': _rng.normal(25, 6, _n) + 0.1 * _shift,
    'op4_amp_uv': _rng.normal(15, 4, _n) + 0.1 * _shift,
    'op_sum_uv': _rng.normal(60, 12, _n) + 0.3 * _shift,
    'phnr_amp_uv': _rng.normal(-20, 5, _n),
    'a_implicit_ms': _rng.normal(15, 1, _n) - 0.01 * _shift,
    'b_implicit_ms': _rng.normal(50, 4, _n) - 0.03 * _shift,
    'op2_implicit_ms': _rng.normal(21, 1.5, _n),
    'ba_ratio': _rng.normal(2.0, 0.3, _n),
})
X_train.loc[_rng.choice(_n, 8, replace=False), 'op2_amp_uv'] = np.nan
X_train.loc[_rng.choice(_n, 4, replace=False), 'a_amp_uv'] = -9999.0
X_train.loc[_rng.choice(_n, 4, replace=False), 'a_implicit_ms'] = 9999.0

clf_rf.fit(X_train, y_train)
oob = clf_rf.named_steps['classifier'].oob_score_
print(f'OOB accuracy: {oob:.3f}')

from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold

param_grid = {
    'classifier__n_estimators': [100, 200, 250, 500],
    'classifier__max_depth': [None, 10, 20, 30],
    'classifier__min_samples_split': [2, 5, 10],
    'classifier__max_features': ['sqrt', 'log2'],
}

# Patient-level folds: all recordings of one patient share a fold
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

grid_search = GridSearchCV(
    estimator=clf_rf,
    param_grid=param_grid,
    scoring='roc_auc_ovr',
    cv=cv,
    n_jobs=-1,
    refit=True,
)

grid_search.fit(X_train, y_train, groups=groups_train)

print('Best parameters:', grid_search.best_params_)
print('Best CV AUC:', round(grid_search.best_score_, 4))

import os
import pandas as pd
import matplotlib.pyplot as plt

best_pipeline = grid_search.best_estimator_
best_rf = best_pipeline.named_steps['classifier']
preprocessor = best_pipeline.named_steps['preprocessor']
feature_names = preprocessor.get_feature_names_out()

importances = pd.Series(
    best_rf.feature_importances_,
    index=feature_names,
).sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(10, 7))
importances.head(15).plot(kind='barh', ax=ax, color='steelblue')
ax.set_xlabel('Mean decrease in Gini impurity')
ax.set_title('Random Forest feature importance (top 15)')
ax.invert_yaxis()
plt.tight_layout()
os.makedirs('outputs', exist_ok=True)
plt.savefig('outputs/rf_feature_importance.png', dpi=220)

from sklearn.model_selection import StratifiedGroupKFold
from sklearn.model_selection import cross_validate

cv_results = cross_validate(
    estimator=grid_search.best_estimator_,
    X=X_train,
    y=y_train,
    groups=groups_train,
    cv=StratifiedGroupKFold(n_splits=5, shuffle=True,
                            random_state=42),
    scoring={
        'accuracy': 'accuracy',
        'auc_ovr': 'roc_auc_ovr',
        'f1_macro': 'f1_macro',
    },
    return_train_score=True,
)

for metric, values in cv_results.items():
    if metric.startswith('test'):
        print(f'{metric:15s}: {values.mean():.4f} '
              f'+/- {values.std():.4f}')

import os
import graphviz
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier, export_graphviz

dt = DecisionTreeClassifier(
    criterion='gini',
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=5,
    class_weight='balanced',
    random_state=42,
)

clf_dt = Pipeline(steps=[
    ('preprocessor', build_feature_pipeline(scale=False)),
    ('classifier', dt),
])

clf_dt.fit(X_train, y_train)

# Draw the first four levels (depths 0 to 3) for the Model Card
preprocessor = clf_dt.named_steps['preprocessor']
tree = clf_dt.named_steps['classifier']
dot_data = export_graphviz(
    tree,
    out_file=None,
    feature_names=preprocessor.get_feature_names_out(),
    class_names=[str(c) for c in tree.classes_],
    filled=True,
    rounded=True,
    max_depth=3,
)

os.makedirs('outputs', exist_ok=True)
graph = graphviz.Source(dot_data)
graph.render('outputs/decision_tree_top4', format='png', cleanup=True)

from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

# Platt scaling: a sigmoid fitted to SVM scores from held-out folds
svc = CalibratedClassifierCV(
    SVC(class_weight='balanced', random_state=42),
    method='sigmoid',
    cv=3,
    ensemble=False,
)

clf_svc = Pipeline(steps=[
    ('preprocessor', build_feature_pipeline(scale=True)),
    ('classifier', svc),
])

C_VALUES = [0.1, 1.0, 10.0, 100.0]
svc_grid = [
    {'classifier__estimator__kernel': ['rbf'],
     'classifier__estimator__C': C_VALUES,
     'classifier__estimator__gamma': ['scale', 0.01, 0.001]},
    {'classifier__estimator__kernel': ['linear'],   # no gamma
     'classifier__estimator__C': C_VALUES},
]

grid_svc = GridSearchCV(
    clf_svc, svc_grid,
    scoring='roc_auc_ovr',
    cv=StratifiedGroupKFold(n_splits=5, shuffle=True,
                            random_state=42),
    n_jobs=-1,
    refit=True,
)

grid_svc.fit(X_train, y_train, groups=groups_train)
print('SVM best settings:', grid_svc.best_params_)

import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# scikit-learn 1.8+ selects the penalty by l1_ratio; older versions
# need penalty='l1' or 'l2'
SK_NEW = tuple(int(v) for v in
               sklearn.__version__.split('.')[:2]) >= (1, 8)


def penalty_args(l1):
    if SK_NEW:
        return {'l1_ratio': 1 if l1 else 0}
    return {'penalty': 'l1' if l1 else 'l2'}


# L2 (Ridge): keeps all features; lbfgs solver
lr_l2 = LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000,
                           class_weight='balanced', random_state=42,
                           **penalty_args(l1=False))

# L1 (Lasso): sparse model; saga supports L1 with several classes
lr_l1 = LogisticRegression(solver='saga', C=1.0, max_iter=5000,
                           class_weight='balanced', random_state=42,
                           **penalty_args(l1=True))

clf_lr_l2 = Pipeline([('preprocessor', build_feature_pipeline()),
                      ('classifier', lr_l2)])
clf_lr_l1 = Pipeline([('preprocessor', build_feature_pipeline()),
                      ('classifier', lr_l1)])

clf_lr_l2.fit(X_train, y_train)
clf_lr_l1.fit(X_train, y_train)

# Coefficient table of the L2 model: one row per class
model = clf_lr_l2.named_steps['classifier']
names = clf_lr_l2.named_steps['preprocessor'].get_feature_names_out()
coef_df = pd.DataFrame(model.coef_,
                       index=[str(c) for c in model.classes_],
                       columns=names)
print(coef_df.round(3))
n_zero = (clf_lr_l1.named_steps['classifier'].coef_ == 0).sum()
print('Coefficients set to zero by L1:', n_zero)

from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline

knn = KNeighborsClassifier(n_jobs=-1)   # settings come from the grid

clf_knn = Pipeline([('preprocessor', build_feature_pipeline()),
                    ('classifier', knn)])

# Grid over k (odd values 3 to 19), distance metric, and weights
k_grid = {
    'classifier__n_neighbors': list(range(3, 21, 2)),
    'classifier__metric': ['euclidean', 'manhattan'],
    'classifier__weights': ['uniform', 'distance'],
}

grid_knn = GridSearchCV(
    clf_knn, k_grid, scoring='roc_auc_ovr',
    cv=StratifiedGroupKFold(n_splits=5, shuffle=True,
                            random_state=42),
    n_jobs=-1,
)

grid_knn.fit(X_train, y_train, groups=groups_train)
print('Best k, metric, and weights:', grid_knn.best_params_)

import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.model_selection import cross_val_predict

# Cross-validated predictions on the development set, patient-level
# folds: every recording is scored by a model that did not train on
# its patient. Swap in another tuned pipeline to evaluate it.
model = grid_search.best_estimator_
y_true = np.asarray(y_train)
classes = np.unique(y_true)
class_names = [str(c) for c in classes]

y_prob = cross_val_predict(
    model, X_train, y_true,
    groups=groups_train,
    cv=StratifiedGroupKFold(n_splits=5, shuffle=True,
                            random_state=42),
    method='predict_proba',
)
y_pred = classes[y_prob.argmax(axis=1)]

# Per-class precision, recall, and F1; accuracy comes last
print(classification_report(y_true, y_pred,
                            target_names=class_names, digits=3))

# Confusion matrix heatmap
cm = confusion_matrix(y_true, y_pred, labels=classes)
fig, ax = plt.subplots(figsize=(8, 7))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_names, yticklabels=class_names, ax=ax)
ax.set_ylabel('True label')
ax.set_xlabel('Predicted label')
ax.set_title('Random Forest confusion matrix (cross-validated)')
plt.tight_layout()
os.makedirs('outputs', exist_ok=True)
plt.savefig('outputs/rf_confusion_matrix.png', dpi=220)

import numpy as np
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import label_binarize


def delong_auc_ci(y_binary, scores, alpha=0.05):
    """AUC with a DeLong confidence interval (DeLong et al., 1988).

    Recordings are treated as independent, so recordings from the
    same patient make the interval somewhat too narrow.
    """
    y_binary = np.asarray(y_binary)
    scores = np.asarray(scores)
    pos, neg = scores[y_binary == 1], scores[y_binary == 0]
    m, n = len(pos), len(neg)
    # Structural components: for each positive, the share of
    # negatives it beats (ties count one half), and the reverse
    # for each negative.
    comp = ((pos[:, None] > neg[None, :])
            + 0.5 * (pos[:, None] == neg[None, :]))
    v10 = comp.mean(axis=1)
    v01 = comp.mean(axis=0)
    auc = v10.mean()
    var = np.var(v10, ddof=1) / m + np.var(v01, ddof=1) / n
    z = norm.ppf(1 - alpha / 2)
    half = z * np.sqrt(var)
    return auc, max(0.0, auc - half), min(1.0, auc + half)


y_true_bin = label_binarize(y_true, classes=classes)
macro_auc = roc_auc_score(y_true_bin, y_prob, average='macro')
print(f'Macro-average AUC: {macro_auc:.4f}')
for i, cls in enumerate(class_names):
    auc_i, lo, hi = delong_auc_ci(y_true_bin[:, i], y_prob[:, i])
    print(f'  {cls:12s}: AUC = {auc_i:.4f} '
          f'(95% CI {lo:.4f} to {hi:.4f})')

import math
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

n_classes = len(class_names)
n_cols = 4
n_rows = math.ceil(n_classes / n_cols)
fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 4 * n_rows),
                         squeeze=False)

for i, (cls, ax) in enumerate(zip(class_names, axes.flat)):
    frac_pos, mean_pred = calibration_curve(
        y_true_bin[:, i], y_prob[:, i], n_bins=10, strategy='uniform')
    ax.plot(mean_pred, frac_pos, 's-', color='steelblue', label=cls)
    ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
    ax.set_title(cls, fontsize=9)
    ax.set_xlabel('Mean predicted probability')
    ax.set_ylabel('Fraction of positives')

for ax in list(axes.flat)[n_classes:]:
    ax.set_visible(False)   # hide unused panels

plt.suptitle('Random Forest calibration plots (cross-validated)',
             fontweight='bold')
plt.tight_layout()
plt.savefig('outputs/calibration_plots.png', dpi=220)

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedGroupKFold

# Brier Score per class, against the frequency-only reference p(1 - p)
brier = np.array([brier_score_loss(y_true_bin[:, i], y_prob[:, i])
                  for i in range(len(class_names))])
freq = y_true_bin.mean(axis=0)
reference = freq * (1 - freq)

for cls, b, r in zip(class_names, brier, reference):
    flag = '' if b < r else '  <- no better than class frequency'
    print(f'  {cls:12s}: Brier = {b:.4f} (reference {r:.4f}){flag}')

# Recalibration with Platt's sigmoid and patient-level folds,
# used only if a class fails the check above
splits = list(StratifiedGroupKFold(n_splits=5, shuffle=True,
                                   random_state=42)
              .split(X_train, y_train, groups_train))
calibrated_clf = CalibratedClassifierCV(
    grid_search.best_estimator_, method='sigmoid', cv=splits)
calibrated_clf.fit(X_train, y_train)

import json
import os
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.pipeline import Pipeline


class PooledImputationModel:
    """Average the probabilities of pipelines fitted on different
    MICE draws (multiple imputation, Chapter 11 Section 11.4.1)."""

    def __init__(self, pipelines):
        self.pipelines = pipelines
        self.classes_ = pipelines[0].classes_

    def predict_proba(self, X):
        return np.mean([p.predict_proba(X) for p in self.pipelines],
                       axis=0)

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def fit_multiple_imputation(model, scale, n_imputations=20,
                            seed=42):
    """Fit the classifier once per imputed dataset and pool them."""
    pipelines = []
    for k in range(n_imputations):
        prep = build_feature_pipeline(scale=scale,
                                      random_state=seed + k,
                                      sample_posterior=True)
        pipe = Pipeline(steps=[('preprocessor', prep),
                               ('classifier', clone(model))])
        pipelines.append(pipe.fit(X_train, y_train))
    return PooledImputationModel(pipelines)


def fit_and_serialize(model, scale, config, tag, n_imputations=20):
    """Fit the pooled model on the development set, save it, and
    record it in the config-API dictionary. Reloading the file
    needs the class and function definitions of this chapter."""
    pooled = fit_multiple_imputation(model, scale, n_imputations)

    os.makedirs('models', exist_ok=True)
    model_path = f"models/{config['model_version']}_{tag}.pkl"
    joblib.dump(pooled, model_path)

    prep = pooled.pipelines[0].named_steps['preprocessor']
    config.setdefault('classical_ml', {})[tag] = {
        'model_path': model_path,
        'model_type': type(model).__name__,
        'n_imputations': n_imputations,
        'feature_names': list(prep.get_feature_names_out()),
        'class_names': [str(c) for c in pooled.classes_],
        'sklearn_version': sklearn.__version__,
        'fitted_at': pd.Timestamp.now().isoformat(),
    }
    config_path = f"models/{config['model_version']}_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    return pooled


# Save the tuned Random Forest of Section 12.2.3
config = {'model_version': 'v1'}
best_rf = grid_search.best_estimator_.named_steps['classifier']
rf_final = fit_and_serialize(best_rf, scale=False, config=config,
                             tag='rf')
