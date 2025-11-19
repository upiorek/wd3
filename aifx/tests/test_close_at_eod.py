"""
Testy dla opcji close_at_eod (zamykanie pozycji na koniec dnia).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from support_breakout_strategy import SupportBreakoutStrategy

def test_close_at_eod_disabled():
    """Test: pozycja NIE jest zamykana na koniec dnia gdy close_at_eod=False"""
    
    # Strategia z wyłączonym EOD
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=3,
        close_at_eod=False
    )
    
    # Stwórz DataFrame z danymi na 2 dni
    # Dzień 1: 2025-01-02, Dzień 2: 2025-01-03
    dates = []
    for day in [2, 3]:
        for hour in range(0, 24):
            dates.append(datetime(2025, 1, day, hour, 0))
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': [25000.0] * len(dates),
        'High': [25100.0] * len(dates),
        'Low': [24980.0] * len(dates),  # Low POWYŻEJ SL (24950)
        'Close': [25050.0] * len(dates),
        'Volume': [1000] * len(dates)
    })
    
    # Symuluj trade otwarty o 10:00 pierwszego dnia
    trade = {
        'direction': 'long',
        'entry_price': 25000.0,
        'sl_price': 24950.0,  # SL 50 pips niżej
        'tp_price': 25150.0,  # TP 150 pips wyżej
        'time': datetime(2025, 1, 2, 10, 0)
    }
    
    # Sprawdź exit na ostatniej świeczce dnia 1 (23:00)
    idx_last_candle_day1 = 23  # 23:00 pierwszego dnia
    exit_info = strategy.check_exit(df, idx_last_candle_day1, trade)
    
    # Nie powinno być wyjścia (close_at_eod=False)
    assert exit_info is None, f"Expected no exit with close_at_eod=False, got {exit_info}"
    
    print("✓ Test 1 PASSED: Pozycja NIE zamknięta na EOD gdy close_at_eod=False")


def test_close_at_eod_enabled():
    """Test: pozycja JEST zamykana na koniec dnia gdy close_at_eod=True"""
    
    # Strategia z włączonym EOD
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=3,
        close_at_eod=True
    )
    
    # Stwórz DataFrame z danymi na 2 dni
    dates = []
    for day in [2, 3]:
        for hour in range(0, 24):
            dates.append(datetime(2025, 1, day, hour, 0))
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': [25000.0] * len(dates),
        'High': [25100.0] * len(dates),
        'Low': [24980.0] * len(dates),  # Low POWYŻEJ SL
        'Close': [25050.0] * len(dates),  # Close wyżej o 50 pips
        'Volume': [1000] * len(dates)
    })
    
    # Symuluj LONG trade otwarty o 10:00 pierwszego dnia
    trade_long = {
        'direction': 'long',
        'entry_price': 25000.0,
        'sl_price': 24950.0,
        'tp_price': 25150.0,
        'time': datetime(2025, 1, 2, 10, 0)
    }
    
    # Sprawdź exit na ostatniej świeczce dnia 1 (23:00)
    idx_last_candle_day1 = 23
    exit_info = strategy.check_exit(df, idx_last_candle_day1, trade_long)
    
    # Powinno być wyjście EOD
    assert exit_info is not None, "Expected EOD exit with close_at_eod=True"
    assert exit_info['result'] == 'EOD', f"Expected result='EOD', got {exit_info['result']}"
    assert exit_info['reason'] == 'End of Day close', f"Expected EOD reason, got {exit_info['reason']}"
    assert exit_info['exit_price'] == 25050.0, f"Expected exit at Close price 25050.0, got {exit_info['exit_price']}"
    
    # Sprawdź pips dla LONG (exit_price - entry_price)
    expected_pips = 25050.0 - 25000.0
    assert exit_info['pips'] == expected_pips, f"Expected {expected_pips} pips, got {exit_info['pips']}"
    
    print("✓ Test 2 PASSED: Pozycja LONG zamknięta na EOD po cenie Close (50 pips zysku)")


def test_close_at_eod_short_position():
    """Test: pozycja SHORT zamykana na koniec dnia z poprawnym obliczeniem pips"""
    
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=3,
        close_at_eod=True
    )
    
    dates = []
    for day in [2, 3]:
        for hour in range(0, 24):
            dates.append(datetime(2025, 1, day, hour, 0))
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': [25000.0] * len(dates),
        'High': [25020.0] * len(dates),  # High PONIŻEJ SL dla SHORT
        'Low': [24900.0] * len(dates),
        'Close': [24950.0] * len(dates),  # Close niżej o 50 pips
        'Volume': [1000] * len(dates)
    })
    
    # Symuluj SHORT trade
    trade_short = {
        'direction': 'short',
        'entry_price': 25000.0,
        'sl_price': 25050.0,  # SL wyżej dla SHORT
        'tp_price': 24850.0,  # TP niżej dla SHORT
        'time': datetime(2025, 1, 2, 10, 0)
    }
    
    idx_last_candle_day1 = 23
    exit_info = strategy.check_exit(df, idx_last_candle_day1, trade_short)
    
    assert exit_info is not None, "Expected EOD exit for SHORT"
    assert exit_info['result'] == 'EOD', f"Expected result='EOD', got {exit_info['result']}"
    
    # Sprawdź pips dla SHORT (entry_price - exit_price)
    expected_pips = 25000.0 - 24950.0  # 50 pips zysku
    assert exit_info['pips'] == expected_pips, f"Expected {expected_pips} pips for SHORT, got {exit_info['pips']}"
    
    print("✓ Test 3 PASSED: Pozycja SHORT zamknięta na EOD z poprawnymi pipsami (50 pips zysku)")


def test_close_at_eod_not_triggered_before_eod():
    """Test: EOD NIE jest triggerowane przed końcem dnia"""
    
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=3,
        close_at_eod=True
    )
    
    dates = []
    for day in [2, 3]:
        for hour in range(0, 24):
            dates.append(datetime(2025, 1, day, hour, 0))
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': [25000.0] * len(dates),
        'High': [25100.0] * len(dates),  # High PONIŻEJ TP
        'Low': [24980.0] * len(dates),  # Low POWYŻEJ SL
        'Close': [25050.0] * len(dates),
        'Volume': [1000] * len(dates)
    })
    
    trade = {
        'direction': 'long',
        'entry_price': 25000.0,
        'sl_price': 24950.0,
        'tp_price': 25150.0,
        'time': datetime(2025, 1, 2, 10, 0)
    }
    
    # Sprawdź exit w środku dnia (12:00)
    idx_middle_day = 12
    exit_info = strategy.check_exit(df, idx_middle_day, trade)
    
    # Nie powinno być EOD exit w środku dnia
    assert exit_info is None, f"Expected no EOD exit in middle of day, got {exit_info}"
    
    print("✓ Test 4 PASSED: EOD NIE triggerowane przed końcem dnia")


def test_close_at_eod_tp_has_priority():
    """Test: TP ma priorytet nad EOD (TP jest sprawdzane najpierw)"""
    
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=3,
        close_at_eod=True
    )
    
    dates = []
    for day in [2, 3]:
        for hour in range(0, 24):
            dates.append(datetime(2025, 1, day, hour, 0))
    
    # Cena osiąga TP na ostatniej świeczce
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': [25000.0] * len(dates),
        'High': [25200.0] * len(dates),  # High osiąga TP
        'Low': [24980.0] * len(dates),  # Low POWYŻEJ SL
        'Close': [25050.0] * len(dates),
        'Volume': [1000] * len(dates)
    })
    
    trade = {
        'direction': 'long',
        'entry_price': 25000.0,
        'sl_price': 24950.0,
        'tp_price': 25150.0,  # TP osiągnięte przez High
        'time': datetime(2025, 1, 2, 10, 0)
    }
    
    idx_last_candle_day1 = 23
    exit_info = strategy.check_exit(df, idx_last_candle_day1, trade)
    
    # Powinno być TP, nie EOD
    assert exit_info is not None, "Expected exit"
    assert exit_info['result'] == 'TP', f"Expected result='TP' (priority over EOD), got {exit_info['result']}"
    assert exit_info['exit_price'] == 25150.0, f"Expected TP price, got {exit_info['exit_price']}"
    
    print("✓ Test 5 PASSED: TP ma priorytet nad EOD")


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    print("Uruchamiam testy close_at_eod...\n")
    
    test_close_at_eod_disabled()
    test_close_at_eod_enabled()
    test_close_at_eod_short_position()
    test_close_at_eod_not_triggered_before_eod()
    test_close_at_eod_tp_has_priority()
    
    print("\n" + "="*60)
    print("✓ Wszystkie testy close_at_eod PASSED (5/5)")
    print("="*60)
