"""
Magic Lines - Standalone Support/Resistance Line Detection and Analysis

Użycie:
    python magic_lines.py  # przetwarza wszystkie pliki CSV w tester-third/mt4_test_results/m15_candles/
    python magic_lines.py <plik.csv>  # przetwarza pojedynczy plik
"""

from functools import cmp_to_key
import math
import sys
import os
import pandas as pd
import mplfinance as mpf

from pathlib import Path
from scipy.signal import argrelextrema
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ===== LOGGING =====
LOG_FILE = 'magic_lines.log'
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

# ===== PARAMETRY LINI =====
MIN_SLOPE = 0.3  # Minimalny slope linii
MAX_SLOPE = 4.0  # Maksymalny slope linii
MAX_HIERARCHICAL_LEVELS = 0  # maksymalna liczba linii wsparcia / oporu poniżej głównej
MIN_HIERARCHICAL_OFFSET = 20  # Minimalny offset między liniami hierarchicznymi (punkty)
LINE_IMPULSE_TOLERANCE = 1.0  # Tolerancja dla dopasowania impulsów do linii
LINE_CANDLE_TOLERANCE = 1.0  # Tolerancja dla dopasowania świeczek do linii

MINMAX_MARGIN_FILTER = 0 # 16 # Minimalna odległość od brzegu danych dla punktów min/max (33/2)
MINMAX_DIFF_FILTER = 50  # 50 # Minimalna różnica między min/max a otoczeniem (punkty)
FA_MIN_HEIGHT = 20  # Minimalna wysokość korpusu świeczki dla first after (punkty)

SCORE_LINES_LEVELS = 1  # Liczba linii do uwzględnienia przy obliczaniu score (główna + ile hierarchicznych)
SCORE_LINES_MIN_POINTS = 1 # Minimalna liczba punktów impulsów do uznania linii za ważną

# ===== RÓŻNE =====
SLOPE_UNIQUENESS_THRESHOLD = 0.01  # minimalna różnica między unikalnymi slope
SCORE_CMP_THRESHOLD = 0.01 # 0.01  # próg porównywania score linii

# ===== WYKRESY =====
SHOW_IMPULSES = True    # Czy pokazywać impulsy na wykresie
SHOW_TOLERANCE = False   # Czy pokazywać tolerancję na wykresie
DUMP_IMAGES = True      # Czy zapisywać wykresy do plików
IMAGE_DPI = 300         # DPI dla zapisywanych obrazów

# ===== SIŁA IMPULSÓW =====
MINMAX_IMPULSE_STRENGTH = 1.0   # siła impulsu dla korpusów lokalnych min/max UWAGA sumuje się
GAP_IMPULSE_STRENGTH = 1.0      # siła impulsu dla luk cenowych
FA_IMPULSE_STRENGTH = 2.0       # siła impulsu dla first after
LAGA_IMPULSE_STRENGTH = 3.0     # siła impulsu dla laga

LAGA_IMPULSE_TRIGGER = 100   # wielkość korpusu dla laga (punkty)
LAGA_IMPULSE_MAX = 5         # maksymalna liczba impulsów laga (najsilniejszych)

# NOTE: zero = same impulsy
BODY_IMPULSE_STRENGTH = 0.0 # 0.3     # siła świeczek - korpusy
SHADOW_IMPULSE_STRENGTH = 0.0 # 0.1   # siła świeczek - cienie

# poziom debugowania 
# # 0 = brak
# 1 = podstawowy
# 2 = szczegółowy (pętle)
DEBUG = 0

# ===== KLASY DANYCH =====

class candle:
    def __init__(self, index, open, high, low, close):
        self.index = index
        self.open = open
        self.high = high
        self.low = low
        self.close = close

