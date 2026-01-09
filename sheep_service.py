#!/usr/bin/env python3
"""
Simple background service that creates a 'sheep' file with hello world and current time.
"""

# Run in background:
#   nohup python3 /home/ubuntu/repo/sheep_service.py > /dev/null 2>&1 &
# If running in background:
#   pkill -f sheep_service.py

import time
from datetime import datetime, timedelta
import signal
import os
import shutil
import subprocess

from aifx.strategy import decissioner

# Global state
running = True
heartbeat = 1

# Base directory paths
VERSION = "2.2"
REPO_DIR = "/home/ubuntu/repo"
MQL4_FILES_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files"
MQL4_EXPERTS_DIR = "/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Experts"

# Candles directory paths
CANDLES_DIR = os.path.join(MQL4_FILES_DIR, "candles")
CANDLES_OLD_DIR = os.path.join(MQL4_FILES_DIR, "candles_old")
CHARTS_DIR = os.path.join(MQL4_FILES_DIR, "candles", "charts")
CHARTS_OLD_DIR = os.path.join(MQL4_FILES_DIR, "candles", "charts_old")
MAGIC_LINES_SCRIPT = os.path.join(REPO_DIR, "aifx", "strategy", "magic_lines.py")

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    global heartbeat
    print("\nShutting down sheep service...")
    running = False

def move_old_candle_files():
    """Move candle files from previous day(s) to the old directory."""
    try:
        if not os.path.exists(CANDLES_OLD_DIR):
            os.makedirs(CANDLES_OLD_DIR)
        
        if not os.path.exists(CANDLES_DIR):
            return 0
        
        today = datetime.now().date()
        moved_count = 0
        
        for filename in os.listdir(CANDLES_DIR):
            file_path = os.path.join(CANDLES_DIR, filename)
            
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(file_mtime).date()
                
                if file_date < today:
                    dest_path = os.path.join(CANDLES_OLD_DIR, filename)
                    shutil.move(file_path, dest_path)
                    moved_count += 1
        
        if moved_count > 0:
            print(f"Moved {moved_count} old candle file(s)")
        
        return moved_count
    except Exception as e:
        print(f"Error moving old candle files: {e}")
        return 0

def move_old_chart_files():
    """Move chart files from previous day(s) to the old directory."""
    try:
        if not os.path.exists(CHARTS_OLD_DIR):
            os.makedirs(CHARTS_OLD_DIR)
        
        if not os.path.exists(CHARTS_DIR):
            return 0
        
        today = datetime.now().date()
        moved_count = 0
        
        for filename in os.listdir(CHARTS_DIR):
            file_path = os.path.join(CHARTS_DIR, filename)
            
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(file_mtime).date()
                
                if file_date < today:
                    dest_path = os.path.join(CHARTS_OLD_DIR, filename)
                    shutil.move(file_path, dest_path)
                    moved_count += 1
        
        if moved_count > 0:
            print(f"Moved {moved_count} old chart file(s)")
        
        return moved_count
    except Exception as e:
        print(f"Error moving old chart files: {e}")
        return 0

def move_old_sheep_logs():
    """Move sheep action logs from previous day(s) to sheep_old directory."""
    try:
        sheep_logs_dir = os.path.join(REPO_DIR, "sheep")
        sheep_old_dir = os.path.join(REPO_DIR, "sheep_old")
        
        if not os.path.exists(sheep_old_dir):
            os.makedirs(sheep_old_dir)
        
        if not os.path.exists(sheep_logs_dir):
            return 0
        
        today = datetime.now().date()
        moved_count = 0
        
        for filename in os.listdir(sheep_logs_dir):
            if filename.startswith("sheep_actions_") and filename.endswith(".log"):
                file_path = os.path.join(sheep_logs_dir, filename)
                
                if os.path.isfile(file_path):
                    try:
                        # Extract date from filename: sheep_actions_YYYY-MM-DD-HH-MM.log
                        date_part = filename.replace("sheep_actions_", "").replace(".log", "")
                        file_datetime = datetime.strptime(date_part, "%Y-%m-%d-%H-%M")
                        file_date = file_datetime.date()
                        
                        if file_date < today:
                            dest_path = os.path.join(sheep_old_dir, filename)
                            shutil.move(file_path, dest_path)
                            moved_count += 1
                    except ValueError:
                        continue
        
        if moved_count > 0:
            print(f"Moved {moved_count} old sheep log(s)")
        
        return moved_count
    except Exception as e:
        print(f"Error moving old sheep logs: {e}")
        return 0

