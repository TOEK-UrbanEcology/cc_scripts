#!/bin/bash
set -e  # Exit on any error

# ------------------------------
# 1. System update and install required packages
# ------------------------------
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y nfs-common r-base gdebi-core wget

# ------------------------------
# 2. Create DSS group (if not exists)
# ------------------------------
if ! getent group pn29su-dss-0007 >/dev/null; then
    sudo groupadd --gid 2222 pn29su-dss-0007
fi

# ------------------------------
# 3. Create mount point and configure persistent NFS mount
# ------------------------------
sudo mkdir -p /mnt/dss/pn29su-dss-0007

FSTAB_LINE="dss01nfs14.dss.lrz.de:/dss/dssfs03/tumdss/pn29su/pn29su-dss-0007  /mnt/dss/pn29su-dss-0007  nfs  rsize=1048576,wsize=1048576,hard,tcp,bg,timeo=600,vers=3  0  0"

grep -qxF "$FSTAB_LINE" /etc/fstab || echo "$FSTAB_LINE" | sudo tee -a /etc/fstab

if ! sudo mount -a; then
    echo "Warning: Mount failed. Check network and NFS server."
fi

# ------------------------------
# 4. Install and start RStudio Server
# ------------------------------
if ! dpkg -l | grep -q rstudio-server; then
    wget https://download2.rstudio.org/server/focal/amd64/rstudio-server-2023.12.0-369-amd64.deb
    sudo gdebi -n rstudio-server-2023.12.0-369-amd64.deb
fi

# Start and enable service
sudo systemctl start rstudio-server
sudo systemctl enable rstudio-server

# ------------------------------
# 5. Install Python 3.11 and venv
# ------------------------------
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# ------------------------------
# 6. Install BirdNET-Analyzer globally
# ------------------------------
# Clone the BirdNET repository globally to /opt
# sudo git clone https://github.com/birdnet-team/BirdNET-Analyzer.git /opt/BirdNET-Analyzer
# cd /opt/BirdNET-Analyzer

# Install BirdNET globally
# sudo python3.11 -m pip install .

# ------------------------------
# 7. Create global Python virtual environment and install BirdNET
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

echo "✅ BirdNET-Analyzer installed globally and virtual environment created"

# ------------------------------
# 8. Final message
# ------------------------------
echo "Server setup complete"
echo "To access RStudio Server, a user must be created"
echo "To add a user run add_user.sh"