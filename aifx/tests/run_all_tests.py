"""
Uruchamia wszystkie testy w projekcie AIFX.

Usage:
    python run_all_tests.py
    python run_all_tests.py --verbose
"""

import sys
import os
import subprocess
from pathlib import Path

# Ustaw kodowanie UTF-8 dla outputu
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


def run_test_file(test_file, verbose=False):
    """Uruchamia pojedynczy plik testowy"""
    print(f"\n{'='*80}")
    print(f"Uruchamiam: {test_file}")
    print('='*80)
    
    try:
        # Ustaw PYTHONIOENCODING dla subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=not verbose,
            text=True,
            cwd=os.path.dirname(test_file),
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            print(f"✅ {test_file} - PASSED")
            if not verbose and result.stdout:
                # Pokaż tylko podsumowanie
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'PASSED' in line or 'TEST' in line or '✓' in line:
                        print(f"   {line}")
            return True
        else:
            print(f"❌ {test_file} - FAILED")
            if result.stdout:
                print("\nSTDOUT:")
                print(result.stdout)
            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ {test_file} - ERROR: {e}")
        return False


def run_impulse_detector_test(impulse_file, verbose=False):
    """Uruchamia test impulse_detector.py --test"""
    test_name = "impulse_detector.py --test"
    print(f"\n{'='*80}")
    print(f"Uruchamiam: {test_name}")
    print('='*80)
    
    try:
        # Ustaw PYTHONIOENCODING dla subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, str(impulse_file), '--test'],
            capture_output=not verbose,
            text=True,
            cwd=os.path.dirname(impulse_file),
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            print(f"✅ {test_name} - PASSED")
            if not verbose and result.stdout:
                # Pokaż tylko podsumowanie
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'PASSED' in line or 'TEST' in line or '✓' in line:
                        print(f"   {line}")
            return True
        else:
            print(f"❌ {test_name} - FAILED")
            if result.stdout:
                print("\nSTDOUT:")
                print(result.stdout)
            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ {test_name} - ERROR: {e}")
        return False


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    # Znajdź wszystkie pliki test_*.py w bieżącym katalogu
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob('test_*.py'))
    
    # Usuń test_hierarchical.py jeśli istnieje (to był tylko przykład)
    test_files = [f for f in test_files if f.name != 'test_hierarchical.py']
    
    # Sprawdź czy impulse_detector.py istnieje w katalogu nadrzędnym
    parent_dir = test_dir.parent
    impulse_detector_path = parent_dir / 'impulse_detector.py'
    impulse_detector_exists = impulse_detector_path.exists()
    
    total_tests = len(test_files) + (1 if impulse_detector_exists else 0)
    
    if total_tests == 0:
        print("❌ Nie znaleziono plików testowych")
        return 1
    
    print(f"\n{'#'*80}")
    print(f"# URUCHAMIAM WSZYSTKIE TESTY ({total_tests} plików)")
    print('#'*80)
    print("\nZnalezione testy:")
    for tf in test_files:
        print(f"  - {tf.name}")
    if impulse_detector_exists:
        print(f"  - impulse_detector.py --test")
    
    # Uruchom wszystkie testy
    results = {}
    for test_file in test_files:
        results[test_file.name] = run_test_file(str(test_file), verbose)
    
    # Uruchom impulse_detector --test
    if impulse_detector_exists:
        results['impulse_detector.py --test'] = run_impulse_detector_test(impulse_detector_path, verbose)
    
    # Podsumowanie
    print(f"\n{'#'*80}")
    print("# PODSUMOWANIE")
    print('#'*80)
    
    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} - {test_name}")
    
    print(f"\n{'#'*80}")
    if failed == 0:
        print(f"# ✅✅✅ WSZYSTKIE TESTY PASSED ({passed}/{len(results)}) ✅✅✅")
    else:
        print(f"# ❌ {failed}/{len(results)} TESTÓW FAILED")
    print(f"{'#'*80}\n")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
