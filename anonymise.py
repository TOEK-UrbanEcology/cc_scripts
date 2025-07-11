#!/usr/bin/env python3
"""
Human Voice Detection and Anonymisation Script
Uses BirdNET to detect human voices and zeros out those segments in audio files.
"""

import subprocess
import shutil
import wave
import numpy as np
import os
import argparse
import pandas as pd
import logging
from pathlib import Path
import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('human_voice_anonymizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_slist():
    """Create a species list file containing only human vocal entries."""
    filename = "species_list.txt"
    file_path = Path(filename)
    
    with open(file_path, "w") as file:
        file.write("Human vocal_Human vocal")
    
    logger.info(f"Created species list file: {file_path}")
    return str(file_path)

def detect_humans(input_path, output_path, threads, slist, min_conf, unknown_args):
    """Run BirdNET analysis to detect human voices."""
    try:
        command = [
            "python", "-m", "birdnet_analyzer.analyze",
            input_path,
            "-o", output_path,
            "--threads", str(threads), 
            "--combine_results", 
            "--slist", str(slist), 
            "--min_conf", str(min_conf)
        ] + unknown_args

        logger.info(f"Running BirdNET analysis on: {input_path}")
        logger.debug(f"Command: {' '.join(command)}")
        
        subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"BirdNET analysis completed for: {input_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"BirdNET analysis failed for {input_path}: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during BirdNET analysis: {e}")
        return False

def parse_birdnet_results(results_file):
    """Parse BirdNET results file to extract detection times."""
    try:
        if not os.path.exists(results_file):
            logger.warning(f"Results file not found: {results_file}")
            return []
            
        # Read the BirdNET results file
        df = pd.read_csv(results_file, sep='\t')
        
        # Since we're using a custom species list with only human voices,
        # all detections are human voices and already filtered by min_conf
        detection_segments = df['start_time'].tolist()
        
        logger.info(f"Found {len(detection_segments)} human voice segments in {results_file}")
        return detection_segments
        
    except Exception as e:
        logger.error(f"Error parsing BirdNET results from {results_file}: {e}")
        return []

def zero_segments(input_wav, output_wav, segments, duration=3.0):
    """Zero out segments in a WAV file where human voices were detected."""
    try:
        if not segments:
            logger.info(f"No human voice segments found. Copying {input_wav} to {output_wav}")
            shutil.copy2(input_wav, output_wav)
            return True
        
        # Open the input WAV file
        with wave.open(input_wav, 'rb') as wav_in:
            params = wav_in.getparams()
            framerate = wav_in.getframerate()
            n_frames = wav_in.getnframes()
            n_channels = wav_in.getnchannels()
            sample_width = wav_in.getsampwidth()
            frames = wav_in.readframes(n_frames)

        # Convert frames to numpy array
        if sample_width == 1:
            dtype = np.uint8
        elif sample_width == 2:
            dtype = np.int16
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
            
        audio = np.frombuffer(frames, dtype=dtype)
        
        # Reshape for multi-channel audio
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels)

        # Zero out the segments
        segments_zeroed = 0
        for start_time in segments:
            start_frame = int(start_time * framerate)
            end_frame = int(start_frame + duration * framerate)
            
            # Ensure we don't go beyond the audio length
            end_frame = min(end_frame, len(audio))
            
            if start_frame < len(audio):
                audio[start_frame:end_frame] = 0
                segments_zeroed += 1
                logger.debug(f"Zeroed segment from {start_time}s to {start_time + duration}s")

        # Write the modified audio
        with wave.open(output_wav, 'wb') as wav_out:
            wav_out.setparams(params)
            wav_out.writeframes(audio.tobytes())

        logger.info(f"Successfully anonymized {input_wav} -> {output_wav} ({segments_zeroed} segments zeroed)")
        return True
        
    except Exception as e:
        logger.error(f"Error zeroing segments in {input_wav}: {e}")
        return False

def process_audio_file(wav_file, temp_path, output_path, threads, slist, min_conf, unknown_args, overwrite=False, duration=3.0):
    """Process a single audio file: detect humans and anonymize."""
    wav_path = Path(wav_file)
    output_file = Path(output_path) / wav_path.name
    
    # Check if output file exists and handle overwrite behavior
    if output_file.exists() and not overwrite:
        logger.info(f"Output file {output_file} already exists. Skipping (use --overwrite to force).")
        return True
    
    # Run BirdNET analysis
    if not detect_humans(str(wav_path), temp_path, threads, slist, min_conf, unknown_args):
        return False
    
    # Find the results file
    results_file = Path(temp_path) / f"{wav_path.stem}.BirdNET.results.csv"
    
    # Parse results to get human voice segments
    human_segments = parse_birdnet_results(str(results_file))
    
    # Zero out human voice segments
    return zero_segments(str(wav_path), str(output_file), human_segments, duration)

