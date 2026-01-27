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
import calendar
import re
import html as html_lib

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
REPO_ROOT = CURRENT_DIR.parent.parent

# Check for --month flag (wd_tester only). Supports --month N and --month=N
MONTH = None
if any(a == '--month' or a.startswith('--month=') for a in sys.argv):
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a.startswith('--month='):
            if MONTH is not None:
                print("Error: --month specified more than once")
                sys.exit(1)
            raw = a.split('=', 1)[1].strip()
            if not raw:
                print("Error: --month requires a value")
                sys.exit(1)
            try:
                MONTH = int(raw)
            except ValueError:
                print("Error: --month must be an integer 1..12")
                sys.exit(1)
            del sys.argv[i]
            continue
        if a == '--month':
            if MONTH is not None:
                print("Error: --month specified more than once")
                sys.exit(1)
            if i + 1 >= len(sys.argv):
                print("Error: --month requires a value")
                sys.exit(1)
            try:
                MONTH = int(sys.argv[i + 1])
            except ValueError:
                print("Error: --month must be an integer 1..12")
                sys.exit(1)
            del sys.argv[i:i + 2]
            continue
        i += 1

    if MONTH is not None and not (1 <= MONTH <= 12):
        print("Error: --month must be in range 1..12")
        sys.exit(1)

# Check for --input-dir flag (wd_tester only). Supports --input-dir PATH and --input-dir=PATH
INPUT_DIR = None
if any(a == '--input-dir' or a.startswith('--input-dir=') for a in sys.argv):
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a.startswith('--input-dir='):
            if INPUT_DIR is not None:
                print("Error: --input-dir specified more than once")
                sys.exit(1)
            raw = a.split('=', 1)[1].strip()
            if not raw:
                print("Error: --input-dir requires a value")
                sys.exit(1)
            INPUT_DIR = raw
            del sys.argv[i]
            continue
        if a == '--input-dir':
            if INPUT_DIR is not None:
                print("Error: --input-dir specified more than once")
                sys.exit(1)
            if i + 1 >= len(sys.argv):
                print("Error: --input-dir requires a value")
                sys.exit(1)
            INPUT_DIR = sys.argv[i + 1]
            del sys.argv[i:i + 2]
            continue
        i += 1

# Check for --clean flag
CLEAN_LOCAL_RESULTS = '--clean' in sys.argv
if CLEAN_LOCAL_RESULTS:
    sys.argv.remove('--clean')

# Check for --no-copy-data flag (skip copying wd_tester input data)
NO_COPY_DATA = '--no-copy-data' in sys.argv
if NO_COPY_DATA:
    sys.argv.remove('--no-copy-data')

