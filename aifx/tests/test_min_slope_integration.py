"""
Test integracyjny: uruchom run_support_backtest.py i sprawdź czy używa min_slope z config
"""
import subprocess
import re

def test_run_support_backtest_uses_config_min_slope():
    """Test: run_support_backtest.py faktycznie używa min_slope=0.4 z config"""
    
    print("\n" + "="*80)
    print("TEST INTEGRACYJNY: run_support_backtest.py + config_example.json")
    print("="*80)
    
    # Uruchom run_support_backtest.py z config_example.json
    cmd = ['python', 'run_support_backtest.py', 'config_example.json']
    
    print(f"\nUruchamiam: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd='.',
        capture_output=True,
        text=True,
        timeout=60
    )
    
    output = result.stdout + result.stderr
    
    # Szukaj linii z "Min slope:"
    min_slope_pattern = r'Min slope:\s*([\d.]+)'
    matches = re.findall(min_slope_pattern, output)
    
    if not matches:
        print("\n❌ BŁĄD: Nie znaleziono 'Min slope:' w output")
        print("\nOUTPUT:")
        print(output[:1000])
        raise AssertionError("Brak 'Min slope:' w logu")
    
    min_slope_from_log = float(matches[0])
    print(f"\n✓ Znaleziono w logu: Min slope: {min_slope_from_log}")
    
    # Oczekiwana wartość z config
    expected_min_slope = 0.4
    
    # Sprawdź czy się zgadza
    assert min_slope_from_log == expected_min_slope, \
        f"❌ Min slope w logu ({min_slope_from_log}) != min_slope w config ({expected_min_slope})"
    
    print(f"✓ Test PASSED: run_support_backtest.py używa min_slope={min_slope_from_log} z config")
    print("="*80)


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    try:
        test_run_support_backtest_uses_config_min_slope()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
