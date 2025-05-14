import wave
import os
import pandas as pd
import numpy as np
import argparse

def cut_wav(row, wav_output_dir, padding):
    # Ensure the wav_files directory exists
    if not os.path.exists(wav_output_dir):
        os.makedirs(wav_output_dir)

    # Open the source wave file
    wav_path = os.path.join(row['INDIR'], row['FOLDER'], row['IN FILE'])
    with wave.open(wav_path, 'rb') as wav_file:
        framerate = wav_file.getframerate()
        start_frame = int(max(0, (row['OFFSET'] - padding) * framerate))
        end_frame = int((row['OFFSET'] + 3 + padding) * framerate)
        wav_file.setpos(start_frame)
        frames = wav_file.readframes(end_frame - start_frame)
        new_wav_name = f"{row['unique_id']}.wav"
        new_wav_path = os.path.join(wav_output_dir, new_wav_name)
        with wave.open(new_wav_path, 'wb') as new_wav_file:
            new_wav_file.setparams(wav_file.getparams())
            new_wav_file.writeframes(frames)

    # Return new row info for output CSV
    return {
        'site': row.get('site', ''),
        'INDIR': ".", 
        'FOLDER': 'wav_files',  # Always set to 'wav_files'
        'IN FILE': new_wav_name,
        'OFFSET': 0,
        'DURATION': 3 + 2 * padding,
        'MANUAL ID': row.get('common_name', ''),
        'confidence': row.get('confidence', ''), 
        'scientific_name': row.get('scientific_name', ''), 
    }

def main():
    parser = argparse.ArgumentParser(description="Create validation data from detection list")
    parser.add_argument("--p", type=float, default=2, help="Padding (seconds) to add to either side of the cut (default: 2)")
    parser.add_argument("--d", type=str, required=True, help="Detection list CSV file")
    parser.add_argument("--o", type=str, required=True, help="Output directory for WAV files and new CSV")

    args = parser.parse_args()
    padding = args.p
    det_list = args.d
    output = args.o
    
    # Create outPath if it doesn't exist
    if not os.path.exists(output):
        os.makedirs(output)

    # Define the wav_files directory inside the output path
    wav_output_dir = os.path.join(output, "wav_files")

    # Read detection list
    df = pd.read_csv(det_list)
    df['unique_id'] = np.arange(len(df))

    # Process each row and collect results
    processed_rows = []
    for _, row in df.iterrows():
        processed_row = cut_wav(row, wav_output_dir, padding)
        processed_rows.append(processed_row)

    # Create new DataFrame with desired columns
    out_df = pd.DataFrame(processed_rows, columns=['site', 'INDIR', 'FOLDER', 'IN FILE', 'OFFSET', 'DURATION', 'MANUAL ID', 'confidence', 'scientific_name'])

    # Save new CSV file in the output directory
    out_csv_path = os.path.join(output, "validation_list.csv")
    out_df.to_csv(out_csv_path, index=False)
    print(f"New CSV written to: {out_csv_path}")

if __name__ == '__main__':
    main()