# Check for --help flag
if '--help' in sys.argv or '-h' in sys.argv:
    print("=" * 60)
    print("MT4 STRATEGY TESTER RUNNER - HELP")
    print("=" * 60)
    print("\nUsage:")
    print("  python run_mt4_tester.py [EA_NAME] [--clean] [--month N] [--input-dir PATH] [--no-copy-data]")
    print("\nOptions:")
    print("  EA_NAME            Expert advisor to test (order-maker, candle-maker)")
    print("                     Or a custom .ini config file name")
    print("  --clean            Clean local mt4_test_results folder before running")
    print("  --month N          (wd_tester only) Set test range to month (1-12)")
    print("  --input-dir PATH   (wd_tester only) Copy *_decision.txt and *_result.txt from PATH")
    print("  --no-copy-data     (wd_tester only) Skip copying/cleaning wd_tester input data")
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

    print("\n  python run_mt4_tester.py wd_tester --month 1")
    print("    → Run wd_tester using January date range (config year)")

    print("\n  python run_mt4_tester.py wd_tester --input-dir aifx/data/2025.01/charts")
    print("    → Clean MT4 wd_tester input folder, copy decisions/results from PATH, then run")

    print("\n  python run_mt4_tester.py wd_tester --no-copy-data")
    print("    → Run wd_tester assuming input data already present in MT4 tester/files/wd_tester")
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
        'spread': config.get('DEFAULT', 'TestSpread', fallback='0'),
        'from_date': config.get('DEFAULT', 'TestFromDate', fallback='2025.11.07'),
        'to_date': config.get('DEFAULT', 'TestToDate', fallback='2025.11.11'),
        'model': config.get('DEFAULT', 'TestModel', fallback='0'),
        'optimization': config.get('DEFAULT', 'TestOptimization', fallback='false'),
        'visual': config.get('DEFAULT', 'TestVisualEnable', fallback='false'),
        'shutdown': config.get('DEFAULT', 'TestShutdownTerminal', fallback='true'),
        'report': config.get('DEFAULT', 'TestReport', fallback='').strip() or None,
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

    # For wd_tester, use the fastest modeling mode: Open prices only.
    # MT4 TestModel values: 0=Every tick, 1=Control points, 2=Open prices only.
    if config.get('expert') == 'wd_tester':
        config['model'] = '2'
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
    
    # Copy include files (.mqh) to Experts folder
    for mqh_file in CURRENT_DIR.glob("*.mqh"):
        experts_folder = MT4_TERMINAL_PATH / "MQL4" / "Experts"
        if not experts_folder.exists():
            experts_folder.mkdir(parents=True, exist_ok=True)
        
        dest = experts_folder / mqh_file.name
        shutil.copy2(mqh_file, dest)
        print(f"Copied include file: {mqh_file.name}")
    
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


def cleanup_wd_tester_ini() -> int:
    """Remove wd_tester.ini to avoid stale Strategy Tester input overrides."""
    deleted = 0
    candidates = [
        MT4_TERMINAL_PATH / "tester" / "wd_tester.ini",
        MT4_TERMINAL_PATH / "config" / "wd_tester.ini",
    ]

    for p in candidates:
        try:
            if p.exists() and p.is_file():
                p.unlink()
                deleted += 1
                print(f"Removed: {p}")
        except Exception as e:
            print(f"Warning: could not remove {p}: {e}")

    return deleted

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
    for file in results_folder.glob("*.html"):
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


def cleanup_local_logs_folder() -> int:
    """Remove all items in local mt4_test_results/logs (keeps the folder)."""
    logs_folder = CURRENT_DIR / "mt4_test_results" / "logs"

    if not logs_folder.exists():
        return 0

    removed = 0
    for p in logs_folder.glob("*"):
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
                removed += 1
            elif p.is_dir():
                shutil.rmtree(p)
                removed += 1
        except Exception as e:
            print(f"Warning: could not remove {p}: {e}")

    return removed


def cleanup_local_html_gif_reports() -> int:
    """Remove local *.html/*.htm and *.gif files in mt4_test_results root."""
    results_folder = CURRENT_DIR / "mt4_test_results"
    if not results_folder.exists():
        return 0

    removed = 0
    for pat in ("*.html", "*.htm", "*.gif"):
        for p in results_folder.glob(pat):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink()
                    removed += 1
            except Exception as e:
                print(f"Warning: could not remove {p}: {e}")

    return removed


def update_wd_tester_hash_mqh() -> bool:
    """Fill aifx/tester-third/wd_tester_hash.mqh with the latest git commit hash."""
    mqh_path = CURRENT_DIR / "wd_tester_hash.mqh"

    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            print(f"Warning: could not read git hash (git log failed): {stderr or 'unknown error'}")
            return False

        git_hash = (result.stdout or "").strip()
        if not git_hash:
            print("Warning: git log returned empty hash")
            return False

        content = (
            "// Auto-generated before test run\n"
            "#property strict\n\n"
            f"string WD_GIT_HASH = \"{git_hash}\";\n"
        )
        mqh_path.write_text(content, encoding="utf-8")
        print(f"✓ Updated wd_tester hash: {git_hash[:7]} -> {mqh_path}")
        return True
    except Exception as e:
        print(f"Warning: could not update {mqh_path}: {e}")
        return False


