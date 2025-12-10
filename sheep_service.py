#!/usr/bin/env python3
"""
Simple background service that creates a 'sheep' file with hello world and current time.
"""

# Run in background:
#   nohup python3 /home/ubuntu/repo/sheep_service.py > /dev/null 2>&1 &
# If running in background:
#   pkill -f sheep_service.py

import time
from datetime import datetime
import signal
import sys
import os
import shutil

# Flag to control the service loop
running = True
heartbeat = 1

# Candles directory paths
VERSION = "1.1"
CANDLES_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/candles"
CANDLES_OLD_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/candles_old"

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\nShutting down sheep service...")
    running = False

def move_old_candle_files():
    """Move candle files older than 1 day to the old directory."""
    try:
        # Create old directory if it doesn't exist
        if not os.path.exists(CANDLES_OLD_DIR):
            os.makedirs(CANDLES_OLD_DIR)
            print(f"Created directory: {CANDLES_OLD_DIR}")
        
        if not os.path.exists(CANDLES_DIR):
            print(f"Candles directory not found: {CANDLES_DIR}")
            return 0
        
        # Get current time
        current_time = time.time()
        one_day_ago = current_time - (24 * 60 * 60)
        
        moved_count = 0
        
        # Check all files in candles directory
        for filename in os.listdir(CANDLES_DIR):
            file_path = os.path.join(CANDLES_DIR, filename)
            
            # Only process files, not directories
            if os.path.isfile(file_path):
                # Get file modification time
                file_mtime = os.path.getmtime(file_path)
                
                # If file is older than 1 day, move it
                if file_mtime <= one_day_ago:
                    dest_path = os.path.join(CANDLES_OLD_DIR, filename)
                    shutil.move(file_path, dest_path)
                    moved_count += 1
                    print(f"Moved old file: {filename}")
        
        if moved_count > 0:
            print(f"Moved {moved_count} old candle file(s) to {CANDLES_OLD_DIR}")
        
        return moved_count
    except Exception as e:
        print(f"Error moving old candle files: {e}")
        return 0

def count_files_in_directory(directory):
    """Count the number of files in a directory."""
    try:
        if not os.path.exists(directory):
            return 0
        return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
    except Exception as e:
        print(f"Error counting files in {directory}: {e}")
        return 0

def write_sheep_file():
    """Write hello world and current time to the sheep file."""
    try:
        # Move old candle files
        moved_count = move_old_candle_files()
        
        # Count files in both directories
        candles_count = count_files_in_directory(CANDLES_DIR)
        candles_old_count = count_files_in_directory(CANDLES_OLD_DIR)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Hello Sheep: {VERSION} heartbeat: {heartbeat}\nCurrent time: {current_time}\n"
        content += f"Candles: {candles_count} files\n"
        content += f"Candles (old): {candles_old_count} files\n"
        if moved_count > 0:
            content += f"Moved {moved_count} old file(s) this update\n"
        
        with open("sheep", "w") as f:
            f.write(content)
        
        print(f"Updated sheep file at {current_time} - Candles: {candles_count}, Old: {candles_old_count}")
    except Exception as e:
        print(f"Error writing sheep file: {e}")

def main():
    """Main service loop."""
    global running
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Sheep service started. Press Ctrl+C to stop.")
    
    while running:
        write_sheep_file()
        
        # Wait 60 seconds before next update (or exit if stopped)
        for _ in range(60):
            if not running:
                break
            time.sleep(1)
    
    print("Sheep service stopped.")

if __name__ == "__main__":
    main()
