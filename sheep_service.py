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
import subprocess

# Flag to control the service loop
running = True
heartbeat = 1

# Candles directory paths
VERSION = "1.2"
CANDLES_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/candles"
CANDLES_OLD_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/candles_old"
CHARTS_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/candles/charts"
MAGIC_LINES_SCRIPT = "/home/ubuntu/repo/aifx/strategy/magic_lines.py"

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    global heartbeat
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

def get_latest_m15_file():
    """Get the name of the latest m15 file in the candles directory."""
    try:
        if not os.path.exists(CANDLES_DIR):
            return "N/A"
        
        # Get all m15 files
        m15_files = [f for f in os.listdir(CANDLES_DIR) 
                     if os.path.isfile(os.path.join(CANDLES_DIR, f)) and f.endswith('-m15.csv')]
        
        if not m15_files:
            return "N/A"
        
        # Sort by modification time (newest first)
        m15_files.sort(key=lambda f: os.path.getmtime(os.path.join(CANDLES_DIR, f)), reverse=True)
        
        return m15_files[0]
    except Exception as e:
        print(f"Error getting latest m15 file: {e}")
        return "N/A"

def generate_chart_if_missing(m15_filename):
    """Generate chart PNG for m15 file if it doesn't exist."""
    try:
        if m15_filename == "N/A":
            return "N/A - no m15 file"
        
        # Create charts directory if it doesn't exist
        if not os.path.exists(CHARTS_DIR):
            os.makedirs(CHARTS_DIR)
            print(f"Created directory: {CHARTS_DIR}")
        
        # Expected PNG filename: support_YYYY-MM-DD_HH-MM.png
        # From m15 filename: YYYY-MM-DD-HH-MM-m15.csv
        # Extract date and time parts
        parts = m15_filename.replace('-m15.csv', '').split('-')
        if len(parts) >= 5:
            # parts: [YYYY, MM, DD, HH, MM]
            png_filename = f"support_{parts[0]}-{parts[1]}-{parts[2]}_{parts[3]}-{parts[4]}.png"
        else:
            return f"ERROR: invalid filename format"
        
        png_path = os.path.join(CHARTS_DIR, png_filename)
        
        # Check if PNG already exists
        if os.path.exists(png_path):
            return f"EXISTS\n{png_filename}"
        
        # PNG doesn't exist, generate it
        m15_full_path = os.path.join(CANDLES_DIR, m15_filename)
        
        if not os.path.exists(m15_full_path):
            return f"ERROR: CSV not found"
        
        print(f"Generating chart for {m15_filename}...")
        
        # Run magic_lines.py script
        result = subprocess.run(
            ['python3', MAGIC_LINES_SCRIPT, m15_full_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Check if PNG was created
            if os.path.exists(png_path):
                print(f"Successfully generated chart: {png_filename}")
                return f"GENERATED: {png_filename}"
            else:
                print(f"Chart generation completed but PNG not found: {png_filename}")
                return f"ERROR: PNG not created"
        else:
            print(f"Chart generation failed: {result.stderr}")
            return f"ERROR: generation failed"
            
    except subprocess.TimeoutExpired:
        print(f"Chart generation timed out for {m15_filename}")
        return "ERROR: timeout"
    except Exception as e:
        print(f"Error generating chart: {e}")
        return f"ERROR: {str(e)}"

def write_sheep_file():
    """Write hello world and current time to the sheep file."""
    global heartbeat
    try:
        # Move old candle files
        moved_count = move_old_candle_files()
        
        # Count files in both directories
        candles_count = count_files_in_directory(CANDLES_DIR)
        candles_old_count = count_files_in_directory(CANDLES_OLD_DIR)
        
        # Get latest m15 file
        latest_m15 = get_latest_m15_file()
        
        # Check and generate chart if needed
        chart_status = generate_chart_if_missing(latest_m15)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Hello Sheep: {VERSION} heartbeat: {heartbeat}\nCurrent time: {current_time}\n"
        heartbeat += 1
        content += f"Candles: {candles_count} files\n"
        content += f"Candles (old): {candles_old_count} files\n"
        content += f"Latest M15: {latest_m15}\n"
        content += f"Chart status: {chart_status}\n"
        if moved_count > 0:
            content += f"Moved {moved_count} old file(s) this update\n"
        
        with open("sheep", "w") as f:
            f.write(content)
        
        print(f"Updated sheep file at {current_time} - Candles: {candles_count}, Old: {candles_old_count}, Latest M15: {latest_m15}, Chart: {chart_status}")
    except Exception as e:
        print(f"Error writing sheep file: {e}")

def main():
    """Main service loop."""
    global running
    global heartbeat
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Sheep service started. Press Ctrl+C to stop.")
    
    while running:
        write_sheep_file()
        
        # Wait before next update (or exit if stopped)
        for _ in range(1):
            if not running:
                break
            time.sleep(1)
    
    print("Sheep service stopped.")

if __name__ == "__main__":
    main()
