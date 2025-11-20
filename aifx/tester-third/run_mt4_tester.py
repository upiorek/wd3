# -*- coding: utf-8 -*-
"""
MT4 Strategy Tester Runner
Runs MT4 strategy tester based on configuration and copies results

Usage:
    python run_mt4_tester.py                    # Uses default mt4_test_config.ini
    python run_mt4_tester.py order-maker        # Uses mt4_order_config.ini
    python run_mt4_tester.py custom_config.ini  # Uses specified config file
    python run_mt4_tester.py --clean            # Clean local results folder only
    python run_mt4_tester.py order-maker --clean # Run with cleaning local results first
"""
import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
import configparser

# Set UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
# Check user name
USER_NAME = os.getlogin()
print(f"Running as user: {USER_NAME}")

# Configuration
MT4_TERMINAL_PATH_P = Path(r"C:\Users\prudnick\AppData\Roaming\MetaQuotes\Terminal\E014E927B1217F5A561E0813A1C319F3")
MT4_TERMINAL_PATH_R = Path(r"C:\Users\rrudnick\AppData\Roaming\MetaQuotes\Terminal\E014E927B1217F5A561E0813A1C319F3")
MT4_TERMINAL_PATH = MT4_TERMINAL_PATH_P if USER_NAME.lower() == 'prudnick' else MT4_TERMINAL_PATH_R

CURRENT_DIR = Path(__file__).parent

# Check for --clean flag
CLEAN_LOCAL_RESULTS = '--clean' in sys.argv
if CLEAN_LOCAL_RESULTS:
    sys.argv.remove('--clean')

# Check for --help flag
if '--help' in sys.argv or '-h' in sys.argv:
    print("=" * 60)
    print("MT4 STRATEGY TESTER RUNNER - HELP")
    print("=" * 60)
    print("\nUsage:")
    print("  python run_mt4_tester.py [EA_NAME] [--clean]")
    print("\nOptions:")
    print("  EA_NAME            Expert advisor to test (order-maker, candle-maker)")
    print("                     Or a custom .ini config file name")
    print("  --clean            Clean local mt4_test_results folder before running")
    print("  --help, -h         Show this help message")
    print("\nExamples:")
    print("  python run_mt4_tester.py")
    print("    → Run with default mt4_test_config.ini (candle-maker)")
    print("\n  python run_mt4_tester.py order-maker")
    print("    → Run order-maker EA using mt4_order_config.ini")
    print("\n  python run_mt4_tester.py --clean")
    print("    → Only clean local results, don't run tests")
    print("\n  python run_mt4_tester.py order-maker --clean")
    print("    → Clean local results, then run order-maker test")
    print("\n  python run_mt4_tester.py custom_config.ini")
    print("    → Run with custom config file")
    print("\nFolders cleaned:")
    print("  - MT4 tester folder (always cleaned before each run)")
    print("  - mt4_test_results folder (only with --clean flag)")
    print("=" * 60)
    sys.exit(0)

# Determine config file from command line argument
if len(sys.argv) > 1:
    arg = sys.argv[1]
    # If argument is 'order-maker', use the order config
    if arg == 'order-maker':
        CONFIG_FILE = CURRENT_DIR / "mt4_order_config.ini"
    # If argument is 'candle-maker', use the candle config
    elif arg == 'candle-maker':
        CONFIG_FILE = CURRENT_DIR / "mt4_test_config.ini"
    # Otherwise, treat as a filename
    elif arg.endswith('.ini'):
        CONFIG_FILE = CURRENT_DIR / arg
    else:
        # Assume it's an EA name, look for matching config
        CONFIG_FILE = CURRENT_DIR / f"mt4_{arg}_config.ini"
        if not CONFIG_FILE.exists():
            print(f"Warning: Config file not found: {CONFIG_FILE}")
            print(f"Using default: mt4_test_config.ini")
            CONFIG_FILE = CURRENT_DIR / "mt4_test_config.ini"
else:
    CONFIG_FILE = CURRENT_DIR / "mt4_test_config.ini"

