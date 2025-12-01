"""
Magic Lines - Standalone Support/Resistance Line Detection and Analysis

Ten skrypt analizuje dane CSV z cenami świeczek, wykrywa linie wsparcia/oporu,
generuje wykresy i zapisuje wyniki przecięć ostatniej świeczki.

Wyjście: plik support_lines_results.txt z wynikami dla każdego pliku CSV.
Wykresy: zapisywane w folderze support_charts/

Użycie:
    python magic_lines.py  # przetwarza wszystkie pliki CSV w tester-third/mt4_test_results/m15_candles/
    python magic_lines.py <plik.csv>  # przetwarza pojedynczy plik
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date
from scipy.signal import argrelextrema
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf

# ===== KONFIGURACJA =====
LOOKBACK_CANDLES = 300  # Liczba świeczek do analizy
MIN_SLOPE = 0.4  # Minimalny slope linii
HIERARCHICAL_LEVELS_BELOW = 4  # Liczba linii wsparcia poniżej głównej
HIERARCHICAL_LEVELS_ABOVE = 4  # Liczba linii oporu powyżej głównej
HIERARCHICAL_TOLERANCE = 10  # Tolerancja dla linii hierarchicznych (punkty)
LINE_TOLERANCE = 5  # Tolerancja dla dopasowania punktów do linii głównej
SHOW_IMPULSES = True  # Czy pokazywać impulsy / local min / local max na wykresie
DUMP_IMAGES = True  # Czy zapisywać wykresy do plików

# ===== FUNKCJE POMOCNICZE =====

def load_csv_data(filepath):
    """Wczytuje dane CSV w formacie mbank (Time;Open;High;Low;Close)"""
    df = pd.read_csv(filepath, sep=';', parse_dates=['Time'])
    df.rename(columns={'Time': 'DateTime'}, inplace=True)
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    
    # Konwertuj ceny z string na float (zastąp przecinki kropkami jeśli są)
    for col in ['Open', 'High', 'Low', 'Close']:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '.').astype(float)
    
    # Dodaj kolumnę Volume (wymagane przez mplfinance nawet gdy volume=False)
    df['Volume'] = 0
    
    return df

def detect_impulses(df):
    """
    Wykrywa impulsy rynkowe na podstawie 7 kryteriów.
    Zwraca listę indeksów świeczek będących impulsami.
    """
    impulses = []
    
    if len(df) < 50:
        return impulses
    
    # Oblicz wskaźniki
    ema20 = df['Close'].ewm(span=20, adjust=False).mean()
    ema50 = df['Close'].ewm(span=50, adjust=False).mean()
    
    # ATR dla volatility
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()
    
    for i in range(50, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        strength = 0
        
        # 1. Strong bullish candle
        body_size = abs(current['Close'] - current['Open'])
        candle_range = current['High'] - current['Low']
        if current['Close'] > current['Open'] and body_size > candle_range * 0.6:
            strength += 1
        
        # 2. Momentum candle
        if current['Close'] > prev['Close'] and body_size > df.iloc[i-5:i]['Close'].diff().abs().mean() * 1.5:
            strength += 1
        
        # 3. Price gap (luka cenowa)
        gap_up = current['Low'] > prev['High']
        if gap_up:
            gap_size = current['Low'] - prev['High']
            # Luka większa niż 50 punktów
            if gap_size > 50:
                strength += 2  # Duża luka = 2 punkty
            elif gap_size > 20:
                strength += 1  # Mała luka = 1 punkt
        
        # 4. Volatility expansion
        if not pd.isna(atr.iloc[i]) and not pd.isna(atr.iloc[i-1]):
            if atr.iloc[i] > atr.iloc[i-1] * 1.2:
                strength += 1
        
        # 5. EMA20 bounce
        if prev['Low'] <= ema20.iloc[i-1] * 1.002 and current['Close'] > ema20.iloc[i]:
            strength += 1
        
        # 6. New high (trend continuation)
        recent_high = df.iloc[i-20:i]['High'].max()
        if current['High'] > recent_high:
            strength += 1
        
        # 7. Support retest
        recent_low = df.iloc[i-20:i]['Low'].min()
        if abs(current['Low'] - recent_low) < 50 and current['Close'] > current['Low'] + body_size * 0.5:
            strength += 1
        
        # Impulse jeśli spełnia min 4 kryteria
        if strength >= 4:
            impulses.append(i)
    
    return impulses


def find_hierarchical_lines(df, base_slope, base_intercept, used_points, extrema_low, extrema_high, impulses_idx, 
                            num_below=4, num_above=4, tolerance=50):
    """
    Znajduje hierarchiczne linie równoległe poniżej (wsparcia S2, S3...) i powyżej (opory R2, R3...).
    
    Zwraca:
        (supports_below, resistances_above)
        gdzie każda linia to dict z: slope, intercept, touches, offset, score, level
    """
    supports_below = []
    resistances_above = []
    
    # Zbierz wszystkie punkty (minima + impulsy)
    all_low_points = []
    for idx in extrema_low:
        all_low_points.append({
            'index': int(df.iloc[idx]['index']),
            'price': float(df.iloc[idx]['Low'])
        })
    for idx in impulses_idx:
        all_low_points.append({
            'index': int(df.iloc[idx]['index']),
            'price': float(df.iloc[idx]['Low'])
        })
    
    # Zbierz wszystkie punkty (maxima)
    all_high_points = []
    for idx in extrema_high:
        all_high_points.append({
            'index': int(df.iloc[idx]['index']),
            'price': float(df.iloc[idx]['High'])
        })
    
    # Funkcja do znajdowania linii poniżej głównej (wsparcia)
    def find_support_level(points, excluded_points, level):
        """Znajduje kolejny poziom wsparcia poniżej głównej linii"""
        best_intercept = None
        best_score = 0
        best_touches = []
        best_offset = 0
        
        # Dla każdego punktu sprawdź czy może być bazą dla nowej linii
        for p in points:
            # Sprawdź czy punkt nie jest już użyty w poprzednich poziomach
            if any(abs(p['index'] - ep['index']) < 2 and abs(p['price'] - ep['price']) < 10 
                   for ep in excluded_points):
                continue
            
            # Oblicz intercept dla linii równoległej przechodzącej przez ten punkt
            intercept = p['price'] - base_slope * p['index']
            offset = intercept - base_intercept
            
            # Offset musi być ujemny (linia poniżej głównej)
            if offset >= 0:
                continue
            
            # Policz ile punktów pasuje do tej linii
            score = 0
            touches = []
            for pt in points:
                expected_price = base_slope * pt['index'] + intercept
                dist = abs(pt['price'] - expected_price)
                
                if dist <= tolerance:
                    score += 1
                    touches.append({'index': pt['index'], 'price': pt['price']})
            
            if score > best_score:
                best_score = score
                best_intercept = intercept
                best_touches = touches
                best_offset = offset
        
        if best_score >= 2:  # Minimum 2 punkty
            return {
                'slope': base_slope,
                'intercept': best_intercept,
                'touches': best_touches,
                'offset': best_offset,
                'score': best_score,
                'level': level
            }
        return None
    
    # Funkcja do znajdowania linii powyżej głównej (opory)
    def find_resistance_level(points, excluded_points, level):
        """Znajduje kolejny poziom oporu powyżej głównej linii"""
        best_intercept = None
        best_score = 0
        best_touches = []
        best_offset = 0
        
        for p in points:
            # Sprawdź czy punkt nie jest już użyty
            if any(abs(p['index'] - ep['index']) < 2 and abs(p['price'] - ep['price']) < 10 
                   for ep in excluded_points):
                continue
            
            intercept = p['price'] - base_slope * p['index']
            offset = intercept - base_intercept
            
            # Offset musi być dodatni (linia powyżej głównej)
            if offset <= 0:
                continue
            
            score = 0
            touches = []
            for pt in points:
                expected_price = base_slope * pt['index'] + intercept
                dist = abs(pt['price'] - expected_price)
                
                if dist <= tolerance:
                    score += 1
                    touches.append({'index': pt['index'], 'price': pt['price']})
            
            if score > best_score:
                best_score = score
                best_intercept = intercept
                best_touches = touches
                best_offset = offset
        
        if best_score >= 2:
            return {
                'slope': base_slope,
                'intercept': best_intercept,
                'touches': best_touches,
                'offset': best_offset,
                'score': best_score,
                'level': level
            }
        return None
    
    # Znajdź linie wsparcia poniżej
    excluded = list(used_points)
    for level in range(2, num_below + 2):
        support = find_support_level(all_low_points, excluded, level)
        if support:
            supports_below.append(support)
            excluded.extend(support['touches'])
        else:
            break
    
    # Znajdź linie oporu powyżej
    excluded = list(used_points)
    for level in range(2, num_above + 2):
        resistance = find_resistance_level(all_high_points, excluded, level)
        if resistance:
            resistances_above.append(resistance)
            excluded.extend(resistance['touches'])
        else:
            break
    
    return supports_below, resistances_above


def find_support_lines(lookback_df):
    """
    Znajduje główną linię support/resistance oraz hierarchiczne linie równoległe.
    
    Zwraca listę wykrytych linii (może być 0, 1 lub 2 - wznosząca i/lub opadająca).
    Każda linia to dict z kluczami:
        - type: 'ascending' lub 'descending'
        - slope, intercept: parametry linii
        - score: liczba punktów dopasowanych
        - used_minima: lista punktów użytych do głównej linii
        - local_maxima, all_minima, impulses: punkty dla wykresu
        - hierarchical_supports: linie wsparcia poniżej (S2, S3, ...)
        - hierarchical_resistances: linie oporu powyżej (R2, R3, ...)
    """
    # Dodaj kolumnę index dla lookback_df
    lookback_df = lookback_df.copy()
    lookback_df['index'] = range(len(lookback_df))
    
    # 1. Wykryj impulsy
    impulses_idx = detect_impulses(lookback_df)
    
    # 2. Znajdź lokalne minima/maxima
    minima_idx = argrelextrema(lookback_df['Low'].values, np.less, order=5)[0]
    maxima_idx = argrelextrema(lookback_df['High'].values, np.greater, order=5)[0]
    
    # 3. Zbuduj listę punktów (impulses + minima)
    points = []
    for imp_idx in impulses_idx:
        points.append({
            'index': lookback_df.iloc[imp_idx]['index'],
            'price': lookback_df.iloc[imp_idx]['Low'],
            'type': 'impulse'
        })
    
    for min_idx in minima_idx:
        points.append({
            'index': lookback_df.iloc[min_idx]['index'],
            'price': lookback_df.iloc[min_idx]['Low'],
            'type': 'minimum'
        })
    
    # Zbierz punkty dla wizualizacji
    all_minima = [{'index': int(lookback_df.iloc[i]['index']), 
                   'price': float(lookback_df.iloc[i]['Low'])} for i in minima_idx]
    local_maxima = [{'index': int(lookback_df.iloc[i]['index']), 
                     'price': float(lookback_df.iloc[i]['High'])} for i in maxima_idx]
    impulse_points = [{'index': int(lookback_df.iloc[i]['index']), 
                       'price': float(lookback_df.iloc[i]['Low'])} for i in impulses_idx]
    
    if len(points) < 2:
        # Fallback: użyj dwóch najniższych punktów
        sorted_idx = lookback_df.nsmallest(2, 'Low').index.tolist()
        points = [{'index': int(lookback_df.loc[i, 'index']), 
                   'price': float(lookback_df.loc[i, 'Low']),
                   'type': 'fallback'} for i in sorted_idx]
    
    # 4. Znajdź najlepsze pary linii (wznosząca + opadająca)
    def calculate_line_score(slope, points, tolerance=LINE_TOLERANCE):
        """Oblicza score dla linii o danym slope"""
        best_intercept = None
        best_score = 0
        best_used = []
        
        for p_start in points:
            intercept = p_start['price'] - slope * p_start['index']
            
            score = 0
            used = []
            for p in points:
                expected_price = slope * p['index'] + intercept
                dist = abs(p['price'] - expected_price)
                
                if dist <= tolerance:
                    weight = 2 if p['type'] == 'impulse' else 1
                    score += weight
                    used.append({'index': int(p['index']), 'price': float(p['price'])})
            
            if score > best_score:
                best_score = score
                best_intercept = intercept
                best_used = used
        
        return {
            'slope': slope,
            'intercept': best_intercept,
            'score': best_score,
            'used': best_used
        }
    
    # Zbierz wszystkie unikalne wartości |slope|
    unique_slopes = set()
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            p1, p2 = points[i], points[j]
            if p2['index'] == p1['index']:
                continue
            
            slope = (p2['price'] - p1['price']) / (p2['index'] - p1['index'])
            abs_slope = abs(slope)
            
            if abs_slope >= MIN_SLOPE:
                unique_slopes.add(abs_slope)
    
    # Dla każdego |slope| oblicz combined_score
    best_pair = None
    best_combined_score = 0
    
    for abs_slope in unique_slopes:
        asc_result = calculate_line_score(abs_slope, points)
        desc_result = calculate_line_score(-abs_slope, points)
        combined_score = asc_result['score'] + desc_result['score']
        
        if combined_score > best_combined_score:
            best_combined_score = combined_score
            best_pair = {
                'ascending': asc_result,
                'descending': desc_result,
                'combined_score': combined_score
            }
    
    # Przygotuj wyniki
    if not best_pair:
        return []
    
    best_ascending = best_pair['ascending'] if best_pair['ascending']['score'] > 0 else {'score': 0}
    best_descending = best_pair['descending'] if best_pair['descending']['score'] > 0 else {'score': 0}
    
    detected_lines = []
    
    # Dodaj linię wznosząc
    if best_ascending['score'] > 0:
        # Znajdź hierarchiczne linie
        supp_below, res_above = find_hierarchical_lines(
            lookback_df, 
            best_ascending['slope'], 
            best_ascending['intercept'], 
            best_ascending['used'],
            minima_idx, 
            maxima_idx, 
            impulses_idx,
            num_below=HIERARCHICAL_LEVELS_BELOW,
            num_above=HIERARCHICAL_LEVELS_ABOVE,
            tolerance=HIERARCHICAL_TOLERANCE
        )
        
        detected_lines.append({
            'type': 'ascending',
            'slope': best_ascending['slope'],
            'intercept': best_ascending['intercept'],
            'score': best_ascending['score'],
            'used_minima': best_ascending['used'],
            'local_maxima': local_maxima,
            'all_minima': all_minima,
            'impulses': impulse_points,
            'hierarchical_supports': supp_below,
            'hierarchical_resistances': res_above
        })
    
    # Dodaj linię opadającą
    if best_descending['score'] > 0:
        supp_below, res_above = find_hierarchical_lines(
            lookback_df,
            best_descending['slope'],
            best_descending['intercept'],
            best_descending['used'],
            minima_idx,
            maxima_idx,
            impulses_idx,
            num_below=HIERARCHICAL_LEVELS_BELOW,
            num_above=HIERARCHICAL_LEVELS_ABOVE,
            tolerance=HIERARCHICAL_TOLERANCE
        )
        
        detected_lines.append({
            'type': 'descending',
            'slope': best_descending['slope'],
            'intercept': best_descending['intercept'],
            'score': best_descending['score'],
            'used_minima': best_descending['used'],
            'local_maxima': local_maxima,
            'all_minima': all_minima,
            'impulses': impulse_points,
            'hierarchical_supports': supp_below,
            'hierarchical_resistances': res_above
        })
    
    return detected_lines


def plot_chart(df_plot, detected_lines, output_filepath, lookback_start_dt, lookback_end_dt):
    """
    Generuje wykres świeczkowy z liniami wsparcia/oporu.
    """
    # Przygotuj dane dla mplfinance
    df_plot = df_plot.set_index('DateTime')
    
    if len(df_plot) == 0:
        return
    
    apds = []
    scatter_data = []  # Lista punktów do wyświetlenia
    
    # Dla każdej wykrytej linii
    for line_idx, line_info in enumerate(detected_lines):
        slope = line_info['slope']
        intercept = line_info['intercept']
        line_type = line_info['type']
        
        # Oblicz wartości linii głównej
        support_values = []
        for idx_val in df_plot.index:
            # Offset względem lookback_start_dt
            offset = len(df_plot[df_plot.index < idx_val])
            support_price = intercept + slope * offset
            support_values.append(support_price)
        
        col_prefix = f'Line{line_idx}'
        df_plot[f'{col_prefix}_Support'] = support_values
        
        # Kolor: zielony dla wznoszącej, czerwony dla opadającej
        main_line_color = 'green' if slope > 0 else 'red'
        main_line_label = 'S1 Main' if slope > 0 else 'R1 Main'
        
        apds.append(mpf.make_addplot(
            df_plot[f'{col_prefix}_Support'],
            color=main_line_color,
            width=1,
            linestyle='-',
            alpha=0.6
        ))
        
        # Linie hierarchiczne wsparcia (S2, S3, ...)
        for supp in line_info.get('hierarchical_supports', []):
            supp_values = []
            for idx_val in df_plot.index:
                offset = len(df_plot[df_plot.index < idx_val])
                supp_price = supp['intercept'] + supp['slope'] * offset
                supp_values.append(supp_price)
            
            df_plot[f"{col_prefix}_S{supp['level']}"] = supp_values
            apds.append(mpf.make_addplot(
                df_plot[f"{col_prefix}_S{supp['level']}"],
                color=main_line_color,
                width=1,
                linestyle='--',
                alpha=0.6
            ))
        
        # Linie hierarchiczne oporu (R2, R3, ...)
        for res in line_info.get('hierarchical_resistances', []):
            res_values = []
            for idx_val in df_plot.index:
                offset = len(df_plot[df_plot.index < idx_val])
                res_price = res['intercept'] + res['slope'] * offset
                res_values.append(res_price)
            
            df_plot[f"{col_prefix}_R{res['level']}"] = res_values
            apds.append(mpf.make_addplot(
                df_plot[f"{col_prefix}_R{res['level']}"],
                color=main_line_color,
                width=1,
                linestyle='--',
                alpha=0.6
            ))
    
    # Wyświetl impulsy, local min/max jeśli SHOW_IMPULSES = True
    if SHOW_IMPULSES and detected_lines:
        # Zbierz wszystkie unikalne punkty ze wszystkich linii
        all_impulses = {}
        all_minima = {}
        all_maxima = {}
        
        for line_info in detected_lines:
            # Impulsy
            for imp in line_info.get('impulses', []):
                idx = imp['index']
                all_impulses[idx] = imp['price']
            
            # Local minima
            for minimum in line_info.get('all_minima', []):
                idx = minimum['index']
                all_minima[idx] = minimum['price']
            
            # Local maxima
            for maximum in line_info.get('local_maxima', []):
                idx = maximum['index']
                all_maxima[idx] = maximum['price']
        
        # Utwórz serie dla każdego typu punktu
        impulse_series = pd.Series(index=df_plot.index, dtype=float)
        minima_series = pd.Series(index=df_plot.index, dtype=float)
        maxima_series = pd.Series(index=df_plot.index, dtype=float)
        
        for i, dt in enumerate(df_plot.index):
            if i in all_impulses:
                impulse_series.iloc[i] = all_impulses[i]
            if i in all_minima:
                minima_series.iloc[i] = all_minima[i]
            if i in all_maxima:
                maxima_series.iloc[i] = all_maxima[i]
        
        # Dodaj do wykresu
        if not impulse_series.isna().all():
            apds.append(mpf.make_addplot(
                impulse_series,
                type='scatter',
                markersize=80,
                marker='^',
                color='blue',
                alpha=0.7
            ))
        
        if not minima_series.isna().all():
            apds.append(mpf.make_addplot(
                minima_series,
                type='scatter',
                markersize=60,
                marker='v',
                color='orange',
                alpha=0.5
            ))
        
        if not maxima_series.isna().all():
            apds.append(mpf.make_addplot(
                maxima_series,
                type='scatter',
                markersize=60,
                marker='v',
                color='purple',
                alpha=0.5
            ))
    
    # Generuj wykres
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    
    # Konfiguracja siatki - pionowe linie o pełnych godzinach (00:00)
    import matplotlib.dates as mdates
    
    # Ustaw styl matplotlib przed generowaniem wykresu
    plt.rcParams['figure.subplot.left'] = 0.05
    plt.rcParams['figure.subplot.right'] = 0.95
    plt.rcParams['figure.subplot.top'] = 0.95
    plt.rcParams['figure.subplot.bottom'] = 0.05
    
    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        style='charles',
        addplot=apds if apds else None,
        volume=False,
        figsize=(16, 10),
        tight_layout=False,
        returnfig=True
    )
    
    # Wyłącz domyślną siatkę i dodaj pionowe linie tylko o 00:00
    ax = axes[0]
    ax.grid(False)  # Wyłącz wszystkie linie siatki
    
    # Ustaw marginesy na minumum
    ax.margins(x=0.05, y=0.05)
    
    # Znajdź daty o godzinie 00:00 w zakresie wykresu
    dates = df_plot.index
    midnight_indices = []
    midnight_labels = []
    for i, dt in enumerate(dates):
        if dt.hour == 0 and dt.minute == 0:
            midnight_indices.append(i)
            midnight_labels.append(dt.strftime('%Y-%m-%d'))
    
    # Dodaj pionowe linie o północy
    for idx in midnight_indices:
        ax.axvline(x=idx, color='gray', linestyle='-', linewidth=0.8, alpha=0.5)
    
    # Ustaw podpisy osi X dokładnie w miejscach linii pionowych
    ax.set_xticks(midnight_indices)
    ax.set_xticklabels(midnight_labels, rotation=0, ha='center')
    
    if DUMP_IMAGES:
        fig.savefig(output_filepath, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)


def check_crossings(last_candle, detected_lines, lookback_df_for_lines):
    """
    Sprawdza czy ostatnia świeczka przecina któreś linie.
    Zwraca listę przeciętych linii według konwencji:
    - Ascending: AS1 (main), AS2-AS5 (supports below), AR2-AR5 (resistances above)
    - Descending: DR1 (main), DS2-DS5 (supports above), DR2-DR5 (resistances below)
    """
    last_candle_low = last_candle['Low']
    last_candle_high = last_candle['High']
    last_candle_direction = 'UP' if last_candle['Close'] > last_candle['Open'] else 'DOWN'
    last_candle_idx = len(lookback_df_for_lines)  # Index ostatniej świeczki (299 dla 300 świeczek)
    
    crossed_lines = []
    offsets = {}  # Przechowuj offset dla każdej linii
    
    for line_info in detected_lines:
        slope = line_info['slope']
        intercept = line_info['intercept']
        line_type = line_info['type']
        
        line_value = slope * last_candle_idx + intercept
        
        # Oblicz offset (odległość od linii do last_candle)
        # Użyj mid-point świeczki dla offset
        last_candle_mid = (last_candle_low + last_candle_high) / 2
        offset = last_candle_mid - line_value
        
        # Zapisz offset dla głównych linii (zawsze)
        if line_type == 'ascending':
            offsets["AS1"] = offset
        else:
            offsets["DR1"] = offset
        
        # Prefix kierunku: A=ascending, D=descending
        direction_prefix = "A" if line_type == 'ascending' else "D"
        
        # Sprawdź linię główną - dla ascending AS1, dla descending DR1
        if last_candle_low <= line_value <= last_candle_high:
            if line_type == 'ascending':
                crossed_lines.append("AS1")
            else:
                crossed_lines.append("DR1")
        
        # Sprawdź linie hierarchiczne wsparcia
        # Ascending: wsparcia poniżej (AS2-AS5), offset < 0
        # Descending: wsparcia powyżej (DS2-DS5), offset > 0
        for supp in line_info.get('hierarchical_supports', []):
            supp_value = line_value + supp['offset']
            if last_candle_low <= supp_value <= last_candle_high:
                if line_type == 'ascending':
                    crossed_lines.append(f"AS{supp['level']}")
                else:
                    crossed_lines.append(f"DS{supp['level']}")
        
        # Sprawdź linie hierarchiczne oporu
        # Ascending: opory powyżej (AR2-AR5), offset > 0
        # Descending: opory poniżej (DR2-DR5), offset < 0
        for res in line_info.get('hierarchical_resistances', []):
            res_value = line_value + res['offset']
            if last_candle_low <= res_value <= last_candle_high:
                if line_type == 'ascending':
                    crossed_lines.append(f"AR{res['level']}")
                else:
                    crossed_lines.append(f"DR{res['level']}")

    # jeżeli były jakieś przecięcia...
    if crossed_lines:
        crossed_lines = ["CROSSED " + last_candle_direction] + crossed_lines
    
    # Dodaj offset dla AS1/DR1 zawsze (niezależnie od crossings)
    result = crossed_lines if crossed_lines else []
    if "AS1" in offsets:
        result.append(f"AS1_OFFSET:{offsets['AS1']:.1f}")
    if "DR1" in offsets:
        result.append(f"DR1_OFFSET:{offsets['DR1']:.1f}")
    
    return result


def process_single_file(csv_filepath, output_dir='support_charts'):
    """
    Przetwarza pojedynczy plik CSV:
    1. Wczytuje dane
    2. Wyznacza linie wsparcia/oporu
    3. Generuje wykres
    4. Sprawdza przecięcia ostatniej świeczki
    
    Zwraca: string z wynikiem (np. "LONG S2 | SHORT" lub "NONE")
    """
    # Wczytaj dane
    df = load_csv_data(csv_filepath)
    
    # Przygotuj okno lookback
    total_candles = len(df)
    start_idx = max(0, total_candles - LOOKBACK_CANDLES)
    lookback_df_full = df.iloc[start_idx:].copy()
    
    # Oblicz linie na podstawie pierwszych N-1 świeczek (pomijamy ostatnią)
    lookback_df_for_lines = lookback_df_full.iloc[:-1].copy()
    
    # Wykryj linie
    detected_lines = find_support_lines(lookback_df_for_lines)
    
    if not detected_lines:
        return "NONE"
    
    # Sprawdź przecięcia ostatniej świeczki
    last_candle = lookback_df_full.iloc[-1]
    crossed_lines = check_crossings(last_candle, detected_lines, lookback_df_for_lines)
    
    # Wygeneruj wykres tylko gdy DUMP_IMAGES=True
    if DUMP_IMAGES:
        last_candle_dt = df.iloc[-1]['DateTime']
        hour_min = last_candle_dt.strftime('%H-%M')
        date_str = last_candle_dt.strftime('%Y-%m-%d')
        
        chart_filename = f"support_{date_str}_{hour_min}.png"
        chart_filepath = os.path.join(output_dir, chart_filename)
        
        lookback_start_dt = df.iloc[start_idx]['DateTime']
        lookback_end_dt = df.iloc[-1]['DateTime']
        
        plot_chart(lookback_df_full.copy(), detected_lines, chart_filepath, 
                   lookback_start_dt, lookback_end_dt)
    
    if crossed_lines:
        return " | ".join(crossed_lines)
    else:
        return "NONE"


def process_all_files(input_dir, output_file='support_lines_results.txt', output_charts_dir='support_charts'):
    """
    Przetwarza wszystkie pliki CSV w katalogu.
    Zapisuje wyniki do pliku support_lines_results.txt.
    """
    all_csv_files = sorted(Path(input_dir).glob('*.csv'))
    
    # Filtruj pliki - pomijaj te z '_mod' przed rozszerzeniem
    csv_files = [f for f in all_csv_files if not f.stem.endswith('_mod')]
    
    if not csv_files:
        print(f"Nie znaleziono plików CSV w: {input_dir}")
        return
    
    print(f"Znaleziono {len(csv_files)} plików CSV (pominięto {len(all_csv_files) - len(csv_files)} plików *_mod.csv)")
    print("Rozpoczynam przetwarzanie...")
    
    results = []
    
    for idx, csv_file in enumerate(csv_files, 1):
        print(f"[{idx}/{len(csv_files)}] Przetwarzam: {csv_file.name}")
        
        try:
            result = process_single_file(str(csv_file), output_charts_dir)
            results.append(f"{csv_file.name}: {result}")
        except Exception as e:
            print(f"  BŁĄD: {e}")
            results.append(f"{csv_file.name}: ERROR - {str(e)}")
    
    # Zapisz wyniki
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    
    print(f"\n✓ Gotowe! Wyniki zapisano w: {output_file}")
    print(f"Przetworzono {len(csv_files)} plików")


def main():
    """Główna funkcja - uruchamia przetwarzanie"""
    if len(sys.argv) > 1 and sys.argv[1] != '--help':
        # Tryb pojedynczego pliku
        csv_file = sys.argv[1]
        if not os.path.exists(csv_file):
            print(f"Błąd: Plik {csv_file} nie istnieje!")
            sys.exit(1)
        
        # Utwórz katalog charts/ w tym samym miejscu co plik CSV
        csv_path = Path(csv_file)
        output_dir = csv_path.parent / 'charts'
        output_dir.mkdir(exist_ok=True)
        
        result = process_single_file(csv_file, str(output_dir))
        print(f"Wynik: {result}")
        print(f"Wykres zapisano w: {output_dir}")
    else:
        # Tryb batch - przetwarzanie wszystkich plików
        if len(sys.argv) > 1 and sys.argv[1] == '--help':
            print(__doc__)
            sys.exit(0)
        
        # Domyślna ścieżka do plików CSV
        script_dir = Path(__file__).parent.parent
        input_dir = script_dir / 'tester-third' / 'mt4_test_results' / 'm15_candles'
        
        if not input_dir.exists():
            print(f"Błąd: Katalog {input_dir} nie istnieje!")
            print("Użycie: python magic_lines.py <plik.csv>")
            sys.exit(1)
        
        process_all_files(str(input_dir))


if __name__ == '__main__':
    main()
