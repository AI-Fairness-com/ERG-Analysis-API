"""
erg_server.py — Local Flask server for ERG Analysis API v2.3.2
Run with:  python erg_server.py
Then open: http://localhost:5000
"""

import os
import sys
import time
import json
import tempfile
import traceback
import importlib.util
import threading
import uuid
from collections import OrderedDict

import numpy as np
from flask import Flask, request, Response, send_file
from flask_cors import CORS

from erg_report_generator import generate_clinical_report_pdf

# ── 0. JSON encoder that handles all numpy / Python types ─────────────────────

class SafeEncoder(json.JSONEncoder):
    """Serialise numpy scalars, bools, NaN/Inf safely."""
    def default(self, obj):
        # numpy integer types
        if isinstance(obj, (np.integer,)):
            return int(obj)
        # numpy float types
        if isinstance(obj, (np.floating,)):
            f = float(obj)
            if np.isnan(f) or np.isinf(f):
                return None
            return f
        # numpy bool
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        # numpy arrays → list
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def safe_jsonify(data, status=200):
    """Return a Flask Response with SafeEncoder-serialised JSON."""
    payload = json.dumps(data, cls=SafeEncoder)
    return Response(payload, status=status, mimetype="application/json")


def sanitise(obj):
    """
    Recursively walk dicts/lists and replace un-serialisable values:
      - numpy scalars  → Python int / float / bool
      - NaN / Inf      → None
      - numpy arrays   → list
    """
    if isinstance(obj, dict):
        return {k: sanitise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitise(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (np.isnan(f) or np.isinf(f)) else f
    if isinstance(obj, float):
        return None if (np.isnan(obj) or np.isinf(obj)) else obj
    if isinstance(obj, np.ndarray):
        return sanitise(obj.tolist())
    return obj


# ── 1. Load the pipeline module (strips Colab-only top-level code) ────────────

PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "erg_v2_4_0.py")

def _load_pipeline(path: str):
    """Import pipeline, neutralising Colab-only top-level code."""
    with open(path, "r") as fh:
        source = fh.read()

    replacements = [
        ("from google.colab import files", "# colab import removed"),
        ("import ipywidgets as widgets",   "# ipywidgets import removed"),
        ("from IPython.display import display, clear_output",
         "# IPython import removed"),
    ]
    for old, new in replacements:
        source = source.replace(old, new)

    cell10_marker = "# CELL 10: COLAB UI INTEGRATION"
    idx = source.find(cell10_marker)
    if idx != -1:
        source = source[:idx] + "\n# Cell 10 UI removed for server mode\n"

    spec   = importlib.util.spec_from_loader("erg_pipeline", loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, path, "exec"), module.__dict__)
    return module


print("Loading ERG pipeline …", flush=True)
try:
    pipeline = _load_pipeline(PIPELINE_PATH)
    print(f"✓ Pipeline loaded  (v{pipeline.CONFIG.PIPELINE_VERSION})", flush=True)
except Exception as exc:
    print(f"✗ Failed to load pipeline: {exc}")
    traceback.print_exc()
    sys.exit(1)

ERGAudit            = pipeline.ERGAudit
ERGFilter           = pipeline.ERGFilter
ERGFeatureExtractor = pipeline.ERGFeatureExtractor
ERGReportGenerator  = pipeline.ERGReportGenerator
ERGFHIRGenerator    = pipeline.ERGFHIRGenerator
load_erg_csv        = pipeline.load_erg_csv

# ── 2. Flask app ──────────────────────────────────────────────────────────────

HTML_PATH = os.path.join(os.path.dirname(__file__), "ERG_API_v2_4.html")
if not os.path.exists(HTML_PATH):
    HTML_PATH = os.path.join(os.path.dirname(__file__), "ERG_API_updated.html")

app = Flask(__name__)
CORS(app)

PIPELINE_TIMEOUT_S = 60

