"""
Testy jednostkowe dla SupportBreakoutStrategy z hierarchicznymi liniami.

Testuje:
1. Wykrywanie głównej linii wsparcia
2. Wykrywanie hierarchicznych linii równoległych (S2, S3, R2, R3)
3. Równoległość wszystkich linii (ten sam slope)
4. Znaki offsetów (wsparcia ujemne, opory dodatnie)
5. Generowanie wykresów z hierarchicznymi liniami

Author: AI FX Trading System
Version: 1.0
Date: 2025-11-12
"""

import sys
from pathlib import Path

# Dodaj katalog nadrzędny do sys.path aby importować moduły z aifx/
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import os
from datetime import datetime
from support_breakout_strategy import SupportBreakoutStrategy


def create_synthetic_data(num_candles=500, base_price=25000, trend_slope=2.0):
    """
    Tworzy syntetyczne dane OHLCV z trendem wzrostowym.
    
    Parametry:
    - num_candles: liczba świeczek
    - base_price: cena bazowa
    - trend_slope: nachylenie trendu (punkty na świeczkę)
    
    Zwraca DataFrame z kolumnami: DateTime, Open, High, Low, Close, Volume
    """
    dates = pd.date_range(start='2025-10-01', periods=num_candles, freq='15min')
    
    # Trend wzrostowy + szum
    trend = np.arange(num_candles) * trend_slope
    noise = np.random.normal(0, 50, num_candles)
    
    close_prices = base_price + trend + noise
    
    # OHLC
    open_prices = close_prices + np.random.normal(0, 10, num_candles)
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0, 15, num_candles))
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0, 15, num_candles))
    volume = np.random.randint(100, 1000, num_candles)
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volume
    })
    
    return df


def test_basic_support_detection():
    """Test 1: Podstawowe wykrywanie linii wsparcia"""
    print("\n" + "="*60)
    print("TEST 1: Podstawowe wykrywanie linii wsparcia")
    print("="*60)
    
    # Syntetyczne dane: 500 świeczek, trend wzrostowy
    df = create_synthetic_data(num_candles=500, base_price=25000, trend_slope=2.0)
    
    # Strategia z lookback 3 dni (288 świeczek M15)
    strategy = SupportBreakoutStrategy(lookback_days=3, min_slope=0.1)
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Weryfikacje
    assert len(strategy.daily_support_data) > 0, "Brak danych o liniach wsparcia"
    
    print(f"✓ Wykryto {len(strategy.daily_support_data)} dni z liniami wsparcia")
    
    # Sprawdź pierwszą linię
    first_entry = strategy.daily_support_data[0]
    assert 'slope' in first_entry, "Brak slope w danych"
    assert 'intercept' in first_entry, "Brak intercept w danych"
    
    print(f"✓ Pierwsza linia: slope={first_entry['slope']:.4f}, intercept={first_entry['intercept']:.2f}")
    
    # Sprawdź trend wzrostowy (slope > 0)
    positive_slopes = sum(1 for entry in strategy.daily_support_data if entry['slope'] > 0)
    print(f"✓ {positive_slopes}/{len(strategy.daily_support_data)} linii ma slope > 0 (trend wzrostowy)")
    
    print("\n✓✓✓ TEST 1 PASSED ✓✓✓\n")


def test_hierarchical_lines_detection():
    """Test 2: Wykrywanie hierarchicznych linii równoległych"""
    print("\n" + "="*60)
    print("TEST 2: Wykrywanie hierarchicznych linii równoległych")
    print("="*60)
    
    # Syntetyczne dane z wyraźnym trendem
    df = create_synthetic_data(num_candles=600, base_price=24000, trend_slope=3.0)
    
    strategy = SupportBreakoutStrategy(lookback_days=3, min_slope=0.5)
    df_calc = strategy.calculate_indicators(df)
    
    # Zlicz dni z hierarchicznymi liniami
    days_with_supports = 0
    days_with_resistances = 0
    total_support_lines = 0
    total_resistance_lines = 0
    
    for entry in strategy.daily_support_data:
        h_supp = entry.get('hierarchical_supports', [])
        h_res = entry.get('hierarchical_resistances', [])
        
        if h_supp:
            days_with_supports += 1
            total_support_lines += len(h_supp)
        
        if h_res:
            days_with_resistances += 1
            total_resistance_lines += len(h_res)
    
    print(f"✓ Dni z hierarchicznymi liniami wsparcia: {days_with_supports}/{len(strategy.daily_support_data)}")
    print(f"✓ Dni z hierarchicznymi liniami oporu: {days_with_resistances}/{len(strategy.daily_support_data)}")
    print(f"✓ Łącznie linii wsparcia: {total_support_lines}")
    print(f"✓ Łącznie linii oporu: {total_resistance_lines}")
    
    assert days_with_supports > 0 or days_with_resistances > 0, \
        "Brak hierarchicznych linii (ani wsparć ani oporów)"
    
    print("\n✓✓✓ TEST 2 PASSED ✓✓✓\n")


