# ---------------------------------------------------------------------------- #
# Code for running BirdNET using TOEK specific metadata files
# Author: Andrew J. Fairbairn
#
# Metadata must have a minimum of the following columns:
## |site|lat|lon|start_date|path|
# site: site name to be added to results file
# lat: site latitude for BirdNET filtering
# lon: site longitude for BirdNET filtering
# start_date: start date of the recording, used to calculate week of the year for filtering
# path: path on the DSS in the following format: daa/acoustics/<PROJET>/<SITE>
#
# Example use:
# 1. Enter Terminal
# 2. Activate the BirdNET venv. source /opt/birdnet-venv/bin/activate
# 3. Enter the program call:
# python3 run_birdnet.py --o birdnet_results --meta marlene.csv --threads 18

# Test the different hyperparameters of the model
import csv
import datetime
import os
import subprocess
import shutil
import re
import glob
import pandas as pd
import argparse
import wave
import traceback
import logging
import sys

# Get date from filename
def extract_date(filename):
    m = re.search(r'(\d{8})', filename)
    return m.group(1) if m else None

# Get time from filename
def extract_time(filename):
    name_without_ext = filename.replace('.wav', '').replace('.WAV', '')
    match = re.search(r'\d{8}.*?(\d{6})(?=\D|$)', name_without_ext)
    return match.group(1) if match else None

