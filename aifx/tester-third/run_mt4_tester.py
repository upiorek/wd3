"""
MT4 Strategy Tester Runner
Runs MT4 strategy tester based on configuration and copies results
"""
import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
import configparser

# Configuration
MT4_TERMINAL_PATH = Path(r"C:\Users\prudnick\AppData\Roaming\MetaQuotes\Terminal\E014E927B1217F5A561E0813A1C319F3")
CURRENT_DIR = Path(__file__).parent
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
    # Try both .ex4 (compiled) and .mq4 (source)
    expert_files = [
        ("candle-maker.ex4", "compiled"),
        ("candle-maker.mq4", "source")
    ]
    
    copied = False
    
    for expert_name, file_type in expert_files:
        source = CURRENT_DIR / expert_name
        
        if source.exists():
            # Copy to MT4 Experts folder
            experts_folder = MT4_TERMINAL_PATH / "MQL4" / "Experts"
            if not experts_folder.exists():
                print(f"Creating Experts folder: {experts_folder}")
                experts_folder.mkdir(parents=True, exist_ok=True)
            
            dest = experts_folder / expert_name
            shutil.copy2(source, dest)
            print(f"Copied {expert_name} ({file_type}) to {experts_folder}")
            copied = True
            
            # If source file, MT4 will compile it automatically
            if file_type == "source":
                print("Note: MT4 will compile the .mq4 file automatically")
    
    if not copied:
        print("Warning: No candle-maker.ex4 or candle-maker.mq4 found")
        print("Make sure the EA is available in the current directory")
        return False
    
    return True

def cleanup_mt4_data():
    """Clean up MT4 data folders from previous tests"""
    print("\nCleaning up previous test data...")
    
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
        
        # Clean m15_candles folder in tester/files (this is where MT4 tester saves files)
        tester_files = tester_folder / "files" / "m15_candles"
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
        m15_folder = files_folder / "m15_candles"
        if m15_folder.exists():
            for file in m15_folder.glob("*.csv"):
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
        f.write(f"; Generated by run_mt4_tester.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
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
    
    # Copy CSV files from tester/files/m15_candles (this is where MT4 tester saves files)
    tester_files = tester_folder / "files" / "m15_candles"
    if tester_files.exists():
        m15_dest = results_folder / "m15_candles"
        m15_dest.mkdir(exist_ok=True)
        csv_files = list(tester_files.glob("*.csv"))
        for csv_file in csv_files:
            dest = m15_dest / csv_file.name
            shutil.copy2(csv_file, dest)
        if csv_files:
            print(f"Copied m15_candles folder with {len(csv_files)} CSV files")
            files_copied += len(csv_files)
    
    # Also copy from MQL4/Files if it exists (for regular EA operation)
    files_folder = MT4_TERMINAL_PATH / "MQL4" / "Files"
    if files_folder.exists():
        m15_source = files_folder / "m15_candles"
        if m15_source.exists() and list(m15_source.glob("*.csv")):
            m15_dest_alt = results_folder / "m15_candles_mql4"
            m15_dest_alt.mkdir(exist_ok=True)
            csv_files = list(m15_source.glob("*.csv"))
            for csv_file in csv_files:
                dest = m15_dest_alt / csv_file.name
                shutil.copy2(csv_file, dest)
            if csv_files:
                print(f"Copied MQL4 m15_candles folder with {len(csv_files)} CSV files")
                files_copied += len(csv_files)
    
    if files_copied > 0:
        print(f"\nTotal files copied: {files_copied}")
        print(f"Results saved to: {results_folder}")
    else:
        print("No result files found to copy")

def main():
    print("=" * 60)
    print("MT4 STRATEGY TESTER RUNNER")
    print("=" * 60)
    
    # Check if MT4 terminal path exists
    if not MT4_TERMINAL_PATH.exists():
        print(f"Error: MT4 terminal path not found: {MT4_TERMINAL_PATH}")
        print("Please update MT4_TERMINAL_PATH in the script")
        return 1
    
    print(f"MT4 Terminal: {MT4_TERMINAL_PATH}")
    
    # Read configuration
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found: {CONFIG_FILE}")
        return 1
    
    print(f"Config file: {CONFIG_FILE}")
    
    config = read_config()
    
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
