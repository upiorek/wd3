"""
Impulse Detector - Wykrywanie impulsów i hierarchicznych linii wsparcia/oporu

Moduł implementujący strategię Multi-Level Impulse Breakout, która wykrywa:
1. Impulsy rynkowe (momenty ekstremalnego zaangażowania)
2. Lokalne ekstrema (H/L - High/Low)
3. Hierarchiczne równoległe linie wsparcia i oporu

KLUCZOWE KONCEPCJE:
- Wszystkie linie wsparcia są równoległe między sobą
- Wszystkie linie oporu są równoległe między sobą  
- Nachylenie support i resistance: symetrycznie odbite (slope_R = -slope_S)
- Odległość między poziomami często stała (struktura równoodległa, nie fraktalna)

HIERARCHIA POZIOMÓW:
- Poziom 1 (główny): bazowa linia wsparcia/oporu z najlepszym dopasowaniem
- Poziom 2: równoległa linia przesunięta pionowo o odległość d₁
- Poziom 3+: kolejne równoległe linie z odległością ≈ d₁ (stepping)

FUNKCJE:
- find_support_trendline(): Znajduje główną linię wsparcia (poziom 1)
- find_hierarchical_parallel_lines(): Znajduje poziomy 2, 3, 4... powyżej i poniżej
- detect_impulse_points(): Wykrywa impulsy (7 kryteriów)
- find_local_extrema(): Wykrywa lokalne H/L
- plot_with_impulses(): Generuje wykres z wszystkimi poziomami

UŻYCIE:
    # Analiza z domyślnymi parametrami
    python impulse_detector.py
    
    # Analiza dla konkretnego zakresu dat
    python impulse_detector.py 2025-10-01 2025-10-31
    
    # Uruchomienie testów
    python impulse_detector.py --test

WYMAGANIA:
- pandas, numpy, matplotlib, mplfinance, scipy

AUTOR: aifx strategy implementation
WERSJA: 2.0 (hierarchiczne linie równoległe)
DATA: 2025-11-12
"""

import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
from scipy.signal import argrelextrema

