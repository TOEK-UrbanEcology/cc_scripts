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

# Read all csv files in the current directory to a list
def readCsv(path):
    csvList = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".csv"):
                csvList.append(os.path.join(root, file))
    csvList = list(dict.fromkeys(csvList))
    return csvList 


# Combine all csv files in the list into one csv with a column for file name
def combineCsvWithFileName(csvList, fileName):
    # Create a new csv file
    with open(fileName, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["start", "end", "scientificName", "commonName", "confidence", "fileName"])
        for file in csvList:
            name = getFileName(file)
            with open(file, "r") as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)
                for row in reader:
                    row.append(name)
                    writer.writerow(row)

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
                    

# Now ignoring the new BIrdNET_analyisi_params.csv file
def combineCsv_plusSite(csvList, fileName, site):
    # Create a new csv file
    with open(fileName, "w", newline='') as f:
        writer = csv.writer(f)
        for i, file in enumerate(csvList):
            # Skip the 'BirdNET_analysis_params.csv' file when combining
            if "BirdNET_analysis_params.csv" in file:
                continue  # Skip this file
            
            with open(file, "r") as csvfile:
                reader = csv.reader(csvfile)
                if i == 0:
                    # Write the header for the first file
                    writer.writerow(next(reader) + ['site'])
                else:
                    # Skip the header for subsequent files
                    next(reader, None)
                for row in reader:
                    # Add the site value to each row
                    writer.writerow(row + [site])


# get file name from path
def getFileName(path):
    fileName = os.path.basename(path)
    # strip everything after the first .
    fileName = fileName[:fileName.find(".")]
    # add .wav to the end
    fileName = fileName + ".wav"
    return fileName

# Get calender week from date
def getCalenderWeek(date):
    #date = datetime.datetime.strptime(date, "%Y-%m-%d")
    date = datetime.datetime.strptime(date, "%d/%m/%Y")
    return date.isocalendar()[1]

# Get date from folder name. Folders are named AAD[1 or 2]_YYYYMMDD_Brandstr
def getDate(folderName):
    res = re.search(r"\d{8}", folderName)
    return res.group()

# Get list of subfolders containing .wav files in the inPath
def getSubDirs(inPath):
    subDirs = []
    for root, dirs, files in os.walk(inPath):
        for dir in dirs:
            if glob.glob(os.path.join(root, dir, "*.wav")):
                subDirs.append(os.path.join(root, dir))
    return subDirs
  
  
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
    
    args = parser.parse_args()

    # Set variables from command line arguments
    outPath = args.o
    metaData = args.meta
    threads = args.threads

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
                "--rtype", "kaleidoscope",
                "--threads", str(threads), 
                "--min_conf", "0.1", 
                "--combine_results"
            ]
            
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
    combineCsv(csv_files, os.path.join(outPath, 'birdnet_results.csv'))

if __name__ == '__main__':
    main()
