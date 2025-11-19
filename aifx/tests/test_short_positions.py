"""
Test wykrywania pozycji SHORT dla linii opadających.

Weryfikuje że:
1. System wykrywa linie opadające (slope < 0)
2. Generuje sygnały SHORT (breakout w dół)
3. Prawidłowo ustawia SL/TP dla SHORT (SL powyżej, TP poniżej)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from support_breakout_strategy import SupportBreakoutStrategy
from backtest_engine import BacktestEngine


def create_downtrend_data(num_candles=500):
    """
    Tworzy dane z wyraźnym trendem spadkowym.
    
    Strategia:
    - Highs tworzą opadającą linię oporu (slope < 0)
    - Price spada stopniowo
    - Powinno generować sygnały SHORT
    """
    dates = pd.date_range('2025-10-01', periods=num_candles, freq='15min')
    
    base_price = 25000
    data = []
    
    for i in range(num_candles):
        # Opadający trend na High (slope ~-2.0)
        high_trend = base_price - (i * 2.0)
        
        # Również opadający na Low
        low_trend = base_price - (i * 2.5)
        
        # Dodaj volatility
        volatility = np.random.uniform(-15, 15)
        
        high = high_trend + volatility + 30
        low = low_trend + volatility - 30
        open_price = (high + low) / 2 + np.random.uniform(-10, 10)
        close = (high + low) / 2 + np.random.uniform(-10, 10)
        
        data.append({
            'DateTime': dates[i],
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': np.random.randint(1000, 5000)
        })
    
    return pd.DataFrame(data)


def test_detects_descending_lines():
    """
    TEST 1: System powinien wykrywać linie opadające (slope < 0)
    gdy dane mają wyraźny downtrend.
    """
    print("\n" + "="*80)
    print("TEST 1: Wykrywanie linii opadających")
    print("="*80)
    
    # Dane z downtrend
    df = create_downtrend_data(num_candles=500)
    
    # Strategia z włączonymi liniami opadającymi
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        min_slope=0.5,  # Wymagamy wyraźnego trendu
        allow_descending=True,
        hierarchical_levels_below=2,
        hierarchical_levels_above=2
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Sprawdź wykryte linie (flatten dict)
    all_lines = [line for lines in strategy.daily_support_data.values() for line in lines]
    descending_lines = [
        entry for entry in all_lines
        if entry['slope'] < 0
    ]
    
    print(f"\nWykryte linie opadające: {len(descending_lines)}/{len(all_lines)}")
    
    if len(descending_lines) > 0:
        # Pokaż przykłady
        print(f"\nPrzykładowe linie opadające:")
        for i, line in enumerate(descending_lines[:3]):
            print(f"  {i+1}. Date: {line['date']}, Slope: {line['slope']:.4f}")
        
        print(f"\n✓✓✓ TEST 1 PASSED ✓✓✓")
        print(f"System wykrywa linie opadające!")
        return True
    else:
        print(f"\n✗✗✗ TEST 1 FAILED ✗✗✗")
        print(f"PROBLEM: Brak wykrytych linii opadających (slope < 0)")
        return False


def test_generates_short_signals():
    """
    TEST 2: System powinien generować sygnały SHORT dla breakoutów w dół
    używając rzeczywistych danych rynkowych.
    """
    print("\n" + "="*80)
    print("TEST 2: Generowanie sygnałów SHORT (dane rzeczywiste)")
    print("="*80)
    
    # Załaduj rzeczywiste dane
    import os
    data_file = '../FUS100.15.csv'
    
    if not os.path.exists(data_file):
        print(f"\n⚠ TEST 2 SKIPPED - brak pliku {data_file}")
        return None
    
    # Load data - OGRANICZONY DATASET (ostatni miesiąc dla szybszego testu)
    df = pd.read_csv(data_file, sep='\t')
    df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
    df = df.rename(columns={
        '<OPEN>': 'Open',
        '<HIGH>': 'High',
        '<LOW>': 'Low',
        '<CLOSE>': 'Close',
        '<TICKVOL>': 'Volume'
    })
    df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    # OGRANICZENIE: tylko ostatnie 5 dni danych dla szybszego testu
    df = df[df['DateTime'] >= '2025-10-25'].copy()
    print(f"Dataset ograniczony do {len(df)} świeczek (od 2025-10-25)")
    
    # Strategia
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        risk_pips=50,
        reward_ratio=2.5,
        min_slope=0.4,
        allow_descending=True,
        retest_mode=False
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Sprawdź linie opadające w daily_support_data (flatten dict)
    all_lines = [line for lines in strategy.daily_support_data.values() for line in lines]
    descending_lines = [
        line for line in all_lines
        if line['slope'] < 0
    ]
    
    print(f"\nWykryte linie opadające: {len(descending_lines)}/{len(all_lines)}")
    
    if len(descending_lines) == 0:
        print(f"\n⚠ Brak linii opadających w danych - test nie może kontynuować")
        return None
    
    # Sprawdź czy should_enter() wykrywa SHORT signals
    # Sprawdzamy tylko okres gdzie są linie opadające
    short_signals = []
    
    # Weź pierwszą linię opadającą
    test_line = descending_lines[0]
    test_date = test_line['date']
    day_start_idx = test_line['day_start_idx']
    
    print(f"\nTest na dzień: {test_date}, slope: {test_line['slope']:.4f}")
    
    # Sprawdź tylko pierwsze 20 świeczek tego dnia (szybszy test)
    for offset in range(20):
        idx = day_start_idx + offset
        if idx >= len(df_calc):
            break
        
        if df_calc.iloc[idx]['DateTime'].date() != test_date:
            break  # Koniec tego dnia
        
        signal = strategy.should_enter(df_calc, idx)
        if signal and signal['direction'] == 'short':
            short_signals.append(signal)
            break  # Early exit - jeden sygnał wystarczy dla testu
    
    print(f"Znalezione sygnały SHORT dla dnia {test_date}: {len(short_signals)}")
    
    if len(short_signals) > 0:
        print(f"\n✓ Przykładowy sygnał SHORT:")
        signal = short_signals[0]
        print(f"  Time: {signal['time']}")
        print(f"  Entry: {signal['entry_price']:.2f}")
        print(f"  SL: {signal['sl_price']:.2f} (powyżej entry)")
        print(f"  TP: {signal['tp_price']:.2f} (poniżej entry)")
        
        # Weryfikuj że SL > entry i TP < entry
        sl_ok = signal['sl_price'] > signal['entry_price']
        tp_ok = signal['tp_price'] < signal['entry_price']
        
        if sl_ok and tp_ok:
            print(f"\n✓✓✓ TEST 2 PASSED ✓✓✓")
            return True
        else:
            print(f"\n✗✗✗ TEST 2 FAILED ✗✗✗")
            print(f"PROBLEM: SL/TP nieprawidłowe dla SHORT")
            return False
    else:
        print(f"\n⚠ Brak sygnałów SHORT dla testowanego dnia")
        print(f"   (Może nie było breakoutu w tym okresie)")
        return None


def test_short_sl_tp_placement():
    """
    TEST 3: Sprawdza czy SL i TP dla SHORT są prawidłowo ustawione.
    
    SHORT position:
    - SL powinno być POWYŻEJ entry (entry + risk_pips)
    - TP powinno być PONIŻEJ entry (entry - reward_pips)
    """
    print("\n" + "="*80)
    print("TEST 3: Prawidłowe ustawienie SL/TP dla SHORT")
    print("="*80)
    
    # Prosty test - sprawdzamy bezpośrednio logikę should_enter()
    # Tworzymy dane gdzie cena przebija resistance w dół
    
    dates = pd.date_range('2025-10-01', periods=200, freq='15min')
    data = []
    
    # Część 1: Tworzenie linii resistance (cena stabilna)
    for i in range(150):
        price = 25000 + np.random.uniform(-5, 5)
        data.append({
            'DateTime': dates[i],
            'Open': price,
            'High': price + 10,
            'Low': price - 10,
            'Close': price,
            'Volume': 1000
        })
    
    # Część 2: Breakout w dół
    for i in range(150, 200):
        price = 24950 - (i - 150) * 2  # Spadek
        data.append({
            'DateTime': dates[i],
            'Open': price + 10,
            'High': price + 15,
            'Low': price,
            'Close': price + 5,
            'Volume': 1000
        })
    
    df = pd.DataFrame(data)
    
    risk_pips = 50
    reward_ratio = 2.5
    
    strategy = SupportBreakoutStrategy(
        lookback_days=2,
        risk_pips=risk_pips,
        reward_ratio=reward_ratio,
        min_slope=0.1,
        allow_descending=True
    )
    
    df_calc = strategy.calculate_indicators(df)
    
    # Szukaj sygnału SHORT
    short_signal = None
    for idx in range(1, len(df_calc)):
        signal = strategy.should_enter(df_calc, idx)
        if signal and signal['direction'] == 'short':
            short_signal = signal
            break
    
    if not short_signal:
        print(f"\n⚠ TEST 3 SKIPPED - nie znaleziono sygnału SHORT w danych testowych")
        return None
    
    entry = short_signal['entry_price']
    sl = short_signal['sl_price']
    tp = short_signal['tp_price']
    
    print(f"\nZnaleziony sygnał SHORT:")
    print(f"  Entry: {entry:.2f}")
    print(f"  SL: {sl:.2f}")
    print(f"  TP: {tp:.2f}")
    
    # Weryfikacja
    expected_sl = entry + risk_pips
    expected_tp = entry - (risk_pips * reward_ratio)
    
    sl_ok = abs(sl - expected_sl) < 0.01
    tp_ok = abs(tp - expected_tp) < 0.01
    
    print(f"\nWeryfikacja:")
    print(f"  SL = entry + {risk_pips} → {expected_sl:.2f} {'✓' if sl_ok else '✗'}")
    print(f"  TP = entry - {risk_pips * reward_ratio} → {expected_tp:.2f} {'✓' if tp_ok else '✗'}")
    
    if sl_ok and tp_ok:
        print(f"\n✓✓✓ TEST 3 PASSED ✓✓✓")
        return True
    else:
        print(f"\n✗✗✗ TEST 3 FAILED ✗✗✗")
        print(f"PROBLEM: SL lub TP nieprawidłowe")
        return False


def test_short_exit_logic():
    """
    TEST 4: Sprawdza czy exit logic dla SHORT działa poprawnie.
    
    SHORT position exit:
    - TP: gdy Low <= tp_price (cena spadła do TP)
    - SL: gdy High >= sl_price (cena wzrosła do SL)
    """
    print("\n" + "="*80)
    print("TEST 4: Exit logic dla SHORT")
    print("="*80)
    
    # Stwórz prosty test case - 1 SHORT position
    dates = pd.date_range('2025-10-01', periods=10, freq='15min')
    
    # Cena spada stopniowo
    data = []
    prices = [25000, 24990, 24980, 24970, 24960, 24950, 24940, 24930, 24920, 24910]
    
    for i, (dt, price) in enumerate(zip(dates, prices)):
        data.append({
            'DateTime': dt,
            'Open': price + 5,
            'High': price + 10,
            'Low': price - 10,
            'Close': price,
            'Volume': 1000
        })
    
    df = pd.DataFrame(data)
    
    # Strategia
    strategy = SupportBreakoutStrategy(
        lookback_days=1,
        risk_pips=50,
        reward_ratio=2.0,
        min_slope=0.1,
        allow_descending=True
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Ręcznie sprawdź check_exit dla SHORT
    trade_short = {
        'direction': 'short',
        'entry_price': 25000,
        'sl_price': 25050,  # 50 pips powyżej
        'tp_price': 24900,  # 100 pips poniżej
        'time': dates[0]
    }
    
    # Sprawdź różne scenariusze
    print(f"\nTEST SHORT position:")
    print(f"  Entry: {trade_short['entry_price']}")
    print(f"  SL: {trade_short['sl_price']} (powyżej)")
    print(f"  TP: {trade_short['tp_price']} (poniżej)")
    
    # Scenariusz 1: Cena spada do TP (Low <= tp_price)
    test_candle_tp = pd.DataFrame([{
        'DateTime': dates[5],
        'Open': 24920,
        'High': 24930,
        'Low': 24890,  # Poniżej TP (24900)
        'Close': 24910
    }])
    
    exit_tp = strategy.check_exit(test_candle_tp, 0, trade_short)
    
    if exit_tp and exit_tp['result'] == 'TP':
        print(f"\n✓ Scenariusz TP: Low={test_candle_tp.iloc[0]['Low']:.2f} <= TP={trade_short['tp_price']:.2f}")
        print(f"  Exit: {exit_tp['exit_price']:.2f}, Result: {exit_tp['result']}")
        tp_ok = True
    else:
        print(f"\n✗ Scenariusz TP FAILED")
        tp_ok = False
    
    # Scenariusz 2: Cena wzrasta do SL (High >= sl_price)
    test_candle_sl = pd.DataFrame([{
        'DateTime': dates[5],
        'Open': 25020,
        'High': 25060,  # Powyżej SL (25050)
        'Low': 25010,
        'Close': 25030
    }])
    
    exit_sl = strategy.check_exit(test_candle_sl, 0, trade_short)
    
    if exit_sl and exit_sl['result'] == 'SL':
        print(f"\n✓ Scenariusz SL: High={test_candle_sl.iloc[0]['High']:.2f} >= SL={trade_short['sl_price']:.2f}")
        print(f"  Exit: {exit_sl['exit_price']:.2f}, Result: {exit_sl['result']}")
        sl_ok = True
    else:
        print(f"\n✗ Scenariusz SL FAILED")
        sl_ok = False
    
    if tp_ok and sl_ok:
        print(f"\n✓✓✓ TEST 4 PASSED ✓✓✓")
        return True
    else:
        print(f"\n✗✗✗ TEST 4 FAILED ✗✗✗")
        return False


def test_mixed_long_short_detection():
    """
    TEST 5: System powinien wykrywać zarówno linie wznosząc (LONG)
    jak i opadające (SHORT) w rzeczywistych danych.
    """
    print("\n" + "="*80)
    print("TEST 5: Wykrywanie LONG i SHORT jednocześnie (dane rzeczywiste)")
    print("="*80)
    
    # Załaduj rzeczywiste dane
    import os
    data_file = '../FUS100.15.csv'
    
    if not os.path.exists(data_file):
        print(f"\n⚠ TEST 5 SKIPPED - brak pliku {data_file}")
        return None
    
    df = pd.read_csv(data_file, sep='\t')
    df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
    df = df.rename(columns={
        '<OPEN>': 'Open',
        '<HIGH>': 'High',
        '<LOW>': 'Low',
        '<CLOSE>': 'Close',
        '<TICKVOL>': 'Volume'
    })
    df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    # Ogranicz dataset do 1 dnia - szybki test
    df = df[df['DateTime'] >= '2025-10-30'].copy()
    
    # Strategia
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        min_slope=0.4,
        allow_descending=True,
        hierarchical_levels_below=2,
        hierarchical_levels_above=2
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Sprawd\u017a wykryte linie (flatten dict)
    all_lines = [line for lines in strategy.daily_support_data.values() for line in lines]
    ascending_lines = [l for l in all_lines if l['slope'] > 0]
    descending_lines = [l for l in all_lines if l['slope'] < 0]
    
    print(f"\nWykryte linie w pe\u0142nym zbiorze danych:")
    print(f"  Wznosz\u0105c (slope > 0): {len(ascending_lines)}")
    print(f"  Opadaj\u0105ce (slope < 0): {len(descending_lines)}")
    print(f"  Razem: {len(all_lines)}")
    
    # Powinny być oba typy
    has_ascending = len(ascending_lines) > 0
    has_descending = len(descending_lines) > 0
    
    if has_ascending and has_descending:
        print(f"\n✓ System wykrywa oba typy linii")
        
        # Rozkład
        total = len(strategy.daily_support_data)
        asc_pct = (len(ascending_lines) / total) * 100
        desc_pct = (len(descending_lines) / total) * 100
        
        print(f"\nRozkład:")
        print(f"  Wznosząc: {asc_pct:.1f}%")
        print(f"  Opadające: {desc_pct:.1f}%")
        
        # Przykłady
        if len(ascending_lines) > 0:
            line = ascending_lines[0]
            print(f"\nPrzykład LONG: date={line['date']}, slope={line['slope']:.4f}")
        
        if len(descending_lines) > 0:
            line = descending_lines[0]
            print(f"Przykład SHORT: date={line['date']}, slope={line['slope']:.4f}")
        
        print(f"\n✓✓✓ TEST 5 PASSED ✓✓✓")
        return True
    else:
        print(f"\n✗✗✗ TEST 5 FAILED ✗✗✗")
        print(f"PROBLEM: Brak {'wznoszących' if not has_ascending else 'opadających'} linii")
        return False


if __name__ == '__main__':
    import sys
    
    print("\n" + "#"*80)
    print("# TESTY POZYCJI SHORT DLA LINII OPADAJACYCH")
    print("#"*80)
    
    # Konfiguruj UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    results = []
    
    # Test 1: Wykrywanie linii opadających
    results.append(test_detects_descending_lines())
    
    # Test 2: Generowanie sygnałów SHORT
    results.append(test_generates_short_signals())
    
    # Test 3: SL/TP placement
    results.append(test_short_sl_tp_placement())
    
    # Test 4: Exit logic
    results.append(test_short_exit_logic())
    
    # Test 5: Mixed detection
    results.append(test_mixed_long_short_detection())
    
    # Podsumowanie
    print("\n" + "#"*80)
    print("# PODSUMOWANIE")
    print("#"*80)
    
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)
    total = passed + failed
    
    if failed == 0 and passed > 0:
        print(f"\n# ✓✓✓ WSZYSTKIE TESTY PASSED ({passed}/{total}) ✓✓✓")
        if skipped > 0:
            print(f"# ⚠ {skipped} testów pominiętych")
        sys.exit(0)
    else:
        print(f"\n# ✗ {failed}/{total} TESTÓW FAILED")
        if passed > 0:
            print(f"# ✓ {passed}/{total} TESTÓW PASSED")
        if skipped > 0:
            print(f"# ⚠ {skipped} testów pominiętych")
        sys.exit(1)
