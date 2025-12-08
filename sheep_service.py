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

# Flag to control the service loop
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\nShutting down sheep service...")
    running = False

def write_sheep_file():
    """Write hello world and current time to the sheep file."""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Hello World\nCurrent time: {current_time}\n"
        
        with open("sheep", "w") as f:
            f.write(content)
        
        print(f"Updated sheep file at {current_time}")
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
