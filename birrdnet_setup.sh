#!/bin/bash
set -e  # Exit on any error

# ------------------------------
# 1. Install Python 3.11 and venv
# ------------------------------
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# ------------------------------
# 2. Install BirdNET-Analyzer globally
# ------------------------------
# Clone the BirdNET repository globally to /opt
sudo git clone https://github.com/birdnet-team/BirdNET-Analyzer.git /opt/BirdNET-Analyzer
cd /opt/BirdNET-Analyzer

# Install BirdNET globally
sudo python3.11 -m pip install .

# ------------------------------
# 3. Create global Python virtual environment and install BirdNET
# ------------------------------
# Create global venv
sudo mkdir -p /opt/birdnet-venv
sudo python3.11 -m venv /opt/birdnet-venv

# Upgrade pip inside the venv
sudo /opt/birdnet-venv/bin/pip install --upgrade pip

# Clone BirdNET-Analyzer repo
sudo git clone https://github.com/birdnet-team/BirdNET-Analyzer.git /opt/BirdNET-Analyzer

# Install BirdNET into the venv
cd /opt/BirdNET-Analyzer
sudo /opt/birdnet-venv/bin/pip install .

# Optional: Give all users read access to the repo and venv
sudo chmod -R a+rx /opt/BirdNET-Analyzer
sudo chmod -R a+rx /opt/birdnet-venv

echo "✅ BirdNET-Analyzer installed globally and virtual environment created for user."