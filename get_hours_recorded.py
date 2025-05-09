# import libraries
import pandas as pd
import wave
import os
import argparse

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

# Main function
def main():
    # Create command line arguments for inPath, outPath, metaDataPath and threads
    parser = argparse.ArgumentParser(description="Get hours recorded")
    parser.add_argument("--meta", type=str, help="Metadata csv file path")
    
    args = parser.parse_args()
    
    # Example command
    # python3 sophia_birdnet.py --o greennessresults --meta greenness_sites.csv --threads 18
    # python3 sophia_birdnet.py --o haberer_results --meta Metadata_Haberer.csv --threads 18

    # Set variables from command line arguments
    metaData = args.meta

    # read metaData csv file
    metaDataList = pd.read_csv(metaData)
    
    # Call BirdNET for every site in the metaData csv file. Every row in the file reperesents a site
    for index, row in metaDataList.iterrows():

        # Get path from the path_to_recordings column in the current row
        path = row['path_to_recordings']
        
        row['minutes_recorded'] = total_wav_length(path)
        # Save the DataFrame to a CSV file
        metaDataList.at[index, 'minutes_recorded'] = total_wav_length(path)
        metaDataList.to_csv(metaData, index=False)

if __name__ == '__main__':
    main()
