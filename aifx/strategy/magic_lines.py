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



"""
TODO 

fix min/max - powinno lepiej wygladać
przyspieszenie: generuj tylko najbliższe linie względem ostatniej świeczki
czy linie rosnące powinny mieć wyższy score dla maxmia niż dla minima (i odwrotnie dla linii opadającej)?
brać pod uwagę "pierwszą rosnącą po minimum"
buy tylko na zielonych
bugi - czasem złe min/max
lepszy opis crossingu + dodać offsety

"""


import math
import sys
import os
import pandas as pd
import numpy as np
import mplfinance as mpf

from pathlib import Path
from scipy.signal import argrelextrema
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ===== LOGGING =====
LOG_FILE = '/home/ubuntu/repo/magic_lines.log'
log_file_handle = None

def log(message):
    """Wyświetla wiadomość na konsoli i zapisuje do pliku log"""
    formatted_message = f"{message}"
    print(formatted_message)
    if log_file_handle:
        log_file_handle.write(formatted_message + '\n')
        log_file_handle.flush()

# ===== KONFIGURACJA =====
LOOKBACK_CANDLES = 300  # Liczba świeczek do analizy
MIN_SLOPE = 0.3  # Minimalny slope linii
MAX_SLOPE = 5.0  # Maksymalny slope linii
MAX_HIERARCHICAL_LEVELS = 4  # maksymalna liczba linii wsparcia / oporu poniżej głównej
MIN_HIERARCHICAL_OFFSET = 20  # Minimalny offset między liniami hierarchicznymi (punkty)
MINMAX_ORDER = 7  # liczba świeczek do analizy lokalnych min/max
HIERARCHICAL_TOLERANCE = 10  # Tolerancja dla linii hierarchicznych (punkty)
LINE_TOLERANCE = 5  # Tolerancja dla dopasowania punktów do linii głównej
SHOW_IMPULSES = True  # Czy pokazywać impulsy na wykresie
FILTER_MINMAX_IMPULSES = True  # Czy filtrować impulsy min/max
DUMP_IMAGES = True  # Czy zapisywać wykresy do plików

# ===== score impulsow =====
SHADOW_IMPULSE_STRENGTH = 0.5  # siła impulsu dla cieni lokalnych min/max
BODY_IMPULSE_STRENGTH = 1.0    # siła impulsu dla korpusów lokalnych min/max

# ===== KLASY DANYCH =====

class impulse_point:
    def __init__(self, 
                 index, # indeks świeczki
                 price, # cena impulsu
                 strength=1.0, # siła impulsu
                 type='impulse' # typ impulsu (np. 'gap', 'minimum', 'maximum')
                 ):
        self.index = index 
        self.price = price 
        self.strength = strength 
        self.type = type 

class magic_line:
    def __init__(self, 
                 slope,  # nachylenie linii
                 intercept, # wartość y przy x=0
                 offset,  # offset względem poprzedniej linii
                 used_points, # lista punktów użytych do wyznaczenia linii
                 score,  # liczba punktów dopasowanych do linii
                 level  # poziom hierarchii linii
                 ):
        self.slope = slope
        self.intercept = intercept 
        self.offset = offset
        self.score = score
        self.used_points = used_points 
        self.level = level

# ===== FUNKCJE POMOCNICZE =====

def load_csv_data(filepath):
    """Wczytuje dane CSV w formacie mbank (Time;Open;High;Low;Close)"""
    # UWAGA: pomiń dodatkowe kolumny, jeśli istnieją np: ";decision-here"
    df = pd.read_csv(filepath, sep=';', parse_dates=['Time'], usecols=[0, 1, 2, 3, 4], on_bad_lines='warn')
    df.rename(columns={'Time': 'DateTime'}, inplace=True)
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    
    # Konwertuj ceny z string na float (zastąp przecinki kropkami jeśli są)
    for col in ['Open', 'High', 'Low', 'Close']:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '.').astype(float)
    
    # Dodaj kolumnę Volume (wymagane przez mplfinance nawet gdy volume=False)
    df['Volume'] = 0
    
    return df

