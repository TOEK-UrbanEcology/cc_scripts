#!/bin/bash
set -e  # Exit on any error

# ------------------------------
# 1. Prompt for user input
# ------------------------------
read -p "Enter the username to create: " USERNAME
read -p "Enter the DSS UID for $USERNAME (e.g., 3965193 from DSS): " USER_UID
read -s -p "Enter the password for $USERNAME: " PASSWORD
echo ""  # new line after password entry

USER_HOME="/home/$USERNAME"

# ------------------------------
# 2. Create user and configure
# ------------------------------
sudo adduser --uid $USER_UID --ingroup pn29su-dss-0007 --home $USER_HOME --disabled-password --gecos "" $USERNAME
echo "$USERNAME:$PASSWORD" | sudo chpasswd
sudo usermod -aG sudo $USERNAME

# ------------------------------
# 8. Link DSS storage to user's home
# ------------------------------
sudo -u $USERNAME ln -s /mnt/dss/pn29su-dss-0007 $USER_HOME/dss


echo "Created user '$USERNAME', and added DSS to home."