def find_hierarchical_parallel_lines(df, base_line, extrema, impulses, num_levels_below=2, num_levels_above=2, tolerance=30, debug=True):
    """
    Znajduje hierarchiczne równoległe linie poniżej i powyżej głównej linii.
    Każda kolejna linia analizuje tylko punkty poniżej/powyżej poprzedniej.
    
    Strategia:
    - Linia główna (poziom 1) = bazowa linia wsparcia/oporu
    - Poziom 2 = równoległa linia przesunięta o odległość d₁
    - Poziom 3+ = kolejne równoległe linie z odległością ≈ d₁
    
    Parametry:
    - df: DataFrame z danymi OHLCV
    - base_line: główna linia (dict z 'slope' i 'intercept')
    - extrema: DataFrame z lokalnymi ekstremami (H/L)
    - impulses: DataFrame z wykrytymi impulsami (I)
    - num_levels_below: ile linii wsparcia poniżej głównej
    - num_levels_above: ile linii oporu powyżej głównej
    - tolerance: maksymalna odległość punktu od linii (w punktach)
    - debug: czy wyświetlać informacje debugowe
    
    Zwraca:
    - support_lines_below: lista linii wsparcia poniżej głównej
    - resistance_lines_above: lista linii oporu powyżej głównej
    
    Każda linia to dict:
    {
        'slope': nachylenie (równoległe do głównej),
        'intercept': przesunięcie Y,
        'touches': lista punktów dotykających linii,
        'offset': odległość pionowa od głównej linii,
        'score': liczba punktów na linii,
        'level': numer poziomu (1, 2, 3, ...)
    }
    """
    
    # Zbierz wszystkie punkty
    all_points = []
    
    for idx, ext in extrema.iterrows():
        all_points.append({
            'datetime': ext['datetime'],
            'price': ext['price'],
            'type': ext['type']
        })
    
    for idx, imp in impulses.iterrows():
        all_points.append({
            'datetime': imp['datetime'],
            'price': imp['price'],
            'type': 'impulse'
        })
    
    if debug:
        print(f"\n=== find_hierarchical_parallel_lines DEBUG ===")
        print(f"Punktów H/L: {len(extrema)}, Impulsów: {len(impulses)}, Razem: {len(all_points)}")
        print(f"Główna linia: slope={base_line['slope']:.6f}, intercept={base_line['intercept']:.2f}")
        print(f"Szukam {num_levels_above} poziomów powyżej i {num_levels_below} poniżej")
    
    # Konwertuj na indeksy
    points = []
    for p in all_points:
        idx = df.index.get_loc(p['datetime'])
        points.append({
            'index': idx,
            'price': p['price'],
            'datetime': p['datetime'],
            'type': p['type']
        })
    
    slope = base_line['slope']
    base_intercept = base_line['intercept']
    
    # Funkcja do znajdowania najlepszej równoległej linii
    def find_best_parallel_line(candidate_points, reference_intercept, direction, level):
        """
        Znajduje najlepszą równoległą linię dla danego zestawu punktów.
        
        direction: 'above' (szukamy oporu powyżej) lub 'below' (szukamy wsparcia poniżej)
        level: numer poziomu hierarchii (2, 3, 4, ...)
        """
        best_score = 0
        best_line = None
        
        if debug:
            print(f"\n  Poziom {level} ({direction}): kandydatów punktów = {len(candidate_points)}")
        
        # Próbuj różne offsety
        for offset in range(40, 300, 10):
            if direction == 'above':
                test_intercept = reference_intercept + offset
            else:  # below
                test_intercept = reference_intercept - offset
            
            touches = []
            
            for p in candidate_points:
                expected_price = slope * p['index'] + test_intercept
                distance = abs(p['price'] - expected_price)
                
                if distance <= tolerance:
                    # Sprawdź czy punkt jest po właściwej stronie
                    if direction == 'above' and p['price'] >= expected_price - tolerance:
                        touches.append(p)
                    elif direction == 'below' and p['price'] <= expected_price + tolerance:
                        touches.append(p)
            
            score = len(touches)
            
            if score > best_score and score >= 3:
                best_score = score
                best_line = {
                    'slope': slope,
                    'intercept': test_intercept,
                    'touches': touches,
                    'offset': offset if direction == 'above' else -offset,
                    'score': score,
                    'level': level
                }
                
                if debug:
                    print(f"    Offset {offset if direction == 'above' else -offset:+.0f}: {score} punktów (NEW BEST)")
        
        if best_line and debug:
            print(f"  ✓ Znaleziono linię poziomu {level}: offset={best_line['offset']:+.0f}, score={best_line['score']}")
        elif debug:
            print(f"  ✗ Nie znaleziono linii poziomu {level} (min 3 punkty)")
        
        return best_line
    
    # Znajdź linie wsparcia PONIŻEJ głównej
    if debug:
        print(f"\n--- Szukam linii wsparcia PONIŻEJ głównej ---")
    
    support_lines_below = []
    current_intercept = base_intercept
    available_points = points.copy()
    
    for level in range(1, num_levels_below + 1):
        # Filtruj punkty poniżej obecnej linii
        points_below = []
        for p in available_points:
            expected_price = slope * p['index'] + current_intercept
            if p['price'] < expected_price - tolerance:
                points_below.append(p)
        
        if not points_below:
            if debug:
                print(f"  Poziom {level+1}: brak punktów poniżej")
            break
        
        line = find_best_parallel_line(points_below, current_intercept, 'below', level + 1)
        if line:
            support_lines_below.append(line)
            current_intercept = line['intercept']
            # Usuń użyte punkty
            used_datetimes = set(p['datetime'] for p in line['touches'])
            available_points = [p for p in available_points if p['datetime'] not in used_datetimes]
    
    # Znajdź linie oporu POWYŻEJ głównej
    if debug:
        print(f"\n--- Szukam linii oporu POWYŻEJ głównej ---")
    
    resistance_lines_above = []
    current_intercept = base_intercept
    available_points = points.copy()
    
    for level in range(1, num_levels_above + 1):
        # Filtruj punkty powyżej obecnej linii
        points_above = []
        for p in available_points:
            expected_price = slope * p['index'] + current_intercept
            if p['price'] > expected_price + tolerance:
                points_above.append(p)
        
        if not points_above:
            if debug:
                print(f"  Poziom {level+1}: brak punktów powyżej")
            break
        
        line = find_best_parallel_line(points_above, current_intercept, 'above', level + 1)
        if line:
            resistance_lines_above.append(line)
            current_intercept = line['intercept']
            # Usuń użyte punkty
            used_datetimes = set(p['datetime'] for p in line['touches'])
            available_points = [p for p in available_points if p['datetime'] not in used_datetimes]
    
    if debug:
        print(f"\n=== WYNIK: {len(resistance_lines_above)} linii oporu, {len(support_lines_below)} linii wsparcia ===\n")
    
    return support_lines_below, resistance_lines_above


