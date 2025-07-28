#!/usr/bin/env python3
"""
Human Voice Detection and Anonymisation Script
Uses BirdNET to detect human voices and zeros out those segments.
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

def setup_logging(verbose=False):
    """Set up logging with console and file handlers based on verbosity."""
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(message)s')
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler - always detailed
    file_handler = logging.FileHandler('anonymise.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - detailed if verbose, basic otherwise
    console_handler = logging.StreamHandler()
    if verbose:
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
    else:
        console_handler.setLevel(logging.WARNING)  # Only show warnings and errors
        console_handler.setFormatter(simple_formatter)
    
    logger.addHandler(console_handler)
    
    return logger

def print_progress(message, verbose=False):
    """Print progress messages to console regardless of verbose setting."""
    if not verbose:
        print(message)

def create_slist():
    """Create a species list file containing only human vocal entries."""
    filename = "species_list.txt"
    with open(filename, "w") as file:
        file.write("Human vocal_Human vocal")
    logger.info(f"Created species list file: {filename}")
    return filename

def run_birdnet_batch(input_dir, output_dir, threads, slist, min_conf, verbose=False):
    """Run BirdNET analysis on entire directory."""
    try:
        command = [
            "python", "-m", "birdnet_analyzer.analyze",
            str(input_dir),
            "-o", str(output_dir),
            "--threads", str(threads), 
            "--combine_results", 
            "--slist", str(slist), 
            "--min_conf", str(min_conf), 
            "--rtype", "csv"
        ]

        logger.info(f"Running BirdNET on: {input_dir}")
        if not verbose:
            print_progress(f"  Running BirdNET analysis...", verbose)
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"BirdNET analysis completed")
        if not verbose:
            print_progress(f"  BirdNET analysis completed", verbose)
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"BirdNET failed: {e}")
        logger.error(f"stderr: {e.stderr}")
        if not verbose:
            print(f"  ERROR: BirdNET analysis failed")
        return False

def parse_results(results_file):
    """Parse BirdNET results to get human voice detections by file."""
    try:
        # Check if file exists
        if not os.path.exists(results_file):
            logger.error(f"Results file does not exist: {results_file}")
            return {}
        
        # Read the CSV with comma separator (based on your header format)
        df = pd.read_csv(results_file, sep=',')
        logger.info(f"Successfully parsed CSV. Columns: {list(df.columns)}")
        logger.info(f"Number of rows: {len(df)}")
        
        # Check if file is empty
        if len(df) == 0:
            logger.info("Results file is empty - no detections found")
            return {}
        
        # Verify we have the expected columns
        required_columns = ['Start (s)', 'End (s)', 'File']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            logger.error(f"Available columns: {list(df.columns)}")
            return {}
        
        # Parse the detections
        file_detections = {}
        for _, row in df.iterrows():
            try:
                filename = row['File']
                start_time = float(row['Start (s)'])
                end_time = float(row['End (s)'])
                
                if filename not in file_detections:
                    file_detections[filename] = []
                file_detections[filename].append((start_time, end_time))
            except Exception as row_error:
                logger.warning(f"Error processing row: {row_error}")
                continue
        
        logger.info(f"Found human voice detections in {len(file_detections)} files")
        if file_detections:
            for filename, segments in file_detections.items():
                logger.info(f"  {filename}: {len(segments)} segments")
        
        return file_detections
        
    except Exception as e:
        logger.error(f"Error parsing results file {results_file}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {}

def zero_segments(input_wav, output_wav, segments, verbose=False):
    """Zero out segments in a WAV file where human voices were detected."""
    try:
        logger.info(f"=== ZEROING SEGMENTS DEBUG ===")
        logger.info(f"Input: {input_wav}")
        logger.info(f"Output: {output_wav}")
        logger.info(f"Segments to zero: {segments}")
        
        if not segments:
            logger.info(f"No human voice segments found in {input_wav}")
            if str(input_wav) != str(output_wav):
                shutil.copy2(input_wav, output_wav)
            return True
        
        # Read WAV file
        with wave.open(str(input_wav), 'rb') as wav_in:
            params = wav_in.getparams()
            framerate = wav_in.getframerate()
            nchannels = wav_in.getnchannels()
            sampwidth = wav_in.getsampwidth()
            nframes = wav_in.getnframes()
            frames = wav_in.readframes(nframes)

        logger.info(f"WAV params: {framerate}Hz, {nchannels}ch, {sampwidth}bytes/sample, {nframes}frames, duration={nframes/framerate:.2f}s")
        
        # Verify it's mono
        if nchannels != 1:
            logger.error(f"Expected mono audio, got {nchannels} channels")
            return False
        
        # Convert to numpy array
        if sampwidth == 2:
            dtype = np.int16
            zero_value = 0
        elif sampwidth == 1:
            dtype = np.uint8
            zero_value = 128
        elif sampwidth == 4:
            dtype = np.int32
            zero_value = 0
        else:
            logger.error(f"Unsupported sample width: {sampwidth}")
            return False
        
        audio = np.frombuffer(frames, dtype=dtype).copy()
        logger.info(f"Audio array: {len(audio)} samples, dtype={dtype}")
        
        # Show some sample values before modification
        logger.info(f"First 10 samples: {audio[:10]}")
        if len(audio) > 10:
            logger.info(f"Sample around middle: {audio[len(audio)//2-5:len(audio)//2+5]}")
        
        # Process each segment
        total_samples_zeroed = 0
        for i, (start_time, end_time) in enumerate(segments):
            logger.info(f"--- Processing segment {i+1}: {start_time:.3f}s to {end_time:.3f}s ---")
            
            # Calculate sample indices
            start_sample = int(start_time * framerate)
            end_sample = int(end_time * framerate)
            
            logger.info(f"Sample range: {start_sample} to {end_sample}")
            logger.info(f"Duration in samples: {end_sample - start_sample}")
            
            # Clamp to valid range
            start_sample = max(0, start_sample)
            end_sample = min(len(audio), end_sample)
            
            if start_sample >= end_sample:
                logger.warning(f"Invalid segment: start_sample {start_sample} >= end_sample {end_sample}")
                continue
                
            if start_sample >= len(audio):
                logger.warning(f"Segment starts beyond audio length: {start_sample} >= {len(audio)}")
                continue
            
            # Show values before zeroing
            logger.info(f"Before zeroing - samples {start_sample} to {start_sample+5}: {audio[start_sample:start_sample+5]}")
            
            # ZERO THE SEGMENT
            audio[start_sample:end_sample] = zero_value
            
            # Show values after zeroing
            logger.info(f"After zeroing - samples {start_sample} to {start_sample+5}: {audio[start_sample:start_sample+5]}")
            
            samples_zeroed = end_sample - start_sample
            total_samples_zeroed += samples_zeroed
            logger.info(f"Zeroed {samples_zeroed} samples ({samples_zeroed/framerate:.3f} seconds)")
        
        logger.info(f"=== TOTAL: {total_samples_zeroed} samples zeroed across {len(segments)} segments ===")
        
        if not verbose:
            if segments:
                print_progress(f"    Processed {Path(input_wav).name} - zeroed {len(segments)} segments", verbose)
            # Don't print anything for files with no segments to reduce clutter
        
        # Write the modified audio
        with wave.open(str(output_wav), 'wb') as wav_out:
            wav_out.setparams(params)
            wav_out.writeframes(audio.tobytes())
        
        logger.info(f"Written modified audio to: {output_wav}")
        
        # Verify the output file was created and has the right size
        if os.path.exists(output_wav):
            output_size = os.path.getsize(output_wav)
            input_size = os.path.getsize(input_wav)
            logger.info(f"Output file size: {output_size} bytes (input was {input_size} bytes)")
        else:
            logger.error(f"Output file was not created: {output_wav}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing {input_wav}: {e}")
        if not verbose:
            print(f"    ERROR processing {Path(input_wav).name}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def get_wav_files(path):
    """Get all WAV files from a directory."""
    wav_files = glob.glob(os.path.join(path, "**", "*.wav"), recursive=True)
    wav_files.extend(glob.glob(os.path.join(path, "**", "*.WAV"), recursive=True))
    return wav_files

def main():
    parser = argparse.ArgumentParser(description="Detect and anonymize human voices in audio files using BirdNET")
    
    parser.add_argument("--meta", "-m", type=str, required=True, 
                       help="Metadata CSV file containing 'path_to_recordings' column")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="Output folder for anonymized files (if not overwriting)")
    parser.add_argument("--threads", type=int, default=1, 
                       help="Number of threads for BirdNET analysis")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite original files instead of creating copies")
    parser.add_argument("--minconf", type=float, default=0.5,
                       help="Minimum confidence threshold for detections")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose console output (default: minimal console output)")
    
    args = parser.parse_args()
    
    # Set up logging based on verbosity
    global logger
    logger = setup_logging(args.verbose)
    
    # Show initial info
    if not args.verbose:
        print("Human Voice Detection and Anonymisation")
        print("======================================")
        print("Detailed logs are being written to 'anonymise.log'")
        print()
    
    # Read metadata
    try:
        metadata_df = pd.read_csv(args.meta)
        if 'path_to_recordings' not in metadata_df.columns:
            logger.error("Metadata CSV must contain 'path_to_recordings' column")
            return 1
        
        if not args.verbose:
            print(f"Loaded metadata for {len(metadata_df)} sites")
            
    except Exception as e:
        logger.error(f"Error reading metadata file: {e}")
        return 1
    
    # Create species list file
    slist = create_slist()
    
    try:
        total_processed = 0
        total_failed = 0
        
        for site_idx, row in enumerate(metadata_df.iterrows(), 1):
            _, row = row  # Unpack the tuple from iterrows()
            
            # Get full path
            path = row['path_to_recordings']
            home_dir = os.path.expanduser("~")
            full_path = os.path.join(home_dir, path)
            
            if not os.path.exists(full_path):
                logger.warning(f"Path not found: {full_path}")
                if not args.verbose:
                    print(f"[{site_idx}/{len(metadata_df)}] SKIPPED: Path not found - {Path(full_path).name}")
                continue
            
            site_name = Path(full_path).name
            
            if not args.verbose:
                print(f"[{site_idx}/{len(metadata_df)}] Processing site: {site_name}")
            
            # Set up output directory
            if args.overwrite:
                output_dir = Path(full_path)
            else:
                output_dir = Path(args.output) if args.output else Path(full_path) / "anonymised_files"
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temp directory for BirdNET results
            temp_dir = output_dir / "temp_birdnet_results"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Processing site: {site_name}")
            
            # Step 1: Run BirdNET
            if not run_birdnet_batch(full_path, temp_dir, args.threads, slist, args.minconf, args.verbose):
                logger.error(f"Failed BirdNET analysis for: {site_name}")
                if not args.verbose:
                    print(f"  FAILED: BirdNET analysis failed")
                continue
            
            # Step 2: Find and move the combined results file
            birdnet_combined = temp_dir / "BirdNET_CombinedTable.csv"
            if not birdnet_combined.exists():
                logger.error(f"BirdNET combined results file not found: {birdnet_combined}")
                # List what files are actually in the temp directory
                temp_files = list(temp_dir.glob("*"))
                logger.error(f"Files in temp directory: {temp_files}")
                if not args.verbose:
                    print(f"  FAILED: Results file not found")
                continue
            
            # Move and rename the results file to the site directory
            human_voices_file = Path(full_path) / "human_voices.csv"
            shutil.move(str(birdnet_combined), str(human_voices_file))
            logger.info(f"Moved results file to: {human_voices_file}")
            
            # Verify the file exists and show its size
            if human_voices_file.exists():
                file_size = human_voices_file.stat().st_size
                logger.info(f"Results file exists and is {file_size} bytes")
            else:
                logger.error(f"Results file does not exist after move: {human_voices_file}")
                if not args.verbose:
                    print(f"  FAILED: Could not create results file")
                continue
            
            # Step 3: Parse results and process files
            file_detections = parse_results(str(human_voices_file))
            wav_files = get_wav_files(full_path)
            
            if not wav_files:
                logger.warning(f"No WAV files found in: {full_path}")
                if not args.verbose:
                    print(f"  No WAV files found")
                continue
            
            if not args.verbose:
                total_detections = sum(len(segments) for segments in file_detections.values())
                files_with_detections = len(file_detections)
                files_without_detections = len(wav_files) - files_with_detections
                print(f"  Found {total_detections} human voice segments in {files_with_detections} files")
                if files_without_detections > 0:
                    print(f"  {files_without_detections} files have no human voice detections")
                print(f"  Processing {files_with_detections} WAV files...")
            
            # Process each WAV file
            site_processed = 0
            site_failed = 0
            
            # Instead of iterating through all wav_files, iterate through files that have detections
            for wav_path_str in file_detections.keys():
                wav_path = Path(wav_path_str)  # Convert string path to Path object
                
                # Debug: Show what we're processing
                logger.info(f"=== Processing WAV file: {wav_path.name} ===")
                logger.info(f"Full path: {wav_path}")
                
                # Determine output path
                if args.overwrite:
                    output_file = wav_path
                else:
                    rel_path = wav_path.relative_to(full_path)
                    output_file = output_dir / rel_path
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Get detections for this file (we know it exists since we're iterating through the keys)
                segments = file_detections[wav_path_str]
                
                logger.info(f"Found {len(segments)} segments for {wav_path.name}")
                if segments:
                    logger.info(f"First few segments: {segments[:3]}...")  # Show first 3 segments
                
                # Zero out human voice segments
                if zero_segments(wav_path, output_file, segments, args.verbose):
                    total_processed += 1
                    site_processed += 1
                else:
                    total_failed += 1
                    site_failed += 1
                        
            if not args.verbose:
                print(f"  Completed: {site_processed} processed, {site_failed} failed")
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            logger.info(f"Site {site_name} complete")
        
        # Final summary
        if not args.verbose:
            print()
            print("=" * 50)
        
        summary_msg = f"Processing complete: {total_processed} files processed, {total_failed} failed"
        logger.info(summary_msg)
        if not args.verbose:
            print(summary_msg)
        
        return 0 if total_failed == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        if not args.verbose:
            print("\nProcessing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if not args.verbose:
            print(f"ERROR: {e}")
        return 1
    finally:
        # Clean up species list file
        if os.path.exists(slist):
            os.remove(slist)

if __name__ == "__main__":
    exit(main())