class impulse_point:
    # typy
    TYPE_MIN = 0 
    TYPE_MAX = 1
    # podtypy min/max - rozmiar okna
    SUBTYPE_MINMAX_5 = 5
    SUBTYPE_MINMAX_9 = 9
    SUBTYPE_MINMAX_17 = 17
    SUBTYPE_MINMAX_33 = 33

    TYPE_GAP = 2
    SUBTYPE_GAP_LD = 0
    SUBTYPE_GAP_LU = 1
    SUBTYPE_GAP_RD = 2
    SUBTYPE_GAP_RU = 3

    # first after
    TYPE_FA = 3
    SUBTYPE_FA_MIN = 0
    SUBTYPE_FA_MAX = 1

    TYPE_LAGA = 4
    SUBTYPE_LAGA_UP = 1
    SUBTYPE_LAGA_DOWN = 2

    def __init__(self, 
                 index, # indeks świeczki
                 candle : candle, # świeczka
                 type=-1,
                 subtype=-1):
        assert(type >= 0)
        assert(subtype >= 0)

        self.index = index
        self.candle = candle 
        self.type = type
        self.subtype = subtype

        self.price = self.calc_price()
        self.strength = self.calc_strength()

    def subtype_str(self):
        if self.type == self.TYPE_MIN or self.type == self.TYPE_MAX:
            return f"{self.subtype}"
        elif self.type == self.TYPE_GAP:
            if self.subtype == self.SUBTYPE_GAP_LD:
                return "LD"
            elif self.subtype == self.SUBTYPE_GAP_LU:
                return "LU"
            elif self.subtype == self.SUBTYPE_GAP_RD:
                return "RD"
            elif self.subtype == self.SUBTYPE_GAP_RU:
                return "RU"
        elif self.type == self.TYPE_FA:
            if self.subtype == self.SUBTYPE_FA_MIN:
                return "MIN"
            elif self.subtype == self.SUBTYPE_FA_MAX:
                return "MAX"
        elif self.type == self.TYPE_LAGA:
            if self.subtype == self.SUBTYPE_LAGA_UP:
                return "LAGA_UP"
        elif self.subtype == self.SUBTYPE_LAGA_DOWN:
                return "LAGA_DOWN"

    def type_str(self):
        if self.type == self.TYPE_MIN:
            return f"MIN_{self.subtype_str()}"
        elif self.type == self.TYPE_MAX:
            return f"MAX_{self.subtype_str()}"
        elif self.type == self.TYPE_GAP:
            return f"GAP_{self.subtype_str()}"
        elif self.type == self.TYPE_FA:
            return f"FA_{self.subtype_str()}"
        else:
            return "UNKNOWN"

    def calc_price(self):            
        if self.type == self.TYPE_MIN:
            return min(self.candle.open, self.candle.close)
        elif self.type == self.TYPE_MAX:
            return max(self.candle.open, self.candle.close)
        elif self.type == self.TYPE_GAP:
            # gap - price = body edge
            if self.subtype in [self.SUBTYPE_GAP_LD, self.SUBTYPE_GAP_RD]:
                return max(self.candle.open, self.candle.close)
            else:
                return min(self.candle.open, self.candle.close)
        elif self.type == self.TYPE_FA:
            if self.subtype == self.SUBTYPE_FA_MIN:
                return max(self.candle.open, self.candle.close)
            elif self.subtype == self.SUBTYPE_FA_MAX:
                return min(self.candle.open, self.candle.close)
        elif self.type == self.TYPE_LAGA:
            return self.candle.open
        assert False, "Unknown impulse point type"
            
    def calc_strength(self):
        if self.type == self.TYPE_MIN or self.type == self.TYPE_MAX:
            if self.subtype == self.SUBTYPE_MINMAX_5:
                return MINMAX_IMPULSE_STRENGTH * 1.0
            elif self.subtype == self.SUBTYPE_MINMAX_9:
                return MINMAX_IMPULSE_STRENGTH * 2.0
            elif self.subtype == self.SUBTYPE_MINMAX_17:
                return MINMAX_IMPULSE_STRENGTH * 3.0
            elif self.subtype == self.SUBTYPE_MINMAX_33:
                return MINMAX_IMPULSE_STRENGTH * 4.0
            else:
                assert False, "Unknown min/max subtype"
        elif self.type == self.TYPE_GAP:
            return GAP_IMPULSE_STRENGTH
        elif self.type == self.TYPE_FA:
            return FA_IMPULSE_STRENGTH
        elif self.type == self.TYPE_LAGA:
            return LAGA_IMPULSE_STRENGTH
        else:
            assert False, "Unknown impulse point type"