def detect_impulses(df) -> list[impulse_point]:
    """
    Wykrywa impulsy rynkowe na podstawie różnych kryteriów.
    Zwraca listę impulse_point.
    """
    impulses = []

    # specjalna lista do min/max - będzie przefiltrowana później
    impulses_min_max = []
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]        
        
        # Price gap (luka cenowa)
        gap_up = current['Low'] > prev['High']
        gap_size = math.fabs(current['Open'] - prev['Close'])
        if gap_size > 20: # luka większa niż 20 punktów
            # dodaj 2 punkty na krańcach luki
            impulse_prev = impulse_point(i-1, prev['High'] if gap_up else prev['Low'], strength=1, type='gap')
            impulses.append(impulse_prev)

            impulse_curr = impulse_point(i, current['Low'] if gap_up else current['High'], strength=1, type='gap')
            impulses.append(impulse_curr)

    # Lokalna minima/maxima - korpusy świec
    body_low = []
    body_high = []
    for i in range(0, len(df)-1):
        body_low.append(min(df['Open'].values[i], df['Close'].values[i]))
        body_high.append(max(df['Open'].values[i], df['Close'].values[i]))
            
    minima_idx = argrelextrema(
        np.array(body_low), 
        np.less_equal, 
        order=MINMAX_ORDER)[0]
    
    # Odfiltruj ciągi min - zostaw tylko pierwszy punkt z ciągu równych wartości
    filtered_minima = []
    for idx in minima_idx:
        if idx == 0 or body_low[idx] < body_low[idx - 1]:
            filtered_minima.append(idx)
            # print("Znaleziono minimum na idx:", idx, "cena:", body_low[idx])

    for idx in filtered_minima:
        impulses_min_max.append(impulse_point(idx, body_low[idx], 
                                      strength=BODY_IMPULSE_STRENGTH, type='minimum'))

    maxima_idx = argrelextrema(
        np.array(body_high), 
        np.greater_equal, 
        order=MINMAX_ORDER)[0]
    
    # Odfiltruj ciągi max - zostaw tylko pierwszy punkt z ciągu równych wartości
    filtered_maxima = []
    for idx in maxima_idx:
        if idx == 0 or body_high[idx] > body_high[idx - 1]:
            filtered_maxima.append(idx)
    
    for idx in filtered_maxima:
        impulses_min_max.append(impulse_point(idx, body_high[idx], 
                                      strength=BODY_IMPULSE_STRENGTH, type='maximum'))
        
    # Sortuj impulsy po indeksie świeczki
    impulses_min_max.sort(key=lambda p: (p.index, p.type, p.price))

    # Filtruj impulsy - zostaw tylko te otoczone min/max
    # Dodaj pierwszy element
    filtered_impulses = [impulses_min_max[0]]
    
    # Dodaj tylko impulsy z pattern min-max-min lub max-min-max
    i = 1
    while i < len(impulses_min_max) - 1:
        prev_p = filtered_impulses[-1] # ostatni element
        p = impulses_min_max[i]

        if prev_p.type != p.type:
            filtered_impulses.append(p)
        elif prev_p.type == 'minimum':
            # dwa minima pod rząd - zostaw to z niższą ceną
            filtered_impulses[-1] = p if p.price < prev_p.price else prev_p
        elif prev_p.type == 'maximum':
            # dwa maxima pod rząd - zostaw to z wyższą ceną
            filtered_impulses[-1] = p if p.price > prev_p.price else prev_p                
        i += 1
    
    # Odrzuć min/max na krawędziach danych
    if FILTER_MINMAX_IMPULSES:
        for p in impulses_min_max:
            if p.index > (MINMAX_ORDER / 2) and p.index < len(df) - (MINMAX_ORDER / 2):
                filtered_impulses.append(p)
    
    return impulses + filtered_impulses

