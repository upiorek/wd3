import os
import time
import sys
from pathlib import Path

def process_file(file_path, revert=False):
    """Process or revert a CSV file - simulates order-maker logic."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return
    
    if revert:
        # Remove BUY/SELL and distSL markers, restore original filename
        cleaned_lines = []
        for line in lines:
            # Remove everything after the OHLC data
            parts = line.split(';')
            if len(parts) >= 5:
                # Keep Time;Open;High;Low;Close, remove any trailing data
                clean_line = ';'.join(parts[:5])
                # Remove any trailing markers (BUY/SELL, distSL, etc)
                clean_line = clean_line.split(' ')[0]
                cleaned_lines.append(clean_line + '\n')
            else:
                cleaned_lines.append(line)
        
        new_path = file_path.parent / f"{file_path.stem.replace('_mod', '')}.csv"
        action = "Reverted"
        
        # Write to original file and remove _mod file
        with open(new_path, 'w') as f:
            f.writelines(cleaned_lines)
        os.remove(file_path)
    else:
        # Only add decision BUY/SELL marker:
        processed_lines = []
        
        # Line 100 (index 100): Decision candle - mark BUY/SELL based on odd/even logic
        decision_index = 100  # Line 100 in file (0=header, 1-99=history, 100=decision)
        
        for i, line in enumerate(lines):
            parts = line.strip().split(';')

            # Remove volume column (6th element)
            ohlc_line = ';'.join(parts[:5])
            
            # Decision candle: analyze open price and mark BUY/SELL
            if i == decision_index:
                open_price = float(parts[1])
                # Odd/even logic (matching order-maker)
                price_int = int(open_price * 100)
                is_odd = (price_int % 2 == 1)
                order_type = "BUY" if is_odd else "SELL"
                processed_lines.append(f"{ohlc_line} {order_type}\n")
                continue
            
            # All other lines: just remove volume
            processed_lines.append(f"{ohlc_line}\n")
        
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
    orders_dir = Path(__file__).parent / "mt4_test_results" / "m15_orders"
    
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
    
    print(f"Found {len(csv_files)} files\n")
    
    if not revert:
        # Get list of order files to match
        order_files = set()
        if orders_dir.exists():
            for order_file in orders_dir.glob("*.csv"):
                order_files.add(order_file.stem)  # Get filename without extension
            print(f"Matching {len(order_files)} order files\n")
        
        if not order_files:
            print("No order files found - skipping processing")
            print("(Run order-maker EA first to generate order files)")
            return
        
        processed_count = 0
        skipped_count = 0
        files_to_remove = []
        
        for csv_file in csv_files:
            # Only process files that have corresponding order files
            if csv_file.stem in order_files:
                process_file(csv_file, revert)
                processed_count += 1
            else:
                # Only delete source files if we're actively matching
                if len(order_files) > 0 and not csv_file.stem.endswith('_mod'):
                    files_to_remove.append(csv_file)
                    skipped_count += 1
            time.sleep(0.01)
        
        # Remove skipped files (only source files without matching orders)
        if files_to_remove:
            print(f"\nRemoving {len(files_to_remove)} unmatched source files...")
            for file_to_remove in files_to_remove:
                try:
                    file_to_remove.unlink()
                    print(f"Removed: {file_to_remove.name}")
                except Exception as e:
                    print(f"Error removing {file_to_remove.name}: {e}")
        
        print(f"\nProcessed: {processed_count} files")
        print(f"Removed: {skipped_count} files")
    else:
        for csv_file in csv_files:
            process_file(csv_file, revert)
            time.sleep(0.01)
    
    print("\nComplete!")

if __name__ == "__main__":
    main()
