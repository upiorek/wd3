"""
Simple cleanup script to remove generated test files
Prepares the workspace for a fresh test run
"""

import os
import shutil
import glob

def cleanup():
    """Remove generated files from previous test runs"""
    
    print("\n" + "="*60)
    print("CLEANUP SCRIPT")
    print("="*60)
    
    files_deleted = 0
    folders_cleaned = 0
    
    # 1. Remove test completion files
    print("\n🗑️  Removing test completion files...")
    test_files = glob.glob("test_completed_*.txt")
    for file in test_files:
        try:
            os.remove(file)
            print(f"   Deleted: {file}")
            files_deleted += 1
        except Exception as e:
            print(f"   Error deleting {file}: {e}")
    
    # 2. Clean m15_candles folder
    candles_folder = "m15_candles"
    if os.path.exists(candles_folder):
        print(f"\n🗑️  Cleaning {candles_folder} folder...")
        try:
            # Count files before deletion
            files_before = len([f for f in os.listdir(candles_folder) if os.path.isfile(os.path.join(candles_folder, f))])
            
            # Remove all files but keep the folder
            for item in os.listdir(candles_folder):
                item_path = os.path.join(candles_folder, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
            
            print(f"   Deleted {files_before} file(s) from {candles_folder}")
            files_deleted += files_before
            folders_cleaned += 1
        except Exception as e:
            print(f"   Error cleaning {candles_folder}: {e}")
    else:
        print(f"\n✓ {candles_folder} folder doesn't exist (nothing to clean)")
    
    # 3. Clean MT4 Files folders
    print("\n🗑️  Cleaning MT4 Files folders...")
    appdata = os.getenv('APPDATA')
    if appdata:
        terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
        if os.path.exists(terminal_base):
            for item in os.listdir(terminal_base):
                # Clean m15_candles subfolder
                mt4_candles = os.path.join(terminal_base, item, 'tester', 'files', 'm15_candles')
                if os.path.exists(mt4_candles):
                    try:
                        files_count = len([f for f in os.listdir(mt4_candles) if os.path.isfile(os.path.join(mt4_candles, f))])
                        for file in os.listdir(mt4_candles):
                            file_path = os.path.join(mt4_candles, file)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        if files_count > 0:
                            print(f"   Cleaned MT4 m15_candles: {files_count} files")
                            files_deleted += files_count
                            folders_cleaned += 1
                    except Exception as e:
                        print(f"   Error cleaning {mt4_candles}: {e}")
                
                # Clean root tester/files folder (Python scripts, result files, etc.)
                mt4_files_root = os.path.join(terminal_base, item, 'tester', 'files')
                if os.path.exists(mt4_files_root):
                    try:
                        # Only remove specific files, not all files
                        cleanup_patterns = ['python_result.txt', 'analyze_candles.py', 'test_completed_*.txt']
                        root_files_deleted = 0
                        for pattern in cleanup_patterns:
                            for file_path in glob.glob(os.path.join(mt4_files_root, pattern)):
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                                    root_files_deleted += 1
                        if root_files_deleted > 0:
                            print(f"   Cleaned MT4 files root: {root_files_deleted} files")
                            files_deleted += root_files_deleted
                    except Exception as e:
                        print(f"   Error cleaning {mt4_files_root}: {e}")
                
                # Clean Experts folder (EA files)
                mt4_experts = os.path.join(terminal_base, item, 'MQL4', 'Experts')
                if os.path.exists(mt4_experts):
                    try:
                        # Remove SaveM15Candles EA files (.mq4, .ex4, .log)
                        ea_patterns = ['SaveM15Candles.mq4', 'SaveM15Candles.ex4', 'SaveM15Candles.log']
                        experts_files_deleted = 0
                        for pattern in ea_patterns:
                            file_path = os.path.join(mt4_experts, pattern)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                experts_files_deleted += 1
                        if experts_files_deleted > 0:
                            print(f"   Cleaned MT4 Experts: {experts_files_deleted} files")
                            files_deleted += experts_files_deleted
                    except Exception as e:
                        print(f"   Error cleaning {mt4_experts}: {e}")
        else:
            print(f"   MT4 Terminal folder not found")
    else:
        print(f"   APPDATA environment variable not found")
    
    # Summary
    print("\n" + "="*60)
    print("✓ CLEANUP COMPLETE")
    print("="*60)
    print(f"   Files deleted: {files_deleted}")
    print(f"   Folders cleaned: {folders_cleaned}")
    print()

if __name__ == "__main__":
    cleanup()
