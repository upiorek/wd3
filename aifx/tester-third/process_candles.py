import os
import time
import sys
from pathlib import Path

def process_file(file_path, revert=False):
    """Process or revert a CSV file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return
    
    if revert:
        # Remove BUY/SELL and restore original filename
        lines[1] = lines[1].rsplit(" ", 1)[0] + "\n"
        new_path = file_path.parent / f"{file_path.stem.replace('_mod', '')}.csv"
        action = "Reverted"
        
        # Write to original file and remove _mod file
        with open(new_path, 'w') as f:
            f.writelines(lines)
        os.remove(file_path)
    else:
        # Remove Volume column from all lines
        processed_lines = []
        for i, line in enumerate(lines):
            parts = line.strip().split(';')
            if i == 0:
                # Header: remove Volume column
                processed_lines.append(';'.join(parts[:5]) + '\n')
            else:
                # Data lines: remove volume, add BUY/SELL based on open price
                if i == 1:
                    open_price = float(parts[1])
                    signal = "BUY" if int(open_price) % 2 == 0 else "SELL"
                    processed_lines.append(';'.join(parts[:5]) + f' {signal}\n')
                else:
                    processed_lines.append(';'.join(parts[:5]) + '\n')
        
        new_path = file_path.parent / f"{file_path.stem}_mod.csv"
        action = f"Processed"
        
        # Write to new _mod file, keep original
        with open(new_path, 'w') as f:
            f.writelines(processed_lines)
    
    print(f"{action}: {file_path.name} -> {new_path.name}")

def main():
    revert = len(sys.argv) > 1 and sys.argv[1] == "--revert"
    
    # Check for candles in mt4_test_results first, then fall back to m15_candles
    test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_candles"
    original_dir = Path(__file__).parent / "m15_candles"
    
    if test_results_dir.exists():
        candles_dir = test_results_dir
        print(f"Using MT4 test results: {candles_dir}")
    elif original_dir.exists():
        candles_dir = original_dir
        print(f"Using original candles: {candles_dir}")
    else:
        print(f"Directory not found: {test_results_dir}")
        print(f"Directory not found: {original_dir}")
        return
    
    pattern = "*_mod.csv" if revert else "*.csv"
    csv_files = sorted([f for f in candles_dir.glob(pattern) 
                        if revert or not f.stem.endswith("_mod")])
    
    print(f"Found {len(csv_files)} files to {'revert' if revert else 'process'}\n")
    
    for csv_file in csv_files:
        process_file(csv_file, revert)
        time.sleep(0.01)
    
    print("\nComplete!")

if __name__ == "__main__":
    main()