# ── Result cache for PDF report generation (Option B) ─────────────────────
# Stores the last N analysis results in memory, keyed by report_id, so the
# "Download Clinical PDF" button can produce a PDF identical to the result
# the user is currently looking at, without re-uploading the CSV. This is a
# local, single-user demo server — a simple bounded dict is sufficient.
RESULT_CACHE = OrderedDict()
RESULT_CACHE_MAX = 20  # oldest entries evicted beyond this


def _cache_put(report_id, full_report, waveform, meta):
    RESULT_CACHE[report_id] = {
        "full_report": full_report,
        "waveform": waveform,
        "meta": meta,
        "ts": time.time(),
    }
    RESULT_CACHE.move_to_end(report_id)
    while len(RESULT_CACHE) > RESULT_CACHE_MAX:
        RESULT_CACHE.popitem(last=False)


def _format_recording_date(date_str):
    """
    Validate and format the recording_date form field for clinical display.
    The HTML <input type="date"> guarantees YYYY-MM-DD or empty string on
    submission in any standards-compliant browser, but this is server-side
    state that ends up in a clinical PDF — it must never trust the client
    alone. Returns a human-readable date string, or a clear placeholder
    if the value is missing, malformed, or in the future.
    """
    from datetime import datetime as _dt

    if not date_str:
        return "Not provided"
    try:
        parsed = _dt.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date submitted"
    if parsed.date() > _dt.now().date():
        return "Invalid date submitted (future date)"
    return parsed.strftime("%d %B %Y")


@app.route("/", methods=["GET"])
def serve_ui():
    return send_file(HTML_PATH, mimetype="text/html")


@app.route("/api/v1/health", methods=["GET"])
def health():
    """Health check — confirms server and pipeline are running."""
    return safe_jsonify({
        "status":  "ok",
        "version": pipeline.CONFIG.PIPELINE_VERSION,
        "pipeline": "ERG Analysis API",
    })