# Funkcja do znajdowania linii równoległych
def find_parallel_level(
        points : list[impulse_point], 
        prev_line : magic_line, 
        search_up : bool) \
            -> magic_line:
    """
    Znajduje kolejną linie równoległą (wsparcia lub oporu).
    
    Args:
        points: lista punktów do analizy
        prev_line: poprzednia linia (do wykluczenia punktów z obszau)
        search_up: bool, czy szukamy powyżej (True) czy poniżej (False) poprzedniej linii
    """

    best_intercept = None
    best_score = 0
    best_touches = []
    best_offset = 0
    base_slope = 0
    
    # Dla każdego punktu sprawdź czy może być bazą dla nowej linii
    for p in points:
        # Sprawdź czy punkt leży w obszarze wykluczenia na podstawie prev_line
        # oraz search_dir
        if prev_line:
            expected_price = prev_line.slope * p.index + prev_line.intercept
            if not search_up and p.price >= expected_price:
                continue
            if search_up and p.price <= expected_price:
                continue

        base_slope = prev_line.slope
        
        # Oblicz intercept dla linii równoległej przechodzącej przez ten punkt
        intercept = p.price - prev_line.slope * p.index
        offset = intercept - prev_line.intercept
                
        # Sprawdź czy offset ma odpowiedni znak
        # search_up=False (poniżej): offset musi być ujemny (linia niżej)
        # search_up=True (powyżej): offset musi być dodatni (linia wyżej)
        if not search_up and offset >= 0:
            continue
        if search_up and offset <= 0:
            continue

        # Sprawdź czy offset jest wystarczająco duży 
        # (minimalna odległość od poprzedniej linii)
        if abs(offset) < MIN_HIERARCHICAL_OFFSET:
            continue
        
        # Policz ile punktów pasuje do tej linii
        score = 0
        touches = []
        for pt in points:
            expected_price = base_slope * pt.index + intercept
            dist = abs(pt.price - expected_price)
            
            if dist <= HIERARCHICAL_TOLERANCE:
                score += pt.strength
                touches.append(pt)
        
        if score > best_score:
            best_score = score
            best_intercept = intercept
            best_touches = touches
            best_offset = offset
    
    if best_score >= 2:  # Minimum 2 punkty
        return magic_line(
            slope=base_slope,
            intercept=best_intercept,
            offset=best_offset,
            used_points=best_touches,
            score=best_score,
            level=prev_line.level + 1
        )
    
    # No parallel line found - return None
    return None

def find_hierarchical_lines(base_line : magic_line,
                            points : list[impulse_point], 
                            max_num_lines=4, 
                            tolerance=50) \
                                -> tuple[list[magic_line], list[magic_line]]:
    """
    Znajduje hierarchiczne linie równoległe poniżej i powyżej bazowej linii.

    """

    lines_below = []
    lines_above = []

    for search_up in [True, False]:
        prev_line = base_line
        for i in range(max_num_lines):
            parallel_line = find_parallel_level(points, prev_line, search_up)
            if parallel_line:
                if search_up:
                    lines_above.append(parallel_line)
                else:
                    lines_below.append(parallel_line)
                prev_line = parallel_line
            else:
                break
    
    return lines_below, lines_above

def calculate_line_score(slope, points, tolerance=LINE_TOLERANCE) -> magic_line:
    """Oblicza score dla linii o danym slope"""
    best_intercept = None
    best_score = 0
    best_used = []
    
    # Dla każdego punktu oblicz intercept i policz score
    for p_start in points:
        intercept = p_start.price - slope * p_start.index
        
        score = 0
        used = []
        # Sprawdź ile punktów pasuje do tej linii
        for p in points:
            expected_price = slope * p.index + intercept
            dist = abs(p.price - expected_price)
            if dist <= tolerance:
                score += p.strength
                used.append(p)
        
        # Zaktualizuj najlepszy wynik
        if score > best_score:
            best_score = score
            best_intercept = intercept
            best_used = used
    
    return magic_line(
        slope=slope,
        intercept=best_intercept,
        offset=0,  # główna linia nie ma offsetu
        score=best_score,
        used_points=best_used,
        level=1 # główna linia
    )