def read_config():
    """Read MT4 test configuration"""
    config = configparser.ConfigParser()
    
    # Read file and add a default section if missing
    with open(CONFIG_FILE, 'r') as f:
        config_string = '[DEFAULT]\n' + f.read()
    config.read_string(config_string)
    
    test_config = {
        'expert': config.get('DEFAULT', 'TestExpert', fallback='candle-maker'),
        'symbol': config.get('DEFAULT', 'TestSymbol', fallback='US100.f'),
        'period': config.get('DEFAULT', 'TestPeriod', fallback='M15'),
        'from_date': config.get('DEFAULT', 'TestFromDate', fallback='2025.11.07'),
        'to_date': config.get('DEFAULT', 'TestToDate', fallback='2025.11.11'),
        'model': config.get('DEFAULT', 'TestModel', fallback='0'),
        'optimization': config.get('DEFAULT', 'TestOptimization', fallback='false'),
        'visual': config.get('DEFAULT', 'TestVisualEnable', fallback='false'),
        'shutdown': config.get('DEFAULT', 'TestShutdownTerminal', fallback='true'),
    }
    
    return test_config

def find_mt4_executable():
    """Find MT4 terminal.exe"""
    # Common MT4 installation paths
    possible_paths = [
        Path(r"C:\Program Files (x86)\mForex Trader\terminal.exe"),
        Path(r"C:\Program Files\MetaTrader 4\terminal.exe"),
        Path(r"C:\Program Files (x86)\MetaTrader 4\terminal.exe"),
        Path(r"C:\Program Files\OANDA - MetaTrader\terminal.exe"),
        Path(r"C:\Program Files (x86)\OANDA - MetaTrader\terminal.exe"),
    ]
    
    # Also check in MT4 terminal data directory
    if MT4_TERMINAL_PATH.exists():
        # Go up to find terminal.exe
        parent = MT4_TERMINAL_PATH.parent.parent.parent
        possible_paths.append(parent / "terminal.exe")
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def prepare_expert():
    """Copy expert advisor to MT4 Experts folder"""
    config = read_config()
    expert_name = config['expert']
    
    # Try both .ex4 (compiled) and .mq4 (source)
    expert_files = [
        (f"{expert_name}.ex4", "compiled"),
        (f"{expert_name}.mq4", "source")
    ]
    
    copied = False
    
    for expert_file, file_type in expert_files:
        source = CURRENT_DIR / expert_file
        
        if source.exists():
            # Copy to MT4 Experts folder
            experts_folder = MT4_TERMINAL_PATH / "MQL4" / "Experts"
            if not experts_folder.exists():
                print(f"Creating Experts folder: {experts_folder}")
                experts_folder.mkdir(parents=True, exist_ok=True)
            
            dest = experts_folder / expert_file
            shutil.copy2(source, dest)
            print(f"Copied {expert_file} ({file_type}) to {experts_folder}")
            copied = True
            
            # If source file, MT4 will compile it automatically
            if file_type == "source":
                print("Note: MT4 will compile the .mq4 file automatically")
    
    if not copied:
        print(f"Warning: No {expert_name}.ex4 or {expert_name}.mq4 found")
        print("Make sure the EA is available in the current directory")
        return False
    
    return True

