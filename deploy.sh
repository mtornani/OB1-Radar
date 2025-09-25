#!/bin/bash
set -e

echo "Cleaning..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete

echo "Installing..."
pip install -r requirements.txt

echo "Testing core..."
python -c "from core.engine import main; print('Engine OK')"

echo "Starting services..."
nohup python core/engine.py > /dev/null 2>&1 &
nohup python api/server.py > /dev/null 2>&1 &
nohup python monetize/controversy.py > /dev/null 2>&1 &

echo "Deployed. No logs. No monitoring. Money flows or it doesn't."
