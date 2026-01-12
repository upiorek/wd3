import os
import time
import sys
from pathlib import Path
import importlib.util
import shutil
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

PRINT_LOCK = threading.Lock()
STOP_EVENT = threading.Event()

def process_file(file_path, percentage=.0, revert=False, keep_results=False):
    """Process or revert a CSV file - simulates order-maker logic."""
    if STOP_EVENT.is_set():
        return
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
                    if STOP_EVENT.is_set():
                        return
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
                        if keep_results:
                            # Skip files without existing results when --keep-results is set
                            with PRINT_LOCK:
                                print(f"Skipping {file_path.name}: no existing result file found")
                            temp_path.unlink(missing_ok=True)
                            return
                        
                        if STOP_EVENT.is_set():
                            temp_path.unlink(missing_ok=True)
                            return
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
    
    with PRINT_LOCK:
        if ALGO == "magic_lines":
            print(f"{action} {percentage:.2f}%: {file_path.name} -> {new_path.name} {order_type}")
        else:
            print(f"{action} {percentage:.2f}%: {file_path.name} -> {new_path.name}")

def main():
    parser = argparse.ArgumentParser(description="Process or revert MT4 candle CSV files.")
    parser.add_argument(
        "--input-dir",
        help=(
            "Directory containing candle CSV files to process. "
            "Overrides the default auto-detected directories."
        ),
    )
    parser.add_argument("--revert", action="store_true", help="Revert *_mod.csv back to original format")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Only process candles that have matching order files in mt4_test_results/m15_orders",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use test-mode default directories (mt4_test_results/m15_tests or m15_tests)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all *_mod.csv files and remove the charts folder in the selected candles directory, then exit",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Do not generate PNG chart images (still writes *_result.txt and *_decision.txt)",
    )
    parser.add_argument(
        "--mt",
        action="store_true",
        help="Process files using multiple threads",
    )
    parser.add_argument(
        "--keep-results",
        action="store_true",
        help="Process files but keep result and chart PNG files, create decision files only",
    )
    args = parser.parse_args()

    revert = args.revert
    compare_mode = args.compare
    test_mode = args.test
    no_images = args.no_images
    cleanup = args.cleanup
    mt = args.mt
    keep_results = args.keep_results

    mt_workers = (os.cpu_count() or 4) if mt else None

    # magic_lines uses a module-level flag to decide whether to write PNGs.
    # Keep the default behavior unless the user explicitly disables it.
    if no_images:
        magic_lines.DUMP_IMAGES = False

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
    
    # Determine input directory.
    # If --input-dir is supplied, it takes precedence.
    # Otherwise, check for candles in mt4_test_results first, then fall back to m15_candles or m15_tests.
    if args.input_dir:
        candles_dir = Path(args.input_dir).expanduser()
        if not candles_dir.is_absolute():
            candles_dir = (Path.cwd() / candles_dir)
        candles_dir = candles_dir.resolve()
        if not candles_dir.exists() or not candles_dir.is_dir():
            print(f"Directory not found: {candles_dir}")
            return
        print(f"Using --input-dir: {candles_dir}")
    else:
        if test_mode:
            test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_tests"
            original_dir = Path(__file__).parent / "m15_tests"
        else:
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

    orders_dir = Path(__file__).parent / "mt4_test_results" / "m15_orders"

    if cleanup:
        mod_files = sorted(candles_dir.glob("*_mod.csv"))
        removed_mod = 0
        for mod_file in mod_files:
            try:
                mod_file.unlink()
                removed_mod += 1
            except Exception as e:
                print(f"Warning: could not remove {mod_file}: {e}")

        charts_dir = candles_dir / "charts"
        removed_charts = False
        if charts_dir.exists() and charts_dir.is_dir():
            try:
                shutil.rmtree(charts_dir)
                removed_charts = True
            except Exception as e:
                print(f"Warning: could not remove charts directory {charts_dir}: {e}")

        print(f"Cleanup complete in: {candles_dir}")
        print(f"Removed *_mod.csv: {removed_mod}")
        print(f"Removed charts folder: {removed_charts}")
        return
    
    pattern = "*_mod.csv" if revert else "*.csv"
    csv_files = sorted([f for f in candles_dir.glob(pattern) 
                        if revert or not f.stem.endswith("_mod")])
    
    print(f"Found {len(csv_files)} files\n")

    if mt:
        print(f"Multithreaded mode: enabled ({mt_workers} threads)\n")
    if no_images:
        print("Image generation: disabled\n")
    if keep_results:
        print("Keep results mode: enabled (only creating decision files)\n")

    # In test mode, always start with a clean charts folder.
    # Requested cleanup target: mt4_test_results/m15_candles/charts.
    if test_mode and not revert:
        requested_charts_dir = Path(__file__).parent / "mt4_test_results" / "m15_candles" / "charts"
        # If we're not generating images, avoid deleting existing PNGs.
        if not no_images:
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

        if mt:
            errors = 0
            futures = []
            inflight_limit = max(1, (mt_workers or 1) * 2)

            executor = ThreadPoolExecutor(max_workers=mt_workers)
            try:
                file_iter = iter(csv_files)

                def _submit_next() -> bool:
                    nonlocal processed_count, skipped_count
                    for csv_file in file_iter:
                        if STOP_EVENT.is_set():
                            return False
                        # In compare mode: only process files that have corresponding order files
                        # In normal mode: process all files
                        if compare_mode:
                            if csv_file.stem in order_files:
                                percentage = (processed_count + 1) * 100 / len(csv_files)
                                futures.append(executor.submit(process_file, csv_file, percentage, revert, keep_results))
                                processed_count += 1
                                return True
                            else:
                                if not csv_file.stem.endswith('_mod'):
                                    files_to_remove.append(csv_file)
                                    skipped_count += 1
                                continue
                        else:
                            if csv_file.stem.endswith('_temp') or csv_file.stem.endswith('_mod'):
                                continue
                            percentage = (processed_count + 1) * 100 / len(csv_files)
                            futures.append(executor.submit(process_file, csv_file, percentage, revert, keep_results))
                            processed_count += 1
                            return True
                    return False

                while len(futures) < inflight_limit and _submit_next():
                    pass

                while futures:
                    done_future = next(as_completed(futures))
                    futures.remove(done_future)
                    try:
                        done_future.result()
                    except Exception as e:
                        errors += 1
                        with PRINT_LOCK:
                            print(f"Error: {e}")

                    while len(futures) < inflight_limit and _submit_next():
                        pass

            except KeyboardInterrupt:
                STOP_EVENT.set()
                with PRINT_LOCK:
                    print("\nInterrupted (Ctrl+C). Stopping new work; waiting for in-flight tasks to finish...")
            finally:
                executor.shutdown(wait=True, cancel_futures=True)

            if errors:
                with PRINT_LOCK:
                    print(f"Warning: {errors} file(s) failed during multithreaded processing")
        else:
            for csv_file in csv_files:
                # In compare mode: only process files that have corresponding order files
                # In normal mode: process all files
                if compare_mode:
                    if csv_file.stem in order_files:
                        percentage = (processed_count + 1) * 100 / len(csv_files) 
                        process_file(csv_file, percentage, revert, keep_results)
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
                    process_file(csv_file, percentage, revert, mt_keep_results)
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
        # Decissioner version
        print(f"Decissioner version: {decissioner.version()}")
        # Statistics - #BUY vs #SELL in decision files
        for (buy_count, sell_count) in [(0, 0)]:
            decision_files = sorted((candles_dir / "charts").glob("*_decision.txt"))
            for decision_file in decision_files:
                try:
                    with open(decision_file, 'r') as f:
                        content = f.read().strip()
                        if content == "BUY":
                            buy_count += 1
                        elif content == "SELL":
                            sell_count += 1
                except Exception as e:
                    print(f"Warning: could not read {decision_file}: {e}")
            print(f"Decisions: BUY={buy_count}, SELL={sell_count}")
            break
    else:
        processed_count = 0

        if mt:
            futures = []
            errors = 0
            inflight_limit = max(1, (mt_workers or 1) * 2)

            executor = ThreadPoolExecutor(max_workers=mt_workers)
            try:
                file_iter = iter(csv_files)

                def _submit_next() -> bool:
                    nonlocal processed_count
                    for csv_file in file_iter:
                        if STOP_EVENT.is_set():
                            return False
                        percentage = (processed_count + 1) * 100 / len(csv_files) if csv_files else 100.0
                        futures.append(executor.submit(process_file, csv_file, percentage, True))
                        processed_count += 1
                        return True
                    return False

                while len(futures) < inflight_limit and _submit_next():
                    pass

                while futures:
                    done_future = next(as_completed(futures))
                    futures.remove(done_future)
                    try:
                        done_future.result()
                    except Exception as e:
                        errors += 1
                        with PRINT_LOCK:
                            print(f"Error: {e}")
                    while len(futures) < inflight_limit and _submit_next():
                        pass

            except KeyboardInterrupt:
                STOP_EVENT.set()
                with PRINT_LOCK:
                    print("\nInterrupted (Ctrl+C). Stopping new work; waiting for in-flight tasks to finish...")
            finally:
                executor.shutdown(wait=True, cancel_futures=True)

            if errors:
                with PRINT_LOCK:
                    print(f"Warning: {errors} file(s) failed during multithreaded revert")
        else:
            for csv_file in csv_files:
                percentage = (processed_count + 1) * 100 / len(csv_files) if csv_files else 100.0
                process_file(csv_file, percentage, revert=True)
                processed_count += 1
        
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