def find_parallel_support_lines(df, base_line, extrema, impulses, tolerance=30):
    """
    Znajduje równoległe linie do głównej linii wsparcia (wyżej i niżej),
    które również przechodzą przez istotne punkty (H/L/I).
    
    Parametry:
    - base_line: główna linia wsparcia (dict z 'slope' i 'intercept')
    - tolerance: maksymalna odległość punktu od linii
    """
    
    # Zbierz wszystkie punkty (ekstrema + impulsy)
    all_points = []
    
    for idx, ext in extrema.iterrows():
        all_points.append({
            'datetime': ext['datetime'],
            'price': ext['price'],
            'type': ext['type']
        })
    
    for idx, imp in impulses.iterrows():
        all_points.append({
            'datetime': imp['datetime'],
            'price': imp['price'],
            'type': 'impulse'
        })
    
    # Konwertuj na indeksy
    points = []
    for p in all_points:
        idx = df.index.get_loc(p['datetime'])
        points.append({
            'index': idx,
            'price': p['price'],
            'datetime': p['datetime'],
            'type': p['type']
        })
    
    # Użyj tego samego nachylenia co główna linia
    slope = base_line['slope']
    base_intercept = base_line['intercept']
    
    # Znajdź punkty które NIE są na głównej linii
    remaining_points = []
    for p in points:
        expected_price = slope * p['index'] + base_intercept
        distance = abs(p['price'] - expected_price)
        
        if distance > tolerance:  # Nie jest na głównej linii
            remaining_points.append(p)
    
    # Szukaj najlepszych równoległych linii powyżej i poniżej
    best_upper_line = None
    best_lower_line = None
    best_upper_score = 0
    best_lower_score = 0
    
    # Próbuj różne offsety (przesunięcia w pionie)
    for offset in range(-200, 300, 10):
        if abs(offset) < 40:  # Pomijaj bardzo bliskie linie do głównej
            continue
            
        test_intercept = base_intercept + offset
        touches = []
        
        for p in remaining_points:
            expected_price = slope * p['index'] + test_intercept
            distance = abs(p['price'] - expected_price)
            
            if distance <= tolerance:
                touches.append(p)
        
        score = len(touches)
        
        # Jeśli linia jest POWYŻEJ głównej
        if offset > 0 and score > best_upper_score and score >= 3:
            best_upper_score = score
            best_upper_line = {
                'slope': slope,
                'intercept': test_intercept,
                'touches': touches,
                'offset': offset,
                'score': score
            }
        
        # Jeśli linia jest PONIŻEJ głównej
        if offset < 0 and score > best_lower_score and score >= 3:
            best_lower_score = score
            best_lower_line = {
                'slope': slope,
                'intercept': test_intercept,
                'touches': touches,
                'offset': offset,
                'score': score
            }
    
    return best_upper_line, best_lower_line


def find_support_trendline(df, extrema, impulses, tolerance=30):
    """
    Znajduje dolną linię wsparcia (support trendline) przechodzącą przez:
    - Lokalne minima (L) gdzie cena dotyka linii
    - Impulsy (I) które wystąpiły przy testowaniu wsparcia
    
    Priorytet: linia powinna łapać punkty gdzie cena się odbija lub dynamicznie przebija w górę
    
    Parametry:
    - tolerance: maksymalna odległość punktu od linii (w punktach)
    """
    
    # Zbierz punkty które powinny być na linii wsparcia
    support_candidates = []
    
    # 1. Lokalne MINIMA (dołki)
    for idx, ext in extrema.iterrows():
        if ext['type'] == 'minimum':
            support_candidates.append({
                'datetime': ext['datetime'],
                'price': ext['price'],
                'type': 'minimum'
            })
    
    # 2. Impulsy które mogły wystąpić przy wsparciu
    for idx, imp in impulses.iterrows():
        support_candidates.append({
            'datetime': imp['datetime'],
            'price': imp['price'],
            'type': 'impulse'
        })
    
    # Konwertuj na indeksy
    points = []
    for p in support_candidates:
        idx = df.index.get_loc(p['datetime'])
        points.append({
            'index': idx,
            'price': p['price'],
            'datetime': p['datetime'],
            'type': p['type']
        })
    
    # Sortuj po czasie
    points = sorted(points, key=lambda x: x['index'])
    
    best_score = 0
    best_line = None
    
    # Próbuj różne kombinacje dwóch punktów minimum jako podstawę linii
    minima_points = [p for p in points if p['type'] == 'minimum']
    
    for i in range(len(minima_points)):
        for j in range(i + 1, len(minima_points)):
            p1 = minima_points[i]
            p2 = minima_points[j]
            
            # Oblicz nachylenie
            dx = p2['index'] - p1['index']
            if dx == 0 or dx < 20:  # Zbyt blisko siebie
                continue
            
            slope = (p2['price'] - p1['price']) / dx
            
            # Preferuj lekko rosnące lub płaskie linie (uptrend/sideways)
            if slope < -1:  # Zbyt spadkowa linia
                continue
            
            intercept = p1['price'] - slope * p1['index']
            
            # Oceń jak dobrze ta linia działa jako wsparcie
            touches = []
            bounces = 0
            dynamic_breaks = 0
            
            for k, p in enumerate(points):
                expected_price = slope * p['index'] + intercept
                distance = p['price'] - expected_price  # Dodatnia = powyżej linii
                abs_distance = abs(distance)
                
                # Punkt dotyka linii (±tolerance)
                if abs_distance <= tolerance:
                    touches.append(p)
                    
                    # Sprawdź czy był bounce (odbicie w górę)
                    if k < len(points) - 3:
                        # Sprawdź czy następne punkty są wyżej
                        next_prices = [points[k+1]['price'], points[k+2]['price']]
                        if all(next_p > p['price'] + 20 for next_p in next_prices):
                            bounces += 1
                    
                    # Sprawdź dynamiczne przebicie (dla impulsów)
                    if p['type'] == 'impulse' and distance >= -tolerance:
                        dynamic_breaks += 1
                
                # Penalizuj punkty znacznie PONIŻEJ linii (false support)
                if distance < -tolerance * 2:
                    touches.append(None)  # Oznacz jako bad point
            
            # Oceń linię
            valid_touches = [t for t in touches if t is not None]
            score = len(valid_touches) * 2 + bounces * 3 + dynamic_breaks * 2
            
            # Bonus za dobre nachylenie (lekki wzrost)
            if 0 <= slope <= 0.5:
                score += 5
            
            if score > best_score and len(valid_touches) >= 5:
                best_score = score
                best_line = {
                    'slope': slope,
                    'intercept': intercept,
                    'touches': valid_touches,
                    'bounces': bounces,
                    'dynamic_breaks': dynamic_breaks,
                    'score': score
                }
    
    return best_line


