"""
Test wykrywający błąd: min_slope z config nie jest używany
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from support_breakout_strategy import SupportBreakoutStrategy

def test_min_slope_from_config():
    """Test: min_slope z config powinien być używany w strategii"""
    
    # Wczytaj config
    with open('config_example.json', 'r') as f:
        config = json.load(f)
    
    min_slope_from_config = config['min_slope']
    print(f"\nmin_slope w config: {min_slope_from_config}")
    
    # Stwórz strategię z parametrami z config
    strategy = SupportBreakoutStrategy(
        lookback_days=config['lookback_days'],
        risk_pips=config['risk_pips'],
        reward_ratio=config['reward_ratio'],
        min_slope=config['min_slope'],
        close_at_eod=config.get('close_at_eod', False)
    )
    
    # Sprawdź czy min_slope został zapisany w strategii
    print(f"min_slope w strategii: {strategy.min_slope}")
    
    # Asercja
    assert strategy.min_slope == min_slope_from_config, \
        f"min_slope w strategii ({strategy.min_slope}) != min_slope z config ({min_slope_from_config})"
    
    print(f"✓ Test PASSED: min_slope poprawnie przechowany w strategii")


def test_min_slope_used_in_run_support_backtest():
    """Test: run_support_backtest.py przekazuje min_slope z config do strategii"""
    
    # Wczytaj config
    with open('config_example.json', 'r') as f:
        config = json.load(f)
    
    min_slope_from_config = config['min_slope']
    
    # Sprawdź czy min_slope jest w config
    assert 'min_slope' in config, "Brak min_slope w config"
    
    print(f"\n✓ min_slope={config['min_slope']} znaleziony w config")
    
    # Symuluj to co robi run_support_backtest.py
    default_options = {
        'start_date': None,
        'end_date': None,
        'lookback_days': 5,
        'risk_pips': 20,
        'reward_ratio': 2.5,
        'retest_mode': False,
        'initial_capital': 10000,
        'risk_per_trade_pct': 2.0,
        'min_slope': 0.1,  # DEFAULT!
        'show_volume': True,
        'generate_charts': True,
        'hierarchical_levels_below': 4,
        'hierarchical_levels_above': 4,
        'hierarchical_tolerance': 30,
        'allow_descending': True
    }
    
    # Merge jak w run_support_backtest.py line 126
    options = {**default_options, **config}
    
    print(f"✓ Po merge: min_slope={options['min_slope']}")
    
    # Sprawdź czy merge zadziałał
    assert options['min_slope'] == min_slope_from_config, \
        f"Merge nie zadziałał! Oczekiwano {min_slope_from_config}, dostano {options['min_slope']}"
    
    # Sprawdź czy zostałby przekazany do strategii
    strategy = SupportBreakoutStrategy(
        lookback_days=config['lookback_days'],
        risk_pips=config['risk_pips'],
        reward_ratio=config['reward_ratio'],
        min_slope=options.get('min_slope', 0.1),  # Jak w run_support_backtest.py
        close_at_eod=config.get('close_at_eod', False)
    )
    
    assert strategy.min_slope == min_slope_from_config, \
        f"min_slope nie został przekazany! Oczekiwano {min_slope_from_config}, dostano {strategy.min_slope}"
    
    print(f"✓ Test PASSED: min_slope={strategy.min_slope} poprawnie przekazany do strategii")


if __name__ == '__main__':
    print("=" * 80)
    print("TESTY MIN_SLOPE")
    print("=" * 80)
    
    try:
        test_min_slope_from_config()
        print()
        test_min_slope_used_in_run_support_backtest()
        
        print("\n" + "=" * 80)
        print("✓✓✓ WSZYSTKIE TESTY PASSED ✓✓✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("=" * 80)
        exit(1)
