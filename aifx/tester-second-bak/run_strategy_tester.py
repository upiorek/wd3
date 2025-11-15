"""
Simple MT4 Strategy Tester Runner
Runs MT4 strategy tester using configuration from mt4_test_config.ini
"""

import subprocess
import os
import sys
import time
import configparser
import shutil
import argparse
from pathlib import Path

# MT4 Terminal Path
MT4_PATH = r"C:\Program Files (x86)\mForex Trader\terminal.exe"

# Configuration file path
CONFIG_FILE = "mt4_test_config.ini"

# EA file to copy (in same directory as script)
EA_SOURCE = os.path.join(os.path.dirname(__file__), "SaveM15Candles.mq4")
if not EA_SOURCE or EA_SOURCE == "SaveM15Candles.mq4":
    EA_SOURCE = "SaveM15Candles.mq4"

# Analyze candles script to copy
ANALYZE_SCRIPT = os.path.join(os.path.dirname(__file__), "analyze_candles.py")
if not ANALYZE_SCRIPT or ANALYZE_SCRIPT == "analyze_candles.py":
    ANALYZE_SCRIPT = "analyze_candles.py"

# Python analyzer DLL to copy
DLL_SOURCE = os.path.join(os.path.dirname(__file__), "dll_wrapper", "PythonAnalyzer.dll")

# Destination folder for candle data
CANDLES_DEST = r"C:\trading_system\wd3\aifx\tester\m15_candles"


def find_mt4_files_folder():
    """Find MT4 Files folder"""
    # Get MT4 directory
    mt4_dir = os.path.dirname(MT4_PATH)
    
    # Check AppData
    appdata = os.getenv('APPDATA')
    if appdata:
        terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
        if os.path.exists(terminal_base):
            for item in os.listdir(terminal_base):
                # Try tester/files first (for strategy tester)
                possible_path = os.path.join(terminal_base, item, 'tester', 'files')
                if os.path.exists(possible_path):
                    return possible_path
                # Fall back to MQL4/Files (for live trading)
                possible_path = os.path.join(terminal_base, item, 'MQL4', 'Files')
                if os.path.exists(possible_path):
                    return possible_path
    
    return None


def find_mt4_library_folders():
    """Locate possible MT4 library folders"""
    folders = []

    # MT4 installation directory
    mt4_dir = os.path.dirname(MT4_PATH)
    install_lib = os.path.join(mt4_dir, "MQL4", "Libraries")
    if os.path.exists(install_lib):
        folders.append(install_lib)

    parent_lib = os.path.join(mt4_dir, "..", "MQL4", "Libraries")
    if os.path.exists(parent_lib):
        folders.append(os.path.abspath(parent_lib))

    appdata = os.getenv('APPDATA')
    if appdata:
        terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
        if os.path.exists(terminal_base):
            for item in os.listdir(terminal_base):
                base_path = os.path.join(terminal_base, item)
                mql_lib = os.path.join(base_path, 'MQL4', 'Libraries')
                tester_lib = os.path.join(base_path, 'tester', 'libraries')

                if os.path.exists(mql_lib):
                    folders.append(mql_lib)
                if os.path.exists(tester_lib):
                    folders.append(tester_lib)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for folder in folders:
        if folder not in seen:
            unique.append(folder)
            seen.add(folder)

    return unique


def copy_candles_to_destination():
    """Copy candle CSV files from MT4 Files folder to destination"""
    mt4_files = find_mt4_files_folder()
    if not mt4_files:
        print(f"⚠ Warning: Could not find MT4 Files folder")
        return False
    
    source_folder = os.path.join(mt4_files, "m15_candles")
    if not os.path.exists(source_folder):
        print(f"⚠ No candle data found at: {source_folder}")
        return False
    
    # Create destination folder
    os.makedirs(CANDLES_DEST, exist_ok=True)
    
    # Copy all CSV files
    copied_count = 0
    for filename in os.listdir(source_folder):
        if filename.endswith('.csv'):
            src = os.path.join(source_folder, filename)
            dst = os.path.join(CANDLES_DEST, filename)
            shutil.copy2(src, dst)
            copied_count += 1
    
    # Copy test completion file if exists
    completion_files = [f for f in os.listdir(source_folder) if f.startswith('test_completed_')]
    for filename in completion_files:
        src = os.path.join(source_folder, filename)
        dst = os.path.join(os.path.dirname(__file__), filename)
        shutil.copy2(src, dst)
        print(f"✓ Copied test completion file: {filename}")
    
    if copied_count > 0:
        print(f"✓ Copied {copied_count} candle file(s) to: {CANDLES_DEST}")
        return True
    else:
        print(f"⚠ No CSV files found in: {source_folder}")
        return False