def find_support_lines(lookback_df) -> tuple[list[magic_line], list[impulse_point]]:
    """
    Znajduje główną linię support/resistance oraz hierarchiczne linie równoległe.    
    Zwraca listę wykrytych linii (od 0 do HIERARCHICAL_LEVELS - wznosząca i/lub opadająca).
    """
    # Dodaj kolumnę index dla lookback_df
    lookback_df = lookback_df.copy()
    lookback_df['index'] = range(len(lookback_df))
    
    # Wykryj impulsy
    points = detect_impulses(lookback_df)
    # print(f"  Wykryto {len(points)} punktów impulsów/min/max")
        
    if len(points) < 2:
        # Fallback: użyj dwóch najniższych punktów
        sorted_idx = lookback_df.nsmallest(2, 'Low').index.tolist()
        points = [impulse_point(int(lookback_df.loc[i, 'index']),
                                float(lookback_df.loc[i, 'Low']),
                                strength=1,
                                type='fallback') for i in sorted_idx]
    
    # Znajdź najlepsze pary linii (wznosząca + opadająca)    
    # Zbierz wszystkie unikalne wartości |slope|
    unique_slopes = set()
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            p1, p2 = points[i], points[j]
            if p2.index == p1.index:
                continue
            
            slope = (p2.price - p1.price) / (p2.index - p1.index)
            abs_slope = abs(slope)
            
            if abs_slope >= MIN_SLOPE and abs_slope <= MAX_SLOPE:
                unique_slopes.add(abs_slope)

    # filter very simialr slopes
    unique_slopes = sorted(unique_slopes)
    filtered_slopes = []
    prev_slope = None
    for s in unique_slopes:
        if prev_slope is None or abs(s - prev_slope) / prev_slope > 0.01:
            filtered_slopes.append(s)
            prev_slope = s
    unique_slopes = filtered_slopes

    # Dla każdego |slope| oblicz combined_score
    best_pair = None
    best_combined_score = 0
    
    for i, abs_slope in enumerate(unique_slopes):
        # print(f"Sprawdzam slope: {abs_slope:.4f} {i+1}/{len(unique_slopes)}     ", end='\r')
        asc_line = calculate_line_score(abs_slope, points)
        desc_line = calculate_line_score(-abs_slope, points)
        combined_score = asc_line.score + desc_line.score
        
        if combined_score > best_combined_score:
            best_combined_score = combined_score
            best_pair = {
                'ascending': asc_line,
                'descending': desc_line,
                'combined_score': combined_score
            }
    
    # Przygotuj wyniki
    if not best_pair:
        return []
    
    best_ascending = best_pair['ascending'] if best_pair['ascending'].score > 0 else magic_line(score=0)
    best_descending = best_pair['descending'] if best_pair['descending'].score > 0 else magic_line(score=0)
    
    detected_lines = []
    
    # Dodaj główną oraz hierarchiczne linie
    for main_line in [best_descending, best_ascending]:
        below, above = find_hierarchical_lines(
            main_line,
            points,
            max_num_lines=MAX_HIERARCHICAL_LEVELS,
            tolerance=HIERARCHICAL_TOLERANCE
        )
        
        detected_lines += [main_line]
        detected_lines += below
        detected_lines += above  

    return detected_lines, points


