#!/usr/bin/env bash
# setup.sh — Run once to create venv and install dependencies
set -e

echo "============================================================"
echo "  ERG API — Local Setup"
echo "============================================================"

# Require Python 3.9+
python3 -c "import sys; assert sys.version_info >= (3,9), 'Python 3.9+ required'" \
  || { echo "ERROR: Python 3.9 or newer is required."; exit 1; }

# Create virtual environment
python3 -m venv .venv
echo "✓ Virtual environment created (.venv)"

# Activate and install
source .venv/bin/activate
pip install --upgrade pip --quiet

pip install \
  flask \
  flask-cors \
  numpy \
  pandas \
  scipy \
  scikit-image \
  reportlab \
  --quiet

echo ""
echo "============================================================"
echo "  Setup complete."
echo ""
echo "  To start the server:"
echo "    source .venv/bin/activate"
echo "    python erg_server.py"
echo ""
echo "  Then open:  http://localhost:8080"
echo "============================================================"