def find_mt4_experts_folder():
    """Find MT4 Experts folder"""
    # Get MT4 directory
    mt4_dir = os.path.dirname(MT4_PATH)
    
    # Try common locations
    possible_paths = [
        os.path.join(mt4_dir, "MQL4", "Experts"),
        os.path.join(mt4_dir, "..", "MQL4", "Experts"),
    ]
    
    # Check AppData
    appdata = os.getenv('APPDATA')
    if appdata:
        terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
        if os.path.exists(terminal_base):
            for item in os.listdir(terminal_base):
                possible_path = os.path.join(terminal_base, item, 'MQL4', 'Experts')
                if os.path.exists(possible_path):
                    possible_paths.append(possible_path)
    
    # Return first existing path
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def compile_ea(mq4_path):
    """Compile MQ4 file using MetaEditor"""
    # Find MetaEditor
    mt4_dir = os.path.dirname(MT4_PATH)
    metaeditor_path = os.path.join(mt4_dir, "metaeditor.exe")
    
    # Also check one level up
    if not os.path.exists(metaeditor_path):
        metaeditor_path = os.path.join(mt4_dir, "..", "metaeditor.exe")
    
    if not os.path.exists(metaeditor_path):
        print(f"⚠ Warning: MetaEditor not found")
        return False
    
    print(f"🔨 Compiling EA with MetaEditor...")
    print(f"   Source: {mq4_path}")
    
    try:
        # MetaEditor command line: metaeditor.exe /compile:"path\to\file.mq4"
        cmd = [metaeditor_path, f'/compile:{mq4_path}']
        
        # Run compilation
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Wait a moment for compilation to complete
        time.sleep(2)
        
        # Check if .ex4 was created
        ex4_path = mq4_path.replace('.mq4', '.ex4')
        if os.path.exists(ex4_path):
            print(f"✓ EA compiled successfully: {os.path.basename(ex4_path)}")
            return True
        else:
            print(f"⚠ Compilation may have failed - .ex4 file not found")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⚠ Compilation timeout")
        return False
    except Exception as e:
        print(f"⚠ Error during compilation: {e}")
        return False


def copy_ea_to_mt4():
    """Copy EA file to MT4 Experts folder and compile if needed"""
    if not os.path.exists(EA_SOURCE):
        print(f"⚠ Warning: EA file not found: {EA_SOURCE}")
        return False
    
    experts_folder = find_mt4_experts_folder()
    if not experts_folder:
        print(f"⚠ Warning: Could not find MT4 Experts folder")
        print(f"   Please manually copy {EA_SOURCE} to MT4's Experts folder")
        return False
    
    try:
        dest_path = os.path.join(experts_folder, "SaveM15Candles.mq4")
        ex4_path = dest_path.replace('.mq4', '.ex4')
        
        # Always copy the source file
        shutil.copy2(EA_SOURCE, dest_path)
        print(f"✓ EA source copied to: {dest_path}")
        
        # Check if we need to compile
        needs_compilation = False
        
        if not os.path.exists(ex4_path):
            print(f"ℹ Compiled .ex4 file not found - will compile")
            needs_compilation = True
        else:
            # Check if source is newer than compiled version
            mq4_time = os.path.getmtime(dest_path)
            ex4_time = os.path.getmtime(ex4_path)
            if mq4_time > ex4_time:
                print(f"ℹ Source file is newer - will recompile")
                needs_compilation = True
            else:
                print(f"✓ Compiled .ex4 file is up to date")
        
        # Compile if needed
        if needs_compilation:
            if not compile_ea(dest_path):
                print(f"❌ ERROR: Compilation failed - cannot continue")
                print(f"   Please fix compilation errors in the MQ4 file")
                return False
        
        return True
    except Exception as e:
        print(f"⚠ Warning: Error copying EA: {e}")
        return False


