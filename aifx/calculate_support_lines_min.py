"""
Minimalny skrypt do obliczania linii support i sprawdzania przecięć ostatniej świeczki.
Użycie: python calculate_support_lines_min.py <plik_csv>
Wyjście: NONE lub ID przeciętej linii (LONG/SHORT S1/S2/.../R1/R2)
"""

import sys
import pandas as pd
from run_support_backtest import load_data
from support_breakout_strategy import SupportBreakoutStrategy
from datetime import date

if len(sys.argv) < 2:
    print("Użycie: python calculate_support_lines_min.py <plik_csv>")
    print("Przykład: python calculate_support_lines_min.py FUS100.15_single.csv")
    sys.exit(1)

data_file = sys.argv[1]

# Wczytaj dane
df = load_data(data_file, data_format='mbank')

lookback_candles = 300

# Utwórz strategię w trybie candles
strategy = SupportBreakoutStrategy(
    lookback_mode='candles',
    lookback_candles=lookback_candles,
    risk_pips=50,
    reward_ratio=3,
    min_slope=0.1,
    allow_descending=True,
    hierarchical_levels_below=4,
    hierarchical_levels_above=4,
    hierarchical_tolerance=50,
    show_legend=False
)

# Oblicz wskaźniki (wykrywa linie support)
df_calc = strategy.calculate_indicators(df)

# Wygeneruj wykres
if strategy.daily_support_data:
    last_date = sorted(strategy.daily_support_data.keys())[-1]
    
    # Pobierz godzinę i minutę ostatniej świeczki
    last_candle_dt = df.iloc[-1]['DateTime']
    hour_min = last_candle_dt.strftime('%H-%M')
    
    # Wygeneruj wykres
    filename = strategy.plot_daily_chart(
        df,
        last_date,
        output_dir='support_charts',
        show_volume=False,
        mark_high_low=True
    )
    
    # Zmień nazwę pliku aby zawierała godzinę i minutę
    if filename:
        import os
        from pathlib import Path
        
        path_obj = Path(filename)
        # Nowa nazwa: support_2025-10-29_18-00.png
        new_filename = path_obj.parent / f"{path_obj.stem}_{hour_min}{path_obj.suffix}"
        os.rename(filename, new_filename)

# Sprawdź przecięcia ostatniej świeczki
if not strategy.daily_support_data:
    print("NONE")
    sys.exit(0)

last_candle = df.iloc[-1]
last_candle_idx = len(df) - 1
last_candle_low = last_candle['Low']
last_candle_high = last_candle['High']

crossed_lines = []

# Sprawdź wszystkie linie
for date_key, lines_list in sorted(strategy.daily_support_data.items()):
    for idx, line_info in enumerate(lines_list, 1):
        slope = line_info['slope']
        intercept = line_info['intercept']
        line_type = line_info['type']
        
        # Oblicz wartość linii głównej dla ostatniej świeczki
        line_value = slope * last_candle_idx + intercept
        
        # Typ linii (LONG/SHORT)
        line_prefix = "LONG" if line_type == 'ascending' else "SHORT"
        
        # Sprawdź przecięcie linii głównej (S1/R1)
        if last_candle_low <= line_value <= last_candle_high:
            crossed_lines.append(f"{line_prefix}")
        
        # Sprawdź przecięcia linii hierarchicznych (wsparcia)
        for supp in line_info.get('hierarchical_supports', []):
            supp_value = line_value + supp['offset']
            if last_candle_low <= supp_value <= last_candle_high:
                crossed_lines.append(f"{line_prefix} S{supp['level']}")
        
        # Sprawdź przecięcia linii hierarchicznych (opory)
        for res in line_info.get('hierarchical_resistances', []):
            res_value = line_value + res['offset']
            if last_candle_low <= res_value <= last_candle_high:
                crossed_lines.append(f"{line_prefix} R{res['level']}")

# Wypisz wynik
if crossed_lines:
    print(" | ".join(crossed_lines))
else:
    print("NONE")