def _get_current_git_hash() -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return None
        git_hash = (result.stdout or "").strip()
        return git_hash or None
    except Exception:
        return None


def verify_wd_tester_git_hash_from_latest_log() -> bool:
    """Validate wd_tester log git hash matches current repo HEAD."""
    current_hash = _get_current_git_hash()
    if not current_hash:
        print("ERROR: could not determine current git commit (HEAD)")
        return False

    logs_dir = CURRENT_DIR / "mt4_test_results" / "logs"
    log_files = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
    if not log_files:
        print(f"ERROR: no local log files found in {logs_dir}")
        return False

    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)

    try:
        data = latest_log.read_bytes()
    except Exception as e:
        print(f"ERROR: could not read latest log file {latest_log}: {e}")
        return False

    text = data.decode("utf-8", errors="ignore")
    if not text:
        text = data.decode("latin-1", errors="ignore")

    # Example line: "wd_tester ...: git hash: <40-hex>"
    matches = re.findall(r"git\s+hash\s*:\s*([0-9a-fA-F]{7,40})", text)
    if not matches:
        print(f"ERROR: could not find 'git hash:' in latest log: {latest_log}")
        return False

    log_hash = matches[-1].lower()
    if log_hash != current_hash.lower():
        print("ERROR: git commit mismatch between repo and latest MT4 log")
        print(f"  Repo HEAD : {current_hash}")
        print(f"  Log hash  : {log_hash}")
        print(f"  Log file  : {latest_log}")
        return False

    print(f"✓ Verified git hash in latest log matches HEAD: {current_hash[:7]}")
    return True


def fail_if_error_messages_in_latest_log() -> bool:
    """Fail the run if the latest copied MT4 log contains any ERROR messages."""
    logs_dir = CURRENT_DIR / "mt4_test_results" / "logs"
    log_files = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
    if not log_files:
        print(f"ERROR: no local log files found in {logs_dir}")
        return False

    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)

    try:
        data = latest_log.read_bytes()
    except Exception as e:
        print(f"ERROR: could not read latest log file {latest_log}: {e}")
        return False

    text = data.decode("utf-8", errors="ignore")
    if not text:
        text = data.decode("latin-1", errors="ignore")

    error_lines: list[str] = []
    for line in text.splitlines():
        if re.search(r"\bERROR\b", line, flags=re.IGNORECASE):
            error_lines.append(line.strip())

    if error_lines:
        print("ERROR: 'ERROR' messages found in latest MT4 log")
        print(f"  Log file: {latest_log}")
        print(f"  Count   : {len(error_lines)}")
        for i, line in enumerate(error_lines[:10], start=1):
            print(f"  {i:02d}: {line}")
        if len(error_lines) > 10:
            print(f"  ... ({len(error_lines) - 10} more)")
        return False

    print("✓ No 'ERROR' messages found in latest MT4 log")
    return True

