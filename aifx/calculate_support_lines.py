"""
Skrypt do obliczania linii support dla ostatnich 400 świeczek z FUS100.15_single.csv
"""

import pandas as pd
from run_support_backtest import load_data
from support_breakout_strategy import SupportBreakoutStrategy
from datetime import date

# Wczytaj dane
print("Wczytuję dane z FUS100.15_single.csv...")
df = load_data('FUS100.15_single.csv', data_format='mbank')
print(f"Załadowano {len(df)} świeczek")
print(f"Zakres: {df['DateTime'].min()} - {df['DateTime'].max()}\n")

lookback_candles = 300
print(f"Analizuję wszystkie {len(df)} świeczek (lookback={lookback_candles})")
print(f"Zakres analizy: {df['DateTime'].min()} - {df['DateTime'].max()}\n")

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
print("Wykrywam linie support...")
df_calc = strategy.calculate_indicators(df)

# Wyświetl wyniki
print("\n" + "="*80)
print("WYNIKI WYKRYWANIA LINII SUPPORT")
print("="*80 + "\n")

if strategy.daily_support_data:
    total_lines = sum(len(lines) for lines in strategy.daily_support_data.values())
    print(f"Wykryto {total_lines} linii dla {len(strategy.daily_support_data)} dat\n")
    
    for date_key, lines_list in sorted(strategy.daily_support_data.items()):
        print(f"📅 Data: {date_key}")
        print(f"   Liczba linii: {len(lines_list)}")
        
        for idx, line_info in enumerate(lines_list, 1):
            slope = line_info['slope']
            intercept = line_info['intercept']
            line_type = line_info['type']
            
            # Kierunek linii
            direction = "↗ WZNOSZĄCA (LONG)" if line_type == 'ascending' else "↘ OPADAJĄCA (SHORT)"
            
            print(f"\n   Linia #{idx}: {direction}")
            print(f"      Slope: {slope:.6f}")
            print(f"      Intercept: {intercept:.2f}")
            print(f"      Punkty dopasowania: {len(line_info['support_points'])}")
            
            # Hierarchiczne linie wsparcia (poniżej)
            h_supp = line_info.get('hierarchical_supports', [])
            if h_supp:
                print(f"      Linie wsparcia (poniżej głównej): {len(h_supp)}")
                for supp in h_supp:
                    print(f"         S{supp['level']}: offset={supp['offset']:+.0f} pkt, score={supp['score']}, touches={supp['touches']}")
            
            # Hierarchiczne linie oporu (powyżej)
            h_res = line_info.get('hierarchical_resistances', [])
            if h_res:
                print(f"      Linie oporu (powyżej głównej): {len(h_res)}")
                for res in h_res:
                    print(f"         R{res['level']}: offset={res['offset']:+.0f} pkt, score={res['score']}, touches={res['touches']}")
            
            # Zakres lookback
            print(f"      Lookback: {line_info['lookback_start_dt']} - {line_info['lookback_end_dt']}")
        
        print()

    # Wygeneruj wykres dla ostatniej daty
    print("\n" + "="*80)
    print("GENEROWANIE WYKRESU")
    print("="*80 + "\n")
    
    last_date = sorted(strategy.daily_support_data.keys())[-1]
    print(f"Generuję wykres dla {last_date}...")
    
    filename = strategy.plot_daily_chart(
        df,
        last_date,
        output_dir='support_charts',
        show_volume=False,
        mark_high_low=True
    )
    
    if filename:
        print(f"✓ Zapisano wykres: {filename}")
    else:
        print("⚠ Nie udało się wygenerować wykresu")
    
    # Podsumowanie
    print("\n" + "="*80)
    print("PODSUMOWANIE")
    print("="*80 + "\n")
    
    total_ascending = 0
    total_descending = 0
    total_hierarchical_supports = 0
    total_hierarchical_resistances = 0
    
    for lines_list in strategy.daily_support_data.values():
        for line_info in lines_list:
            if line_info['type'] == 'ascending':
                total_ascending += 1
            else:
                total_descending += 1
            
            total_hierarchical_supports += len(line_info.get('hierarchical_supports', []))
            total_hierarchical_resistances += len(line_info.get('hierarchical_resistances', []))
    
    print(f"Linie główne:")
    print(f"   Wznosząc (LONG): {total_ascending}")
    print(f"   Opadające (SHORT): {total_descending}")
    print(f"\nLinie hierarchiczne:")
    print(f"   Wsparcia (S2, S3, ...): {total_hierarchical_supports}")
    print(f"   Opory (R2, R3, ...): {total_hierarchical_resistances}")
    print(f"\nŁącznie: {total_lines} linii głównych + {total_hierarchical_supports + total_hierarchical_resistances} hierarchicznych")
    
    # Sprawdź przecięcia ostatniej świeczki
    print("\n" + "="*80)
    print("PRZECIĘCIA OSTATNIEJ ŚWIECZKI")
    print("="*80 + "\n")
    
    last_candle = df.iloc[-1]
    last_candle_idx = len(df) - 1
    last_candle_low = last_candle['Low']
    last_candle_high = last_candle['High']
    last_candle_close = last_candle['Close']
    last_candle_dt = last_candle['DateTime']
    
    print(f"Ostatnia świeczka: {last_candle_dt}")
    print(f"   Low: {last_candle_low:.2f}")
    print(f"   High: {last_candle_high:.2f}")
    print(f"   Close: {last_candle_close:.2f}\n")
    
    crossings_found = False
    
    # Sprawdź wszystkie linie
    for date_key, lines_list in sorted(strategy.daily_support_data.items()):
        for idx, line_info in enumerate(lines_list, 1):
            slope = line_info['slope']
            intercept = line_info['intercept']
            line_type = line_info['type']
            
            # Oblicz wartość linii głównej dla ostatniej świeczki
            line_value = slope * last_candle_idx + intercept
            
            # Sprawdź przecięcie linii głównej
            if last_candle_low <= line_value <= last_candle_high:
                crossings_found = True
                direction = "WZNOSZĄCA (LONG)" if line_type == 'ascending' else "OPADAJĄCA (SHORT)"
                print(f"✓ PRZECIĘCIE - Linia główna #{idx} ({direction})")
                print(f"   Wartość linii: {line_value:.2f}")
                print(f"   Slope: {slope:.6f}")
                
                # Określ typ przecięcia
                if last_candle_close > line_value:
                    print(f"   Typ: Przebicie w górę (close={last_candle_close:.2f} > line={line_value:.2f})")
                elif last_candle_close < line_value:
                    print(f"   Typ: Odbicie w dół (close={last_candle_close:.2f} < line={line_value:.2f})")
                else:
                    print(f"   Typ: Close dokładnie na linii")
                print()
            
            # Sprawdź przecięcia linii hierarchicznych (wsparcia)
            for supp in line_info.get('hierarchical_supports', []):
                supp_value = line_value + supp['offset']
                if last_candle_low <= supp_value <= last_candle_high:
                    crossings_found = True
                    print(f"✓ PRZECIĘCIE - Wsparcie S{supp['level']} (linia #{idx})")
                    print(f"   Wartość linii: {supp_value:.2f} (offset={supp['offset']:+.0f} pkt)")
                    if last_candle_close > supp_value:
                        print(f"   Typ: Przebicie w górę (close={last_candle_close:.2f} > line={supp_value:.2f})")
                    elif last_candle_close < supp_value:
                        print(f"   Typ: Odbicie w dół (close={last_candle_close:.2f} < line={supp_value:.2f})")
                    else:
                        print(f"   Typ: Close dokładnie na linii")
                    print()
            
            # Sprawdź przecięcia linii hierarchicznych (opory)
            for res in line_info.get('hierarchical_resistances', []):
                res_value = line_value + res['offset']
                if last_candle_low <= res_value <= last_candle_high:
                    crossings_found = True
                    print(f"✓ PRZECIĘCIE - Opór R{res['level']} (linia #{idx})")
                    print(f"   Wartość linii: {res_value:.2f} (offset={res['offset']:+.0f} pkt)")
                    if last_candle_close > res_value:
                        print(f"   Typ: Przebicie w górę (close={last_candle_close:.2f} > line={res_value:.2f})")
                    elif last_candle_close < res_value:
                        print(f"   Typ: Odbicie w dół (close={last_candle_close:.2f} < line={res_value:.2f})")
                    else:
                        print(f"   Typ: Close dokładnie na linii")
                    print()
    
    if not crossings_found:
        print("⚠ Ostatnia świeczka NIE przecinała żadnej linii")
        print("   (ani głównych, ani hierarchicznych)")
    
else:
    print("⚠ Nie wykryto żadnych linii support w ostatnich 400 świeczkach")
    print("   Spróbuj:")
    print("   - Zmniejszyć min_slope (np. 0.1)")
    print("   - Zwiększyć hierarchical_tolerance (np. 50)")
    print("   - Sprawdzić czy dane zawierają trend")

print("\n✓ Analiza zakończona")