def cleanup_mt4_data():
    """Clean up MT4 data folders from previous tests"""
    print("\nCleaning up previous test data...")
    
    config = read_config()
    expert_name = config['expert']
    
    # Determine which folder to clean based on EA
    if 'order' in expert_name.lower():
        data_folders = ['m15_orders', 'm15_candles']
    else:
        data_folders = ['m15_candles', 'm15_orders']
    
    cleaned_items = 0
    
    # Clean up tester folder
    tester_folder = MT4_TERMINAL_PATH / "tester"
    if tester_folder.exists():
        # Clean reports
        reports_folder = tester_folder / "reports"
        if reports_folder.exists():
            for file in reports_folder.glob("*"):
                try:
                    file.unlink()
                    cleaned_items += 1
                except Exception as e:
                    print(f"Warning: Could not delete {file.name}: {e}")
        
        # Clean logs
        logs_folder = tester_folder / "logs"
        if logs_folder.exists():
            for file in logs_folder.glob("*.log"):
                try:
                    file.unlink()
                    cleaned_items += 1
                except Exception as e:
                    print(f"Warning: Could not delete {file.name}: {e}")
        
        # Clean data folders in tester/files
        for folder_name in data_folders:
            tester_files = tester_folder / "files" / folder_name
            if tester_files.exists():
                for file in tester_files.glob("*.csv"):
                    try:
                        file.unlink()
                        cleaned_items += 1
                    except Exception as e:
                        print(f"Warning: Could not delete {file.name}: {e}")
    
    # Also clean MQL4/Files folder (used during regular EA operation, not testing)
    files_folder = MT4_TERMINAL_PATH / "MQL4" / "Files"
    if files_folder.exists():
        for folder_name in data_folders:
            data_folder = files_folder / folder_name
            if data_folder.exists():
                for file in data_folder.glob("*.csv"):
                    try:
                        file.unlink()
                        cleaned_items += 1
                    except Exception as e:
                        print(f"Warning: Could not delete {file.name}: {e}")
    
    if cleaned_items > 0:
        print(f"✓ Cleaned {cleaned_items} old test files")
    else:
        print("✓ No old test files to clean")
    
    return True

def cleanup_local_results():
    """Clean up local mt4_test_results folder - only the relevant subfolder"""
    print("\nCleaning up local test results...")
    
    results_folder = CURRENT_DIR / "mt4_test_results"
    
    if not results_folder.exists():
        print("✓ No local results folder to clean")
        return True
    
    # Read config to determine which EA is being tested
    config = read_config()
    expert_name = config['expert']
    
    # Determine which folder to clean based on EA
    if 'order' in expert_name.lower():
        target_folder = 'm15_orders'
    else:
        target_folder = 'm15_candles'
    
    cleaned_items = 0
    
    # Clean only the relevant data folder
    data_folder = results_folder / target_folder
    if data_folder.exists():
        for file in data_folder.glob("*.csv"):
            try:
                file.unlink()
                cleaned_items += 1
            except Exception as e:
                print(f"Warning: Could not delete {file.name}: {e}")
        print(f"✓ Cleaned {target_folder} folder")
    
    # Clean logs folder
    logs_folder = results_folder / "logs"
    if logs_folder.exists():
        for file in logs_folder.glob("*.log"):
            try:
                file.unlink()
                cleaned_items += 1
            except Exception as e:
                print(f"Warning: Could not delete {file.name}: {e}")
    
    # Clean HTML reports
    for file in results_folder.glob("*.htm"):
        try:
            file.unlink()
            cleaned_items += 1
        except Exception as e:
            print(f"Warning: Could not delete {file.name}: {e}")
    
    # Clean GIF files
    for file in results_folder.glob("*.gif"):
        try:
            file.unlink()
            cleaned_items += 1
        except Exception as e:
            print(f"Warning: Could not delete {file.name}: {e}")
    
    if cleaned_items > 0:
        print(f"✓ Cleaned {cleaned_items} local result files from {target_folder}")
    else:
        print(f"✓ No local result files to clean in {target_folder}")
    
    return True

