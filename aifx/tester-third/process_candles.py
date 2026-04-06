import os
import time
import sys
from pathlib import Path
import importlib.util
import shutil
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

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

quality_stats = {
    "num_slopes": 0, # num of unique slopes in month
    "add_remove_line": 0, # num of add/remove lines in month
    "avg_slope_live": 0.0, # average num of period where slope doesn't change
    "bonus_count": 0, # num of periods where bonus was applied

    # data
    "slopes": [], # (val, num_periods)
    "lines": [], # [(line_id, num_periods), ...]
    "results": [], # [(filename, result_str), ...] for deferred processing
}

def version() -> str:
    """Return module version info."""
    return "process_candles 1.2"

def update_quality_stats(filename: str, result: str):
    """Collect result for later processing in chronological order."""
    # Thread-safe append to results list
    with PRINT_LOCK:
        quality_stats["results"].append((filename, result))


def calculate_quality_stats():
    """Process collected results in chronological order to calculate stats."""
    # Sort results by filename (which is timestamp-based)
    sorted_results = sorted(quality_stats["results"], key=lambda x: x[0])
    
    for filename, result in sorted_results:
        # example result: 'CROSSED DS2 UP | D0: -121.69 | DR1: -372.39 | DS1: -85.58 | DS2: -7.45 | 
        #   DS3: 107.10 | A0: 1308.55 | AR1: 326.98 | AR2: 230.42 | AR3: -80.66 | AS1: 1633.04 | 
        #   SLOPE: -3.0385 | BASE: 21299.18'

        try:
            result_slope = float(result.split('| SLOPE: ')[-1].split(' |')[0].strip())
        except (ValueError, IndexError):
            # Skip malformed results
            with PRINT_LOCK:
                print(f"Warning: Skipping malformed result for {filename}: {result[:100]}")
            continue
            
        result_line_ids = [] # e.g. ['DS2', 'D0', ...]
        for part in result.split('|'):
            part = part.strip()
            if part.startswith(('D', 'A')) and ':' in part:
                line_id = part.split(':')[0].strip()
                result_line_ids.append(line_id)
        result_line_ids.sort()

        # check if given slope matches the last slope in quality_stats
        reset_lines = False
        if quality_stats["slopes"] == []:
            # initialize
            quality_stats["slopes"].append((result_slope, 1))
            reset_lines = True
        elif quality_stats["slopes"] and quality_stats["slopes"][-1][0] == result_slope:
            # same slope as last one - increment num_periods
            num_periods = quality_stats["slopes"][-1][1] + 1
            quality_stats["slopes"][-1] = (result_slope, num_periods)
        else:
            # new slope - add to list
            quality_stats["slopes"].append((result_slope, 1))
            reset_lines = True

        # update lines data
        if reset_lines:
            # just add new set of ids
            quality_stats["lines"] += [[(line_id, 1) for line_id in result_line_ids]]
        else:
            # for each line in result_line_ids, check if it exists in last quality_stats["lines"]
            all_match = True
            num_diff = 0
            temp_stats = quality_stats["lines"][-1][:]
            for i, (line_id, num_periods) in enumerate(quality_stats["lines"][-1]):
                if line_id in result_line_ids:
                    # line exists - increment num_periods
                    temp_stats[i] = (line_id, num_periods + 1)
                else:
                    all_match = False
                    num_diff += 1
            if all_match and len(temp_stats) == len(result_line_ids):
                # all lines match - update quality_stats
                quality_stats["lines"][-1] = temp_stats
            else:
                # lines changed - add new entry
                quality_stats["lines"].append([(line_id, 1) for line_id in result_line_ids])
                # slope stays the same but lines changed - count as add/remove line
                quality_stats["add_remove_line"] += abs(len(temp_stats) - len(result_line_ids)) + num_diff

def revert_csv_file(file_path, lines):
    """Revert a modified CSV file by removing BUY/SELL markers and restoring original format.
    
    Args:
        file_path: Path to the _mod.csv file to revert
        lines: List of lines from the file
    
    Returns:
        tuple: (new_path, action) for logging
    """
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
    
    return new_path, action

def odd_even_decision(open_price):
    """Determine BUY/SELL based on odd/even logic.
    
    Args:
        open_price: The opening price as a float
    
    Returns:
        str: "BUY" or "SELL"
    """
    price_int = int(open_price * 100)
    is_odd = (price_int % 2 == 1)
    return "BUY" if is_odd else "SELL"

