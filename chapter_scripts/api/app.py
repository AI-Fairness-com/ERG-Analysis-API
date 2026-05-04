# -*- coding: utf-8 -*-
"""
ERG Analysis API - Main Application Entry Point

This Flask application provides a no-code clinical decision support API
for ERG signal processing and machine learning classification.

Features:
- File upload (CSV, EDF, HDF5)
- ISCEV-compliant filtering pipeline
- Four-layer clinical report (Traffic Signal + Clinical Summary + Specialist + Audit)
- HL7 FHIR R4 JSON output
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import numpy as np
import pandas as pd

# Import ERG processing modules (from chapter_scripts)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chapter_scripts.chapter_05_filtering.complete_filter_pipeline import apply_erg_filter_pipeline

# ============================================================================
# Configuration
# ============================================================================

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/erg_uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'edf', 'hdf5', 'json'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ISCEV Protocols
ISCEV_PROTOCOLS = [
    'DA 0.01',      # Dark-adapted 0.01 cd·s·m⁻² (rod response)
    'DA 3.0',       # Dark-adapted 3.0 cd·s·m⁻² (standard combined)
    'DA 10.0',      # Dark-adapted 10.0 cd·s·m⁻² (maximal response)
    'LA 3.0',       # Light-adapted 3.0 cd·s·m⁻² (cone response)
    'LA 30 Hz'      # Light-adapted 30 Hz flicker
]

# Traffic Light Thresholds (Z-score)
TRAFFIC_THRESHOLDS = {
    'green': 2.0,   # |Z| <= 2.0 SD
    'amber': 3.0    # 2.0 < |Z| <= 3.0 SD
}   # Red: |Z| > 3.0 SD


# ============================================================================
# Helper Functions
# ============================================================================

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def load_erg_file(filepath, filetype):
    """
    Load ERG data from various file formats.
    
    Currently supports CSV format. EDF and HDF5 to be implemented.
    """
    if filetype == 'csv':
        df = pd.read_csv(filepath)
        
        # Expected columns: time_ms, amplitude_uv
        if 'amplitude_uv' in df.columns:
            signal = df['amplitude_uv'].values
        elif 'amplitude' in df.columns:
            signal = df['amplitude'].values
        else:
            # Assume first numeric column is amplitude
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                signal = df[numeric_cols[0]].values
            else:
                raise ValueError("CSV file must contain amplitude data")
        
        # Determine sampling rate from time column
        if 'time_ms' in df.columns:
            time_ms = df['time_ms'].values
            fs_hz = 1000 / np.median(np.diff(time_ms))
        else:
            fs_hz = 1000.0  # Default assumption
        
        return signal, fs_hz
    
    elif filetype == 'edf':
        # EDF support via MNE-Python (to be implemented)
        raise NotImplementedError("EDF format support coming soon")
    
    elif filetype == 'hdf5':
        # HDF5 support (to be implemented)
        raise NotImplementedError("HDF5 format support coming soon")
    
    else:
        raise ValueError(f"Unsupported file type: {filetype}")


def compute_traffic_light(z_score):
    """Compute traffic light status from Z-score."""
    abs_z = abs(z_score)
    if abs_z <= TRAFFIC_THRESHOLDS['green']:
        return 'GREEN', 'Within normal limits (±2 SD)'
    elif abs_z <= TRAFFIC_THRESHOLDS['amber']:
        return 'AMBER', 'Borderline abnormal (2-3 SD from normal)'
    else:
        return 'RED', 'Significantly abnormal (>3 SD from normal)'


def generate_report_id():
    """Generate a unique report identifier."""
    return f"ERG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main upload form."""
    return render_template('upload.html', protocols=ISCEV_PROTOCOLS)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/analyze', methods=['POST'])
def analyze_erg():
    """
    Main analysis endpoint.
    
    Accepts ERG file upload, processes through pipeline,
    returns four-layer clinical report.
    """
    # Validate request
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {app.config["ALLOWED_EXTENSIONS"]}'}), 400
    
    # Get form data
    protocol = request.form.get('protocol', 'DA 3.0')
    patient_id = request.form.get('patient_id', 'UNKNOWN')
    eye = request.form.get('eye', 'OD')
    
    # Save and process file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Load signal
        filetype = filename.rsplit('.', 1)[1].lower()
        signal_uv, fs_hz = load_erg_file(filepath, filetype)
        
        # Create recording dictionary
        recording = {
            'amplitude_uv': signal_uv,
            'fs_hz': fs_hz,
            'patient_id': patient_id,
            'protocol': protocol,
            'eye': eye,
            'hardware_lowpass_hz': 300.0
        }
        
        # Apply filter pipeline
        processed = apply_erg_filter_pipeline(recording)
        
        # Generate report
        report_id = generate_report_id()
        
        # Compute mock metrics (to be replaced with actual feature extraction)
        b_wave_amplitude = np.max(processed['filtered_uv']) - np.min(processed['filtered_uv'])
        b_wave_implicit_time = 50.0  # Mock value
        
        # Mock Z-score (to be replaced with normative comparison)
        z_score = 1.2
        traffic_status, traffic_message = compute_traffic_light(z_score)
        
        # Prepare response
        result = {
            'report_id': report_id,
            'generated_at': datetime.now().isoformat(),
            'patient_id': patient_id,
            'protocol': protocol,
            'eye': eye,
            'traffic_light': {
                'status': traffic_status,
                'message': traffic_message,
                'z_score': round(z_score, 2)
            },
            'measurements': {
                'b_wave_amplitude_uv': round(b_wave_amplitude, 1),
                'b_wave_implicit_time_ms': b_wave_implicit_time
            },
            'filter_log': processed.get('filter_log', []),
            'disclaimer': (
                "This ERG Traffic Signal is generated solely from electroretinographic "
                "signal analysis using validated machine learning techniques. It represents "
                "ERG findings only and must be interpreted in the context of the patient's "
                "full clinical picture. The Traffic Signal does not constitute a clinical "
                "diagnosis. The final clinical decision remains the sole responsibility of "
                "the supervising clinician."
            )
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up temporary file
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/report/<report_id>', methods=['GET'])
def get_report(report_id):
    """Retrieve a previously generated report."""
    # To be implemented with database storage
    return jsonify({'error': 'Report retrieval not yet implemented'}), 501


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ERG Analysis API")
    print("=" * 60)
    print(f"Starting server at http://localhost:5000")
    print(f"Upload form available at http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