def find_parallel_channels(df, extrema, impulses, tolerance=50):
    """
    Znajduje dwie równoległe linie (kanał) przechodzące przez maksymalną liczbę punktów.
    
    Parametry:
    - tolerance: maksymalna odległość punktu od linii aby uznać za dopasowany (w punktach)
    """
    
    # Zbierz wszystkie punkty (ekstrema + impulsy)
    all_points = []
    
    # Dodaj ekstrema
    for idx, ext in extrema.iterrows():
        all_points.append({
            'datetime': ext['datetime'],
            'price': ext['price'],
            'type': ext['type']
        })
    
    # Dodaj impulsy
    for idx, imp in impulses.iterrows():
        all_points.append({
            'datetime': imp['datetime'],
            'price': imp['price'],
            'type': 'impulse'
        })
    
    # Konwertuj datetime na indeks numeryczny
    points_with_index = []
    for p in all_points:
        idx = df.index.get_loc(p['datetime'])
        points_with_index.append({
            'index': idx,
            'price': p['price'],
            'type': p['type']
        })
    
    best_score = 0
    best_channel = None
    
    # Próbuj różne kombinacje dwóch punktów do zdefiniowania pierwszej linii
    for i in range(len(points_with_index)):
        for j in range(i + 1, min(i + 20, len(points_with_index))):  # Ogranicz kombinacje
            p1 = points_with_index[i]
            p2 = points_with_index[j]
            
            # Oblicz nachylenie (slope)
            dx = p2['index'] - p1['index']
            if dx == 0:
                continue
            slope = (p2['price'] - p1['price']) / dx
            
            # Intercept dla pierwszej linii
            intercept1 = p1['price'] - slope * p1['index']
            
            # Policz ile punktów jest blisko tej linii
            points_on_line1 = []
            remaining_points = []
            
            for p in points_with_index:
                expected_price = slope * p['index'] + intercept1
                distance = abs(p['price'] - expected_price)
                
                if distance <= tolerance:
                    points_on_line1.append(p)
                else:
                    remaining_points.append(p)
            
            # Szukaj równoległej linii dla pozostałych punktów
            if len(remaining_points) > 0:
                # Próbuj różne offsety (odległości między liniami)
                for offset in range(-300, 300, 20):
                    intercept2 = intercept1 + offset
                    
                    points_on_line2 = []
                    for p in remaining_points:
                        expected_price = slope * p['index'] + intercept2
                        distance = abs(p['price'] - expected_price)
                        
                        if distance <= tolerance:
                            points_on_line2.append(p)
                    
                    # Ocena: suma punktów na obu liniach
                    score = len(points_on_line1) + len(points_on_line2)
                    
                    if score > best_score:
                        best_score = score
                        best_channel = {
                            'slope': slope,
                            'intercept1': intercept1,
                            'intercept2': intercept2,
                            'points_on_line1': len(points_on_line1),
                            'points_on_line2': len(points_on_line2),
                            'total_score': score,
                            'line1_points': points_on_line1,
                            'line2_points': points_on_line2
                        }
    
    return best_channel


def find_local_extrema(df, order=5):
    """
    Znajduje lokalne minima i maksima używając scipy.
    
    Parametry:
    - order: ile świec po obu stronach musi być wyższych/niższych
    """
    from scipy.signal import argrelextrema
    
    # Lokalne maksima
    local_max_indices = argrelextrema(df['High'].values, np.greater, order=order)[0]
    local_maxima = pd.DataFrame({
        'index': local_max_indices,
        'datetime': df.index[local_max_indices],
        'price': df['High'].iloc[local_max_indices].values,
        'type': 'maximum'
    })
    
    # Lokalne minima
    local_min_indices = argrelextrema(df['Low'].values, np.less, order=order)[0]
    local_minima = pd.DataFrame({
        'index': local_min_indices,
        'datetime': df.index[local_min_indices],
        'price': df['Low'].iloc[local_min_indices].values,
        'type': 'minimum'
    })
    
    # Połącz
    extrema = pd.concat([local_maxima, local_minima], ignore_index=True)
    extrema = extrema.sort_values('datetime').reset_index(drop=True)
    
    return extrema


