# Server Management Scripts

This repository contains a collection of shell scripts and Python utilities for setting up and managing the compute cloud for use with BirdNET and RStudio Server.

## Available Scripts

### server_setup.sh

Performs initial server configuration:
- Updates the OS
- Installs NFS client, R, and RStudio Server
- Sets up DSS group and mount
- Installs Python 3.11 and BirdNET in a global virtual environment

### add_user.sh

Creates a new user with DSS and RStudio Server access:
- Prompts for username, DSS UID, and password
- Adds user to DSS group and links DSS storage to home

### run_birdnet.py

Runs BirdNET analysis for each site listed in a metadata CSV:
- Processes .wav files per site
- Produces per-site and combined results files
- Logs output and errors

### get_hours_recorded.py

Calculates the total minutes of .wav audio recorded for each site listed in a metadata CSV:
- Updates the metadata file with a new `minutes_recorded` column

### createValidationData.py

Generates validation data from a detection list:
- Cuts .wav files into short clips based on detection offsets
- Produces a new CSV and a directory of validation audio clips

### anonymization.py

(Empty placeholder) Intended for future anonymization utilities.

### project_readme_template.Rmd

A template for project documentation in RMarkdown format:
- Fill in project, publication, and technical details for reproducibility