def copy_python_script_to_mt4():
    """Copy Python analysis script to MT4 Files folder"""
    if not os.path.exists(ANALYZE_SCRIPT):
        print(f"⚠ Warning: Python script not found: {ANALYZE_SCRIPT}")
        return False
    
    mt4_files = find_mt4_files_folder()
    if not mt4_files:
        print(f"⚠ Warning: Could not find MT4 Files folder")
        return False
    
    try:
        # Copy to both root Files folder and m15_candles subfolder
        dest_root = os.path.join(mt4_files, "analyze_candles.py")
        shutil.copy2(ANALYZE_SCRIPT, dest_root)
        print(f"✓ Python script copied to: {dest_root}")
        
        # Also copy to m15_candles subfolder if it exists
        candles_folder = os.path.join(mt4_files, "m15_candles")
        if os.path.exists(candles_folder):
            dest_candles = os.path.join(candles_folder, "analyze_candles.py")
            shutil.copy2(ANALYZE_SCRIPT, dest_candles)
            print(f"✓ Python script also copied to: {dest_candles}")
        
        return True
    except Exception as e:
        print(f"⚠ Warning: Error copying Python script: {e}")
        return False


def copy_dll_to_mt4():
    """Copy Python analyzer DLL to all relevant MT4 library folders"""
    if not os.path.exists(DLL_SOURCE):
        print(f"⚠ Warning: Python analyzer DLL not found: {DLL_SOURCE}")
        print("   Compile the DLL (PythonAnalyzer.dll) before running the tester.")
        return False

    target_folders = find_mt4_library_folders()
    if not target_folders:
        print("⚠ Warning: Could not locate MT4 library folders")
        return False

    success = True
    for folder in target_folders:
        try:
            os.makedirs(folder, exist_ok=True)
            dest = os.path.join(folder, "PythonAnalyzer.dll")
            shutil.copy2(DLL_SOURCE, dest)
            print(f"✓ DLL copied to: {dest}")
            
            # Also copy python311.dll runtime
            python_dll_source = os.path.join(os.path.dirname(DLL_SOURCE), "python311.dll")
            if os.path.exists(python_dll_source):
                python_dll_dest = os.path.join(folder, "python311.dll")
                shutil.copy2(python_dll_source, python_dll_dest)
                print(f"✓ Python runtime copied to: {python_dll_dest}")
        except Exception as exc:
            success = False
            print(f"⚠ Warning: Failed to copy DLL to {folder}: {exc}")

    return success


def check_mt4_exists():
    """Check if MT4 terminal exists at specified path"""
    if not os.path.exists(MT4_PATH):
        print(f"❌ Error: MT4 terminal not found at: {MT4_PATH}")
        print(f"   Please update MT4_PATH in this script to match your installation")
        return False
    return True


