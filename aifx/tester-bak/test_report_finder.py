"""Quick test to find MT4 reports"""
import os
import glob
import time
from datetime import datetime

appdata = os.getenv('APPDATA')
terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')

print(f"\n{'='*70}")
print("MT4 REPORT FINDER - DIAGNOSTIC TEST")
print(f"{'='*70}\n")

print(f"Checking: {terminal_base}")
print(f"Exists: {os.path.exists(terminal_base)}\n")

if os.path.exists(terminal_base):
    dirs = os.listdir(terminal_base)
    print(f"Found {len(dirs)} terminal directories:\n")
    
    for dir_name in dirs:
        terminal_dir = os.path.join(terminal_base, dir_name)
        reports_dir = os.path.join(terminal_dir, 'tester', 'reports')
        
        if os.path.exists(reports_dir):
            print(f"  ✓ {dir_name}")
            print(f"    Reports folder: {reports_dir}")
            
            # Find HTML reports
            pattern = os.path.join(reports_dir, "*.htm")
            reports = glob.glob(pattern)
            
            print(f"    Found {len(reports)} report file(s)")
            
            # Show recent reports (last 24 hours)
            cutoff = time.time() - (24 * 3600)
            recent = [r for r in reports if os.path.getmtime(r) >= cutoff]
            
            if recent:
                print(f"    Recent reports (last 24 hours): {len(recent)}")
                for report in sorted(recent, key=lambda x: os.path.getmtime(x), reverse=True)[:3]:
                    mtime = datetime.fromtimestamp(os.path.getmtime(report))
                    print(f"      - {os.path.basename(report)}")
                    print(f"        Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"    No reports from last 24 hours")
            print()
        else:
            print(f"  ✗ {dir_name} (no reports folder)")
else:
    print("❌ Terminal directory not found!")

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}\n")
print("If no recent reports were found:")
print("  1. Make sure an MT4 test has been run")
print("  2. Check that MT4 is configured to generate reports")
print("  3. Verify TestReport setting in mt4_test_config.ini")
print("  4. The test may still be running\n")
