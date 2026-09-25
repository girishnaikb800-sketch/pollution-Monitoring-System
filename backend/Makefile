# ==============================================================================
# ECOPULSE - Environmental Pollution Monitoring System Makefile (Backend)
# ==============================================================================

.PHONY: help install run start test simulate clean apk

# Default target
help:
	@echo "=================================================================="
	@echo "  🌿 EcoPulse Pollution Monitoring System - Backend Commands      "
	@echo "=================================================================="
	@echo "  make install   - Install required Python dependencies"
	@echo "  make run       - Start the FastAPI Backend Server (Port 8000)"
	@echo "  make simulate  - Run the live IoT Hardware Sensor Simulator"
	@echo "  make test      - Test API endpoint with live sample reading"
	@echo "  make apk       - Compile the Android App (EcoPulse APK)"
	@echo "  make clean     - Clean __pycache__ and temporary build artifacts"
	@echo "=================================================================="

# Install dependencies
install:
	pip install -r ../requirements.txt

# Run the FastAPI server
run:
	python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Alias for run
start: run

# Run sensor node simulation
simulate:
	python ../simulator/sensor_node.py

# Test API with curl / python request
test:
	python -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/reading/latest').read().decode()), indent=2))"

# Build Android APK
apk:
	python ../compile_apk.py

# Clean Python caches
clean:
	python -c "import os, shutil; [shutil.rmtree(os.path.join(root, d)) for root, dirs, _ in os.walk('..') for d in dirs if d == '__pycache__']"
