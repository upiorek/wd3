#!/usr/bin/env python3
import subprocess
import os
from datetime import datetime

def capture_screenshot():
    """Capture a screenshot and save it to ~/scrs folder"""
    
    # Create scrs directory if it doesn't exist
    scrs_dir = os.path.expanduser("~/scrs")
    os.makedirs(scrs_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"screenshot-{timestamp}.png"
    filepath = os.path.join(scrs_dir, filename)
    
    # Set environment variables for X display
    env = os.environ.copy()
    env['DISPLAY'] = ':1'
    env['XAUTHORITY'] = '/home/ubuntu/.Xauthority'
    
    try:
        # Unlock session
        subprocess.run(['loginctl', 'unlock-session', '2'], check=False)
        
        # Wake up display
        subprocess.run(['xset', 'dpms', 'force', 'on'], env=env, check=True)
        subprocess.run(['xset', 's', 'reset'], env=env, check=True)
        
        # Wait a moment for display to wake up
        subprocess.run(['sleep', '1'], check=True)
        
        # Capture screenshot
        subprocess.run(['scrot', filepath], env=env, check=True)
        
        print(f"Screenshot saved: {filepath}")
        
        # Clean up old screenshots - keep only 500 most recent
        try:
            files = []
            for f in os.listdir(scrs_dir):
                if f.startswith("screenshot-") and f.endswith(".png"):
                    full_path = os.path.join(scrs_dir, f)
                    if os.path.isfile(full_path):
                        files.append((full_path, os.path.getmtime(full_path)))
            
            # If we have more than 500 files, delete the oldest ones
            if len(files) > 500:
                # Sort by modification time (oldest first)
                files.sort(key=lambda x: x[1])
                
                # Calculate how many to delete
                files_to_delete = len(files) - 500
                
                # Delete the oldest files
                for i in range(files_to_delete):
                    os.remove(files[i][0])
                    print(f"Deleted old screenshot: {os.path.basename(files[i][0])}")
                
                print(f"Cleaned up {files_to_delete} old screenshot(s), kept 500 most recent")
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        
        return filepath
        
    except subprocess.CalledProcessError as e:
        print(f"Error capturing screenshot: {e}")
        return None
    except FileNotFoundError as e:
        print(f"Command not found: {e}")
        print("Make sure scrot and xset are installed: sudo apt install scrot x11-xserver-utils")
        return None

if __name__ == "__main__":
    capture_screenshot()