def run_strategy_tester(config):
    """Run MT4 strategy tester"""
    mt4_exe = find_mt4_executable()
    
    if not mt4_exe:
        print("Error: Could not find MT4 terminal.exe")
        print("Please specify the MT4 installation path manually")
        return False
    
    print(f"Found MT4 at: {mt4_exe}")
    
    # Update the actual config file with proper format
    print(f"Updating configuration file...")
    
    # The config file needs to be in the format MT4 expects
    # Write it in the same directory
    config_file = CONFIG_FILE
    
    # Re-write config file to ensure proper format
    from datetime import datetime
    with open(config_file, 'w') as f:
        f.write("; MT4 Strategy Tester Configuration\n")
        f.write("; Generated by run_mt4_tester.py\n")
        f.write("; Enable Experts\n")
        f.write("ExpertsEnable=true\n")
        f.write("ExpertsDllImport=true\n")
        f.write("ExpertsExpImport=false\n")
        f.write("ExpertsTrades=true\n\n")
        f.write("; Strategy Tester Settings\n")
        f.write(f"TestExpert={config['expert']}\n")
        f.write(f"TestSymbol={config['symbol']}\n")
        f.write(f"TestPeriod={config['period']}\n")
        f.write(f"TestModel={config['model']}\n")
        f.write(f"TestSpread=0\n")
        f.write(f"TestOptimization={config['optimization']}\n")
        f.write(f"TestDateEnable=true\n")
        f.write(f"TestFromDate={config['from_date']}\n")
        f.write(f"TestToDate={config['to_date']}\n")
        f.write(f"TestReplaceReport=true\n")
        f.write(f"TestShutdownTerminal={config['shutdown']}\n")
        f.write(f"TestVisualEnable={config['visual']}\n")
    
    print(f"Configuration updated: {config_file}")
    
    # Get absolute path to config file (CRITICAL for MT4)
    config_path = str(config_file.resolve())
    
    # Launch MT4 with config file as command-line argument
    cmd = [str(mt4_exe), config_path]
    
    print(f"\nStarting MT4 Strategy Tester...")
    print(f"Expert: {config['expert']}")
    print(f"Symbol: {config['symbol']}")
    print(f"Period: {config['period']}")
    print(f"Date Range: {config['from_date']} to {config['to_date']}")
    print(f"\nCommand: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        # Start MT4 with config file
        process = subprocess.Popen(cmd, cwd=str(mt4_exe.parent))
        print(f"MT4 started with PID: {process.pid}")
        
        print("\n✓ MT4 launched successfully with test configuration!")
        print("\nMT4 will automatically:")
        print(f"  1. Load the {config['expert']} EA")
        print("  2. Configure the Strategy Tester")
        print("  3. Start the backtest")
        print("  4. Generate a report when complete")
        
        if config['shutdown'].lower() == 'true':
            print("\nWaiting for MT4 to complete testing and shutdown...")
            print("(You can watch the progress in MT4's Strategy Tester window)")
            
            # Wait for process to complete
            process.wait()
            print("\n✓ MT4 has shut down - testing complete!")
        else:
            print("\nMT4 is running. Close it manually when done.")
            process.wait()
        
        return True
        
    except Exception as e:
        print(f"Error starting MT4: {e}")
        return False

def copy_results():
    """Copy test results to current folder"""
    print("\nCopying test results...")
    
    config = read_config()
    expert_name = config['expert']
    
    # Determine which folder to copy based on EA
    if 'order' in expert_name.lower():
        data_folders = ['m15_orders', 'm15_candles']
    else:
        data_folders = ['m15_candles', 'm15_orders']
    
    # Find tester folder
    tester_folder = MT4_TERMINAL_PATH / "tester"
    
    if not tester_folder.exists():
        print(f"Warning: Tester folder not found at {tester_folder}")
        return
    
    # Create results folder
    results_folder = CURRENT_DIR / "mt4_test_results"
    results_folder.mkdir(exist_ok=True)
    
    # Copy report files
    files_copied = 0
    
    # Copy HTML reports from tester/reports folder
    reports_folder = tester_folder / "reports"
    if reports_folder.exists():
        for html_file in reports_folder.glob("*.htm"):
            dest = results_folder / html_file.name
            shutil.copy2(html_file, dest)
            print(f"Copied report: {html_file.name}")
            files_copied += 1
        
        for gif_file in reports_folder.glob("*.gif"):
            dest = results_folder / gif_file.name
            shutil.copy2(gif_file, dest)
            print(f"Copied: {gif_file.name}")
            files_copied += 1
    
    # Copy logs
    logs_folder = tester_folder / "logs"
    if logs_folder.exists():
        dest_logs = results_folder / "logs"
        dest_logs.mkdir(exist_ok=True)
        for log_file in logs_folder.glob("*.log"):
            dest = dest_logs / log_file.name
            shutil.copy2(log_file, dest)
            print(f"Copied log: {log_file.name}")
            files_copied += 1
    
    # Copy CSV files from tester/files (for each data folder type)
    for folder_name in data_folders:
        tester_files = tester_folder / "files" / folder_name
        if tester_files.exists():
            dest_folder = results_folder / folder_name
            dest_folder.mkdir(exist_ok=True)
            csv_files = list(tester_files.glob("*.csv"))
            for csv_file in csv_files:
                dest = dest_folder / csv_file.name
                shutil.copy2(csv_file, dest)
            if csv_files:
                print(f"Copied {folder_name} folder with {len(csv_files)} CSV files")
                files_copied += len(csv_files)
    
    # Also copy from MQL4/Files if it exists (for regular EA operation)
    files_folder = MT4_TERMINAL_PATH / "MQL4" / "Files"
    if files_folder.exists():
        for folder_name in data_folders:
            source_folder = files_folder / folder_name
            if source_folder.exists() and list(source_folder.glob("*.csv")):
                dest_folder_alt = results_folder / f"{folder_name}_mql4"
                dest_folder_alt.mkdir(exist_ok=True)
                csv_files = list(source_folder.glob("*.csv"))
                for csv_file in csv_files:
                    dest = dest_folder_alt / csv_file.name
                    shutil.copy2(csv_file, dest)
                if csv_files:
                    print(f"Copied MQL4 {folder_name} folder with {len(csv_files)} CSV files")
                    files_copied += len(csv_files)
    
    if files_copied > 0:
        print(f"\nTotal files copied: {files_copied}")
        print(f"Results saved to: {results_folder}")
    else:
        print("No result files found to copy")
        assert(False), "No result files were copied!"

def main():
    print("=" * 60)
    print("MT4 STRATEGY TESTER RUNNER")
    print("=" * 60)
    
    # Display which config file is being used
    print(f"Config file: {CONFIG_FILE.name}")
    
    # If only --clean flag was provided, just clean and exit
    if CLEAN_LOCAL_RESULTS and len(sys.argv) == 1:
        cleanup_local_results()
        print("\n" + "=" * 60)
        print("LOCAL CLEANUP COMPLETE!")
        print("=" * 60)
        return 0
    
    # Check if MT4 terminal path exists
    if not MT4_TERMINAL_PATH.exists():
        print(f"Error: MT4 terminal path not found: {MT4_TERMINAL_PATH}")
        print("Please update MT4_TERMINAL_PATH in the script")
        return 1
    
    print(f"MT4 Terminal: {MT4_TERMINAL_PATH}")
    
    # Read configuration
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found: {CONFIG_FILE}")
        print("\nAvailable config files:")
        for ini_file in CURRENT_DIR.glob("mt4_*.ini"):
            print(f"  - {ini_file.name}")
        print("\nUsage:")
        print("  python run_mt4_tester.py                    # Uses mt4_test_config.ini")
        print("  python run_mt4_tester.py order-maker        # Uses mt4_order_config.ini")
        print("  python run_mt4_tester.py candle-maker       # Uses mt4_test_config.ini")
        print("  python run_mt4_tester.py custom_config.ini  # Uses specified file")
        print("  python run_mt4_tester.py --clean            # Clean local results only")
        print("  python run_mt4_tester.py order-maker --clean # Run with local cleanup")
        return 1
    
    config = read_config()
    
    # Clean local results if flag is set
    if CLEAN_LOCAL_RESULTS:
        cleanup_local_results()
    
    # Clean up previous test data
    cleanup_mt4_data()
    
    # Prepare expert advisor
    print("\nPreparing Expert Advisor...")
    if not prepare_expert():
        print("Warning: Could not prepare expert advisor")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1
    
    # Run strategy tester
    print("\n" + "=" * 60)
    if not run_strategy_tester(config):
        print("Failed to run strategy tester")
        return 1
    
    # Copy results
    print("\n" + "=" * 60)
    copy_results()
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