@app.route("/api/v1/analyse", methods=["POST"])
def analyse():
    if "file" not in request.files:
        return safe_jsonify({"message": "No file uploaded"}, 400)

    csv_file        = request.files["file"]
    patient_id      = request.form.get("patient_id", "UNKNOWN")
    recording_date  = request.form.get("recording_date", "")  # YYYY-MM-DD from HTML date input
    age_group       = request.form.get("age_group",  "≤35y")   # Baker stratum
    protocol        = request.form.get("protocol",   "DA 3")
    electrode_type  = request.form.get("electrode_type", "contact_lens")
    pre_stimulus_ms = float(request.form.get("pre_stimulus_ms", 50.0))
    flash_dur_ms    = float(request.form.get("flash_duration_ms", 1.0))
    apply_notch     = request.form.get("apply_notch",   "false").lower() == "true"
    notch_consent   = request.form.get("notch_consent", "false").lower() == "true"
    extract_ops     = request.form.get("extract_ops",   "true").lower()  == "true"

    # Map Baker et al. (2025) age strata → ERGConfig vocabulary for ERGAudit.
    # ERGReportGenerator already understands Baker strings natively (line 1119).
    # ≥60y maps to 80+y so the elderly amplitude caution flag is applied.
    _BAKER_TO_CONFIG = {
        "≤35y":   "18-80y",   # Baker stratum 1
        "36-59y": "18-80y",   # Baker stratum 2
        "≥60y":   "80+y",    # Baker stratum 3 → elderly caution
        "le35":   "18-80y",   # legacy fallback
        "36to59": "18-80y",   # legacy fallback
        "ge60":   "80+y",     # legacy fallback
    }
    audit_age_group = _BAKER_TO_CONFIG.get(age_group, "18-80y")

    suffix = os.path.splitext(csv_file.filename)[1] or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        csv_file.save(tmp.name)
        temp_path = tmp.name

    result  = {}
    error   = {}
    t_start = time.perf_counter()

    def _run():
        try:
            time_ms, signal_uv, fs_hz, _ = load_erg_csv(temp_path)

            flash_onset_sample  = int(pre_stimulus_ms * fs_hz / 1000)
            prestimulus_samples = flash_onset_sample

            if prestimulus_samples > 0 and prestimulus_samples < len(signal_uv):
                noise_rms_uv = float(np.sqrt(
                    np.mean(signal_uv[:prestimulus_samples] ** 2)
                ))
            else:
                noise_rms_uv = 1.0

            auditor      = ERGAudit()
            audit_result = auditor.run_full_audit(
                signal_uv, fs_hz,
                electrode_type=electrode_type,
                prestimulus_samples=prestimulus_samples,
                age_group=audit_age_group,  # ERGConfig vocab
            )

            filter_obj  = ERGFilter()
            hw_cutoff   = audit_result["bandwidth"].get("hardware_cutoff_hz")
            filtered_signal, filter_log = filter_obj.run_filter_pipeline(
                signal_uv, fs_hz,
                apply_notch=apply_notch,
                notch_hz=50.0,
                hardware_cutoff_hz=hw_cutoff,
                user_confirmed_notch=notch_consent,
            )

            op_signal = None
            if extract_ops and audit_result["oscillatory_potentials"]["available"]:
                op_signal = filter_obj.extract_ops(filtered_signal, fs_hz)

            extractor = ERGFeatureExtractor()
            features  = extractor.extract_all_features(
                signal=filtered_signal,
                fs_hz=fs_hz,
                protocol=protocol,
                flash_onset_sample=flash_onset_sample,
                flash_duration_ms=flash_dur_ms,
                op_signal=op_signal,
                noise_rms_uv=noise_rms_uv,
            )

            processing_time_ms = (time.perf_counter() - t_start) * 1000

            report_gen  = ERGReportGenerator()
            full_report = report_gen.generate_full_report(
                features=features,
                audit_results=audit_result,
                electrode_type=electrode_type,
                protocol=protocol,
                age_years=age_group,
                filtered_signal=filtered_signal,
                time_ms=time_ms,
                filter_log=filter_log,
                processing_time_ms=processing_time_ms,
            )

            fhir_gen         = ERGFHIRGenerator()
            fhir_observation = fhir_gen.generate_observation(
                report_id=full_report["layer_4_technical_audit"]["report_id"],
                patient_id=patient_id,
                traffic_light=full_report["layer_1_traffic_light"],
                features=features,
                z_scores=full_report["layer_2_clinical_summary"]["z_scores"],
                audit_results=audit_result,
                electrode_type=electrode_type,
                protocol=protocol,
            )
            full_report["fhir_observation"] = fhir_observation

            tl       = full_report["layer_1_traffic_light"]
            z_scores = full_report["layer_2_clinical_summary"]["z_scores"]

            # Downsample waveform for wire transfer — cap at 1400 points
            # (preserves full 2000 Hz x 700 ms; decimates longer recordings)
            MAX_POINTS = 1400
            n_sig = len(filtered_signal)
            if n_sig > MAX_POINTS:
                step = n_sig // MAX_POINTS
                waveform_t   = time_ms[::step].tolist()
                waveform_sig = filtered_signal[::step].tolist()
                waveform_op  = op_signal[::step].tolist() if op_signal is not None else None
            else:
                waveform_t   = time_ms.tolist()
                waveform_sig = filtered_signal.tolist()
                waveform_op  = op_signal.tolist() if op_signal is not None else None

            result["data"] = sanitise({
                "traffic_light":    tl,
                "features":         features,
                "z_scores":         z_scores,
                "audit_results":    audit_result,
                "fhir_observation": fhir_observation,
                "processing_ms":    processing_time_ms,
                "waveform": {
                    "time_ms":          waveform_t,
                    "amplitude_uv":     waveform_sig,
                    "op_signal":        waveform_op,
                    "pre_stimulus_ms":  pre_stimulus_ms,
                    "fs_hz":            float(fs_hz),
                },
            })

            # Cache for on-demand PDF generation (Option B — see RESULT_CACHE above).
            # Use the FHIR observation id as the cache key; the front end already
            # has access to this via window._lastResult.fhir_observation.id.
            report_id = fhir_observation.get("id")
            if report_id:
                a_wave_t = None
                b_wave_t = None
                if features.get("a_wave_implicit_time_ms") is not None:
                    a_wave_t = pre_stimulus_ms + features["a_wave_implicit_time_ms"]
                if features.get("b_wave_implicit_time_ms") is not None:
                    b_wave_t = pre_stimulus_ms + features["b_wave_implicit_time_ms"]

                cache_waveform = sanitise({
                    "time_ms":         waveform_t,
                    "amplitude_uv":    waveform_sig,
                    "op_signal":       waveform_op,
                    "pre_stimulus_ms": pre_stimulus_ms,
                    "fs_hz":           float(fs_hz),
                    "a_wave": (
                        {"time_ms": a_wave_t, "amp_uv": features.get("a_wave_amplitude_uv")}
                        if a_wave_t is not None else None
                    ),
                    "b_wave": (
                        {"time_ms": b_wave_t, "amp_uv": features.get("b_wave_amplitude_uv")}
                        if b_wave_t is not None else None
                    ),
                })
                cache_meta = {
                    "patient_id":   patient_id,
                    "age_stratum":  age_group,
                    "protocol":     protocol,
                    "electrode":    electrode_type,
                    "recording_date": _format_recording_date(recording_date),
                }
                _cache_put(report_id, result["data"], cache_waveform, cache_meta)

        except Exception as exc:
            error["exc"] = str(exc)
            error["tb"]  = traceback.format_exc()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=PIPELINE_TIMEOUT_S)

    try:
        os.remove(temp_path)
    except OSError:
        pass

    if thread.is_alive():
        return safe_jsonify({
            "message": (
                f"Analysis timed out after {PIPELINE_TIMEOUT_S} s. "
                "The signal may be malformed or excessively long. "
                "Check your CSV file and try again."
            )
        }, 504)

    if error:
        print(error["tb"], flush=True)
        return safe_jsonify({"message": error["exc"]}, 500)

    return safe_jsonify(result["data"], 200)