def count_files_in_directory(directory):
    """Count the number of files in a directory."""
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

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
        
        # Expected PNG filename: YYYY-MM-DD-HH-MM-m15.png
        # From m15 filename: YYYY-MM-DD-HH-MM-m15.csv
        # Simply replace .csv extension with .png
        png_filename = m15_filename.replace('.csv', '.png')
        
        png_path = os.path.join(CHARTS_DIR, png_filename)
        
        # Check if PNG already exists
        if os.path.exists(png_path):
            return f"EXISTS\n{png_filename}"
        
        # PNG doesn't exist, generate it
        m15_full_path = os.path.join(CANDLES_DIR, m15_filename)
        
        if not os.path.exists(m15_full_path):
            return f"ERROR: CSV not found"
        
        print(f"Generating chart for {m15_filename}...")
        
        # Run magic_lines.py script (60 second timeout)
        result = subprocess.run(
            ['python3', MAGIC_LINES_SCRIPT, m15_full_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Check if PNG was created
            if os.path.exists(png_path):
                print(f"Successfully generated chart: {png_filename}\n{png_path}")
                return f"GENERATED: {png_filename}"
            else:
                print(f"Chart generation completed but PNG not found: {png_filename}\n{png_path}")
                return f"ERROR: PNG not created: {png_filename}"
        else:
            print(f"Chart generation failed: {result.stderr}")
            return f"ERROR: generation failed"
            
    except subprocess.TimeoutExpired:
        print(f"Chart generation timed out for {m15_filename}")
        return f"ERROR: timeout (60s)"
    except Exception as e:
        print(f"Error generating chart: {e}")
        return f"ERROR: {str(e)}"

def get_current_market_price(symbol="US100.f"):
    """Get current market price from market_log.txt."""
    try:
        market_log = os.path.join(MQL4_FILES_DIR, "market_log.txt")
        with open(market_log, 'r') as f:
            for line in f:
                if symbol in line:
                    # Parse line like "US100.f: 25696.99 | EURUSD: 1.17505"
                    parts = line.split('|')
                    for part in parts:
                        if symbol in part:
                            price_str = part.split(':')[1].strip()
                            return float(price_str)
        return None
    except Exception as e:
        print(f"Error reading market price: {e}")
        return None

def write_order_to_approved(order_type, candle_time):
    """Write order to approved.txt file."""
    approved_file = os.path.join(MQL4_FILES_DIR, "approved.txt")
 
    try:
        with open(approved_file, 'a') as f:
            f.write(f"US100.f {order_type} 0.01 0 0 0\n")
        print(f"Signal detected: for {candle_time} added {order_type} to approved.txt")
        return order_type
    except Exception as e:
        print(f"Error writing {order_type} to approved.txt: {e}")
        return None

def check_for_signals(candle_time, decision):
    """Check decision, write to approved.txt if found."""
    
    for line in decision.splitlines():
        # Check for BUY signal
        if line.find("BUY") != -1:
            return write_order_to_approved("BUY", candle_time)
        
        # Check for SELL signal
        if line.find("SELL") != -1:
            return write_order_to_approved("SELL", candle_time)
        
    return None

def copy_wdsettings():
    """Copy wdsettings from repo to wine directory."""
    try:
        source = os.path.join(REPO_DIR, "wdsettings")
        destination = os.path.join(MQL4_EXPERTS_DIR, "wdsettings")
        
        if os.path.exists(source):
            shutil.copy2(source, destination)
            print(f"Copied wdsettings from {source} to {destination}")
        else:
            print(f"Warning: wdsettings source file not found at {source}")
    except Exception as e:
        print(f"Error copying wdsettings: {e}")

def write_sheep_file():
    """Write hello world and current time to the sheep file."""
    global heartbeat
    try:
        # Move old candle files
        moved_candles = move_old_candle_files()
        moved_charts = move_old_chart_files()
        
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
        if moved_candles > 0:
            content += f"Moved {moved_candles} old candle file(s) this update\n"
        if moved_charts > 0:
            content += f"Moved {moved_charts} old chart file(s) this update\n"


        # Add magic_lines.log to the content and check for signals
        try:
            with open(os.path.join(REPO_DIR, 'magic_lines.log'), 'r') as log_file:
                log_content = log_file.read()
            content += "\n" + log_content
            
            debug_content = f"\nDebug Info:\n"
            candle_time = latest_m15.replace("-m15.csv", "") if latest_m15 != "N/A" else "unknown"
            debug_content += f"\nCandle Time: {candle_time}\n"

            decision = None
            # If chart was just generated, check for trading signals
            if "GENERATED" in chart_status:
                result = None
                # Copy log to the CHARTS_DIR
                dest_log_path = os.path.join(CHARTS_DIR, candle_time.replace('.csv', '_results.log'))
                with open(dest_log_path, 'w') as f:
                    # Write the result line, what is after "Wynik: "
                    for line in log_content.splitlines():
                        if line.startswith("Wynik:"):
                            result = line.split("Wynik:")[1].strip() + "\n"
                            f.write(result)
                            break
                # Use line that was processed as decissioner input
                decision = decissioner.decision(result)
                content += f"\ndecisionner\n{decision}\n"
                # Write last decision to the decision.log
                with open(os.path.join(REPO_DIR, "decision.log"), "w") as decision_file:
                    decision += f"for andle Time: {candle_time}\n"
                    decision_file.write(decision)

                signal_type = check_for_signals(candle_time, decision)
                if signal_type:
                    if signal_type.startswith("SKIPPED_"):
                        order_type = signal_type.replace("SKIPPED_", "")
                        content += f"\n[SIGNAL SKIPPED] {order_type}\n"
                    else:
                        content += f"\n[SIGNAL DETECTED] Added {signal_type} order to approved.txt\n"
                    with open(os.path.join(REPO_DIR, "sheep", f"sheep_actions_{candle_time}.log"), "w") as f:
                        f.write(content)
        except Exception as e:
            content += f"Could not read magic_lines.log.\n"

        #content += debug_content
        with open(os.path.join(REPO_DIR, "sheep.log"), "w") as f:
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
    
    # Copy wdsettings from repo to wine directory
    copy_wdsettings()
    
    print("Sheep service started. Press Ctrl+C to stop.")
    
    while running:
        # Check settings file for disabled status
        try:
            settings_file = os.path.join(REPO_DIR, "settings")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings_content = f.read().strip().lower()
                    if 'service: disabled' in settings_content:
                        print("Service disabled, waiting 15 seconds...")
                        content = f"Sheep service is currently DISABLED.\nHeartbeat: {heartbeat}\n"
                        with open(os.path.join(REPO_DIR, "sheep.log"), "w") as f:
                            f.write(content)
                        time.sleep(15)
                        continue
        except Exception as e:
            print(f"Error reading settings file: {e}")
        
        write_sheep_file()

        # Move old sheep action logs from previous day(s)
        move_old_sheep_logs()

        # Wait before next update
        time.sleep(1)
    
    print("Sheep service stopped.")

if __name__ == "__main__":
    main()