def get_wav_files(path):
    """Get all WAV files from a path (file or directory)."""
    if os.path.isfile(path) and path.lower().endswith('.wav'):
        return [path]
    elif os.path.isdir(path):
        wav_files = glob.glob(os.path.join(path, "*.wav"))
        wav_files.extend(glob.glob(os.path.join(path, "*.WAV")))
        return wav_files
    else:
        return []

def main():
    """Main function to process audio files and anonymize human voices."""
    parser = argparse.ArgumentParser(
        description="Detect and anonymize human voices in audio files using BirdNET",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python human_voice_anonymizer.py --input /path/to/audio/files --output /path/to/output --meta metadata.csv
  python human_voice_anonymizer.py --input /path/to/audio/files --output /path/to/output --meta metadata.csv --threads 4 --overwrite
        """
    )
    
    parser.add_argument("--input", "-i", type=str, required=True, 
                       help="Input folder containing WAV files or path from metadata CSV")
    parser.add_argument("--output", "-o", type=str, required=True,
                       help="Output folder for anonymized files")
    parser.add_argument("--meta", type=str, 
                       help="Metadata CSV file path with 'path_to_recordings' column")
    parser.add_argument("--threads", type=int, default=1, 
                       help="Number of threads to use for BirdNET analysis")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing output files")
    parser.add_argument("--minconf", type=float, default=0.5,
                       help="Minimum confidence threshold for detections (default: 0.5)")
    parser.add_argument("--duration", type=float, default=3.0,
                       help="Duration in seconds to zero out around each detected human voice (default: 3.0)")
    
    args, unknown_args = parser.parse_known_args()
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for BirdNET results
    temp_path = output_path / "temp"
    temp_path.mkdir(parents=True, exist_ok=True)
    
    # Create species list file
    slist = create_slist()
    
    try:
        processed_files = 0
        failed_files = 0
        
        # Get files to process
        if args.meta:
            # Process files from metadata CSV
            logger.info(f"Processing files from metadata: {args.meta}")
            
            if not os.path.exists(args.meta):
                logger.error(f"Metadata file not found: {args.meta}")
                return 1
                
            metadata_df = pd.read_csv(args.meta)
            
            if 'path_to_recordings' not in metadata_df.columns:
                logger.error("Metadata CSV must contain 'path_to_recordings' column")
                return 1
            
            # Get all WAV files from metadata
            all_wav_files = []
            for _, row in metadata_df.iterrows():
                path = row['path_to_recordings']
                
                # Handle relative paths by expanding home directory
                if path.startswith('~'):
                    full_path = os.path.expanduser(path)
                else:
                    full_path = path
                
                wav_files = get_wav_files(full_path)
                if not wav_files:
                    logger.warning(f"No WAV files found in: {full_path}")
                else:
                    all_wav_files.extend(wav_files)
        
        else:
            # Process files from input directory
            logger.info(f"Processing files from input directory: {args.input}")
            
            if not os.path.exists(args.input):
                logger.error(f"Input directory not found: {args.input}")
                return 1
            
            all_wav_files = get_wav_files(args.input)
            
            if not all_wav_files:
                logger.error(f"No WAV files found in: {args.input}")
                return 1
        
        # Process all WAV files
        total_files = len(all_wav_files)
        for i, wav_file in enumerate(all_wav_files, start=1):
            logger.info(f"Processing file {i}/{total_files}: {wav_file}")
            
            if process_audio_file(wav_file, str(temp_path), str(output_path), 
                                args.threads, slist, args.minconf, unknown_args, 
                                args.overwrite, args.duration):
                processed_files += 1
            else:
                failed_files += 1
        
        # Summary
        logger.info(f"Processing complete: {processed_files} files processed successfully, {failed_files} failed")
        
        return 0 if failed_files == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        # Clean up temporary files
        if temp_path.exists():
            logger.info("Cleaning up temporary files...")
            shutil.rmtree(temp_path)
        
        # Clean up species list file
        if os.path.exists(slist):
            os.remove(slist)

if __name__ == "__main__":
    exit(main())