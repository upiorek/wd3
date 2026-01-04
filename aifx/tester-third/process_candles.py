import os
import time
import sys
from pathlib import Path
import importlib.util
import shutil

# Prefer importing via the aifx package (works well with VS Code/Pylance).
# When launched from inside aifx/tester-third, ensure repo root is on sys.path.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STRATEGY_DIR = Path(__file__).resolve().parent.parent / "strategy"

#ALGO = "odd_even"
ALGO = "magic_lines"

from aifx.strategy import magic_lines as magic_lines
from aifx.strategy import decissioner as decissioner

def process_file(file_path, percentage=.0, revert=False):
    """Process or revert a CSV file - simulates order-maker logic."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return
    
    order_type = "NONE"
    
    if revert:
        # Remove BUY/SELL and distSL markers, restore original filename
        cleaned_lines = []
        for line in lines:
            stripped = line.rstrip()
            # Remove everything after the OHLC data
            parts = stripped.split(';')
            if len(parts) >= 5:
                # Keep Time;Open;High;Low;Close
                base_parts = parts[:5]
                # Clean the Close field if it has any trailing data (BUY/SELL/gain/loss markers)
                # But preserve "decision-here" marker
                close_parts = base_parts[4].split()
                close_field = close_parts[0]  # Take only the number
                # Check if "decision-here" is present
                if "decision-here" in base_parts[4]:
                    base_parts[4] = f"{close_field};decision-here"
                else:
                    base_parts[4] = close_field
                cleaned_lines.append(';'.join(base_parts) + '\n')
            else:
                cleaned_lines.append(line)
        
        new_path = file_path.parent / f"{file_path.stem.replace('_mod', '')}.csv"
        action = "Reverted"
        
        # Write to original file and remove _mod file
        with open(new_path, 'w') as f:
            f.writelines(cleaned_lines)
        os.remove(file_path)
    else:
        # Decision candle - mark BUY/SELL based on odd/even logic
        decision_index = 300 + 1 # 1 for header

        # Only add decision BUY/SELL marker:
        processed_lines = []
        
        for i, line in enumerate(lines):
            parts = line.strip().split(';')

            # Remove volume column (6th element)
            ohlc_line = ';'.join(parts[:5])
            
            # Decision candle: analyze open price and mark BUY/SELL
            if i == decision_index:
                if ALGO == "odd_even":
                    open_price = float(parts[1])
                    # Odd/even logic (matching order-maker)
                    price_int = int(open_price * 100)
                    is_odd = (price_int % 2 == 1)
                    order_type = "BUY" if is_odd else "SELL"
                    processed_lines.append(f"{ohlc_line} {order_type}\n")
                    continue
                
                elif ALGO == "magic_lines":
                    # dump [0:i] lines to temp file
                    temp_lines = []
                    for j in range(i):
                        temp_lines.append(f"{';'.join(lines[j].strip().split(';')[:5])}\n")
                    # add _temp suffix to avoid overwriting original
                    temp_path = file_path.parent / f"{file_path.stem}_temp.csv"
                    with open(temp_path, 'w') as temp_f:
                        temp_f.writelines(temp_lines)

                    charts_dir = file_path.parent / "charts"
                    if not charts_dir.exists():
                        charts_dir.mkdir(parents=True, exist_ok=True)

                    # check if chart and result file exist and if not - call magic_lines.process_single_file()                    
                    result_txt_path = file_path.parent / "charts" / f"{file_path.stem}_result.txt"
                    if result_txt_path.exists():
                        with open(result_txt_path, 'r') as result_f:
                            result = result_f.read().strip()
                    else:
                        result = magic_lines.process_single_file(
                            str(temp_path), 
                            output_dir=str(file_path.parent / "charts"))

                        # save result data to txt file next to charts
                        with open(result_txt_path, 'w') as result_f:
                            result_f.write(result or "No result\n")

                        # rename chart file to match current file
                        chart_path = file_path.parent / "charts" / f"{temp_path.stem}.png"
                        if chart_path.exists():
                            new_chart_path = file_path.parent / "charts" / f"{file_path.stem}.png"
                            if new_chart_path.exists():
                                new_chart_path.unlink()
                            chart_path.rename(new_chart_path)

                    temp_path.unlink()

                    # decision
                    order_type = decissioner.decision(result)

                    # create file with decision if doesn't exist
                    decision_txt_path = file_path.parent / "charts" / f"{file_path.stem}_decision.txt"
                    with open(decision_txt_path, 'w') as decision_f:
                        decision_f.write(order_type)

                    # skip the "log: ..." part if present
                    if order_type.startswith("log:"):
                        order_type = order_type.split('\n', 1)[1]

                    processed_lines.append(f"{ohlc_line} {order_type}\n")
                    continue
            
            # All other lines: just remove volume
            processed_lines.append(f"{ohlc_line}\n")
        
        new_path = file_path.parent / f"{file_path.stem}_mod.csv"
        action = f"Processed"
        
        # Write to new _mod file, keep original
        with open(new_path, 'w') as f:
            f.writelines(processed_lines)
    
    if ALGO == "magic_lines":
        print(f"{action} {percentage:.2f}%: {file_path.name} -> {new_path.name} {order_type}")
    else:
        print(f"{action} {percentage:.2f}%: {file_path.name} -> {new_path.name}")

def main():
    revert = len(sys.argv) > 1 and sys.argv[1] == "--revert"
    compare_mode = len(sys.argv) > 1 and sys.argv[1] == "--compare"
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"

    def _clean_charts_dir(charts_dir: Path) -> None:
        if not charts_dir.exists():
            charts_dir.mkdir(parents=True, exist_ok=True)
            return
        if not charts_dir.is_dir():
            return
        for p in charts_dir.iterdir():
            try:
                if p.is_file() and p.suffix.lower() == ".png":
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
            except Exception as e:
                print(f"Warning: could not remove {p}: {e}")
    
    # Check for candles in mt4_test_results first, then fall back to m15_candles or m15_tests
    if test_mode:
        test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_tests"
        original_dir = Path(__file__).parent / "m15_tests"
    else:
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

    # In test mode, always start with a clean charts folder.
    # Requested cleanup target: mt4_test_results/m15_candles/charts.
    if test_mode and not revert:
        requested_charts_dir = Path(__file__).parent / "mt4_test_results" / "m15_candles" / "charts"
        _clean_charts_dir(requested_charts_dir)
        # Also clean the charts dir for the folder we are actively processing.
        active_charts_dir = candles_dir / "charts"
        if active_charts_dir.resolve() != requested_charts_dir.resolve():
            _clean_charts_dir(active_charts_dir)
    
    if not revert:
        # Get list of order files to match (only in compare mode)
        order_files = set()
        if compare_mode and orders_dir.exists():
            for order_file in orders_dir.glob("*.csv"):
                order_files.add(order_file.stem)  # Get filename without extension
            print(f"Compare mode: Matching {len(order_files)} order files\n")
        
        if compare_mode and not order_files:
            print("No order files found - skipping processing")
            print("(Run order-maker EA first to generate order files)")
            return
        
        processed_count = 0
        skipped_count = 0
        files_to_remove = []
        
        for csv_file in csv_files:
            # In compare mode: only process files that have corresponding order files
            # In normal mode: process all files
            if compare_mode:
                if csv_file.stem in order_files:
                    percentage = (processed_count + 1) * 100 / len(csv_files) 
                    process_file(csv_file, percentage, revert)
                    processed_count += 1
                else:
                    # Only delete source files if we're actively matching
                    if not csv_file.stem.endswith('_mod'):
                        files_to_remove.append(csv_file)
                        skipped_count += 1
            else:
                # Normal mode: process all files (except _mod and _temp)
                if csv_file.stem.endswith('_temp') or csv_file.stem.endswith('_mod'):
                    continue

                percentage = (processed_count + 1) * 100 / len(csv_files) 
                process_file(csv_file, percentage, revert)
                processed_count += 1
        
        # Remove skipped files (only in compare mode)
        if compare_mode and files_to_remove:
            print(f"\nRemoving {len(files_to_remove)} unmatched source files...")
            for file_to_remove in files_to_remove:
                try:
                    file_to_remove.unlink()
                    print(f"Removed: {file_to_remove.name}")
                except Exception as e:
                    print(f"Error removing {file_to_remove.name}: {e}")
        
        print(f"\nProcessed: {processed_count} files")
        if compare_mode:
            print(f"Removed: {skipped_count} files")
    else:
        for csv_file in csv_files:
            process_file(csv_file, revert)
        # delete "charts" directory
        charts_dir = candles_dir / "charts"
        if charts_dir.exists() and charts_dir.is_dir():
            try:
                for chart_file in charts_dir.glob("*.png"):
                    chart_file.unlink()
                charts_dir.rmdir()
                print(f"\nRemoved charts directory: {charts_dir}")
            except Exception as e:
                print(f"Error removing charts directory: {e}")
    
    print("\nComplete!")

if __name__ == "__main__":
    main()
