#!/usr/bin/env python3
"""
Create monthly folders using US100.f15.csv_data file
"""

import os
import sys
import shutil
from datetime import datetime

def get_months_from_data(data_file):
    """Extract unique year-month combinations from the data file."""
    months = set()
    
    print(f"Reading {data_file}...")
    
    with open(data_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse date from first column: YYYY.MM.DD HH:MM;...
                datetime_part = line.split(';')[0]  # Get "YYYY.MM.DD HH:MM"
                date_part = datetime_part.split(' ')[0]  # Get YYYY.MM.DD
                year_month = '.'.join(date_part.split('.')[:2])  # Get YYYY.MM
                months.add(year_month)
            except Exception as e:
                continue
    
    return sorted(months)

def create_month_folders(data_file="US100.f15.csv_data"):
    """Create folders based on months found in the data file."""
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        return []
    
    months = get_months_from_data(data_file)
    print(f"Found {len(months)} unique months in data\n")
    
    created_folders = []
    
    for folder_name in months:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            created_folders.append(folder_name)
            print(f"Created folder: {folder_name}")
        else:
            print(f"Folder already exists: {folder_name}")
    
    print(f"\nTotal folders created: {len(created_folders)}")
    return created_folders

def cleanup_month_folders(data_file="US100.f15.csv_data"):
    """Delete monthly folders based on months found in the data file."""
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        return []
    
    months = get_months_from_data(data_file)
    print(f"Found {len(months)} unique months in data\n")
    
    deleted_folders = []
    
    for folder_name in months:
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
            deleted_folders.append(folder_name)
            print(f"Deleted folder: {folder_name}")
        else:
            print(f"Folder doesn't exist: {folder_name}")
    
    print(f"\nTotal folders deleted: {len(deleted_folders)}")
    return deleted_folders

if __name__ == "__main__":
    # Check for cleanup flag
    cleanup = False
    if len(sys.argv) > 1 and sys.argv[1] in ['--cleanup', '-c', 'cleanup']:
        cleanup = True
        print("Cleanup mode: Will remove monthly folders\n")
        cleanup_month_folders()
        print("\nDone!")
    else:
        print("Creating monthly folders based on US100.f15.csv_data...\n")
        create_month_folders()