def plot_chart(df_plot, 
               points : list[impulse_point],
               detected_lines : list[magic_line], 
               output_filepath, lookback_start_dt, lookback_end_dt):
    """
    Generuje wykres świeczkowy z liniami wsparcia/oporu.
    """
    # Przygotuj dane dla mplfinance
    df_plot = df_plot.set_index('DateTime')
    
    if len(df_plot) == 0:
        return
    
    apds = []
    
    # Dla każdej wykrytej linii
    for line_idx, line_info in enumerate(detected_lines):
        slope = line_info.slope
        intercept = line_info.intercept
        level = line_info.level
        
        # Oblicz wartości linii głównej dla każdej świeczki
        values = []
        for idx_val in df_plot.index:
            # Offset względem lookback_start_dt
            offset = len(df_plot[df_plot.index < idx_val])
            price = intercept + slope * offset
            values.append(price)
        
        col_prefix = f'Line{line_idx}'
        df_plot[f'{col_prefix}_'] = values
        
        # Kolor: zielony dla wznoszącej, czerwony dla opadającej
        main_line_color = 'green' if slope > 0 else 'red'
        
        apds.append(mpf.make_addplot(
            df_plot[f'{col_prefix}_'],
            color=main_line_color,
            width=1,
            linestyle='-' if level == 1 else '--',
            alpha=0.6
        ))        
    
    # Wyświetl impulsy, local min/max jeśli SHOW_IMPULSES = True
    if SHOW_IMPULSES:
        # Zbierz wszystkie unikalne punkty ze wszystkich linii
        all_impulses = {}
        all_minima = {}
        all_maxima = {}

        for point in points:                     
            if point.type == 'gap':
                idx = point.index
                all_impulses[idx] = point.price
            elif point.type == 'minimum':
                idx = point.index
                all_minima[idx] = point.price
            elif point.type == 'maximum':
                idx = point.index
                all_maxima[idx] = point.price
        
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
                markersize=60,
                marker='x',
                color='blue',
                alpha=0.7
            ))
        
        if not minima_series.isna().all():
            apds.append(mpf.make_addplot(
                minima_series,
                type='scatter',
                markersize=60,
                marker='^',
                color='red',
                alpha=0.5
            ))
        
        if not maxima_series.isna().all():
            apds.append(mpf.make_addplot(
                maxima_series,
                type='scatter',
                markersize=60,
                marker='v',
                color='green',
                alpha=0.5
            ))
    
    # Generuj wykres
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    
    # Konfiguracja siatki - pionowe linie o pełnych godzinach (00:00)
    
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


def check_crossings(last_candle, detected_lines : list[magic_line], lookback_df_for_lines):
    """
    Sprawdza czy ostatnia świeczka przecina któreś linie.
    Zwraca listę przeciętych linii według konwencji:
    - Ascending: A0 (main), AS1-AS5 (supports below), AR1-AR5 (resistances above)
    - Descending: D0 (main), DS1-DS5 (supports above), DR1-DR5 (resistances below)
    """
    last_candle_low = last_candle['Low']
    last_candle_high = last_candle['High']
    last_candle_direction = 'UP' if last_candle['Close'] > last_candle['Open'] else 'DOWN'
    last_candle_idx = len(lookback_df_for_lines)  # Index ostatniej świeczki (299 dla 300 świeczek)
    
    crossed_lines = []
    offsets = {}  # Przechowuj offset dla każdej linii
    
    crossed = False
    crossed_id = ""
    for line_info in detected_lines:
        slope = line_info.slope
        intercept = line_info.intercept
        line_type = 'ascending' if slope > 0 else 'descending'        
        line_value = slope * last_candle_idx + intercept
        # offset do obecnie analizowanej linii
        line_offset = line_value - last_candle['Close']        
        level = line_info.level - 1

        line_id = "A" if line_type == 'ascending' else "D"
        if level == 0:
            line_id += "0"  # Główna linia
        else:
            if line_type == 'ascending':
                if line_info.offset > 0:
                    line_id += f"S{level}"
                else:
                    line_id += f"R{level}"
            else:
                if line_info.offset < 0:
                    line_id += f"R{level}"
                else:
                    line_id += f"S{level}"
        
        # Sprawdź linię - dla ascending AS1, dla descending DR1
        if last_candle_low <= line_value <= last_candle_high:
            crossed = True
            if crossed_id == "":
                crossed_id = line_id
            else: 
                crossed_id += " " + line_id

        crossed_lines.append([line_id, line_offset])

    # jeżeli były jakieś przecięcia...
    if crossed:
        crossed_lines = ["CROSSED " + crossed_id + " " + last_candle_direction] + crossed_lines    

    result = crossed_lines if crossed else []    
    return result