def test_parallel_lines():
    """Test 3: Równoległość hierarchicznych linii"""
    print("\n" + "="*60)
    print("TEST 3: Równoległość hierarchicznych linii")
    print("="*60)
    
    # Syntetyczne dane
    df = create_synthetic_data(num_candles=600, base_price=25000, trend_slope=2.5)
    
    strategy = SupportBreakoutStrategy(lookback_days=3, min_slope=0.3)
    df_calc = strategy.calculate_indicators(df)
    
    parallel_violations = 0
    checked_lines = 0
    
    for entry in strategy.daily_support_data:
        base_slope = entry['slope']
        
        # Sprawdź wsparcia
        for supp in entry.get('hierarchical_supports', []):
            checked_lines += 1
            slope_diff = abs(supp['slope'] - base_slope)
            
            if slope_diff > 0.001:  # Tolerancja 0.001
                parallel_violations += 1
                print(f"  ⚠️ {entry['date']}: S{supp['level']} ma slope={supp['slope']:.6f}, "
                      f"główna={base_slope:.6f}, diff={slope_diff:.6f}")
        
        # Sprawdź opory
        for res in entry.get('hierarchical_resistances', []):
            checked_lines += 1
            slope_diff = abs(res['slope'] - base_slope)
            
            if slope_diff > 0.001:
                parallel_violations += 1
                print(f"  ⚠️ {entry['date']}: R{res['level']} ma slope={res['slope']:.6f}, "
                      f"główna={base_slope:.6f}, diff={slope_diff:.6f}")
    
    print(f"✓ Sprawdzono {checked_lines} hierarchicznych linii")
    print(f"✓ Naruszeń równoległości: {parallel_violations}")
    
    assert parallel_violations == 0, f"Znaleziono {parallel_violations} linii nie-równoległych!"
    
    print("\n✓✓✓ TEST 3 PASSED ✓✓✓\n")


def test_offset_signs():
    """Test 4: Znaki offsetów (wsparcia ujemne, opory dodatnie)"""
    print("\n" + "="*60)
    print("TEST 4: Znaki offsetów hierarchicznych linii")
    print("="*60)
    
    df = create_synthetic_data(num_candles=600, base_price=25000, trend_slope=2.0)
    
    strategy = SupportBreakoutStrategy(lookback_days=3, min_slope=0.3)
    df_calc = strategy.calculate_indicators(df)
    
    wrong_sign_supports = 0
    wrong_sign_resistances = 0
    total_supports = 0
    total_resistances = 0
    
    for entry in strategy.daily_support_data:
        # Wsparcia: offset powinien być UJEMNY (poniżej głównej)
        for supp in entry.get('hierarchical_supports', []):
            total_supports += 1
            if supp['offset'] >= 0:
                wrong_sign_supports += 1
                print(f"  ⚠️ {entry['date']}: S{supp['level']} ma offset={supp['offset']} (powinien < 0)")
        
        # Opory: offset powinien być DODATNI (powyżej głównej)
        for res in entry.get('hierarchical_resistances', []):
            total_resistances += 1
            if res['offset'] <= 0:
                wrong_sign_resistances += 1
                print(f"  ⚠️ {entry['date']}: R{res['level']} ma offset={res['offset']} (powinien > 0)")
    
    print(f"✓ Sprawdzono {total_supports} linii wsparcia (offset < 0)")
    print(f"✓ Sprawdzono {total_resistances} linii oporu (offset > 0)")
    print(f"✓ Błędnych znaków wsparć: {wrong_sign_supports}")
    print(f"✓ Błędnych znaków oporów: {wrong_sign_resistances}")
    
    assert wrong_sign_supports == 0, f"Znaleziono {wrong_sign_supports} wsparć z błędnym znakiem!"
    assert wrong_sign_resistances == 0, f"Znaleziono {wrong_sign_resistances} oporów z błędnym znakiem!"
    
    print("\n✓✓✓ TEST 4 PASSED ✓✓✓\n")


