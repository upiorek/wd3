#!/usr/bin/env python3
"""
Create monthly folders from 2024.11 to 2026.01
"""

import os
import sys
import shutil
from datetime import datetime

def create_month_folders(start_year=2024, start_month=11, end_year=2026, end_month=1):
    """Create folders named YYYY.MM from start to end date."""
    created_folders = []
    
    year = start_year
    month = start_month
    
    while (year < end_year) or (year == end_year and month <= end_month):
        folder_name = f"{year}.{month:02d}"
        
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            created_folders.append(folder_name)
            print(f"Created folder: {folder_name}")
        else:
            print(f"Folder already exists: {folder_name}")
        
        # Move to next month
        month += 1
        if month > 12:
            month = 1
            year += 1
    
    print(f"\nTotal folders created: {len(created_folders)}")
    return created_folders

def cleanup_month_folders(start_year=2024, start_month=11, end_year=2026, end_month=1):
    """Delete monthly folders and their contents."""
    deleted_folders = []
    
    year = start_year
    month = start_month
    
    while (year < end_year) or (year == end_year and month <= end_month):
        folder_name = f"{year}.{month:02d}"
        
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
            deleted_folders.append(folder_name)
            print(f"Deleted folder: {folder_name}")
        else:
            print(f"Folder doesn't exist: {folder_name}")
        
        # Move to next month
        month += 1
        if month > 12:
            month = 1
            year += 1
    
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
        print("Creating monthly folders from 2024.11 to 2026.01...\n")
        create_month_folders()
