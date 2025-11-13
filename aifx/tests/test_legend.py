"""Test sprawdzający czy opcja show_legend działa poprawnie"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from support_breakout_strategy import SupportBreakoutStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from PIL import Image
import shutil

def test_legend_off():
    """Test: show_legend=False nie rysuje legendy"""
    print("\n" + "="*80)
    print("TEST: Legenda wyłączona (show_legend=False)")
    print("="*80)
    
    # Utwórz strategię z show_legend=False
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        show_legend=False,
        min_slope=0.1
    )
    
    # Wygeneruj proste dane testowe (trend wzrostowy)
    dates = pd.date_range(start='2025-10-01', periods=96*6, freq='15min')  # 6 dni
    np.random.seed(42)
    
    prices = 25000 + np.arange(len(dates)) * 2 + np.random.randn(len(dates)) * 50
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': prices,
        'High': prices + np.abs(np.random.randn(len(dates)) * 20),
        'Low': prices - np.abs(np.random.randn(len(dates)) * 20),
        'Close': prices + np.random.randn(len(dates)) * 10,
        'Volume': np.random.randint(100, 1000, len(dates))
    })
    
    # Calculate indicators
    df = strategy.calculate_indicators(df)
    
    # Generuj wykres dla ostatniego dnia
    test_date = df['DateTime'].dt.date.max()
    output_dir = 'test_charts_legend'
    os.makedirs(output_dir, exist_ok=True)
    
    filename = strategy.plot_daily_chart(
        df, 
        test_date, 
        output_dir=output_dir,
        show_volume=False,
        mark_high_low=True  # Włącz markery aby sprawdzić czy ich etykiety też są ukryte
    )
    
    print(f"\n✓ Wykres utworzony: {filename}")
    print(f"✓ show_legend = {strategy.show_legend}")
    
    # Sprawdź czy plik istnieje
    if not os.path.exists(filename):
        print(f"\n✗✗✗ TEST FAILED ✗✗✗")
        print(f"Plik {filename} nie istnieje!")
        return False
    
    # Otwórz obrazek i sprawdź rozmiar (legenda zwiększa rozmiar pliku)
    img = Image.open(filename)
    width, height = img.size
    print(f"✓ Rozmiar obrazka: {width}x{height}")
    
    # Sprawdź czy axes mają legendę
    fig = plt.figure()
    test_ax = fig.add_subplot(111)
    test_ax.plot([1, 2, 3], [1, 2, 3], label='Test')
    
    # Symuluj warunek z kodu
    labels = strategy._last_legend_labels
    print(f"✓ Liczba etykiet w legendzie: {len(labels)}")
    
    if len(labels) == 0:
        print(f"\n✓✓✓ TEST PASSED ✓✓✓")
        print(f"Legenda NIE została narysowana (0 etykiet)")
        plt.close('all')
        return True
    else:
        print(f"\n✗✗✗ TEST FAILED ✗✗✗")
        print(f"Legenda została narysowana mimo show_legend=False!")
        print(f"Etykiety: {labels[:5]}...")  # Pokaż pierwsze 5
        plt.close('all')
        return False


def test_legend_on():
    """Test: show_legend=True rysuje legendę"""
    print("\n" + "="*80)
    print("TEST: Legenda włączona (show_legend=True)")
    print("="*80)
    
    # Utwórz strategię z show_legend=True
    strategy = SupportBreakoutStrategy(
        lookback_days=3,
        show_legend=True,
        min_slope=0.1
    )
    
    # Wygeneruj proste dane testowe (trend wzrostowy)
    dates = pd.date_range(start='2025-10-01', periods=96*6, freq='15min')  # 6 dni
    np.random.seed(42)
    
    prices = 25000 + np.arange(len(dates)) * 2 + np.random.randn(len(dates)) * 50
    
    df = pd.DataFrame({
        'DateTime': dates,
        'Open': prices,
        'High': prices + np.abs(np.random.randn(len(dates)) * 20),
        'Low': prices - np.abs(np.random.randn(len(dates)) * 20),
        'Close': prices + np.random.randn(len(dates)) * 10,
        'Volume': np.random.randint(100, 1000, len(dates))
    })
    
    # Calculate indicators
    df = strategy.calculate_indicators(df)
    
    # Generuj wykres dla ostatniego dnia
    test_date = df['DateTime'].dt.date.max()
    output_dir = 'test_charts_legend'
    
    filename = strategy.plot_daily_chart(
        df, 
        test_date, 
        output_dir=output_dir,
        show_volume=False,
        mark_high_low=True
    )
    
    print(f"\n✓ Wykres utworzony: {filename}")
    print(f"✓ show_legend = {strategy.show_legend}")
    
    # Sprawdź czy axes mają legendę
    labels = strategy._last_legend_labels
    print(f"✓ Liczba etykiet w legendzie: {len(labels)}")
    
    if len(labels) > 0:
        print(f"✓ Przykładowe etykiety: {labels[:3]}")
        print(f"\n✓✓✓ TEST PASSED ✓✓✓")
        print(f"Legenda została narysowana ({len(labels)} etykiet)")
        return True
    else:
        print(f"\n✗✗✗ TEST FAILED ✗✗✗")
        print(f"Legenda NIE została narysowana mimo show_legend=True!")
        return False


if __name__ == '__main__':
    # Konfiguruj UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    results = []
    
    # Test 1: show_legend=False
    results.append(test_legend_off())
    
    # Test 2: show_legend=True
    results.append(test_legend_on())
    
    # Podsumowanie
    print("\n" + "="*80)
    print("PODSUMOWANIE")
    print("="*80)
    
    passed = sum(results)
    total = len(results)
    print(f"✓ Testy zaliczone: {passed}/{total}")
    
    if passed == total:
        print("✅✅✅ WSZYSTKIE TESTY PASSED ✅✅✅")
    else:
        print("❌ Niektóre testy nie przeszły!")
    
    sys.exit(0 if passed == total else 1)