def test_data_structure():
    """Test 5: Struktura danych hierarchicznych linii"""
    print("\n" + "="*60)
    print("TEST 5: Struktura danych hierarchicznych linii")
    print("="*60)
    
    df = create_synthetic_data(num_candles=400, base_price=25000, trend_slope=2.0)
    
    strategy = SupportBreakoutStrategy(lookback_days=3)
    df_calc = strategy.calculate_indicators(df)
    
    required_keys = {'slope', 'intercept', 'touches', 'offset', 'score', 'level'}
    
    for entry in strategy.daily_support_data:
        # Sprawdź wsparcia
        for supp in entry.get('hierarchical_supports', []):
            assert isinstance(supp, dict), "Linia wsparcia nie jest dict"
            
            missing_keys = required_keys - set(supp.keys())
            assert not missing_keys, f"Brak kluczy w linii wsparcia: {missing_keys}"
            
            assert isinstance(supp['level'], int), "level nie jest int"
            assert supp['level'] >= 2, "level powinien być >= 2"
            assert isinstance(supp['score'], int), "score nie jest int"
            assert supp['score'] >= 3, "score powinien być >= 3"
        
        # Sprawdź opory
        for res in entry.get('hierarchical_resistances', []):
            assert isinstance(res, dict), "Linia oporu nie jest dict"
            
            missing_keys = required_keys - set(res.keys())
            assert not missing_keys, f"Brak kluczy w linii oporu: {missing_keys}"
            
            assert isinstance(res['level'], int), "level nie jest int"
            assert res['level'] >= 2, "level powinien być >= 2"
            assert isinstance(res['score'], int), "score nie jest int"
            assert res['score'] >= 3, "score powinien być >= 3"
    
    print(f"✓ Wszystkie hierarchiczne linie mają poprawną strukturę")
    print(f"✓ Wymagane klucze: {required_keys}")
    print(f"✓ Poziomy (level) >= 2")
    print(f"✓ Score >= 3 punkty")
    
    print("\n✓✓✓ TEST 5 PASSED ✓✓✓\n")


def test_chart_generation():
    """Test 6: Generowanie wykresów z hierarchicznymi liniami"""
    print("\n" + "="*60)
    print("TEST 6: Generowanie wykresów")
    print("="*60)
    
    # Użyj rzeczywistych danych jeśli dostępne
    try:
        df = pd.read_csv('FUS100.15.csv', sep='\t')
        df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
        df = df.rename(columns={
            '<OPEN>': 'Open',
            '<HIGH>': 'High',
            '<LOW>': 'Low',
            '<CLOSE>': 'Close',
            '<TICKVOL>': 'Volume'
        })
        df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Weź tylko październik 2025
        df = df[df['DateTime'] >= '2025-10-01'].copy()
        df = df[df['DateTime'] <= '2025-10-05'].copy()
        
        print("✓ Użyto rzeczywistych danych (FUS100.15.csv, 2025-10-01 do 2025-10-05)")
    except:
        # Fallback: syntetyczne dane
        df = create_synthetic_data(num_candles=500, base_price=25000, trend_slope=2.0)
        print("✓ Użyto syntetycznych danych")
    
    strategy = SupportBreakoutStrategy(lookback_days=3, min_slope=0.3)
    df_calc = strategy.calculate_indicators(df)
    
    # Wygeneruj wykres dla pierwszego dnia z danymi
    if strategy.daily_support_data:
        test_date = strategy.daily_support_data[0]['date']
        
        output_dir = 'test_charts'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = strategy.plot_daily_chart(df, test_date, output_dir=output_dir, show_volume=False)
        
        assert filename is not None, "Wykres nie został wygenerowany"
        assert os.path.exists(filename), f"Plik wykresu nie istnieje: {filename}"
        
        print(f"✓ Wygenerowano wykres: {filename}")
        
        # Sprawdź czy dane zawierają hierarchiczne linie
        entry = strategy.daily_support_data[0]
        num_supports = len(entry.get('hierarchical_supports', []))
        num_resistances = len(entry.get('hierarchical_resistances', []))
        
        print(f"✓ Wykres zawiera {num_supports} linii wsparcia i {num_resistances} linii oporu")
        print(f"  (oprócz głównej linii S1)")
    
    print("\n✓✓✓ TEST 6 PASSED ✓✓✓\n")


def run_all_tests():
    """Uruchamia wszystkie testy"""
    print("\n" + "#"*60)
    print("# TESTY SUPPORT BREAKOUT STRATEGY - HIERARCHICZNE LINIE")
    print("#"*60)
    
    try:
        test_basic_support_detection()
        test_hierarchical_lines_detection()
        test_parallel_lines()
        test_offset_signs()
        test_data_structure()
        test_chart_generation()
        
        print("\n" + "#"*60)
        print("# ✓✓✓ WSZYSTKIE TESTY PASSED ✓✓✓")
        print("#"*60 + "\n")
        
        return True
    
    except AssertionError as e:
        print(f"\n✗✗✗ TEST FAILED: {e} ✗✗✗\n")
        return False
    except Exception as e:
        print(f"\n✗✗✗ ERROR: {e} ✗✗✗\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