def process_single_file(csv_filepath, output_dir='charts'):
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
    
    lookback_df_for_lines = lookback_df_full.iloc[:].copy()
    
    # Wykryj linie
    detected_lines, points = find_support_lines(lookback_df_for_lines)
    
    if not detected_lines:
        return "NONE"
    
    # Sprawdź przecięcia ostatniej świeczki + policz offsety dla wszystkich linii
    last_candle = lookback_df_full.iloc[-1]
    base_price = float(last_candle['Close'])
    last_candle_low = float(last_candle['Low'])
    last_candle_high = float(last_candle['High'])
    last_candle_direction = 'UP' if last_candle['Close'] > last_candle['Open'] else 'DOWN'
    last_candle_idx = len(lookback_df_for_lines)

    crossed = False
    crossed_id = ""
    line_offsets = []
    for line_info in detected_lines:
        slope = line_info.slope
        intercept = line_info.intercept
        line_type = 'ascending' if slope > 0 else 'descending'
        line_value = slope * last_candle_idx + intercept
        line_offset = line_value - base_price
        level = line_info.level - 1

        line_id = "A" if line_type == 'ascending' else "D"
        if level == 0:
            line_id += "0"  # Główna linia
        else:
            if line_type == 'ascending':
                if line_info.offset > 0:
                    line_id += f"S{level}"
                else:
                    line_id += f"R{level}"
            else:
                if line_info.offset < 0:
                    line_id += f"R{level}"
                else:
                    line_id += f"S{level}"

        if last_candle_low <= line_value <= last_candle_high:
            crossed = True
            crossed_id = line_id if crossed_id == "" else (crossed_id + " " + line_id)

        line_offsets.append((line_id, line_offset))

    slope = detected_lines[0].slope
    
    # Wygeneruj wykres tylko gdy DUMP_IMAGES=True
    if DUMP_IMAGES:
        chart_filename = f"{Path(csv_filepath).stem}.png"
        chart_filepath = os.path.join(output_dir, chart_filename)
        
        lookback_start_dt = df.iloc[start_idx]['DateTime']
        lookback_end_dt = df.iloc[-1]['DateTime']
        
        plot_chart(lookback_df_full.copy(), points, detected_lines, chart_filepath, 
                   lookback_start_dt, lookback_end_dt)
    
    prefix = f"CROSSED {crossed_id} {last_candle_direction}" if crossed else "NONE"
    ret = prefix + " | "
    # offset z dokładnością do 2 miejsca po przecinku
    ret += " | ".join([f"{line_id}: {line_offset:.2f}" for (line_id, line_offset) in line_offsets])
    ret += " | SLOPE: {:.4f}".format(slope)
    ret += " | BASE: {:.2f}".format(base_price)
    return ret