def check_config_exists():
    """Check if configuration file exists"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: Configuration file not found: {CONFIG_FILE}")
        print(f"   Please ensure {CONFIG_FILE} exists in the current directory")
        return False
    return True


def read_config():
    """Read and display configuration settings"""
    try:
        # Read MT4 INI file manually (it doesn't have section headers)
        settings = {}
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line.startswith(';') or not line or '=' not in line:
                    continue
                # Parse key=value
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
        
        print(f"\n{'='*60}")
        print("MT4 STRATEGY TESTER - CONFIGURATION")
        print(f"{'='*60}")
        
        print(f"\n📊 Test Settings:")
        print(f"  Expert Advisor:    {settings.get('TestExpert', 'N/A')}")
        print(f"  Symbol:            {settings.get('TestSymbol', 'N/A')}")
        print(f"  Period:            {settings.get('TestPeriod', 'N/A')}")
        print(f"  Test Model:        {settings.get('TestModel', 'N/A')}")
        print(f"  From Date:         {settings.get('TestFromDate', 'N/A')}")
        print(f"  To Date:           {settings.get('TestToDate', 'N/A')}")
        print(f"  Visual Mode:       {settings.get('TestVisualEnable', 'N/A')}")
        print(f"  Auto Shutdown:     {settings.get('TestShutdownTerminal', 'N/A')}")
        
        # Check for EA parameters
        if 'TestExpertParameters' in settings:
            print(f"  EA Parameters:     {settings['TestExpertParameters']}")
        
        print(f"\n{'='*60}")
        return True
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False


def create_settings_file(candles_count, sl_points, tp_points):
    """Create a settings.txt file with EA parameters"""
    if candles_count is None and sl_points is None and tp_points is None:
        # Remove settings file if no parameters specified
        return None
    
    # Find MT4 Files folder for settings.txt file
    mt4_files = find_mt4_files_folder()
    if not mt4_files:
        print("⚠ Warning: Could not find MT4 Files folder")
        return None
    
    settings_file_path = os.path.join(mt4_files, 'settings.txt')
    
    try:
        # Create settings.txt file
        with open(settings_file_path, 'w') as f:
            f.write("; EA Settings File\n")
            f.write("; Created automatically by run_strategy_tester.py\n")
            f.write(";\n")
            if candles_count is not None:
                f.write(f"NumberOfCandles={candles_count}\n")
            if sl_points is not None:
                f.write(f"StopLossPoints={sl_points}\n")
            if tp_points is not None:
                f.write(f"TakeProfitPoints={tp_points}\n")
        
        print(f"✓ Settings file created: {settings_file_path}")
        if candles_count is not None:
            print(f"  NumberOfCandles={candles_count}")
        if sl_points is not None:
            print(f"  StopLossPoints={sl_points}")
        if tp_points is not None:
            print(f"  TakeProfitPoints={tp_points}")
        return True
    except Exception as e:
        print(f"⚠ Warning: Could not create settings file: {e}")
        return None


def update_config_to_remove_parameters():
    """Remove TestExpertParameters from config file"""
    try:
        # Read current config
        with open(CONFIG_FILE, 'r') as f:
            lines = f.readlines()
        
        # Remove or comment out TestExpertParameters line
        for i, line in enumerate(lines):
            if line.strip().startswith('TestExpertParameters='):
                lines[i] = ';' + line  # Comment it out
                break
        
        # Write updated config
        with open(CONFIG_FILE, 'w') as f:
            f.writelines(lines)
        
        print(f"✓ Config updated to not use .set file")
    except Exception as e:
        print(f"⚠ Warning: Could not update config file: {e}")


def launch_mt4():
    """Launch MT4 with configuration file"""
    config_path = os.path.abspath(CONFIG_FILE)
    
    print(f"\n🚀 Launching MT4 Strategy Tester...")
    print(f"   MT4 Path:   {MT4_PATH}")
    print(f"   Config:     {config_path}")
    
    try:
        # Launch MT4 with config file
        cmd = [MT4_PATH, config_path]
        process = subprocess.Popen(cmd)
        
        return process
        
    except Exception as e:
        print(f"\n❌ Error launching MT4: {e}")
        return None


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run MT4 Strategy Tester')
    parser.add_argument('--candles', type=int, default=None,
                       help='Number of M15 candles to analyze (default: 10)')
    parser.add_argument('--sl', type=float, default=None,
                       help='Stop Loss in points (0 = disabled)')
    parser.add_argument('--tp', type=float, default=None,
                       help='Take Profit in points (0 = disabled)')
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("MT4 STRATEGY TESTER RUNNER")
    print(f"{'='*60}")
    
    # If any parameter is specified, create settings file
    if args.candles is not None or args.sl is not None or args.tp is not None:
        print(f"\n⚙️  Setting EA parameters...")
        if args.candles is not None:
            print(f"   NumberOfCandles: {args.candles}")
        if args.sl is not None:
            print(f"   StopLoss: {args.sl} points")
        if args.tp is not None:
            print(f"   TakeProfit: {args.tp} points")
        create_settings_file(args.candles, args.sl, args.tp)
        update_config_to_remove_parameters()
    
    # Copy EA to MT4
    print(f"\n📁 Copying EA to MT4...")
    if not copy_ea_to_mt4():
        print(f"\n❌ ABORTED: Cannot proceed without compiled EA")
        sys.exit(1)
    
    # Copy Python script to MT4
    print(f"\n🐍 Copying Python script to MT4...")
    copy_python_script_to_mt4()

    # Copy analyzer DLL to MT4
    print(f"\n🧩 Copying analyzer DLL to MT4...")
    copy_dll_to_mt4()
    
    # Check MT4 exists
    if not check_mt4_exists():
        sys.exit(1)
    
    # Check config file exists
    if not check_config_exists():
        sys.exit(1)
    
    # Read and display config
    if not read_config():
        sys.exit(1)
    
    # Launch MT4
    process = launch_mt4()
    if not process:
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("✓ MT4 Launched - Test Starting")
    print(f"{'='*60}")
    
    # Wait for MT4 to complete (it will auto-close when test finishes)
    print(f"\n⏳ Waiting for MT4 to complete test and shutdown...")
    print(f"   (Config has TestShutdownTerminal=true, so MT4 will close automatically)")
    print(f"   (Press Ctrl+C to skip waiting and exit)")
    
    try:
        # Wait for MT4 process to finish
        process.wait()
        print(f"\n✓ MT4 closed - Test completed")
        
        # Give it a moment for files to be written
        time.sleep(2)
        
        print(f"\n📁 Copying candle data files...")
        copy_candles_to_destination()
        
    except KeyboardInterrupt:
        print(f"\n⚠ Interrupted by user")
        print(f"   MT4 may still be running. Check Task Manager if needed.")
    
    print()


if __name__ == "__main__":
    main()