def run_strategy_tester(config):
    """Run MT4 strategy tester"""
    mt4_exe = find_mt4_executable()
    
    if not mt4_exe:
        print("Error: Could not find MT4 terminal.exe")
        print("Please specify the MT4 installation path manually")
        return False
    
    print(f"Found MT4 at: {mt4_exe}")

    # Some MT4 terminals do not create tester/reports automatically.
    # Ensure it exists so TestReport output can be written.
    try:
        reports_dir = MT4_TERMINAL_PATH / "tester" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: could not create tester/reports folder: {e}")
    
    # Update the actual config file with proper format
    print(f"Updating configuration file...")
    
    # The config file needs to be in the format MT4 expects
    # Write it in the same directory
    config_file = CONFIG_FILE
    
    # Re-write config file to ensure proper format
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    def _safe(s: str) -> str:
        return ''.join(ch if (ch.isalnum() or ch in ('-', '_')) else '_' for ch in str(s))

    report_name = f"{_safe(config['expert'])}_{_safe(config['symbol'])}_{_safe(config['from_date'])}_{_safe(config['to_date'])}_{ts}.html"
    config['report'] = report_name
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
        f.write(f"TestSpread={config['spread']}\n")
        f.write(f"TestOptimization={config['optimization']}\n")
        f.write(f"TestDateEnable=true\n")
        f.write(f"TestFromDate={config['from_date']}\n")
        f.write(f"TestToDate={config['to_date']}\n")
        # Without TestReport, MT4 may not produce an HTML report in tester/reports.
        f.write(f"TestReport={report_name}\n")
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
        """
        print("\n✓ MT4 launched successfully with test configuration!")
        
        print("\nMT4 will automatically:")
        print(f"  1. Load the {config['expert']} EA")
        print("  2. Configure the Strategy Tester")
        print("  3. Start the backtest")
        print("  4. Generate a report when complete")
        """
        
        if config['shutdown'].lower() == 'true':
            print("\nWaiting for MT4 to complete testing and shutdown...")
            print("(You can watch the progress in MT4's Strategy Tester window)")
            
            # Wait for process to complete
            process.wait()
            print("✓ MT4 has shut down - testing complete!")
        else:
            print("MT4 is running. Close it manually when done.")
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
        for html_file in list(reports_folder.glob("*.htm")) + list(reports_folder.glob("*.html")):
            dest = results_folder / html_file.name
            shutil.copy2(html_file, dest)
            print(f"Copied report: {html_file.name}")
            files_copied += 1

        for gif_file in reports_folder.glob("*.gif"):
            dest = results_folder / gif_file.name
            shutil.copy2(gif_file, dest)
            print(f"Copied: {gif_file.name}")
            files_copied += 1

    # Some MT4 terminals write TestReport into the terminal data directory root
    # (not into tester/reports). If TestReport is set, try copying that exact file.
    report_name = config.get('report')
    if report_name:
        candidate_paths = [
            tester_folder / "reports" / report_name,
            MT4_TERMINAL_PATH / report_name,
            tester_folder / report_name,
        ]
        copied_report = False
        for p in candidate_paths:
            if p.exists() and p.is_file():
                dest = results_folder / p.name
                shutil.copy2(p, dest)
                if not copied_report:
                    print(f"Copied report: {p.name}")
                files_copied += 1
                copied_report = True
                break
        if not copied_report:
            print(f"Warning: TestReport file not found: {report_name}")
            print("Tried:")
            for p in candidate_paths:
                print(f"  - {p}")

        # If MT4 writes the report to the terminal data directory root, it may also
        # write the associated GIF there (same basename).
        try:
            report_path = Path(report_name)
            gif_name = report_path.with_suffix('.gif').name
        except Exception:
            gif_name = None

        if gif_name:
            gif_candidates = [
                tester_folder / "reports" / gif_name,
                MT4_TERMINAL_PATH / gif_name,
                tester_folder / gif_name,
            ]
            for p in gif_candidates:
                if p.exists() and p.is_file():
                    dest = results_folder / p.name
                    shutil.copy2(p, dest)
                    print(f"Copied: {p.name}")
                    files_copied += 1
                    break
    
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


def _find_report_path(config: dict) -> Path | None:
    report_name = config.get('report')
    if not report_name:
        return None

    results_folder = CURRENT_DIR / "mt4_test_results"
    candidate_paths = [
        results_folder / report_name,
        MT4_TERMINAL_PATH / report_name,
        MT4_TERMINAL_PATH / "tester" / "reports" / report_name,
        MT4_TERMINAL_PATH / "tester" / report_name,
    ]
    for p in candidate_paths:
        if p.exists() and p.is_file():
            return p
    return None


