"""
Test wykrywania linii wznoszących I opadających jednocześnie.

Problem: System powinien wykrywać OBIE linie (wznosząca i opadająca) dla tego samego
okresu danych, ale obecnie wykrywa tylko jedną najlepszą linię.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from support_breakout_strategy import SupportBreakoutStrategy


def create_mixed_trend_data(num_candles=500):
    """
    Tworzy dane z jednoczesnym trendem wzrostowym I spadkowym.
    
    Strategia:
    - Główny trend wzrostowy (Higher Highs)
    - Jednocześnie trend spadkowy na Lows (Lower Lows)
    - To tworzy expanding range gdzie obie linie powinny być wykryte
    """
    dates = pd.date_range('2025-10-01', periods=num_candles, freq='15min')
    
    base_price = 25000
    data = []
    
    for i in range(num_candles):
        # Wzrostowy trend na High (slope ~+2.0)
        high_trend = base_price + (i * 2.0)
        
        # Spadkowy trend na Low (slope ~-1.5)
        low_trend = base_price - (i * 1.5)
        
        # Dodaj losową volatility
        volatility = np.random.uniform(-20, 20)
        
        high = high_trend + volatility + 50
        low = low_trend + volatility - 50
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


def test_detects_both_ascending_and_descending():
    """
    TEST 1: System powinien wykrywać OBIE linie (wznosząca i opadająca) 
    gdy dane mają expanding range.
    """
    print("\n" + "="*80)
    print("TEST 1: Wykrywanie linii wznoszących I opadających jednocześnie")
    print("="*80)
    
    # Dane z expanding range
    df = create_mixed_trend_data(num_candles=500)
    
    # Strategia z włączonymi obiema kierunkami
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        min_slope=0.3,
        allow_descending=True,
        hierarchical_levels_below=2,
        hierarchical_levels_above=2
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Sprawd\u017a wykryte linie (flatten dict)
    all_lines = [line for lines in strategy.daily_support_data.values() for line in lines]
    ascending_count = 0
    descending_count = 0
    
    for entry in all_lines:
        slope = entry['slope']
        if slope > 0:
            ascending_count += 1
        elif slope < 0:
            descending_count += 1
    
    print(f"\nWykryte linie:")
    print(f"  Wznosz\u0105c (slope > 0): {ascending_count}")
    print(f"  Opadaj\u0105ce (slope < 0): {descending_count}")
    print(f"  Razem: {len(all_lines)}")
    
    # PROBLEM: System wykrywa tylko jedną linię na dzień!
    # Powinien wykrywać OBIE (wznosząca dla resistance, opadająca dla support)
    
    if ascending_count > 0 and descending_count > 0:
        print(f"\n✓✓✓ TEST 1 PASSED ✓✓✓")
        print(f"System wykrywa oba kierunki linii!")
        return True
    else:
        print(f"\n✗✗✗ TEST 1 FAILED ✗✗✗")
        print(f"PROBLEM: System wykrywa tylko {ascending_count} wznoszących i {descending_count} opadających")
        print(f"OCZEKIWANE: System powinien wykrywać OBIE linie jednocześnie dla expanding range")
        return False


def test_chart_contains_both_lines():
    """
    TEST 2: Wygenerowany wykres powinien zawierać OBIE główne linie
    (czerwona wznosząca + zielona opadająca).
    """
    print("\n" + "="*80)
    print("TEST 2: Wykres zawiera obie linie (wznosząca + opadająca)")
    print("="*80)
    
    # Dane z expanding range
    df = create_mixed_trend_data(num_candles=500)
    
    # Strategia z włączonymi obiema kierunkami
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        min_slope=0.3,
        allow_descending=True,
        hierarchical_levels_below=2,
        hierarchical_levels_above=2
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Znajdź pierwszy dzień z wykrytymi liniami
    if len(strategy.daily_support_data) == 0:
        print("\n✗✗✗ TEST 2 FAILED ✗✗✗")
        print("PROBLEM: Brak wykrytych linii")
        return False
    
    # Znajdź dzień który ma obie linie (ascending i descending)
    test_date = None
    for date, lines_for_date in strategy.daily_support_data.items():
        has_ascending = any(e['slope'] > 0 for e in lines_for_date)
        has_descending = any(e['slope'] < 0 for e in lines_for_date)
        
        if has_ascending and has_descending:
            test_date = date
            break
    
    if test_date is None:
        print("\n✗✗✗ TEST 2 FAILED ✗✗✗")
        print("PROBLEM: Brak dnia z obiema liniami")
        return False
    
    print(f"\nGeneruję wykres dla {test_date}...")
    
    # Wygeneruj wykres
    import os
    output_dir = 'test_charts_mixed'
    os.makedirs(output_dir, exist_ok=True)
    
    strategy.plot_daily_chart(
        df=df_calc,
        date=test_date,
        output_dir=output_dir,
        mark_high_low=True
    )
    
    # Sprawdź czy wykres został utworzony
    chart_path = f'{output_dir}/support_{test_date}.png'
    if not os.path.exists(chart_path):
        print(f"\n✗✗✗ TEST 2 FAILED ✗✗✗")
        print(f"PROBLEM: Wykres nie został utworzony: {chart_path}")
        return False
    
    print(f"\n\u2713 Wykres utworzony: {chart_path}")
    
    # Sprawd\u017a linie dla tego dnia (z dict)
    lines_for_date = strategy.daily_support_data.get(test_date, [])
    ascending_lines = [e for e in lines_for_date if e['slope'] > 0]
    descending_lines = [e for e in lines_for_date if e['slope'] < 0]
    
    print(f"\nLinie na wykresie:")
    print(f"  Wznosząc (czerwone): {len(ascending_lines)}")
    print(f"  Opadające (zielone): {len(descending_lines)}")
    
    for i, line in enumerate(ascending_lines):
        print(f"    Ascending {i+1}: slope={line['slope']:.4f}, {len(line.get('hierarchical_supports', []))} S, {len(line.get('hierarchical_resistances', []))} R")
    
    for i, line in enumerate(descending_lines):
        print(f"    Descending {i+1}: slope={line['slope']:.4f}, {len(line.get('hierarchical_supports', []))} S, {len(line.get('hierarchical_resistances', []))} R")
    
    if len(ascending_lines) > 0 and len(descending_lines) > 0:
        print(f"\n✓✓✓ TEST 2 PASSED ✓✓✓")
        print(f"Wykres zawiera obie linie!")
        return True
    else:
        print(f"\n✗✗✗ TEST 2 FAILED ✗✗✗")
        print(f"PROBLEM: Wykres powinien mieć obie linie")
        return False


def test_opposite_slopes():
    """
    TEST 3: Sprawdza czy linie wznosząca i opadająca dla tego samego dnia
    mają ten sam |slope| ale przeciwny znak.
    
    W expanding range:
    - Linia wznosząca (Higher Highs): slope > 0
    - Linia opadająca (Lower Lows): slope < 0
    - Powinny mieć zbliżony |slope| (ten sam trend, różny kierunek)
    """
    print("\n" + "="*80)
    print("TEST 3: Przeciwne znaki slope dla linii tego samego dnia")
    print("="*80)
    
    # Dane z expanding range o SYMETRYCZNYM trendzie
    dates = pd.date_range('2025-10-01', periods=500, freq='15min')
    base_price = 25000
    data = []
    
    trend_slope = 1.5  # Ten sam slope dla obu kierunków
    
    for i in range(len(dates)):
        # Symetryczny expanding range
        high_trend = base_price + (i * trend_slope)
        low_trend = base_price - (i * trend_slope)
        
        volatility = np.random.uniform(-10, 10)
        
        high = high_trend + volatility + 30
        low = low_trend + volatility - 30
        open_price = (high + low) / 2 + np.random.uniform(-5, 5)
        close = (high + low) / 2 + np.random.uniform(-5, 5)
        
        data.append({
            'DateTime': dates[i],
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': np.random.randint(1000, 5000)
        })
    
    df = pd.DataFrame(data)
    
    # Strategia
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        min_slope=0.3,
        allow_descending=True,
        hierarchical_levels_below=2,
        hierarchical_levels_above=2
    )
    
    # Oblicz wskaźniki
    df_calc = strategy.calculate_indicators(df)
    
    # Znajdź dni które mają OBE linie
    dates_with_both = {}
    
    # Iteruj po wszystkich liniach (flatten dict)
    for date, lines_for_date in strategy.daily_support_data.items():
        for entry in lines_for_date:
            slope = entry['slope']
            
            if date not in dates_with_both:
                dates_with_both[date] = {'ascending': None, 'descending': None}
            
            if slope > 0:
                dates_with_both[date]['ascending'] = slope
            elif slope < 0:
                dates_with_both[date]['descending'] = slope
    
    # Filtruj tylko dni z obiema liniami
    complete_days = {
        date: slopes for date, slopes in dates_with_both.items()
        if slopes['ascending'] is not None and slopes['descending'] is not None
    }
    
    print(f"\nDni z obiema liniami: {len(complete_days)}/{len(dates_with_both)}")
    
    if len(complete_days) == 0:
        print(f"\n✗✗✗ TEST 3 FAILED ✗✗✗")
        print(f"PROBLEM: Brak dni z obiema liniami!")
        return False
    
    # Sprawdź różnice w |slope|
    slope_comparisons = []
    
    for date, slopes in list(complete_days.items())[:10]:  # Pokaż max 10 przykładów
        asc_slope = slopes['ascending']
        desc_slope = slopes['descending']
        
        # Oblicz stosunek |slopes|
        ratio = abs(asc_slope) / abs(desc_slope) if desc_slope != 0 else 0
        diff_pct = abs(1.0 - ratio) * 100
        
        slope_comparisons.append({
            'date': date,
            'ascending': asc_slope,
            'descending': desc_slope,
            'ratio': ratio,
            'diff_pct': diff_pct
        })
    
    # Wyświetl przykłady
    print(f"\nPrzykładowe porównania slope:")
    print(f"{'Data':<12} {'Ascending':>10} {'Descending':>11} {'|Ratio|':>8} {'Diff%':>7}")
    print("-" * 60)
    
    for comp in slope_comparisons[:5]:
        print(f"{comp['date']} {comp['ascending']:>10.4f} {comp['descending']:>11.4f} "
              f"{comp['ratio']:>8.3f} {comp['diff_pct']:>6.1f}%")
    
    # Analiza statystyczna
    all_ratios = [comp['ratio'] for comp in slope_comparisons]
    all_diffs = [comp['diff_pct'] for comp in slope_comparisons]
    
    avg_ratio = np.mean(all_ratios)
    avg_diff = np.mean(all_diffs)
    max_diff = max(all_diffs)
    
    print(f"\nStatystyki (n={len(slope_comparisons)}):")
    print(f"  Średni stosunek |slope|: {avg_ratio:.3f}")
    print(f"  Średnia różnica: {avg_diff:.1f}%")
    print(f"  Maksymalna różnica: {max_diff:.1f}%")
    
    # Weryfikacja - czy slopes są PRZECIWNE (różne znaki)
    opposite_signs = 0
    exact_same_slope = 0
    tolerance = 0.01  # 1% tolerancja dla błędów numerycznych
    
    for comp in slope_comparisons:
        # Sprawdź przeciwne znaki
        if comp['ascending'] > 0 and comp['descending'] < 0:
            opposite_signs += 1
        
        # Sprawdź czy DOKŁADNIE ten sam |slope| (z małą tolerancją na błędy numeryczne)
        if abs(comp['ratio'] - 1.0) <= tolerance:
            exact_same_slope += 1
    
    print(f"\nWeryfikacja:")
    print(f"  Przeciwne znaki: {opposite_signs}/{len(slope_comparisons)} "
          f"({'✓' if opposite_signs == len(slope_comparisons) else '✗'})")
    print(f"  Dokładnie ten sam |slope| (±{tolerance*100}%): {exact_same_slope}/{len(slope_comparisons)} "
          f"({exact_same_slope/len(slope_comparisons)*100:.0f}%)")
    
    # Test PASSED jeśli:
    # 1. Wszystkie mają przeciwne znaki
    # 2. WSZYSTKIE mają dokładnie ten sam |slope| (±1% tolerancja)
    
    if opposite_signs == len(slope_comparisons) and exact_same_slope == len(slope_comparisons):
        print(f"\n✓✓✓ TEST 3 PASSED ✓✓✓")
        print(f"Linie mają przeciwne znaki i DOKŁADNIE ten sam |slope|!")
        return True
    else:
        print(f"\n✗✗✗ TEST 3 FAILED ✗✗✗")
        if opposite_signs != len(slope_comparisons):
            print(f"PROBLEM: Nie wszystkie linie mają przeciwne znaki")
        if exact_same_slope != len(slope_comparisons):
            print(f"PROBLEM: Linie NIE mają dokładnie tego samego |slope|")
            print(f"  Tylko {exact_same_slope}/{len(slope_comparisons)} linii ma identyczny |slope|")
        return False


if __name__ == '__main__':
    import sys
    
    # Konfiguruj UTF-8 NAJPIERW
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    print("\n" + "#"*80)
    print("# TESTY WYKRYWANIA LINII WZNOSZĄCYCH I OPADAJĄCYCH JEDNOCZEŚNIE")
    print("#"*80)
    
    results = []
    
    # Test 1
    results.append(test_detects_both_ascending_and_descending())
    
    # Test 2
    results.append(test_chart_contains_both_lines())
    
    # Test 3
    results.append(test_opposite_slopes())
    
    # Podsumowanie
    print("\n" + "#"*80)
    print("# PODSUMOWANIE")
    print("#"*80)
    
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)
    
    if failed == 0 and passed > 0:
        print(f"\n# ✓✓✓ WSZYSTKIE TESTY PASSED ({passed}/{passed+failed}) ✓✓✓")
        sys.exit(0)
    else:
        print(f"\n# ✗ {failed}/{passed+failed} TESTÓW FAILED")
        if skipped > 0:
            print(f"# ⚠ {skipped} testów pominiętych")
        sys.exit(1)
