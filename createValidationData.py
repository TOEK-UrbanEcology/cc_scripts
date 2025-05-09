import wave
import os
import pandas as pd
import numpy as np

# Output locaiton
output = "lisa_species/files"

# Read csv file
to_check = pd.read_csv("lisa_species/list_for_lisa.csv")

# Add id column
to_check['unique_id'] = np.arange(len(to_check))

# Add 'MANUAL ID' column with blank values
to_check['MANUAL ID'] = ''

def save_wave_file(row):
    # Create a new directory output if it does not exist
    if not os.path.exists(output):
        os.makedirs(output)
        
    # Open the wave file
    wav_file = wave.open(os.path.join(row['INDIR'], row['FOLDER'], row['IN FILE']), 'rb')

    # Calculate start and end frames
    start_frame = int(max(0, (row['OFFSET'] - 2) * wav_file.getframerate()))
    end_frame = int((row['OFFSET'] + 5) * wav_file.getframerate())

    # Set the position to start_frame and read frames
    wav_file.setpos(start_frame)
    frames = wav_file.readframes(end_frame - start_frame)

    # Create a new wave file and write frames
    new_wav_file = wave.open(os.path.join(output, f"{row['unique_id']}.wav"), 'wb')
    new_wav_file.setparams(wav_file.getparams())
    new_wav_file.writeframes(frames)

    # Close the wave files
    wav_file.close()
    new_wav_file.close()
    
    # Update OFFSET to 0 and DURATION to 7
    row['OFFSET'] = 0
    row['DURATION'] = 7
    
    # Update 'IN FILE' to 'unique_id.wav' after processing
    row['IN FILE'] = f"{row['unique_id']}.wav"
    
    return row

# Apply the function to each row in the DataFrame
to_check.apply(save_wave_file, axis=1)

# Save DataFrame to a new CSV file
to_check.to_csv("lisa_species/list_for_lisa.csv", index=False)

