# -*- coding: utf-8 -*-
"""
ERG Analysis API - Main Application Entry Point
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import numpy as np
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp/erg_uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'edf', 'hdf5'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ISCEV_PROTOCOLS = ['DA 0.01', 'DA 3.0', 'DA 10.0', 'LA 3.0', 'LA 30 Hz']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('upload.html', protocols=ISCEV_PROTOCOLS)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'version': '1.0.0'})

@app.route('/analyze', methods=['POST'])
def analyze_erg():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    return jsonify({'message': 'Analysis complete (stub)'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
