#!/usr/bin/env python3
"""
Divide monthly CSV files into individual files per row
Each file named as YY-MM-DD-HH-MM.csv
"""

import os
import sys
import argparse

def divide_monthly_file(monthly_file, data_dir):
    """Divide a monthly CSV file into individual row files with 300 previous rows."""
    
    folder = os.path.dirname(monthly_file)
    filename = os.path.basename(monthly_file)
    print(f"Processing {monthly_file}...")
    
    # Read all lines into memory first
    with open(monthly_file, 'r') as f:
        all_lines = [line.strip() for line in f if line.strip()]
    
    # Try to load previous month's data (needed for first 300 rows of any month)
    previous_month_lines = []
    # Extract year and month from filename like US100.f15_YYYY.MM.csv
    try:
        year_month_part = filename.split('_')[1].replace('.csv', '')  # YYYY.MM
        year, month = map(int, year_month_part.split('.'))
           
        # Calculate previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
            
        prev_folder = os.path.join(data_dir, f"{prev_year:04d}.{prev_month:02d}")
        prev_file = os.path.join(prev_folder, f"US100.f15_{prev_year:04d}.{prev_month:02d}.csv")
        
        if os.path.exists(prev_file):
            print(f"  Loading previous month data from {prev_file}")
            with open(prev_file, 'r') as f:
                previous_month_lines = [line.strip() for line in f if line.strip()]
        else:
            print(f"  Warning: Previous month file not found: {prev_file}")
    except Exception as e:
        print(f"  Warning: Could not load previous month data: {e}")
    
    created_count = 0
    skipped_count = 0
    
    for i, line in enumerate(all_lines):
        # Check if we have enough previous rows (from current or previous month)
        needed_rows = 300
        available_in_current = i
        
        if available_in_current < needed_rows:
            needed_from_previous = needed_rows - available_in_current
            if len(previous_month_lines) < needed_from_previous:
                # Still not enough data even with previous month
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
            output_filename = f"{year}-{month}-{day}-{hour}-{minute}-m15.csv"
            
            # Write 300 previous rows plus current row to file
            output_path = os.path.join(folder, output_filename)
            with open(output_path, 'w') as out_f:
                # Determine where to get the 300 previous rows
                if i >= 300:
                    # All 300 rows from current month
                    previous_rows = all_lines[i-300:i]
                else:
                    # Need to combine previous month and current month
                    needed_from_previous = 300 - i
                    previous_rows = previous_month_lines[-needed_from_previous:] + all_lines[:i]
                
                for prev_line in previous_rows:
                    out_f.write(prev_line + '\n')
                
                # Write current line
                out_f.write(line + '\n')
            
            created_count += 1
            
        except Exception as e:
            print(f"Error processing line {i}: {e}")
            continue
    
    print(f"Created {created_count} individual files in {folder}")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} files without 300 previous rows")

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
    processed_monthly_files = []
    
    for folder_name in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        # Look for monthly CSV files like US100.f15_YYYY.MM.csv
        for filename in os.listdir(folder_path):
            if filename.startswith("US100.f15_") and filename.endswith(".csv"):
                monthly_file = os.path.join(folder_path, filename)
                count = divide_monthly_file(monthly_file, data_dir)
                total_created += count
                processed_monthly_files.append(monthly_file)

    # Delete monthly source files after processing all months to save space.
    deleted_count = 0
    failed_deletions = 0
    for monthly_file in processed_monthly_files:
        try:
            os.remove(monthly_file)
            deleted_count += 1
        except Exception as e:
            failed_deletions += 1
            print(f"Warning: Could not delete monthly file {monthly_file}: {e}")

    print(f"\nTotal individual files created: {total_created}")
    if processed_monthly_files:
        print(f"Monthly files deleted: {deleted_count}")
        if failed_deletions:
            print(f"Monthly files failed to delete: {failed_deletions}")

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
