"""
Simple script to analyze candle data from M15 CSV files.
Returns True if there are more white (bullish) candles than black (bearish) candles.
"""

import csv
import sys
import os
from datetime import datetime


def analyze_candles(csv_file):
    """
    Analyze candle data and return True if more white candles than black.
    
    White candle: Close > Open (bullish)
    Black candle: Close < Open (bearish)
    
    Args:
        csv_file: Path to CSV file with candle data
        
    Returns:
        bool: True if more white candles than black, False otherwise
    """
    white_candles = 0
    black_candles = 0
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                open_price = float(row['Open'])
                close_price = float(row['Close'])
                
                if close_price > open_price:
                    white_candles += 1
                elif close_price < open_price:
                    black_candles += 1
                # Doji candles (close == open) are not counted
        
        result = white_candles > black_candles
        
        # Log results to file with date as filename
        log_results(csv_file, white_candles, black_candles, result)
        
        print(result)
        
        return result
        
    except FileNotFoundError:
        print(f"Error: File not found: {csv_file}")
        return False
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return False


def log_results(csv_file, white_candles, black_candles, result):
    """
    Log analysis results to a file with current date as filename.
    
    Args:
        csv_file: Path to the analyzed CSV file
        white_candles: Number of white candles
        black_candles: Number of black candles
        result: Analysis result (True/False)
    """
    try:
        # Create log filename with current date: analysis_YYYY-MM-DD.log
        log_filename = f"analysis_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        # Get just the filename from the full path
        csv_filename = os.path.basename(csv_file)
        
        # Append to log file
        with open(log_filename, 'a') as log_file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            decision = "BUY" if result else "SELL"
            log_file.write(f"{timestamp} | {csv_filename} | White:{white_candles} Black:{black_candles} | Decision:{decision}\n")
    
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


if __name__ == "__main__":
    # Default to first CSV file in m15_candles folder if no argument provided
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        candles_dir = "m15_candles"
        if os.path.exists(candles_dir):
            csv_files = [f for f in os.listdir(candles_dir) if f.endswith('.csv')]
            if csv_files:
                csv_files.sort()
                csv_file = os.path.join(candles_dir, csv_files[0])
                print(f"Using file: {csv_file}\n")
            else:
                print("No CSV files found in m15_candles folder")
                sys.exit(1)
        else:
            print("m15_candles folder not found")
            sys.exit(1)
    
    result = analyze_candles(csv_file)
    sys.exit(0 if result else 1)
