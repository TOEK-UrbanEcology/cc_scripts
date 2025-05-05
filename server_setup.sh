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

sudo mount -a

# ------------------------------
# 4. Install and start RStudio Server
# ------------------------------
wget https://download2.rstudio.org/server/focal/amd64/rstudio-server-2023.12.0-369-amd64.deb
sudo gdebi -n rstudio-server-2023.12.0-369-amd64.deb

# Start and enable service
sudo systemctl start rstudio-server
sudo systemctl enable rstudio-server

# ------------------------------
# 5. Final message
# ------------------------------
echo "Server setup complete"
echo "To access RStudio Server, a user must be created"
echo "To add a user run add_user.sh"
echo "To install BirdNET, run birdnet_setup.sh"