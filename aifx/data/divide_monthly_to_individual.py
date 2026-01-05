#!/usr/bin/env python3
"""
Divide monthly CSV files into individual files per row
Each file named as YY-MM-DD-HH-MM.csv
"""

import os
import sys
import argparse

def divide_monthly_file(monthly_file):
    """Divide a monthly CSV file into individual row files with 300 previous rows."""
    
    folder = os.path.dirname(monthly_file)
    print(f"Processing {monthly_file}...")
    
    # Read all lines into memory first
    with open(monthly_file, 'r') as f:
        all_lines = [line.strip() for line in f if line.strip()]
    
    created_count = 0
    skipped_count = 0
    
    for i, line in enumerate(all_lines):
        # Only create file if there are at least 300 previous rows
        if i < 300:
            skipped_count += 1
            continue
            
        try:
            # Parse date and time: YYYY.MM.DD HH:MM;...
            parts = line.split(';')
            datetime_part = parts[0]  # "YYYY.MM.DD HH:MM"
            
            # Split date and time
            datetime_split = datetime_part.split(' ')
            date_part = datetime_split[0]  # YYYY.MM.DD
            time_part = datetime_split[1]  # HH:MM
            
            # Extract components
            year, month, day = date_part.split('.')
            hour, minute = time_part.split(':')
            
            # Create filename: YYYY-MM-DD-HH-MM-m15.csv
            filename = f"{year}-{month}-{day}-{hour}-{minute}-m15.csv"
            
            # Write 300 previous rows plus current row to file
            output_path = os.path.join(folder, filename)
            with open(output_path, 'w') as out_f:
                # Write 300 previous rows
                previous_rows = all_lines[i-300:i]
                for prev_line in previous_rows:
                    out_f.write(prev_line + '\n')
                
                # Write current line
                out_f.write(line + '\n')
            
            created_count += 1
            
        except Exception as e:
            print(f"Error processing line {i}: {e}")
            continue
    
    print(f"Created {created_count} individual files in {folder} (skipped {skipped_count} files without 300 previous rows)")
    return created_count

def cleanup_individual_files(data_dir):
    """Delete all individual CSV files (YY-MM-DD-HH-MM.csv) but keep monthly files."""
    
    deleted_count = 0
    
    for folder_name in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        # Delete individual files (YYYY-MM-DD-HH-MM-m15.csv format, not the monthly aggregated files)
        for filename in os.listdir(folder_path):
            if filename.endswith("-m15.csv") or (filename.endswith(".csv") and not filename.startswith("US100.f15_") and len(filename.split('-')) >= 5):
                file_path = os.path.join(folder_path, filename)
                os.remove(file_path)
                deleted_count += 1
                if deleted_count <= 5:  # Show first 5 deletions
                    print(f"Removed: {file_path}")
    
    if deleted_count > 5:
        print(f"... and {deleted_count - 5} more files")
    
    print(f"\nTotal individual files deleted: {deleted_count}")

def process_all_monthly_files(data_dir):
    """Process all monthly CSV files in the data directory."""
    
    total_created = 0
    
    for folder_name in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        # Look for monthly CSV files like US100.f15_YYYY.MM.csv
        for filename in os.listdir(folder_path):
            if filename.startswith("US100.f15_") and filename.endswith(".csv"):
                monthly_file = os.path.join(folder_path, filename)
                count = divide_monthly_file(monthly_file)
                total_created += count
    
    print(f"\nTotal individual files created: {total_created}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Divide monthly CSV files into individual files per row')
    parser.add_argument('--cleanup', '-c', action='store_true',
                        help='Remove individual CSV files')
    parser.add_argument('--data-dir', '-d', type=str, default=os.path.dirname(os.path.abspath(__file__)),
                        help='Path to the data directory (default: current script directory)')
    
    args = parser.parse_args()
    
    cleanup = args.cleanup
    if cleanup:
        print("Cleanup mode: Will remove individual CSV files\n")
    
    data_dir = args.data_dir
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found: {data_dir}")
        exit(1)
    
    print(f"Working directory: {data_dir}\n")
    
    # Cleanup individual files if requested
    if cleanup:
        cleanup_individual_files(data_dir)
        print("\nDone!")
        exit(0)
    
    process_all_monthly_files(data_dir)
    print("\nDone!")