def detect_impulse_points(df, min_periods=20, forward_candles=15, min_profit_points=80):
    """
    Wykrywa punkty impulsu do kontynuacji trendu wzrostowego.
    WERYFIKUJE czy po sygnale faktycznie nastąpił wzrost.
    
    Parametry:
    - forward_candles: ile świec do przodu sprawdzamy (15 = ~4 godziny na M15)
    - min_profit_points: minimalny wzrost w punktach aby uznać sygnał za skuteczny
    """
    
    # Oblicz wskaźniki techniczne
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # Kierunek EMA20 (czy rośnie?)
    df['EMA_20_Rising'] = df['EMA_20'] > df['EMA_20'].shift(3)
    
    # ATR (Average True Range) - volatility
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # Średni wolumen
    df['Vol_MA'] = df['Volume'].rolling(window=20).mean()
    
    # Identyfikuj trend wzrostowy (EMA20 > EMA50 I EMA20 rośnie)
    df['Uptrend'] = (df['EMA_20'] > df['EMA_50']) & df['EMA_20_Rising']
    
    impulse_points = []
    
    # Iteruj tylko do len(df) - forward_candles, żeby móc zweryfikować wynik
    for i in range(min_periods, len(df) - forward_candles):
        if not df['Uptrend'].iloc[i]:
            continue
            
        score = 0
        reasons = []
        
        # 1. Momentum candle - duża świeca w górę
        candle_size = df['Close'].iloc[i] - df['Open'].iloc[i]
        if candle_size > 1.5 * df['ATR'].iloc[i]:
            score += 3
            reasons.append('Strong_Bullish_Candle')
        
        # 2. Wzrost wolumenu
        if df['Volume'].iloc[i] > 1.5 * df['Vol_MA'].iloc[i]:
            score += 2
            reasons.append('Volume_Spike')
        
        # 3. Breakout z konsolidacji (niski ATR -> wysoki ATR)
        atr_current = df['ATR'].iloc[i]
        atr_prev_avg = df['ATR'].iloc[i-5:i].mean()
        if atr_current > 1.3 * atr_prev_avg and candle_size > 0:
            score += 2
            reasons.append('Volatility_Expansion')
        
        # 4. Odbicie od EMA20 (pullback)
        if i >= 3:
            low_near_ema = abs(df['Low'].iloc[i-1] - df['EMA_20'].iloc[i-1]) < 0.5 * df['ATR'].iloc[i]
            price_bounced = df['Close'].iloc[i] > df['Close'].iloc[i-1]
            if low_near_ema and price_bounced:
                score += 2.5
                reasons.append('EMA20_Bounce')
        
        # 5. Higher high formation
        if i >= 10:
            recent_high = df['High'].iloc[i-10:i].max()
            if df['High'].iloc[i] > recent_high:
                score += 1.5
                reasons.append('New_High')
        
        # 6. Retest wsparcia (poprzedni opór)
        if i >= 20:
            prev_resistance = df['High'].iloc[i-20:i-5].max()
            current_low = df['Low'].iloc[i]
            if abs(current_low - prev_resistance) < 0.3 * df['ATR'].iloc[i] and df['Close'].iloc[i] > current_low:
                score += 2
                reasons.append('Support_Retest')
        
        if score < 3:  # Minimalny threshold
            continue
        
        # ===== KLUCZOWA WERYFIKACJA: CZY PO TYM SYGNALE NASTĄPIŁ WZROST? =====
        entry_price = df['Close'].iloc[i]
        
        # Sprawdź następne forward_candles świec
        future_slice = df.iloc[i+1:i+1+forward_candles]
        max_future_high = future_slice['High'].max()
        min_future_low = future_slice['Low'].min()
        
        # Oblicz potencjalny profit i drawdown
        potential_profit = max_future_high - entry_price
        potential_drawdown = entry_price - min_future_low
        
        # Sprawdź czy sygnał się sprawdził
        if potential_profit < min_profit_points:
            continue  # Odrzuć sygnał - nie było wystarczającego wzrostu
        
        # Dodatkowo: sprawdź risk/reward ratio
        if potential_drawdown > 0:
            rr_ratio = potential_profit / potential_drawdown
        else:
            rr_ratio = 999
        
        # Dodaj bonus za dobry R/R
        if rr_ratio > 2:
            score += 2
            reasons.append(f'Good_RR_{rr_ratio:.1f}')
        
        impulse_points.append({
            'index': i,
            'datetime': df.index[i],
            'price': entry_price,
            'score': score,
            'reasons': ', '.join(reasons),
            'profit_achieved': potential_profit,
            'max_drawdown': potential_drawdown,
            'rr_ratio': rr_ratio
        })
    
    return pd.DataFrame(impulse_points)