def _extract_report_result(report_html: str) -> str | None:
    # MT4 reports usually contain a row like: Total net profit ... <td>123.45</td>
    # Also supports Polish: Całkowity zysk netto (with potential encoding issues)
    patterns = [
        r"Total\s+net\s+profit\s*</td>\s*<td[^>]*>\s*([^<\r\n]+)",
        r"Total\s+net\s+profit\s*[:=\-]?\s*([^<\r\n]+)",
        r"Ca[^\s]*kowity\s+zysk\s+netto\s*</td>\s*<td[^>]*>\s*([^<\r\n]+)",
        r"Ca[^\s]*kowity\s+zysk\s+netto\s*[:=\-]?\s*([^<\r\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, report_html, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_report_closed_orders(report_html: str) -> int | None:
    # MT4 reports typically expose the number of executed trades as "Total trades".
    # In many setups this corresponds to the number of closed orders in the report period.
    patterns = [
        r"Total\s+trades\s*</td>\s*<td[^>]*>\s*([^<\r\n]+)",
        r"Total\s+trades\s*[:=\-]?\s*([^<\r\n]+)",
        r"Transakcji\s+w\s+sumie\s*</td>\s*<td[^>]*>\s*([^<\r\n]+)",
        r"Transakcji\s+w\s+sumie\s*[:=\-]?\s*([^<\r\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, report_html, flags=re.IGNORECASE)
        if not m:
            continue
        raw = m.group(1).strip()
        digits = re.sub(r"[^0-9]", "", raw)
        if digits:
            try:
                return int(digits)
            except Exception:
                return None
    
    return None


def _extract_report_sl_tp_summary(report_html: str) -> dict[str, float | int] | None:
    """Extract SL/TP counts and profit sums from the trade list table.

    MT4 HTML reports include a second table with columns:
    #, Time, Type, Order, Size, Price, S/L, T/P, Profit, Balance.
    Polish version: #, Czas, Typ, Zlecenie, Wolumen, Cena, S/L, T/P, Zysk, Saldo.
    We treat rows where Type is "s/l" or "t/p" as SL/TP outcomes.
    """

    # Locate the trade list header row, then slice out the enclosing table.
    # Support both English and Polish column names.
    header_patterns = [
        re.compile(
            r"<tr[^>]*>\s*<td>\#</td>\s*<td>Time</td>\s*<td>Type</td>",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"<tr[^>]*>\s*<td>\#</td>\s*<td>Czas</td>\s*<td>Typ</td>",
            flags=re.IGNORECASE,
        ),
    ]
    
    m = None
    for pat in header_patterns:
        m = pat.search(report_html)
        if m:
            break
    
    if not m:
        return None

    header_idx = m.start()
    table_start = report_html.rfind("<table", 0, header_idx)
    if table_start < 0:
        return None
    table_end = report_html.find("</table>", header_idx)
    if table_end < 0:
        return None
    table_html = report_html[table_start:table_end]

    # Iterate all rows and parse cell text.
    row_pat = re.compile(r"<tr\b[^>]*>.*?</tr>", flags=re.IGNORECASE | re.DOTALL)
    cell_pat = re.compile(r"<td\b[^>]*>(.*?)</td>", flags=re.IGNORECASE | re.DOTALL)

    def _clean_cell(cell_html: str) -> str:
        txt = re.sub(r"<[^>]+>", "", cell_html)
        txt = html_lib.unescape(txt)
        return txt.strip()

    def _parse_float_maybe(raw: str) -> float | None:
        if raw is None:
            return None
        s = raw.strip()
        if not s:
            return None
        # Accept both 1,23 and 1.23, strip any stray chars.
        s = s.replace(" ", "")
        s = s.replace(",", ".")
        s = re.sub(r"[^0-9+\-.]", "", s)
        if not s or s in {"+", "-", ".", "+.", "-."}:
            return None
        try:
            return float(s)
        except Exception:
            return None

    sl_count = 0
    tp_count = 0
    sl_profit = 0.0
    tp_profit = 0.0

    for row_html in row_pat.findall(table_html):
        raw_cells = cell_pat.findall(row_html)
        if not raw_cells:
            continue
        cells = [_clean_cell(c) for c in raw_cells]

        # Skip header / malformed rows.
        if not cells or cells[0] in {"#", "\u00a0"}:
            continue
        try:
            int(cells[0])
        except Exception:
            continue
        if len(cells) < 3:
            continue

        row_type = cells[2].strip().lower()
        if row_type not in {"s/l", "t/p"}:
            continue

        profit_val = _parse_float_maybe(cells[8]) if len(cells) > 8 else None

        if row_type == "s/l":
            sl_count += 1
            if profit_val is not None:
                sl_profit += profit_val
        else:
            tp_count += 1
            if profit_val is not None:
                tp_profit += profit_val

    return {
        "sl_count": sl_count,
        "tp_count": tp_count,
        "sl_profit": sl_profit,
        "tp_profit": tp_profit,
    }


def write_wd_summary(config: dict) -> None:
    if config.get('expert') != 'wd_tester':
        return

    # Prefer explicit CLI month; otherwise derive from from_date.
    month_num = MONTH
    if month_num is None:
        try:
            month_num = int(str(config.get('from_date', '')).split('.')[1])
        except Exception:
            month_num = 0

    # add padding to month number
    month_num = f"{month_num:02d}"

    report_path = _find_report_path(config)
    result = None
    closed_orders: int | None = None
    sl_tp: dict[str, float | int] | None = None
    if report_path:
        try:
            # Try multiple encodings for Polish reports
            report_html = None
            used_encoding = None
            for enc in ['utf-8', 'windows-1250', 'latin-1', 'iso-8859-2']:
                try:
                    report_html = report_path.read_text(encoding=enc, errors='ignore')
                    if report_html:
                        used_encoding = enc
                        break
                except Exception:
                    continue
            
            if report_html:
                result = _extract_report_result(report_html)
                closed_orders = _extract_report_closed_orders(report_html)
                sl_tp = _extract_report_sl_tp_summary(report_html)
        except Exception as e:
            result = None
            closed_orders = None
            sl_tp = None

    if not report_path:
        result_str = "NO_REPORT"
    elif not result:
        result_str = "UNKNOWN"
    else:
        result_str = result.replace('.', ',')

    # pad result_str to at least 8 characters
    result_str = result_str.ljust(8)

    if not report_path:
        closed_str = "NO_REPORT"
    elif closed_orders is None:
        closed_str = "UNKNOWN"
    else:
        closed_str = str(closed_orders)

    if not report_path:
        sl_str = "NO_REPORT"
        tp_str = "NO_REPORT"
    elif not sl_tp:
        sl_str = "UNKNOWN"
        tp_str = "UNKNOWN"
    else:
        sl_count = int(sl_tp.get("sl_count", 0))
        tp_count = int(sl_tp.get("tp_count", 0))
        sl_profit = float(sl_tp.get("sl_profit", 0.0))
        tp_profit = float(sl_tp.get("tp_profit", 0.0))

        # Keep numeric formatting consistent with the existing result formatting (comma decimal separator).
        sl_str = f"{sl_count} ({sl_profit:+.2f})".replace(".", ",")
        tp_str = f"{tp_count} ({tp_profit:+.2f})".replace(".", ",")

    summary_line = (
        f"{month_num}: {result_str} | closed: {closed_str}"
        f" | sl: {sl_str} | tp: {tp_str} | win: "
        f"{(tp_count / (sl_count + tp_count) * 100 if (sl_count + tp_count) > 0 else 0):.2f}%"
    )
    
    # Try to read additional stats from processing_stats.txt
    try:
        # Derive the data folder path based on the from_date
        from_date = config.get('from_date', '')
        if from_date:
            # from_date is like "2025.01.01"
            year_month = '.'.join(from_date.split('.')[:2])  # "2025.01"
            stats_path = CURRENT_DIR.parent / "data" / year_month / "processing_stats.txt"
            
            if stats_path.exists():
                stats_content = stats_path.read_text(encoding='utf-8')
                
                # Extract BUY and SELL counts
                buy_count = 0
                sell_count = 0
                avg_slope = 0.0
                lines_count = 0
                
                for line in stats_content.splitlines():
                    if line.startswith("Decisions: BUY="):
                        parts = line.replace("Decisions: BUY=", "").split(", SELL=")
                        if len(parts) == 2:
                            buy_count = int(parts[0])
                            sell_count = int(parts[1])
                    elif "Avg slope live (x m15):" in line:
                        avg_slope = float(line.split(":")[-1].strip())
                    elif "Number of add/remove lines in month:" in line:
                        lines_count = int(line.split(":")[-1].strip())
                
                total_decisions = buy_count + sell_count
                if total_decisions > 0:
                    summary_line += f" | BUY: {buy_count} | SELL: {sell_count}"
                if avg_slope > 0:
                    summary_line += f" | slope live: {avg_slope:.2f}"
                if lines_count > 0:
                    summary_line += f" | lines: {lines_count}"
    except Exception as e:
        # If we can't read the stats, just continue without them
        pass
    
    print(f"\nWD summary for month {summary_line}")

    try:
        out_path = (CURRENT_DIR / "mt4_test_results" / "wd_summary.txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'a', encoding='utf-8') as f:
            f.write(summary_line + "\n")
    except Exception as e:
        print(f"Warning: could not write wd_summary.txt: {e}")

def main():
    print("=" * 60)
    print("MT4 STRATEGY TESTER RUNNER")
    print("=" * 60)
    
    # Display which config file is being used
    print(f"Config file: {CONFIG_FILE.name}")
    
    # If only --clean flag was provided, just clean and exit
    if CLEAN_LOCAL_RESULTS and len(sys.argv) == 1 and MONTH is None and INPUT_DIR is None:
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
        print("  python run_mt4_tester.py wd_tester          # Uses wd_tester_config.ini")
        print("  python run_mt4_tester.py custom_config.ini  # Uses specified file")
        print("  python run_mt4_tester.py --clean            # Clean local results only")
        print("  python run_mt4_tester.py order-maker --clean # Run with local cleanup")
        return 1
    
    config = read_config()

    # For wd_tester, always clear local copied logs before the run.
    if config.get('expert') == 'wd_tester':
        print("\nUpdating wd_tester_hash.mqh with latest git commit...")
        update_wd_tester_hash_mqh()

        print("\nCleaning local mt4_test_results/logs before wd_tester run...")
        removed = cleanup_local_logs_folder()
        if removed:
            print(f"✓ Removed {removed} item(s) from local logs folder")
        else:
            print("✓ No local logs to remove")

        print("Cleaning old local HTML/GIF reports before wd_tester run...")
        removed_reports = cleanup_local_html_gif_reports()
        if removed_reports:
            print(f"✓ Removed {removed_reports} report file(s) (*.html/*.htm/*.gif)")
        else:
            print("✓ No report files to remove")

    if NO_COPY_DATA and config.get('expert') != 'wd_tester':
        print("Error: --no-copy-data is only supported for the wd_tester expert")
        return 1

    if INPUT_DIR is not None and config.get('expert') != 'wd_tester':
        print("Error: --input-dir is only supported for the wd_tester expert")
        return 1

    if MONTH is not None:
        if config.get('expert') != 'wd_tester':
            print("Error: --month is only supported for the wd_tester expert")
            return 1

        # Use the year from the existing config date range (YYYY.MM.DD)
        try:
            year = int(str(config.get('from_date', '')).split('.', 1)[0])
        except Exception:
            year = time.localtime().tm_year

        last_day = calendar.monthrange(year, MONTH)[1]
        config['from_date'] = f"{year}.{MONTH:02d}.01"
        config['to_date'] = f"{year}.{MONTH:02d}.{last_day:02d}"
        print(f"WD tester month mode: {config['from_date']} to {config['to_date']} (preparing {CONFIG_FILE.name})")
    
    # Clean local results if flag is set
    if CLEAN_LOCAL_RESULTS:
        cleanup_local_results()
    
    # Clean up previous test data
    cleanup_mt4_data()

    # For wd_tester, remove any cached tester input overrides
    if config.get('expert') == 'wd_tester':
        print("\nRemoving cached wd_tester.ini (if any)...")
        removed = cleanup_wd_tester_ini()
        if removed == 0:
            print("✓ No wd_tester.ini found")

    # for wd_tester, copy additional files
    if config['expert'] == 'wd_tester' and not NO_COPY_DATA:
        print("\nCopying additional WD tester files...")

        if INPUT_DIR is not None:
            source_folder = Path(INPUT_DIR).expanduser()
            if not source_folder.is_absolute():
                source_folder = (REPO_ROOT / source_folder).resolve()
        else:
            source_folder = CURRENT_DIR / "mt4_test_results" / "m15_candles" / "charts"

        if not source_folder.exists() or not source_folder.is_dir():
            print(f"Error: input directory not found: {source_folder}")
            return 1

        source_files = list(source_folder.glob("*_decision.txt")) + list(source_folder.glob("*_result.txt"))
        if not source_files:
            print(f"Warning: no *_decision.txt or *_result.txt files found in {source_folder}")

        dest_folder = MT4_TERMINAL_PATH / "tester" / "files" / "wd_tester"
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Cleanup existing wd_tester input data
        removed = 0
        for p in dest_folder.glob("*"):
            try:
                if p.is_file():
                    p.unlink()
                    removed += 1
                elif p.is_dir():
                    shutil.rmtree(p)
                    removed += 1
            except Exception as e:
                print(f"Warning: could not remove {p}: {e}")
        if removed:
            print(f"Cleaned MT4 wd_tester input folder: removed {removed} item(s)")

        copied = 0
        for file in source_files:
            dest = dest_folder / file.name
            shutil.copy2(file, dest)
            copied += 1
        print(f"Copied {copied} WD tester input file(s) from: {source_folder}")
    elif config['expert'] == 'wd_tester' and NO_COPY_DATA:
        print("\nWD tester: --no-copy-data enabled (skipping input data copy)")
        
    # Remove old wd_main.mqh if exists
    old_mqh = CURRENT_DIR / "wd_main.mqh"
    if old_mqh.exists():
        try:
            old_mqh.unlink()
            print("\nRemoved old wd_main.mqh from current folder")
        except Exception as e:
            print(f"Warning: could not remove old wd_main.mqh: {e}")

    # Copy wd_main.mqh from repo folder to current folder
    if config.get('expert') == 'wd_tester':
        print("\nCopying wd_main.mqh to current folder...")
        source_mqh = REPO_ROOT / "wd_main.mqh"
        dest_mqh = CURRENT_DIR / "wd_main.mqh"
        try:
            shutil.copy2(source_mqh, dest_mqh)
            print(f"✓ Copied wd_main.mqh to {dest_mqh}")
        except Exception as e:
            print(f"Warning: could not copy wd_main.mqh: {e}")
            
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

    # For wd_tester, ensure we didn't run with a different git commit than current.
    # This checks the latest copied MT4 log in mt4_test_results/logs/*.log.
    if config.get('expert') == 'wd_tester':
        print("\nVerifying git commit against latest copied MT4 log...")
        if not verify_wd_tester_git_hash_from_latest_log():
            return 1

        print("Checking latest copied MT4 log for ERROR messages...")
        if not fail_if_error_messages_in_latest_log():
            return 1

    # For wd_tester, summarize the report.
    write_wd_summary(config)
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
