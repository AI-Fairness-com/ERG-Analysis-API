"""Chapter 18, Section 18.4: linear mixed-effects model.

Code from Chapter 18 of "Hands-On Electroretinography in the Age of
AI". Imported by chapter_18.py as longitudinal_lme.
"""

# Linear mixed-effects model on log amplitude (Section 18.4)
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

Z95 = 1.96


def pct(log_value: float) -> float:
    """Convert a change in natural-log units to percent."""
    return float(100 * (np.exp(log_value) - 1))


def fit_longitudinal_lme(
        df: pd.DataFrame,          # patient_id, time_years,
                                   # amplitude_uv
        param_name: str,
        min_visits: int = 3,       # project choice (Section 18.4.1)
        min_span_yrs: float = 1.0) -> dict:
    """
    Fit a linear mixed-effects model to the natural log of an ERG
    amplitude. Returns the cohort slope, each patient's slope and
    trajectory, and the residual SD, in the form that
    predict_next_visit() needs.
    """
    # Eligibility filter (Section 18.4.1)
    eligible = []
    for pid, grp in df.groupby("patient_id"):
        grp = grp.dropna(subset=["amplitude_uv", "time_years"])
        grp = grp[grp["amplitude_uv"] > 0].sort_values("time_years")
        span = grp["time_years"].max() - grp["time_years"].min()
        if len(grp) >= min_visits and span >= min_span_yrs:
            eligible.append(grp)
        else:
            warnings.warn(f"Patient {pid} excluded: {len(grp)} "
                          f"visits, span {span:.1f} years.")
    if not eligible:
        raise ValueError("No patients meet the eligibility criteria.")
    data = pd.concat(eligible, ignore_index=True)
    data["log_amp"] = np.log(data["amplitude_uv"])

    # Log amplitude ~ time, random intercept and slope per patient
    model = smf.mixedlm("log_amp ~ time_years", data,
                        groups=data["patient_id"],
                        re_formula="~time_years")
    result = model.fit(method="lbfgs")

    names = ["Intercept", "time_years"]
    beta = result.fe_params[names].to_numpy()
    cov_fe = result.cov_params().loc[names, names].to_numpy()
    sigma_e = float(np.sqrt(result.scale))
    pop_slope = float(beta[1])
    pop_ci = result.conf_int().loc["time_years"].to_numpy()

    # Per-patient trajectory. Its covariance adds the fixed-effect
    # covariance and the covariance of the random effects given the
    # data. This is an approximation: it ignores the cross-term.
    patients = {}
    for pid in data["patient_id"].unique():
        b = result.random_effects[pid].to_numpy()
        cov_b = np.asarray(result.random_effects_cov[pid])
        traj = beta + b
        traj_cov = cov_fe + cov_b
        slope = float(traj[1])
        se = float(np.sqrt(traj_cov[1, 1]))
        patients[pid] = {
            "intercept": float(traj[0]),
            "slope": slope,
            "slope_pct_per_year": pct(slope),
            "slope_ci95_pct": [pct(slope - Z95 * se),
                               pct(slope + Z95 * se)],
            "traj_cov": traj_cov.tolist(),
        }

    return {
        "param_name": param_name,
        "pop_slope": pop_slope,
        "pop_slope_pct_per_year": pct(pop_slope),
        "pop_slope_ci95_pct": [pct(pop_ci[0]), pct(pop_ci[1])],
        "sigma_e": sigma_e,
        "patients": patients,
        "n_patients": int(data["patient_id"].nunique()),
        "n_recordings": int(len(data)),
    }


def predict_next_visit(lme_result: dict, patient_id: str,
                       t_future_yrs: float) -> dict:
    """
    95% prediction interval for a patient's next amplitude (µV).
    t_future_yrs is measured from the patient's first recording.
    The interval is built on the log scale and converted back.
    """
    p = lme_result["patients"].get(patient_id)
    if p is None:
        raise ValueError(f"Patient {patient_id} not in the model.")
    x = np.array([1.0, t_future_yrs])
    mean_log = float(x @ np.array([p["intercept"], p["slope"]]))
    var_traj = float(x @ np.array(p["traj_cov"]) @ x)
    se_pred = np.sqrt(var_traj + lme_result["sigma_e"] ** 2)
    return {
        "patient_id": patient_id,
        "t_future_yrs": t_future_yrs,
        "predicted_uv": float(np.exp(mean_log)),
        "pi_lower_uv": float(np.exp(mean_log - Z95 * se_pred)),
        "pi_upper_uv": float(np.exp(mean_log + Z95 * se_pred)),
    }
