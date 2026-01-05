#!/usr/bin/env python3
"""
Divide US100.f15.csv file by month and store in monthly folders
"""

import os
import sys
from collections import defaultdict

def divide_csv_by_month(input_file, base_dir="."):
    """Divide CSV file by month based on date column."""
    
    # Dictionary to store rows by month
    monthly_data = defaultdict(list)
    
    print(f"Reading {input_file}...")
    
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            # Parse date from first column: YYYY.MM.DD,HH:MM,...
            try:
                date_part = line.split(',')[0]  # Get YYYY.MM.DD
                year_month = '.'.join(date_part.split('.')[:2])  # Get YYYY.MM
                
                monthly_data[year_month].append(line)
            except Exception as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    
    print(f"Processed {line_num} lines")
    print(f"Found data for {len(monthly_data)} months\n")
    
    # Write data to monthly folders
    total_written = 0
    for year_month, rows in sorted(monthly_data.items()):
        folder_path = os.path.join(base_dir, year_month)
        
        if not os.path.exists(folder_path):
            print(f"Warning: Folder {folder_path} doesn't exist, creating it...")
            os.makedirs(folder_path)
        
        output_file = os.path.join(folder_path, f"US100.f15_{year_month}.csv")
        
        with open(output_file, 'w') as f:
            for row in rows:
                f.write(row + '\n')
        
        print(f"Wrote {len(rows):5d} rows to {output_file}")
        total_written += len(rows)
    
    print(f"\nTotal rows written: {total_written}")

if __name__ == "__main__":
    # Check for cleanup flag
    cleanup = False
    if len(sys.argv) > 1 and sys.argv[1] in ['--cleanup', '-c', 'cleanup']:
        cleanup = True
        print("Cleanup mode: Will remove existing monthly CSV files before processing\n")
    
    # Run from the data directory
    data_dir = "/home/ubuntu/repo/aifx/data"
    input_file = os.path.join(data_dir, "US100.f15.csv_data")
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        exit(1)
    
    os.chdir(data_dir)
    print(f"Working directory: {os.getcwd()}\n")
    
    # Cleanup all files in monthly folders if requested
    if cleanup:
        print("Cleaning up all files in monthly folders...")
        cleaned_count = 0
        for folder in os.listdir(data_dir):
            folder_path = os.path.join(data_dir, folder)
            if os.path.isdir(folder_path) and '.' in folder:  # Only process folders like YYYY.MM
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Removed: {file_path}")
                        cleaned_count += 1
        print(f"Cleaned {cleaned_count} files")
        print("\nDone!")
        exit(0)
    
    divide_csv_by_month(input_file, data_dir)
    print("\nDone!")