def process_all_files(input_dir, output_file='support_lines_results.txt', output_charts_dir='charts'):
    """
    Przetwarza wszystkie pliki CSV w katalogu.
    Zapisuje wyniki do pliku support_lines_results.txt.
    """
    all_csv_files = sorted(Path(input_dir).glob('*.csv'))
    
    # Filtruj pliki - pomijaj te z '_mod' przed rozszerzeniem
    csv_files = [f for f in all_csv_files if not f.stem.endswith('_mod')]
    
    if not csv_files:
        log(f"Nie znaleziono plików CSV w: {input_dir}")
        return
    
    log(f"Znaleziono {len(csv_files)} plików CSV (pominięto {len(all_csv_files) - len(csv_files)} plików *_mod.csv)")
    log("Rozpoczynam przetwarzanie...")
    
    results = []
    
    for idx, csv_file in enumerate(csv_files, 1):
        log(f"[{idx}/{len(csv_files)}] Przetwarzam: {csv_file.name}")
        
        try:
            result = process_single_file(str(csv_file), output_charts_dir)
            results.append(f"{csv_file.name}: {result}")
        except Exception as e:
            log(f"  BŁĄD: {e}")
            results.append(f"{csv_file.name}: ERROR - {str(e)}")
    
    # Zapisz wyniki
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    
    log(f"\nGotowe! Wyniki zapisano w: {output_file}")
    log(f"Wykresy zapisano w: {output_charts_dir}")
    log(f"Przetworzono {len(csv_files)} plików")


def main():
    """Główna funkcja - uruchamia przetwarzanie"""

    # Wyświetl ostatni commit git
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H%n%ci%n%s'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 3:
                commit_hash = lines[0][:7]
                commit_date = lines[1]
                commit_msg = lines[2]
                log(f"magic lines\nGit: [{commit_hash}] {commit_date} - {commit_msg}")
    except Exception:
        pass

    if len(sys.argv) > 1 and sys.argv[1] != '--help':
        # Tryb pojedynczego pliku/folderu

        # sprawdź czy podany argument to plik CSV czy folder
        input_path = Path(sys.argv[1])
        if input_path.is_dir():
            process_all_files(str(input_path))
            sys.exit(0)
        elif input_path.is_file() and input_path.suffix.lower() == '.csv':
            csv_file = str(input_path)

            # Utwórz katalog charts/ w tym samym miejscu co plik CSV
            csv_path = Path(csv_file)
            output_dir = csv_path.parent / 'charts'
            output_dir.mkdir(exist_ok=True)
            
            log(f"Przetwarzam: {csv_path.name}")
            result = process_single_file(csv_file, str(output_dir))
            log(f"Wynik: {result}")
            full_output_path = output_dir.resolve()
            png_filename = f"{csv_path.stem}.png"
            #log(f"Wykres zapisano w: {full_output_path / png_filename}")
        else:
            log(f"Błąd: {input_path} nie jest plikiem CSV ani katalogiem!")
            sys.exit(1)

        if not os.path.exists(csv_file):
            log(f"Błąd: Plik {csv_file} nie istnieje!")
            sys.exit(1)
        
    else:
        # Tryb batch - przetwarzanie wszystkich plików CSV w domyślnym katalogu
        if len(sys.argv) > 1 and sys.argv[1] == '--help':
            print(__doc__)
            sys.exit(0)
        
        # Domyślna ścieżka do plików CSV
        script_dir = Path(__file__).parent.parent
        input_dir = script_dir / 'tester-third' / 'mt4_test_results' / 'm15_candles'
        
        if not input_dir.exists():
            log(f"Błąd: Katalog {input_dir} nie istnieje!")
            log("Użycie: python magic_lines.py <plik.csv>")
            sys.exit(1)
        
        process_all_files(str(input_dir))
    

if __name__ == '__main__':    
    # Otwórz plik log w trybie write (nadpisz istniejący)
    try:
        log_file_handle = open(LOG_FILE, 'w', encoding='utf-8')
    except Exception as e:
        print(f"Błąd otwarcia pliku log: {e}")
        log_file_handle = open('magic_lines.log', 'w', encoding='utf-8')
        # pełna ścieżka do pliku log
        print(f"Zapis do domyślnego pliku magic_lines.log: {os.path.abspath('magic_lines.log')}")

    try:
        main()
    finally:
        if log_file_handle:
            log_file_handle.close()