def magic_lines_decision(file_path, lines, i, keep_results):
    """Determine BUY/SELL using magic_lines algorithm.
    
    Args:
        file_path: Path to the CSV file being processed
        lines: All lines from the file
        i: Current line index (decision candle)
        keep_results: Whether to skip if results don't exist
    
    Returns:
        str: Order type decision ("BUY", "SELL", etc.) or None if skipped
    """
    if STOP_EVENT.is_set():
        return None
    
    # dump [0:i+1] lines to temp file
    temp_lines = []
    for j in range(i+1):
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
            return None
        
        if STOP_EVENT.is_set():
            temp_path.unlink(missing_ok=True)
            return None
        
        # Load previous slope for bonus detection
        prev_slope, prev_lines = magic_lines.load_previous_slope_and_lines(
            Path(file_path), 
            file_path.parent / "charts"
        )
        
        result = magic_lines.process_single_file(
            str(temp_path), 
            output_dir=str(file_path.parent / "charts"),
            prev_slope=prev_slope,
            prev_lines=prev_lines)

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
        
        # rename stats file to match current file
        # Source: {temp_path.stem}_stats.txt (e.g., "25-01-02-00-15_temp_stats.txt")
        # Target: {file_path.stem}_stats.txt (e.g., "25-01-02-00-15_stats.txt")
        stats_path = file_path.parent / "charts" / f"{temp_path.stem}_stats.txt"
        new_stats_path = file_path.parent / "charts" / f"{file_path.stem}_stats.txt"
        if stats_path.exists():
            if new_stats_path.exists():
                new_stats_path.unlink()
            stats_path.rename(new_stats_path)
            
            # Check if bonus was applied and update counter
            try:
                with open(new_stats_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "Bonus added: True" in content:
                        with PRINT_LOCK:
                            quality_stats["bonus_count"] += 1
            except Exception as e:
                with PRINT_LOCK:
                    print(f"Warning: Could not read stats file {new_stats_path.name}: {e}")

    temp_path.unlink()

    # quality stats
    update_quality_stats(file_path.name, result)

    # decision
    order_type = decissioner.decision(result)

    # create file with decision if doesn't exist
    decision_txt_path = file_path.parent / "charts" / f"{file_path.stem}_decision.txt"
    with open(decision_txt_path, 'w') as decision_f:
        decision_f.write(order_type)

    # skip the "log: ..." part if present
    if order_type.startswith("log:"):
        order_type = order_type.split('\n', 1)[1]

    return order_type

def process_file(file_path, percentage=.0, keep_results=False, start_time=None):
    """Process a CSV file by adding BUY/SELL decision markers."""
    if STOP_EVENT.is_set():
        return
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return
    
    order_type = "NONE"
    
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
                order_type = odd_even_decision(open_price)
                processed_lines.append(f"{ohlc_line} {order_type}\n")
                continue
            
            elif ALGO == "magic_lines":
                order_type = magic_lines_decision(file_path, lines, i, keep_results)
                if order_type is None:
                    return
                processed_lines.append(f"{ohlc_line} {order_type}\n")
                continue
        
        # All other lines: just remove volume
        processed_lines.append(f"{ohlc_line}\n")
    
    new_path = file_path.parent / f"{file_path.stem}_mod.csv"
    action = f"Processed"
    
    # Write to new _mod file, keep original
    with open(new_path, 'w') as f:
        f.writelines(processed_lines)
    
    elapsed_str = ""
    left_str = ""
    if start_time is not None:
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        elapsed_str = f"{minutes}m {seconds:.1f}s"

        left_time = (elapsed / (percentage / 100.0)) - elapsed if percentage > 0 else 0
        left_minutes = int(left_time // 60)
        left_seconds = left_time % 60
        left_str = f"left: {left_minutes}m {left_seconds:.1f}s"
    
    with PRINT_LOCK:
        str = f"{action} {percentage:.2f}% {elapsed_str} / {left_str}: "\
            f"{new_path.name}"
        if ALGO == "magic_lines":
            print(str + f" {order_type}")
        else:
            print(str)

def process_files(csv_files, candles_dir, compare_mode, orders_dir, mt, mt_workers, keep_results, start_time=None):
    """Process CSV files by adding BUY/SELL decision markers."""
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
        # For bonus calculation to work correctly, files must be processed in strict
        # chronological order. Set inflight_limit to 1 to ensure previous file completes
        # before next file starts processing.
        inflight_limit = 1

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
                            futures.append(executor.submit(process_file, csv_file, percentage, keep_results, start_time))
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
                        futures.append(executor.submit(process_file, csv_file, percentage, keep_results, start_time))
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
                    process_file(csv_file, percentage, keep_results, start_time)
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
                process_file(csv_file, percentage, keep_results, start_time)
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
    
    # Calculate quality stats from collected results in chronological order
    if quality_stats["results"]:
        calculate_quality_stats()
    
    # Process candles version
    print(f"Process candles version: {version()}")
    # Decissioner version
    print(f"Decissioner version: {decissioner.version()}")
    # Statistics - #BUY vs #SELL in decision files
    buy_count = 0
    sell_count = 0
    decision_files = sorted((candles_dir / "charts").glob("*_decision.txt"))
    for decision_file in decision_files:
        try:
            with open(decision_file, 'r') as f:
                content = f.read().strip()
                # line contains BUY or SELL
                if "BUY" in content:
                    buy_count += 1
                elif "SELL" in content:
                    sell_count += 1
        except Exception as e:
            print(f"Warning: could not read {decision_file}: {e}")
    print(f"Decisions: BUY={buy_count}, SELL={sell_count}")
    
    return processed_count, buy_count, sell_count

def revert_files(csv_files, candles_dir):
    """Revert _mod.csv files back to original format."""
    processed_count = 0
    
    for csv_file in csv_files:
        if STOP_EVENT.is_set():
            break
        with open(csv_file, 'r') as f:
            lines = f.readlines()
        if len(lines) < 2:
            continue
        
        percentage = (processed_count + 1) * 100 / len(csv_files) if csv_files else 100.0
        new_path, action = revert_csv_file(csv_file, lines)
        with PRINT_LOCK:
            print(f"{action} {percentage:.2f}%: {csv_file.name} -> {new_path.name}")
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

def cleanup_files(candles_dir):
    """Delete all *_mod.csv files and remove the charts folder."""
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
    parser.add_argument(
        "--start-date",
        help="Start date in YYYY-MM-DD format (e.g., 2025-01-02)",
    )
    parser.add_argument(
        "--end-date",
        help="End date in YYYY-MM-DD format (e.g., 2025-01-31)",
    )
    args = parser.parse_args()

    revert = args.revert
    compare_mode = args.compare
    test_mode = args.test
    no_images = args.no_images
    cleanup = args.cleanup
    mt = args.mt
    keep_results = args.keep_results
    start_date = args.start_date
    end_date = args.end_date

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
        cleanup_files(candles_dir)
        return
    
    pattern = "*_mod.csv" if revert else "*.csv"
    csv_files = sorted([f for f in candles_dir.glob(pattern) 
                        if revert or not f.stem.endswith("_mod")])
    
    # Filter by date range if specified
    if start_date or end_date:
        try:
            # Parse date arguments (format: YYYY-MM-DD)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
            
            filtered_files = []
            for csv_file in csv_files:
                # Extract date from filename (format: YY-MM-DD-HH-MM.csv)
                stem = csv_file.stem.replace("_mod", "").replace("_temp", "")
                try:
                    # Parse the date portion (first 8 chars: YY-MM-DD)
                    file_date_str = stem[:8]  # "25-01-02"
                    file_dt = datetime.strptime(file_date_str, "%y-%m-%d")
                    
                    # Check if file is within date range
                    if start_dt and file_dt < start_dt:
                        continue
                    if end_dt and file_dt > end_dt:
                        continue
                    
                    filtered_files.append(csv_file)
                except (ValueError, IndexError):
                    # Skip files that don't match expected format
                    continue
            
            csv_files = filtered_files
            if start_date:
                print(f"Start date filter: {start_date}")
            if end_date:
                print(f"End date filter: {end_date}")
        except ValueError as e:
            print(f"Error parsing date: {e}")
            print("Date format should be YYYY-MM-DD (e.g., 2025-01-02)")
            return
    
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
    
    start_time = time.time()
    
    if not revert:
        processed_count, buy_count, sell_count = process_files(csv_files, candles_dir, compare_mode, orders_dir, mt, mt_workers, keep_results, start_time)
    else:
        revert_files(csv_files, candles_dir)
        processed_count = 0
        buy_count = 0
        sell_count = 0
    
    # quality stats output
    if not revert and ALGO == "magic_lines":
        quality_stats["num_slopes"] = len(quality_stats["slopes"])
        # Calculate average based on actual periods processed, not assumed month
        total_periods_processed = processed_count
        avg_slope_live = total_periods_processed / quality_stats["num_slopes"] \
            if quality_stats["num_slopes"] != 0 else 0
        
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = elapsed_time % 60
        
        print("\nQuality Statistics:")
        print(f"  Processing time: {minutes}m {seconds:.2f}s")
        print(f"  Total periods processed: {total_periods_processed}")
        print(f"  Unique slopes detected: {quality_stats['num_slopes']}")
        print(f"  Avg periods per slope: {avg_slope_live:.2f}")
        print(f"  Line add/remove events: {quality_stats['add_remove_line']}")
        print(f"  Bonuses applied: {quality_stats['bonus_count']}")
        
        # Write stats to file
        stats_file = candles_dir / "processing_stats.txt"
        with open(stats_file, 'w') as f:
            f.write(f"Processed: {processed_count} files\n")
            f.write(f"Process candles version: {version()}\n")
            f.write(f"Decissioner version: {decissioner.version()}\n")
            f.write(f"Decisions: BUY={buy_count}, SELL={sell_count}\n")
            f.write(f"\n")
            f.write(f"Quality Statistics:\n")
            f.write(f"  Processing time: {minutes}m {seconds:.2f}s\n")
            f.write(f"  Total periods processed: {total_periods_processed}\n")
            f.write(f"  Unique slopes detected: {quality_stats['num_slopes']}\n")
            f.write(f"  Avg periods per slope: {avg_slope_live:.2f}\n")
            f.write(f"  Line add/remove events: {quality_stats['add_remove_line']}\n")
            f.write(f"  Bonuses applied: {quality_stats['bonus_count']}\n")

        print(f"\nStats written to: {stats_file}")

    print("\nComplete!")

if __name__ == "__main__":
    main()