# Combine all .csv files in the csvList into one csv file using the same headings as the first file in the list
def combineCsv(csvList, fileName):
    # Create a new csv file
    with open(fileName, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for i, file in enumerate(csvList):
            with open(file, "r", newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # Skip the header of all but the first file
                if i != 0:
                    next(reader, None)  # Skip the header row
                for row in reader:
                    writer.writerow(row)
                    
# Get calender week from date
def getCalenderWeek(date):
    #date = datetime.datetime.strptime(date, "%Y-%m-%d")
    date = datetime.datetime.strptime(date, "%d/%m/%Y")
    return date.isocalendar()[1]

# Return the total length of all .wav files in a folder in minutes.
def total_wav_length(directory):
    total_length = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.wav'):
                try:
                    with wave.open(os.path.join(root, file), 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        duration = frames / float(rate)
                        total_length += duration
                except wave.Error:
                    print(f"Could not open {os.path.join(root, file)} as a .wav file")
    total_length = total_length / 60
    return total_length

# Move the combined results file to the outPath, rename it to site.csv and add a 'site' column
def move_and_rename_results(site, tempPath, outPath):
    # Step 1: Set the desired filename and savePath
    filename = str(site) + ".csv"  # Filename based on the site name
    savePath = os.path.join(outPath, filename)  # The final path to save the file

    # Step 2: Search for the combined results file recursively in tempPath
    combined_results_file = None
    for root, dirs, files in os.walk(tempPath):
        if "BirdNET_Kaleidoscope.csv" in files:
            combined_results_file = os.path.join(root, "BirdNET_Kaleidoscope.csv")
            break  # Stop searching once the file is found

    # Step 3: Check if the combined results file exists
    if combined_results_file:
        # Step 4: Load the CSV file into a DataFrame
        df = pd.read_csv(combined_results_file)

        # Step 5: Add the 'site' column to the DataFrame
        df['site'] = site  # Adding the site name as a column

        # Step 6: Save the updated DataFrame with the new column and new filename
        df.to_csv(savePath, index=False)
        print(f"File saved as {savePath}")
    else:
        print(f"Error: BirdNET_Kaleidoscope.csv not found in {tempPath} or its subfolders.")

# Main function
def main():
    # Create command line arguments for inPath, outPath, metaDataPath and threads
    parser = argparse.ArgumentParser(description="Run BirdNET on a folder of .wav files")
    parser.add_argument("--o", type=str, help="Output folder path")
    parser.add_argument("--meta", type=str, help="Metadata csv file path")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads to use")
    parser.add_argument("--min_conf", type=float, default=0.1, help="Minimum confidence threshold. Values in [0.00001, 0.99]")
    parser.add_argument("--rtype", type=str, default="kaleidoscope", help="Specifies output format. Values in [‘table’, ‘audacity’, ‘kaleidoscope’, ‘csv’]")
    parser.add_argument("--results_name", type=str, default="birdnet_results.csv", help="Final combined results CSV file name")

    args, unknown_args = parser.parse_known_args()

    # Set variables from command line arguments
    outPath = args.o
    metaData = args.meta
    threads = args.threads
    min_conf = args.min_conf
    rtype = args.rtype

    # read metaData csv file
    metaDataList = pd.read_csv(metaData)
    
    # Create outPath if it doesn't exist
    if not os.path.exists(outPath):
        os.makedirs(outPath)

    # Set up logging
    log_path = os.path.join(outPath, "run_output.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),        # Save to file
            logging.StreamHandler(sys.stdout)     # Also print to console
        ]
    )

    # Call BirdNET for every site in the metaData csv file. Every row in the file reperesents a site
    for i, (index, row) in enumerate(metaDataList.iterrows(), start=1):
        
        try:
            # Print and log which site of total is being processed
            logging.info(f"Processing site {i} of {len(metaDataList)}: {row['site']}")

            # Create tempPath if it doesn't exist as the outPath plus /temp using os.path.join
            tempPath = os.path.join(outPath, "temp")
            if not os.path.exists(tempPath):
                os.makedirs(tempPath)

            # Get path from the path_to_recordings column in the current row
            path = row['path_to_recordings']

            # Get current users home directory
            home_dir = os.path.expanduser("~")

            # Create full path
            full_path = os.path.join(home_dir, path)
            
            row['minutes_recorded'] = total_wav_length(full_path)
            # Save the DataFrame to a CSV file
            metaDataList.at[index, 'minutes_recorded'] = total_wav_length(full_path)
            metaDataList.to_csv(metaData, index=False)

            # Get lat and lon for the current row
            lat = row['lat']
            lon = row['lon']

            # Get start date from column start_date and get week of the year from the date
            date = row['start_date']
            date = datetime.datetime.strptime(date, "%d/%m/%Y")
            date = date.strftime("%d/%m/%Y")
            week = getCalenderWeek(date)
            
            # Extract site name
            site = row['site']
            
            command = [
                "python", "-m", "birdnet_analyzer.analyze",
                full_path,
                "-o", tempPath,
                "--lat", str(lat),
                "--lon", str(lon),
                "--week", str(week),
                "--rtype", str(rtype),
                "--threads", str(threads), 
                "--min_conf", str(min_conf), 
                "--combine_results"
            ] + unknown_args  # <-- Append any extra args
            
            # Join the command list into a single string for printing
            command_str = " ".join(command)
            
            # Print the command as a string
            logging.info(f"Call: {command_str}")
            output = subprocess.check_output(command)
            # print("Output:", output.decode("utf-8"), end='\r', flush=True)
            logging.info(f"Output: {output.decode('utf-8')}")
            
            # assuming 'date' is a string in the format dd/mm/yyyy
            date = datetime.datetime.strptime(date, "%d/%m/%Y")
            
            # Call the function to move, rename, and add 'site' column to the results
            move_and_rename_results(site, tempPath, outPath)

        except Exception as e:
            log_file = os.path.join(outPath, "error_log.txt")
            with open(log_file, "a") as log:
                log.write(f"Failed processing site {row['site']} (index {index}):\n")
                log.write(traceback.format_exc())
                log.write("\n\n")
            print(f"Error processing site {row['site']}. See error_log.txt for details.")

        finally:
            if os.path.exists(tempPath):
                shutil.rmtree(tempPath) # Removes the directory tree of the results folder after the csv file is created

    # List all the CSV files in the outPath folder with full path
    csv_files = [os.path.join(outPath, f) for f in os.listdir(outPath) if f.endswith('.csv')]

    # Call the combineCsv function with the list of CSV files and output file name
    combineCsv(csv_files, os.path.join(outPath, args.results_name))

    # Add date and timestamp columns based of filename
    results_file = os.path.join(outPath, args.results_name)
    df = pd.read_csv(results_file)
    df['date'] = df['IN FILE'].apply(extract_date)
    df['timestamp'] = df['IN FILE'].apply(extract_time)
    df.to_csv(results_file, index=False)

    # Log saving information
    logging.info(f"Final results saved to {results_file}")

if __name__ == '__main__':
    main()
