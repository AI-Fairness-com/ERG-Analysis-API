"""Chapter 18, Section 18.5.3: difference plot for serial ERGs.

Code from Chapter 18 of "Hands-On Electroretinography in the Age of
AI". Imported by chapter_18.py as difference_plot.
"""

# Difference plot for a serial ERG record (Section 18.5.3)
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_difference_plot(
        visits: pd.DataFrame,      # date, value (sorted by date)
        cor: float,                # Chapter 15 CoR: log10 or ms
        kind: str,                 # "amplitude" or "implicit_time"
        param_name: str,
        patient_id: str,
        output_dir: str = "outputs/longitudinal") -> dict:
    """
    Plot the change between consecutive visits against the CoR band.
    Amplitudes are compared on the log10 scale, implicit times in
    ms. A fall in amplitude or a longer implicit time is progression.
    """
    if kind not in ("amplitude", "implicit_time"):
        raise ValueError("kind must be 'amplitude' or "
                         "'implicit_time'.")
    if len(visits) < 3:
        raise ValueError("A difference plot needs at least three "
                         "visits.")
    os.makedirs(output_dir, exist_ok=True)

    values = visits["value"].to_numpy(dtype=float)
    dates = pd.to_datetime(visits["date"]).dt.strftime("%Y-%m")
    if kind == "amplitude":
        if np.any(values <= 0):
            raise ValueError("Amplitudes must be positive.")
        values = np.log10(values)

    diffs = np.diff(values)              # visit k+1 minus visit k
    means = (values[:-1] + values[1:]) / 2
    worse = diffs < 0 if kind == "amplitude" else diffs > 0
    zones = np.where(np.abs(diffs) < cor, "NO_CHANGE",
                     np.where(worse, "SIGNIFICANT_PROGRESSION",
                              "SIGNIFICANT_IMPROVEMENT"))
    labels = [f"{dates.iloc[i]} to {dates.iloc[i + 1]}"
              for i in range(len(diffs))]

    # Colors and marker shapes both carry the zone.
    style = {"NO_CHANGE": ("#1B7F3B", "o"),
             "SIGNIFICANT_PROGRESSION": ("#B71C1C", "v"),
             "SIGNIFICANT_IMPROVEMENT": ("#1565C0", "^")}
    unit = "log10 units" if kind == "amplitude" else "ms"
    x_unit = "log10 µV" if kind == "amplitude" else "ms"

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.axhspan(-cor, cor, color="#BDBDBD", alpha=0.3,
               label=f"CoR band (±{cor:g} {unit})")
    ax.axhline(0, color="black", linewidth=0.8)
    for m, d, z, lab in zip(means, diffs, zones, labels):
        color, marker = style[z]
        ax.scatter(m, d, color=color, marker=marker, s=70,
                   zorder=3)
        ax.annotate(lab, (m, d), textcoords="offset points",
                    xytext=(6, 5), fontsize=8)
    ax.set_xlabel(f"Mean of the two visits ({x_unit})")
    ax.set_ylabel(f"Change, next visit minus previous ({unit})")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = os.path.join(
        output_dir, f"difference_plot_{patient_id}_{param_name}.png")
    fig.savefig(path, dpi=300)
    plt.close(fig)

    pct = ([round(float((10 ** d - 1) * 100), 1) for d in diffs]
           if kind == "amplitude" else None)
    return {
        "differences": diffs.round(4).tolist(),
        "percent_changes": pct,
        "zones": zones.tolist(),
        "cor": cor,
        "plot_path": path,
    }