class magic_line:
    def __init__(self, 
                 slope,  # nachylenie linii
                 intercept, # wartość y przy x = 0 (ze wzoru na linię: y = slope * x + intercept)
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

def get_max_diff_in_neighborhood(candles: list[candle], center_idx: int, l: int, r: int, value_getter) -> float:
    """Oblicza maksymalną różnicę między wartością świeczki a wszystkimi świeczkami w otoczeniu.
    
    Args:
        candles: Lista świeczek
        center_idx: Indeks centralnej świeczki
        l: Początek zakresu otoczenia (włącznie)
        r: Koniec zakresu otoczenia (wyłącznie)
        value_getter: Funkcja wydobywająca wartość ze świeczki (np. get_low lub get_high)
    
    Returns:
        Maksymalna różnica w punktach
    """
    center_value = value_getter(candles[center_idx])
    max_diff = 0.0
    
    # Sprawdź lewą stronę
    for c in candles[l: center_idx]:
        diff = abs(value_getter(c) - center_value)
        if diff > max_diff:
            max_diff = diff
    
    # Sprawdź prawą stronę
    for c in candles[center_idx + 1: r]:
        diff = abs(value_getter(c) - center_value)
        if diff > max_diff:
            max_diff = diff
    
    return max_diff

def detect_minmax(candles :list[candle], order:int) -> list[impulse_point]:   
    impulses_minmax = []
    for i in range(order // 2, len(candles) - order // 2):
        # Odrzuć punkty blisko krawędzi danych 
        # (zapobiega disco przy nagłej zmianie subtypu min/max gdy dochodzą nowe świeczki)
        if i < MINMAX_MARGIN_FILTER or \
           (i >= len(candles) - MINMAX_MARGIN_FILTER):
            continue

        current = candles[i]
        
        # helper lambdas
        get_low = lambda x: min(x.open, x.close)
        get_high = lambda x: max(x.open, x.close)

        l = max(0, i - order)
        r = min(len(candles), i + 1 + order)

        # min
        body_low = get_low(current)
        if body_low < min(
            min(get_low(c) for c in candles[l: i]),
            min(get_low(c) for c in candles[i + 1 : r])
        ):
            # Sprawdź maksymalną różnicę ze wszystkich świeczek w otoczeniu
            max_diff = get_max_diff_in_neighborhood(candles, i, l, r, get_low)
            if max_diff > MINMAX_DIFF_FILTER:
                impulses_minmax.append(
                    impulse_point(
                        i, 
                        current, 
                        type=impulse_point.TYPE_MIN,
                        subtype=order))        
        # max
        body_high = get_high(current)
        if body_high > max(
            max(get_high(c) for c in candles[l: i]),
            max(get_high(c) for c in candles[i + 1 : r])
        ):
            # Sprawdź maksymalną różnicę ze wszystkich świeczek w otoczeniu
            max_diff = get_max_diff_in_neighborhood(candles, i, l, r, get_high)
            if max_diff > MINMAX_DIFF_FILTER:
                impulses_minmax.append(
                    impulse_point(
                        i, 
                        current, 
                        type=impulse_point.TYPE_MAX,
                        subtype=order))
            
    return impulses_minmax    

def detect_impulses(candles :list[candle]) -> list[impulse_point]:
    """
    Wykrywa impulsy rynkowe na podstawie różnych kryteriów.
    Zwraca listę impulse_point.
    """
    impulses_gap = []
    for i in range(1, len(candles)):
        current = candles[i]
        prev = candles[i-1]
        
        # Price gap (luka cenowa)
        gap_up = prev.close < current.open
        gap_size = 0
        if gap_up:
            gap_size = min(current.open, current.close) - max(prev.open, prev.close)
        else:
            gap_size = min(prev.open, prev.close) - max(current.open, current.close)
        
        if gap_size > 20: # luka większa niż 20 punktów
            # dodaj 2 punkty na krańcach luki
            impulse_prev = impulse_point(
                i-1, 
                prev, 
                type=impulse_point.TYPE_GAP,
                subtype=impulse_point.SUBTYPE_GAP_LD \
                    if gap_up else impulse_point.SUBTYPE_GAP_LU)
            impulses_gap.append(impulse_prev)
            # print(f"  Detected gap {'UP' if gap_up else 'DOWN'} subtype {'LD' if gap_up else 'LU'} "
            # "at index {i}, size: {gap_size}")

            impulse_curr = impulse_point(
                i, 
                current, 
                type=impulse_point.TYPE_GAP,
                subtype=impulse_point.SUBTYPE_GAP_RU \
                    if gap_up else impulse_point.SUBTYPE_GAP_RD)
            # print(f"  Detected gap {'UP' if gap_up else 'DOWN'} subtype {'RU' if gap_up else 'RD'} "
            # "at index {i}, size: {gap_size}")
            impulses_gap.append(impulse_curr)

    # min max - optymalizacja: dodaj tylko jeśli nie ma lub jest silniejszy
    impulses_minmax = {}
    for order in [impulse_point.SUBTYPE_MINMAX_33,
                  impulse_point.SUBTYPE_MINMAX_17,
                  impulse_point.SUBTYPE_MINMAX_9,
                  impulse_point.SUBTYPE_MINMAX_5]:
        temp = detect_minmax(candles, order=order)
        for p in temp:
            if p.index not in impulses_minmax:
                impulses_minmax[p.index] = p
            elif p.subtype > impulses_minmax[p.index].subtype:
                impulses_minmax[p.index] = p
    impulses_minmax = list(impulses_minmax.values())

    impulses_fa = []
    # first after min/max - mark the first candle after local min/max
    # min fa height = FA_MIN_HEIGHT
    for p in impulses_minmax:
        # check bounds
        if p.index + 1 >= len(candles):
            continue
        # check min height
        next_candle = candles[p.index + 1]
        if abs(next_candle.open - next_candle.close) < FA_MIN_HEIGHT:
            continue

        # dodatkowe filtry dla fa min/max
        if p.type == impulse_point.TYPE_MIN:
            next_next_candle = candles[p.index + 2]
            # jeżeli następna świeczka jest spadkowa i zakrywa fa w połowie to pomiń fa
            if next_next_candle.close < next_next_candle.open and next_next_candle.close <= (next_candle.open + next_candle.close) / 2:
                continue
            # jeżeli świeczka jest spadkowa, pomiń fa
            if next_candle.close < next_candle.open:
                continue
        else: # p.type == impulse_point.TYPE_MAX
            next_next_candle = candles[p.index + 2]
            # jeżeli następna świeczka jest wzrostowa i zakrywa fa w połowie to pomiń fa
            if next_next_candle.close > next_next_candle.open and next_next_candle.close >= (next_candle.open + next_candle.close) / 2:
                continue
            # jeżeli świeczka jest wzrostowa, pomiń fa
            if next_candle.close > next_candle.open:
                continue
            
        subt = impulse_point.SUBTYPE_FA_MIN if p.type == impulse_point.TYPE_MIN \
            else impulse_point.SUBTYPE_FA_MAX
        impulses_fa.append(
            impulse_point(
                p.index + 1,
                next_candle,
                type=impulse_point.TYPE_FA,
                subtype=subt))

    impulses_fa.sort(key=lambda p: p.index)

    # jeżeli fa jest na min/max to usuń fa z listy
    impulses_fa = [p for p in impulses_fa \
        if not any(mm.index == p.index for mm in impulses_minmax)]

    impulses_laga = []
    # laga - duża świeczka - iteruj przez wszystkie świeczki które nie są na liście minmax ani fa
    laga_candidates = []
    for i in range(len(candles)):
        # pomiń jeśli to min/max lub fa
        if any(p.index == i for p in impulses_minmax):
            continue
        if any(p.index == i for p in impulses_fa):
            continue
        
        current = candles[i]
        body_size = abs(current.close - current.open)
        # następna świeczka jeżeli jest innego kierunku jej wielkość musi być mniejsza niż pół obecnej
        if i + 1 < len(candles):
            next_candle = candles[i + 1]
            if (current.close > current.open) != (next_candle.close > next_candle.open):
                if abs(next_candle.close - next_candle.open) >= body_size / 2:
                    continue
        # laga trigger
        if body_size > LAGA_IMPULSE_TRIGGER:
            impulse_laga = impulse_point(
                i, 
                current, 
                type=impulse_point.TYPE_LAGA,
                subtype=impulse_point.SUBTYPE_LAGA_UP
                    if current.close > current.open else impulse_point.SUBTYPE_LAGA_DOWN)
            laga_candidates.append((impulse_laga, body_size))
    
    # Posortuj według wielkości korpusu i wybierz LAGA_IMPULSE_MAX najsilniejszych
    laga_candidates.sort(key=lambda x: x[1], reverse=True)    
    impulses_laga = [impulse for impulse, size in laga_candidates[:LAGA_IMPULSE_MAX]]

    # DEBUG print impulses
    if DEBUG == 2:        
        print(f"  Detected gap impulses: {len(impulses_gap)}")
        #for p in impulses_gap:
        #    print(f"  Detected GAP at index {p.index}, price: {p.price:.2f}")
        print(f"  Detected min/max type 33 impulses: {len([p for p in impulses_minmax if p.subtype == impulse_point.SUBTYPE_MINMAX_33])} ")
        print(f"  Detected min/max type 17 impulses: {len([p for p in impulses_minmax if p.subtype == impulse_point.SUBTYPE_MINMAX_17])} ")
        print(f"  Detected min/max type 9 impulses: {len([p for p in impulses_minmax if p.subtype == impulse_point.SUBTYPE_MINMAX_9])} ")
        print(f"  Detected min/max type 5 impulses: {len([p for p in impulses_minmax if p.subtype == impulse_point.SUBTYPE_MINMAX_5])} ")
        #for p in impulses_minmax:
        #    print(f"  Detected minmax {p.subtype} at index {p.index}, price: {p.price:.2f}")
        print(f"  Detected FA impulses: {len(impulses_fa)}")
        #for p in impulses_fa:
        #    print(f"  Detected FA at index {p.index}, price: {p.price:.2f}")
        print(f"  Detected LAGA impulses: {len(impulses_laga)}")
        #for p in impulses_laga:
        #    print(f"  Detected LAGA at index {p.index}, price: {p.price:.2f}")
    if DEBUG:
        print("Total impulses detected: ", len(impulses_gap) + len(impulses_minmax) + len(impulses_fa) + len(impulses_laga))
    return impulses_gap + impulses_minmax + impulses_fa + impulses_laga

def calculate_line_score(slope: float, 
        i_start: impulse_point, 
        impulses : list[impulse_point], 
        candles : list[candle],
        tolerance: float = LINE_IMPULSE_TOLERANCE,
        debug: int = 0) -> tuple[float, float, float, list[impulse_point], str]:
    
    # oblicz intercept z równania linii y = slope * x + intercept
    # gdzie x = index świeczki, y = cena
    intercept = i_start.price - slope * i_start.index
        
    # Sprawdź ile impulsów pasuje do tej linii
    impulses_score = 0
    used_impulses : list[impulse_point] = []
    debug_string = ""

    for p in impulses:
        # optymalizacja: pomiń punkty przed i_start (uwzględnij i_start)
        if p.index < i_start.index:
            continue

        expected_price = slope * p.index + intercept
        dist = abs(p.price - expected_price)
        if dist <= tolerance: 
            # ważone przez odległość
            impulses_score += p.strength * (1.0 - dist / tolerance) 
            used_impulses.append(p)

            # DEBUG
            if (debug):
                debug_string += f"    Impulse at index {p.index} type {p.type_str()} "\
                    f"price {p.price:.2f} matches line " \
                    f"expected {expected_price:.2f} "\
                    f"dist {dist:.2f} "\
                    f"score contrib {p.strength * (1.0 - dist / tolerance):.2f}\n"
                
    # Jeżeli jeden index ma więcej impulsów, to zostaw tylko ten z najwyższą siłą
    unique_used_impulses = {}
    for p in used_impulses:
        if p.index not in unique_used_impulses:
            unique_used_impulses[p.index] = p
        else:
            if p.strength > unique_used_impulses[p.index].strength:
                unique_used_impulses[p.index] = p
    used_impulses = list(unique_used_impulses.values())
                
    # Sprawdź ile świeczek pasuje do tej linii
    candles_score = 0

    # jeśli siła świeczek/cieni = 0 to pomiń tę część
    if BODY_IMPULSE_STRENGTH == 0.0 and SHADOW_IMPULSE_STRENGTH == 0.0:
        return intercept, impulses_score, candles_score, used_impulses, debug_string
    else:
        for candle in candles:
            expected_price = slope * candle.index + intercept
            
            # sprawdź korpus
            body_low = min(candle.open, candle.close)
            body_high = max(candle.open, candle.close)
            if abs(body_low - expected_price) <= LINE_CANDLE_TOLERANCE \
                or abs(body_high - expected_price) <= LINE_CANDLE_TOLERANCE:
                dist = min(abs(body_low - expected_price), abs(body_high - expected_price))
                candles_score += BODY_IMPULSE_STRENGTH * (1.0 - dist / LINE_CANDLE_TOLERANCE)

                # DEBUG
                if (debug):
                    debug_string += f"    Candle at index {candle.index} body matches line "
            # sprawd cień
            elif abs(candle.low - expected_price) <= LINE_CANDLE_TOLERANCE \
                or abs(candle.high - expected_price) <= LINE_CANDLE_TOLERANCE:
                dist = min(abs(candle.low - expected_price), abs(candle.high - expected_price))
                candles_score += SHADOW_IMPULSE_STRENGTH * (1.0 - dist / LINE_CANDLE_TOLERANCE)

                # DEBUG
                if (debug):
                    debug_string += f"    Candle at index {candle.index} shadow matches line "

    return intercept, impulses_score, candles_score, used_impulses, debug_string

def calculate_lines(slope : float, 
        impulses : list[impulse_point], 
        candles : list[candle],
        tolerance: float = LINE_IMPULSE_TOLERANCE,
        debug: int = 0) -> list[magic_line]:    
    """
    Dla danego slope oblicza zestaw linii magicznych
    """

    if (debug):
        print(f"  Calculating line score for slope={slope:.4f}")
    
    line_candidates = [] # (intercept, score, used_points, debug_string)
    # Dla każdego punktu oblicz intercept i policz score
    for i_start in impulses:
        intercept, impulses_score, candles_score, used_impulses, debug_string = calculate_line_score(
            slope,
            i_start,
            impulses,
            candles,
            tolerance,
            debug)
                
        # dodaj do wyników
        # UWAGA: dla linii które nie przecinają żadnego punktu 
        # score = score dla impulsu i_start
        line_candidates.append((intercept, impulses_score, candles_score, used_impulses, debug_string))

        if (debug):
            print(f"    Line intercept {intercept:.2f} impulses score {impulses_score:.2f} "\
                f"candles score {candles_score:.2f} "
                f"using {len(used_impulses)} points starting from index {i_start.index}")
    
    # sortuj linie po score (suma impulsów i świeczek)
    line_candidates.sort(key=lambda x: x[1] + x[2], reverse=True)

    # DEBUG
    if (debug):
        print(f"    Best intercept: {line_candidates[0][0]:.2f} with score i/c {line_candidates[0][1]:.2f}/{line_candidates[0][2]:.2f} "\
              f"using {len(line_candidates[0][3])} points")

    magic_lines = []
    for line in line_candidates:
        magic_lines.append(magic_line(
            slope=slope,
            intercept=line[0],
            offset=0,
            score=line[1] + line[2],
            used_points=line[3],
            level=1))
            
    return magic_lines

def find_support_lines(candles :list[candle], prev_chart_slope: float = None,
        debug: int = 0) -> tuple[list[magic_line], list[impulse_point]]:
    """
    Znajduje główną linię support/resistance oraz hierarchiczne linie równoległe.    
    Zwraca listę wykrytych linii (od 0 do HIERARCHICAL_LEVELS - wznosząca i/lub opadająca).
    """
    
    # Wykryj impulsy
    points = detect_impulses(candles)

    # asc impulses nie zawiera impulsów FA_MAX
    asc_impulses = [p for p in points \
                  if not (p.type == impulse_point.TYPE_FA and p.subtype == impulse_point.SUBTYPE_FA_MAX)]
    # dsc impulses nie zawiera impulsów FA_MIN
    dsc_impulses = [p for p in points \
                  if not (p.type == impulse_point.TYPE_FA and p.subtype == impulse_point.SUBTYPE_FA_MIN)]
        
    if len(points) < 2:
        assert False, "Za mało punktów do wyznaczenia linii"
    
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

    # filter very similar slopes
    # TODO increase SLOPE_UNIQUENESS_THRESHOLD for fewer slopes + calibrate after
    unique_slopes = sorted(unique_slopes)
    filtered_slopes = []
    prev_slope = None
    for s in unique_slopes:
        if prev_slope is None or abs(s - prev_slope) / prev_slope > SLOPE_UNIQUENESS_THRESHOLD:
            filtered_slopes.append(s)
            prev_slope = s
    # DEBUG
    if (debug):
        print(f"  Filtered slopes: {len(filtered_slopes)} from {len(unique_slopes)}")
    unique_slopes = filtered_slopes

    # Dla każdego |slope| oblicz combined_score
    best_pair = None
    
    slope_scores = [] # [(combined_score, {'ascending': , 'descending':}), ...]
    for i, abs_slope in enumerate(unique_slopes):
        # print(f"Sprawdzam slope: {abs_slope:.4f} {i+1}/{len(unique_slopes)}     ", end='\r')
        asc_lines = calculate_lines(abs_slope, asc_impulses, candles, debug=debug)
        desc_lines = calculate_lines(-abs_slope, dsc_impulses, candles, debug=debug)

        # Helper function to find best lines above/below and collect scores
        # levels = how many best lines to consider
        # 1 = only best line
        # 2 = best line + best above + best below
        def get_hierarchical_avg_score(lines, levels):
            # NOTE: MIN_HIERARCHICAL_OFFSET - linie nie mogą być zbyt blisko siebie
            # NOTE: SCORE_LINES_MIN_POINTS - linia musi mieć minimum N punktów użytych do score
            best = lines[0]
            above = sorted([l for l in lines if \
                l.intercept > best.intercept + MIN_HIERARCHICAL_OFFSET and\
                len(l.used_points) >= SCORE_LINES_MIN_POINTS],
                key=lambda x: x.score, reverse=True)
            below = sorted([l for l in lines if \
                l.intercept < best.intercept - MIN_HIERARCHICAL_OFFSET and\
                len(l.used_points) >= SCORE_LINES_MIN_POINTS],
                key=lambda x: x.score, reverse=True)
            scores = [best.score]
            for n in range(1, levels):
                if len(above) >= n:
                    scores.append(above[n-1].score)
                if len(below) >= n:
                    scores.append(below[n-1].score)

            # NOTE: return scores list only for debug
            return sum(scores) / len(scores), scores

        # Oblicz score bazując na avg najlepszych linii
        avg_asc_score, asc_scores = get_hierarchical_avg_score(asc_lines, SCORE_LINES_LEVELS)
        avg_desc_score, desc_scores = get_hierarchical_avg_score(desc_lines, SCORE_LINES_LEVELS)

        # DEBUG
        if (debug):
            print(f"    Slope {abs_slope:.4f} asc scores: {[f'{s:.2f}' for s in asc_scores]} avg {avg_asc_score:.2f} | "
                f"desc scores: {[f'{s:.2f}' for s in desc_scores]} avg {avg_desc_score:.2f}")    

        # Jeżeli slope linii jest identyczny jak prev_chart_slope
        # pomnóż score przez 1.1 (bonus za powtarzalność)
        if prev_chart_slope is not None:
            if abs(abs_slope - abs(prev_chart_slope)) / abs(prev_chart_slope) < 0.01:
                avg_asc_score *= 1.1
                avg_desc_score *= 1.1
                # uaktualnij asc_line score             
                asc_lines[0].score *= 1.1
                desc_lines[0].score *= 1.1
                print(f"Bonus za powtarzalność dla slope {abs_slope:.4f}")   
        elif DEBUG > 1:
            print("Brak poprzedniego slope do porównania")

        # Get score from best lines
        combined_score = avg_asc_score + avg_desc_score
        slope_scores.append((combined_score, {
            'ascending': asc_lines,
            'descending': desc_lines,
            'slope': abs_slope
        }))

    # Wybierz parę z najwyższym combined_score
    slope_scores.sort(key=lambda x: x[0], reverse=True)

    best_pair = slope_scores[0][1]
    # print best_pair score
    if DEBUG > 1:
        print(f"Best ascending line score: {best_pair['ascending'][0].score:.2f}")
        print(f"Best descending line score: {best_pair['descending'][0].score:.2f}")

    # DEBUG
    # calc line score for best desc line with debug info
    # calculate_lines(best_pair['slope'], dsc_impulses, debug=1)

    if (DEBUG >= 1 or debug):
        print("DEBUG Top 5 slope scores:")
        # best 5 lines score
        for k in range(5):
            if k >= len(slope_scores):
                break
            score, pair = slope_scores[k]
            print(f"  Top {k+1} slope {pair['slope']:.4f} combined score {score:.4f}")
    if (DEBUG >= 2 or debug):
        for line in best_pair['ascending']:
            print(f"  Ascending line slope {line.slope:.4f} intercept {line.intercept:.2f} score {line.score:.4f} "
                f"using {len(line.used_points)} points")
        for line in best_pair['descending']:
            print(f"  Descending line slope {line.slope:.4f} intercept {line.intercept:.2f} score {line.score:.4f} "
                f"using {len(line.used_points)} points")

    best_ascending : magic_line = best_pair['ascending'][0]
    best_descending : magic_line = best_pair['descending'][0]

    # Dodaj główne linie do wyników
    detected_lines = [best_ascending, best_descending]

    # Pomocnicze funkcje porównujące linie dla wyboru hierarchicznych
    # Sortowanie najpierw po score, potem po odległości intercept od bazowej linii
    # UWAGA: dla bardzo podobnych score (różnica < SCORE_CMP_THRESHOLD) wybierz bliższą linię
    def line_cmp_down(x: magic_line, y: magic_line):
        if abs(x.score - y.score) < SCORE_CMP_THRESHOLD:
            return -1 if abs(x.intercept) < abs(y.intercept) else 1
        return -1 if x.score > y.score else 1 if x.score < y.score else 0
    def line_cmp_up(x: magic_line, y: magic_line):
        if abs(x.score - y.score) < SCORE_CMP_THRESHOLD:
            return -1 if abs(x.intercept) > abs(y.intercept) else 1
        return -1 if x.score > y.score else 1 if x.score < y.score else 0
    
    # Dodaj linie hierarchiczne
    for lines in [best_pair['ascending'], best_pair['descending']]:
        base_line = lines[0]

        # Wszystkie linie powyżej 
        level = base_line.level + 1
        intercept = base_line.intercept
        while level <= MAX_HIERARCHICAL_LEVELS:
            lines_above = [line for line in lines if line.intercept > intercept + MIN_HIERARCHICAL_OFFSET]         
            if not lines_above: break
            # Posortuj po score i wybierz najlepszą (w przypadku "remisu" wybierz bliższą do bazowej)
            best_line = sorted(lines_above, key=cmp_to_key(line_cmp_down))[0]
            best_line.level = level
            best_line.offset = best_line.intercept - intercept
            detected_lines.append(best_line)
            # DEBUG
            if (DEBUG >= 2 or debug):
                print(f"  Detected hierarchical line slope {best_line.slope:.4f} level {level} score {best_line.score:.4f} "\
                    f"at intercept {best_line.intercept:.2f} offset {best_line.offset:.2f}")
            level += 1
            intercept = best_line.intercept
            
        # Wszystkie linie poniżej
        level = base_line.level + 1
        intercept = base_line.intercept
        while level <= MAX_HIERARCHICAL_LEVELS:
            lines_below = [line for line in lines if line.intercept < intercept - MIN_HIERARCHICAL_OFFSET]
            if not lines_below: break
            best_line = sorted(lines_below, key=cmp_to_key(line_cmp_up))[0]
            best_line.level = level
            best_line.offset = best_line.intercept - intercept
            detected_lines.append(best_line)
            # DEBUG
            if (DEBUG >= 2 or debug):
                print(f"  Detected hierarchical line slope {best_line.slope:.4f} level {level} score {best_line.score:.4f} "\
                    f"at intercept {best_line.intercept:.2f} offset {best_line.offset:.2f}")
            level += 1
            intercept = best_line.intercept

    return detected_lines, points

def plot_chart(df_plot, 
               impulses : list[impulse_point],
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
        all_fa = {}
        all_laga = {}

        for impulse in impulses:                     
            if impulse.type == impulse_point.TYPE_GAP:
                idx = impulse.index
                all_impulses[idx] = impulse.price
            elif impulse.type == impulse_point.TYPE_MIN:
                idx = impulse.index
                all_minima[idx] = impulse.price
            elif impulse.type == impulse_point.TYPE_MAX:
                idx = impulse.index
                all_maxima[idx] = impulse.price
            elif impulse.type == impulse_point.TYPE_FA:
                idx = impulse.index
                all_fa[idx] = impulse.price
                # DEBUG
                # print(f"  FA point at index {idx}, price {point.price():.2f}")
            elif impulse.type == impulse_point.TYPE_LAGA:
                idx = impulse.index
                all_laga[idx] = impulse.price
                # DEBUG
                # print(f"  LAGA point at index {idx}, price {impulse.price:.2f}")
        
        # Utwórz serie dla każdego typu punktu
        impulse_series = pd.Series(index=df_plot.index, dtype=float)
        minima_series = pd.Series(index=df_plot.index, dtype=float)
        maxima_series = pd.Series(index=df_plot.index, dtype=float)
        fa_series = pd.Series(index=df_plot.index, dtype=float)
        laga_series = pd.Series(index=df_plot.index, dtype=float)
        
        for i, dt in enumerate(df_plot.index):
            if i in all_impulses:
                impulse_series.iloc[i] = all_impulses[i]
            if i in all_minima:
                minima_series.iloc[i] = all_minima[i]
            if i in all_maxima:
                maxima_series.iloc[i] = all_maxima[i]
            if i in all_fa:
                fa_series.iloc[i] = all_fa[i]
            if i in all_laga:
                laga_series.iloc[i] = all_laga[i]
        
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

        if not fa_series.isna().all():
            apds.append(mpf.make_addplot(
                fa_series,
                type='scatter',
                markersize=40,
                marker='*',
                color='orange',
                alpha=0.7
            ))

        if not laga_series.isna().all():
            apds.append(mpf.make_addplot(
                laga_series,
                type='scatter',
                markersize=40,
                marker='+',
                color='blue',
                alpha=0.7
            ))

    if SHOW_TOLERANCE:
        up_tolerance = {}
        down_tolerance = {}
        for impulse in impulses:
            tolerance = LINE_IMPULSE_TOLERANCE
            idx = impulse.index
            up_tolerance[idx] = impulse.price() + tolerance
            down_tolerance[idx] = impulse.price() - tolerance
        up_tolerance_series = pd.Series(index=df_plot.index, dtype=float)
        down_tolerance_series = pd.Series(index=df_plot.index, dtype=float)
        for i, dt in enumerate(df_plot.index):
            if i in up_tolerance:
                up_tolerance_series.iloc[i] = up_tolerance[i]
            if i in down_tolerance:
                down_tolerance_series.iloc[i] = down_tolerance[i]
        if not up_tolerance_series.isna().all():
            apds.append(mpf.make_addplot(
                up_tolerance_series,
                type='scatter',
                markersize=1,
                marker='.',
                color='gray',
                alpha=1
            ))
        if not down_tolerance_series.isna().all():
            apds.append(mpf.make_addplot(
                down_tolerance_series,
                type='scatter',
                markersize=1,
                marker='.',
                color='gray',
                alpha=1
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
    
    # Dodaj numery świeczek dla min/max
    if DEBUG == 2 and SHOW_IMPULSES:
        for impulse in impulses:
            if impulse.type == impulse_point.TYPE_MIN or impulse.type == impulse_point.TYPE_MAX:
                idx = impulse.index
                price = impulse.price
                # Offset tekstu w zależności od typu (min na dole, max na górze)
                y_offset = -15 if impulse.type == impulse_point.TYPE_MIN else 15
                ax.text(idx, price, str(idx), 
                       fontsize=8, ha='center', va='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='gray'),
                       transform=ax.transData,
                       verticalalignment='top' if impulse.type == impulse_point.TYPE_MIN else 'bottom')
    
    if DUMP_IMAGES:
        fig.savefig(output_filepath, bbox_inches='tight', pad_inches=0.1, dpi=IMAGE_DPI)
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

def load_previous_slope(csv_path: Path, output_dir: Path) -> float:
    """
    Wczytuje poprzedni slope z pliku wynikowego dla poprzedniej świeczki (15 minut wcześniej).
    
    Args:
        csv_path: Ścieżka do aktualnego pliku CSV
        output_dir: Katalog z plikami wynikowymi
    
    Returns:
        Poprzedni slope lub None jeśli nie można wczytać
    """
    try:
        from datetime import datetime, timedelta
        # Parse filename: YY-MM-DD-HH-MM.csv
        stem_parts = csv_path.stem.split('-')
        if len(stem_parts) == 5:
            year = int('20' + stem_parts[0])
            month = int(stem_parts[1])
            day = int(stem_parts[2])
            hour = int(stem_parts[3])
            minute = int(stem_parts[4])
            current_dt = datetime(year, month, day, hour, minute)
            prev_dt = current_dt - timedelta(minutes=15)
            prev_filename = prev_dt.strftime('%y-%m-%d-%H-%M') + '_result.txt'
            prev_result_file = output_dir / prev_filename
        else:
            return None
    except Exception as e:
        log(f"  Błąd parsowania nazwy pliku: {e}")
        return None
    
    if prev_result_file.exists():
        if DEBUG > 1: 
            log(f"Sprawdzam poprzedni plik wynikowy: {prev_result_file}")
        try:
            with open(prev_result_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'SLOPE:' in line:
                        parts = line.split('SLOPE:')
                        if len(parts) == 2:
                            slope_str = parts[1].split('|')[0].strip()
                            prev_slope = float(slope_str)
                            if DEBUG > 1: 
                                log(f"  Poprzedni slope: {prev_slope:.4f}")
                            return prev_slope
        except Exception as e:
            log(f"  Błąd wczytania poprzedniego pliku wynikowego: {e}")
    
    return None


def process_single_file(csv_filepath, output_dir='charts', prev_slope=None):
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
    candles = [candle(i,
                      lookback_df_for_lines.iloc[i]['Open'],
                      lookback_df_for_lines.iloc[i]['High'],
                      lookback_df_for_lines.iloc[i]['Low'],
                      lookback_df_for_lines.iloc[i]['Close']) 
               for i in range(len(lookback_df_for_lines))]
    detected_lines, points = find_support_lines(candles, prev_slope)
    
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
    
    # TEST
    # wszystkie ID linii powinny być unikalne
    unique_ids = set()
    for line in line_offsets:
        line_id = line[0]
        if line_id in unique_ids:
            print(f"ERROR: Duplicate line ID detected: {line_id}")
            assert False, "Duplicate line ID detected"
        unique_ids.add(line_id)
    
    # Wygeneruj wykres tylko gdy DUMP_IMAGES=True
    if DUMP_IMAGES:
        chart_filename = f"{Path(csv_filepath).stem}.png"
        chart_filepath = os.path.join(output_dir, chart_filename)
        
        lookback_start_dt = df.iloc[start_idx]['DateTime']
        lookback_end_dt = df.iloc[-1]['DateTime']
        
        plot_chart(lookback_df_full.copy(), points, detected_lines, chart_filepath, 
                   lookback_start_dt, lookback_end_dt)        
        if DEBUG:
            print(f"Wykres: {chart_filepath}")

    if DEBUG > 1:
        combined_score = detected_lines[0].score + detected_lines[1].score
        print(f"DEBUG: slope: {slope:.4f} score: {combined_score:.2f}")

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
            prev_slope = load_previous_slope(csv_file, output_charts_dir)
            result = process_single_file(str(csv_file), output_charts_dir, prev_slope)            
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

            # Wczytaj poprzedni slope
            prev_slope = load_previous_slope(csv_path, output_dir)

            log(f"Przetwarzam: {csv_path.name}")
            result = process_single_file(csv_file, str(output_dir), prev_slope)

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