@app.route("/api/v1/report-pdf/<report_id>", methods=["GET"])
def report_pdf(report_id):
    """
    Generate and return the professional clinical PDF report for a previously
    analysed recording. Relies on RESULT_CACHE populated by /api/v1/analyse —
    see Option B in the report-redesign discussion: the PDF reflects exactly
    what the user saw on screen, with no re-upload required.
    """
    cached = RESULT_CACHE.get(report_id)
    if cached is None:
        return safe_jsonify({
            "message": (
                "No cached result found for this report. Results are kept in "
                "memory only and are cleared on server restart, or evicted "
                "once more than 20 newer analyses have been run. Please "
                "re-run the analysis and download the PDF again."
            )
        }, 404)

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name

        generate_clinical_report_pdf(
            pdf_path,
            cached["full_report"],
            cached["waveform"],
            cached["meta"],
        )

        safe_patient = "".join(
            c for c in str(cached["meta"].get("patient_id", "UNKNOWN"))
            if c.isalnum() or c in ("-", "_")
        ) or "UNKNOWN"
        download_name = f"ERG_Clinical_Report_{safe_patient}_{report_id}.pdf"

        response = send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=download_name,
        )
        # Clean up the temp file once the response has been sent.
        @response.call_on_close
        def _cleanup():
            try:
                os.remove(pdf_path)
            except OSError:
                pass
        return response

    except Exception as exc:
        traceback.print_exc()
        return safe_jsonify({"message": f"PDF generation failed: {exc}"}, 500)


# ── 3. Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n{'='*60}")
    print(f"  ERG Analysis API v{pipeline.CONFIG.PIPELINE_VERSION}")
    print(f"  Open in browser → http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
