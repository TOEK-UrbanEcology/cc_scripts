#!/bin/bash
set -e  # Exit on any error

# ------------------------------
# 1. System update and install required packages
# ------------------------------
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y nfs-common r-base gdebi-core wget git

# ------------------------------
# 1b. Add CRAN repository for latest R
# ------------------------------
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9
sudo add-apt-repository -y "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"
sudo apt-get update

# ------------------------------
# 1c. Install latest R globally
# ------------------------------
sudo apt-get install -y r-base

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
    wget https://download2.rstudio.org/server/jammy/amd64/rstudio-server-2024.12.1-563-amd64.deb
    sudo gdebi --non-interactive rstudio-server-2024.12.1-563-amd64.deb
fi

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl start rstudio-server || echo "Warning: Failed to start RStudio Server"
sudo systemctl enable rstudio-server || echo "Warning: Failed to enable RStudio Server"

# ------------------------------
# 5. Install Python 3.11 and venv
# ------------------------------
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# ------------------------------
# 6. Create global Python virtual environment and install BirdNET
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
sudo /opt/birdnet-venv/bin/pip install pandas

# Optional: Give all users read access to the repo and venv
sudo chmod -R a+rwx /opt/birdnet-venv /opt/BirdNET-Analyzer

# ------------------------------
# 7. Download add_user.sh to ubuntu user's home
# ------------------------------
wget -O /home/ubuntu/add_user.sh https://raw.githubusercontent.com/TOEK-UrbanEcology/cc_scripts/main/add_user.sh
sudo chown ubuntu:ubuntu /home/ubuntu/add_user.sh
sudo chmod +x /home/ubuntu/add_user.sh

# ------------------------------
# 8. Download run_birdnet.py to /etc/skel for new users
# ------------------------------
sudo wget -O /etc/skel/run_birdnet.py https://raw.githubusercontent.com/TOEK-UrbanEcology/cc_scripts/main/run_birdnet.py
sudo chmod +x /etc/skel/run_birdnet.py

# ------------------------------
# 9. Final message
# ------------------------------
echo "✅ Server setup complete"
echo "🕊️ BirdNET-Analyzer installed globally and virtual environment created"
echo "📘To access RStudio Server, a user must be created"
echo "➕To add a user get their UID from the DSS and run add_user.sh"