def plot_with_impulses(csv_file, start_date, end_date, output_file='impulse_chart.png', top_n=4, min_profit=40):
    """
    Generuje wykres z zaznaczonymi punktami impulsu.
    """
    
    # Wczytaj dane
    print(f"Wczytuję dane z {csv_file}...")
    df = pd.read_csv(csv_file, 
                     sep='\t',
                     skiprows=1,
                     names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'TickVol', 'Vol', 'Spread'])
    
    df = df[['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'TickVol']]
    df.rename(columns={'TickVol': 'Volume'}, inplace=True)
    
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    df = df.set_index('Datetime')
    df = df.drop(['Date', 'Time'], axis=1)
    df = df.sort_index()
    
    print(f"Załadowano {len(df)} świeczek")
    
    # Filtruj zakres
    df_filtered = df.loc[start_date:end_date].copy()
    print(f"Zakres: {len(df_filtered)} świeczek ({df_filtered.index.min()} - {df_filtered.index.max()})")
    
    # Wykryj punkty impulsu
    print("Wykrywam punkty impulsu...")
    impulses = detect_impulse_points(df_filtered, min_profit_points=min_profit)
    
    # Wykryj lokalne ekstrema
    print("Wykrywam lokalne minima i maksima...")
    extrema = find_local_extrema(df_filtered, order=5)
    
    # Znajdź dolną linię wsparcia
    print("Wyznaczam dolną linię wsparcia (support trendline)...")
    support_line = find_support_trendline(df_filtered, extrema, impulses, tolerance=30)
    
    # Znajdź hierarchiczne równoległe linie powyżej i poniżej
    support_lines_below, resistance_lines_above = [], []
    if support_line:
        print("Wyznaczam równoległe linie wsparcia i oporu...")
        support_lines_below, resistance_lines_above = find_hierarchical_parallel_lines(
            df_filtered, support_line, extrema, impulses, 
            num_levels_below=2, num_levels_above=2, tolerance=30)
    
    if len(impulses) == 0:
        print("Nie znaleziono punktów impulsu!")
        return
    
    # Wybierz top N najsilniejszych
    impulses = impulses.nlargest(top_n, 'score')
    impulses = impulses.sort_values('datetime')
    
    print(f"\n=== Znaleziono {len(impulses)} najsilniejszych punktów impulsu ===")
    for idx, imp in impulses.iterrows():
        print(f"\n{imp['datetime']} | Entry: {imp['price']:.2f}")
        print(f"  Siła: {imp['score']:.1f} | Powody: {imp['reasons']}")
        print(f"  ✓ Profit osiągnięty: +{imp['profit_achieved']:.2f} pkt")
        print(f"  Max Drawdown: -{imp['max_drawdown']:.2f} pkt")
        print(f"  Risk/Reward: 1:{imp['rr_ratio']:.2f}")
    
    print(f"\n=== Znaleziono {len(extrema)} lokalnych ekstremów ===")
    print(f"  Maksima: {len(extrema[extrema['type'] == 'maximum'])}")
    print(f"  Minima: {len(extrema[extrema['type'] == 'minimum'])}")
    
    if support_line:
        print(f"\n=== Dolna linia wsparcia (Support Trendline) - GŁÓWNA ===")
        print(f"  Punktów dotykających: {len(support_line['touches'])}")
        print(f"  Bounces (odbić): {support_line['bounces']}")
        print(f"  Dynamicznych przebić: {support_line['dynamic_breaks']}")
        print(f"  Ocena: {support_line['score']}")
        print(f"  Nachylenie: {support_line['slope']:.4f}")
        
        print(f"\n--- Punkty na głównej linii wsparcia: ---")
        for p in support_line['touches'][:5]:
            print(f"  {p['datetime']} | Cena: {p['price']:.2f} | Typ: {p['type']}")
    
    if resistance_lines_above:
        print(f"\n=== Linie oporu POWYŻEJ ({len(resistance_lines_above)}) ===")
        for i, line in enumerate(resistance_lines_above, 1):
            print(f"\nOpór poziom {i}: +{line['offset']:.0f} pkt, {len(line['touches'])} punktów")
            for p in line['touches'][:3]:
                print(f"  {p['datetime']} | {p['price']:.2f} | {p['type']}")
    
    if support_lines_below:
        print(f"\n=== Linie wsparcia PONIŻEJ ({len(support_lines_below)}) ===")
        for i, line in enumerate(support_lines_below, 1):
            print(f"\nWsparcie poziom {i}: {line['offset']:.0f} pkt, {len(line['touches'])} punktów")
            for p in line['touches'][:3]:
                print(f"  {p['datetime']} | {p['price']:.2f} | {p['type']}")
    
    # Przygotuj punkty do zaznaczenia
    markers = []
    for idx, imp in impulses.iterrows():
        markers.append(mpf.make_addplot(
            [np.nan] * len(df_filtered),
            type='scatter',
            markersize=200,
            marker='o',
            color='cyan',
            alpha=0.3,
            secondary_y=False
        ))
    
    # Dodaj EMA
    ema20 = mpf.make_addplot(df_filtered['EMA_20'], color='orange', width=1.5, label='EMA20')
    ema50 = mpf.make_addplot(df_filtered['EMA_50'], color='blue', width=1.5, label='EMA50')
    
    # Stwórz wykres z markerami
    fig, axes = mpf.plot(df_filtered[['Open', 'High', 'Low', 'Close', 'Volume']], 
                         type='candle',
                         style='charles',
                         title=f'Nasdaq 100 (M15) - Punkty Impulsu Trendu Wzrostowego\n{start_date} do {end_date}',
                         ylabel='Cena',
                         volume=True,
                         ylabel_lower='Wolumen',
                         figsize=(18, 10),
                         warn_too_much_data=10000,
                         addplot=[ema20, ema50],
                         returnfig=True)
    
    # Dodaj ręcznie okręgi na wykresie
    ax = axes[0]
    
    # ZIELONE okręgi - punkty impulsu
    for idx, imp in impulses.iterrows():
        date_pos = df_filtered.index.get_loc(imp['datetime'])
        price = imp['price']
        
        circle = plt.Circle((date_pos, price), radius=3, 
                           color='lime', fill=False, linewidth=3, alpha=0.8)
        ax.add_patch(circle)
        
        ax.text(date_pos, price + 50, f"{imp['score']:.1f}", 
               fontsize=10, color='lime', fontweight='bold',
               ha='center', va='bottom')
    
    # NIEBIESKIE okręgi - lokalne ekstrema
    for idx, ext in extrema.iterrows():
        date_pos = df_filtered.index.get_loc(ext['datetime'])
        price = ext['price']
        
        # Maksima - okrąg nad ceną
        if ext['type'] == 'maximum':
            circle = plt.Circle((date_pos, price), radius=2, 
                               color='blue', fill=False, linewidth=2, alpha=0.6)
            ax.add_patch(circle)
            ax.text(date_pos, price + 30, 'H', 
                   fontsize=8, color='blue', fontweight='bold',
                   ha='center', va='bottom')
        # Minima - okrąg pod ceną
        else:
            circle = plt.Circle((date_pos, price), radius=2, 
                               color='dodgerblue', fill=False, linewidth=2, alpha=0.6)
            ax.add_patch(circle)
            ax.text(date_pos, price - 30, 'L', 
                   fontsize=8, color='dodgerblue', fontweight='bold',
                   ha='center', va='top')
    
    # CZERWONA linia - główna linia wsparcia (ciągła, gruba)
    if support_line:
        x_start = 0
        x_end = len(df_filtered) - 1
        
        y_start = support_line['slope'] * x_start + support_line['intercept']
        y_end = support_line['slope'] * x_end + support_line['intercept']
        ax.plot([x_start, x_end], [y_start, y_end], 
               color='red', linewidth=4, linestyle='-', alpha=1.0, 
               label=f"S1 MAIN ({len(support_line['touches'])} pts)", zorder=10)
        
        # Punkty na głównej linii
        for p in support_line['touches']:
            p_idx = df_filtered.index.get_loc(p['datetime'])
            ax.plot(p_idx, p['price'], 'o', color='orange', markersize=5, alpha=0.8, zorder=11)
    
    # CZERWONE przerywane linie PONIŻEJ (wsparcia niższego poziomu)
    if support_lines_below:
        x_start = 0
        x_end = len(df_filtered) - 1
        
        # Kolory gradientowo ciemniejsze dla kolejnych poziomów
        colors = ['darkred', 'maroon', 'brown', 'firebrick']
        
        for i, line in enumerate(support_lines_below):
            y_start = line['slope'] * x_start + line['intercept']
            y_end = line['slope'] * x_end + line['intercept']
            
            color = colors[min(i, len(colors)-1)]
            linestyle = '--' if i == 0 else ':'
            linewidth = 3 if i == 0 else 2
            
            ax.plot([x_start, x_end], [y_start, y_end], 
                   color=color, linewidth=linewidth, linestyle=linestyle, alpha=0.7, 
                   label=f"S{line['level']} ({line['offset']:+.0f} pts, {line['score']} p)", zorder=8-i)
            
            # Punkty na linii wsparcia
            for p in line['touches']:
                p_idx = df_filtered.index.get_loc(p['datetime'])
                ax.plot(p_idx, p['price'], 's', color=color, markersize=3, alpha=0.6, zorder=9-i)
    
    # NIEBIESKIE linie POWYŻEJ (opory - resistance)
    if resistance_lines_above:
        x_start = 0
        x_end = len(df_filtered) - 1
        
        # Kolory gradientowo jaśniejsze dla kolejnych poziomów
        colors = ['blue', 'dodgerblue', 'deepskyblue', 'lightskyblue']
        
        for i, line in enumerate(resistance_lines_above):
            y_start = line['slope'] * x_start + line['intercept']
            y_end = line['slope'] * x_end + line['intercept']
            
            color = colors[min(i, len(colors)-1)]
            linestyle = '--' if i == 0 else ':'
            linewidth = 3 if i == 0 else 2
            
            ax.plot([x_start, x_end], [y_start, y_end], 
                   color=color, linewidth=linewidth, linestyle=linestyle, alpha=0.8, 
                   label=f"R{line['level']} ({line['offset']:+.0f} pts, {line['score']} p)", zorder=8-i)
            
            # Punkty na linii oporu
            for p in line['touches']:
                p_idx = df_filtered.index.get_loc(p['datetime'])
                ax.plot(p_idx, p['price'], '^', color=color, markersize=3, alpha=0.7, zorder=9-i)
    
    if support_line or resistance_lines_above or support_lines_below:
        ax.legend(loc='upper left', fontsize=9)
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Wykres zapisany jako: {output_file}")
    
    # Statystyki
    print(f"\n--- Statystyki zakresu ---")
    print(f"Open: {df_filtered['Open'].iloc[0]:.2f}")
    print(f"Close: {df_filtered['Close'].iloc[-1]:.2f}")
    print(f"High: {df_filtered['High'].max():.2f}")
    print(f"Low: {df_filtered['Low'].min():.2f}")
    print(f"Zmiana: {df_filtered['Close'].iloc[-1] - df_filtered['Open'].iloc[0]:.2f} pkt")


def test_hierarchical_lines():
    """
    Test jednostkowy dla find_hierarchical_parallel_lines().
    Tworzy syntetyczne dane i weryfikuje czy algorytm poprawnie znajduje linie.
    """
    print("\n" + "="*60)
    print("TEST: find_hierarchical_parallel_lines()")
    print("="*60)
    
    # Stwórz syntetyczne dane
    dates = pd.date_range('2025-01-01', periods=100, freq='15min')
    np.random.seed(42)
    
    # Trend wzrostowy z noise
    prices = 20000 + np.arange(100) * 5 + np.random.normal(0, 20, 100)
    
    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 10,
        'Low': prices - 10,
        'Close': prices,
        'Volume': 1000
    }, index=dates)
    
    # Stwórz sztuczne ekstrema (co 10 świec)
    extrema = pd.DataFrame({
        'datetime': dates[::10],
        'price': prices[::10],
        'type': ['minimum' if i % 2 == 0 else 'maximum' for i in range(10)]
    })
    
    # Stwórz sztuczne impulsy (co 7 świec)
    impulses = pd.DataFrame({
        'datetime': dates[::7],
        'price': prices[::7] + 20,
        'score': 5.0
    })
    
    # Główna linia (slope ~ 5, przechodzi przez środek)
    base_line = {
        'slope': 5.0,
        'intercept': 20000.0,
        'touches': [],
        'score': 10
    }
    
    # Testuj funkcję
    support_below, resistance_above = find_hierarchical_parallel_lines(
        df, base_line, extrema, impulses,
        num_levels_below=2,
        num_levels_above=2,
        tolerance=50,
        debug=True
    )
    
    # Weryfikacje
    print("\n--- WERYFIKACJA ---")
    
    assert isinstance(support_below, list), "support_below powinno być listą"
    assert isinstance(resistance_above, list), "resistance_above powinno być listą"
    
    print(f"✓ Zwrócono listy: {len(support_below)} wsparć poniżej, {len(resistance_above)} oporów powyżej")
    
    # Sprawdź strukturę linii
    for i, line in enumerate(resistance_above, 1):
        assert 'slope' in line, f"Linia oporu {i} nie ma 'slope'"
        assert 'intercept' in line, f"Linia oporu {i} nie ma 'intercept'"
        assert 'touches' in line, f"Linia oporu {i} nie ma 'touches'"
        assert 'offset' in line, f"Linia oporu {i} nie ma 'offset'"
        assert 'score' in line, f"Linia oporu {i} nie ma 'score'"
        assert 'level' in line, f"Linia oporu {i} nie ma 'level'"
        
        # Sprawdź równoległość
        assert abs(line['slope'] - base_line['slope']) < 0.001, \
            f"Linia oporu {i} nie jest równoległa! slope={line['slope']}"
        
        # Sprawdź że jest powyżej głównej
        assert line['offset'] > 0, f"Linia oporu {i} ma offset <= 0"
        
        print(f"✓ Opór poziom {line['level']}: slope={line['slope']:.2f}, offset={line['offset']:+.0f}, {line['score']} punktów")
    
    for i, line in enumerate(support_below, 1):
        assert 'slope' in line, f"Linia wsparcia {i} nie ma 'slope'"
        assert abs(line['slope'] - base_line['slope']) < 0.001, \
            f"Linia wsparcia {i} nie jest równoległa!"
        assert line['offset'] < 0, f"Linia wsparcia {i} ma offset >= 0"
        
        print(f"✓ Wsparcie poziom {line['level']}: slope={line['slope']:.2f}, offset={line['offset']:+.0f}, {line['score']} punktów")
    
    print("\n✓✓✓ TEST PASSED ✓✓✓\n")
    return True


if __name__ == "__main__":
    import sys
    
    # Sprawdź czy uruchomiono w trybie testowym
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("Uruchamiam testy jednostkowe...")
        test_hierarchical_lines()
        print("Wszystkie testy zakończone sukcesem!")
        sys.exit(0)
    
    # Parametry z linii poleceń lub domyślne
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        output_file = f'impulse_analysis_{start_date}_to_{end_date}.png'
    else:
        # Domyślnie: poprzednie 5 dni przed 3.10 (28.09 - 2.10)
        start_date = '2025-09-28'
        end_date = '2025-10-02'
        output_file = 'impulse_analysis_sep_28-oct_2.png'
    
    print(f"Analiza dla: {start_date} do {end_date}")
    
    plot_with_impulses('FUS100.15.csv', 
                      start_date=start_date, 
                      end_date=end_date,
                      output_file=output_file,
                      top_n=10,
                      min_profit=40)
