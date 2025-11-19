import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import matplotlib
# Use non-interactive backend for headless environments/tests
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
import os
import logging
from typing import List, Optional, Dict, Tuple
from impulse_detector import find_hierarchical_parallel_lines
from strategy_types import (
    StrategyConfig, Point, HierarchicalLine, SupportLine, TradeSignal
)

class SupportBreakoutStrategy:
    """
    Strategia breakout z hierarchicznymi liniami równoległymi.
    
    Główne cechy:
    - Support/Resistance wyznaczany z poprzednich N dni (domyślnie 5)
    - Wykrywanie hierarchicznych linii równoległych (S2, S3, R2, R3)
    - Pozycje LONG (linie wznosząc) i SHORT (linie opadające)
    - Integracja z impulse_detector dla wykrywania impulsów
    
    Hierarchiczne linie:
    - S1: główna linia wsparcia/oporu (czerwona/zielona, ciągła)
    - S2, S3: linie wsparcia PONIŻEJ głównej (równoległe, offset ujemny)
    - R2, R3: linie oporu POWYŻEJ głównej (równoległe, offset dodatni)
    
    Wszystkie linie są RÓWNOLEGŁE (ten sam slope) i przesunięte pionowo
    o odległości d₁, 2×d₁, 3×d₁ (struktura równoodległych poziomów).
    
    Kierunki:
    - Linie WZNOSZĄC (slope > 0): strategia LONG (breakout w górę)
    - Linie OPADAJĄCE (slope < 0): strategia SHORT (breakout w dół)
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, 
                 lookback_days=5, risk_pips=50, reward_ratio=3, 
                 retest_mode=False, retest_tolerance=30, min_slope=0.1,
                 hierarchical_levels_below=4, hierarchical_levels_above=4,
                 hierarchical_tolerance=30, allow_descending=True, show_legend=True,
                 chart_dpi=150, close_at_eod=False):
        # Backward compatibility: jeśli config nie podany, użyj starych parametrów
        if config is None:
            config = StrategyConfig(
                lookback_days=lookback_days,
                risk_pips=risk_pips,
                reward_ratio=reward_ratio,
                retest_mode=retest_mode,
                retest_tolerance=retest_tolerance,
                min_slope=min_slope,
                hierarchical_levels_below=hierarchical_levels_below,
                hierarchical_levels_above=hierarchical_levels_above,
                hierarchical_tolerance=hierarchical_tolerance,
                allow_descending=allow_descending,
                show_legend=show_legend,
                chart_dpi=chart_dpi,
                close_at_eod=close_at_eod
            )
        
        self.config = config
        
        # Convenience properties (backward compatibility)
        self.lookback_days = config.lookback_days
        self.lookback_candles = config.lookback_candles
        self.risk_pips = config.risk_pips
        self.reward_pips = config.reward_pips
        self.reward_ratio = config.reward_ratio
        self.retest_mode = config.retest_mode
        self.retest_tolerance = config.retest_tolerance
        self.min_slope = config.min_slope
        self.allow_descending = config.allow_descending
        self.show_legend = config.show_legend
        self.chart_dpi = config.chart_dpi
        self.close_at_eod = config.close_at_eod
        self.hierarchical_levels_below = config.hierarchical_levels_below
        self.hierarchical_levels_above = config.hierarchical_levels_above
        self.hierarchical_tolerance = config.hierarchical_tolerance
        
        # Caching: zmienione na dict dla O(1) lookup
        self.support_lines = {}  # Cache dla support lines
        self.daily_support_data: Dict[date, List[SupportLine]] = {}  # Dict zamiast listy
        # Setup logger (file-based) - write debug logs to support_charts/debug.txt
        # Use the directory of the invoking script (sys.argv[0]) so logs land in the same folder
        # as generated charts even when scripts are executed from another cwd.
        import sys
        main_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if len(sys.argv) > 0 else os.getcwd()
        logs_dir = os.path.join(main_dir, 'support_charts')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'debug.txt')
        self._logger = logging.getLogger('aifx_debug')
        if not self._logger.handlers:
            fh = logging.FileHandler(log_path, mode='a', encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
            fh.setFormatter(formatter)
            self._logger.addHandler(fh)
        self._logger.setLevel(logging.DEBUG)
        
    def calculate_indicators(self, df):
        """
        Oblicza support line - aktualizowana tylko RAZ DZIENNIE (na początku dnia)
        Znacznie przyspiesza backtest (zamiast każdej świeczki)
        """
        df = df.copy()
        df['Date'] = df['DateTime'].dt.date
        
        # Dla każdej świeczki wyznacz support - ale cache'uj per dzień
        support_slopes = []
        support_intercepts = []
        
        current_date = None
        cached_slope = np.nan
        cached_intercept = np.nan
        days_calculated = 0
        
        for idx in range(len(df)):
            row_date = df.iloc[idx]['Date']
            
            if idx < self.lookback_candles:
                support_slopes.append(np.nan)
                support_intercepts.append(np.nan)
            else:
                # Nowy dzień - przelicz support line
                if row_date != current_date:
                    current_date = row_date
                    days_calculated += 1
                    
                    # Dane z ostatnich 5 dni (do początku tego dnia)
                    lookback_df = df.iloc[idx - self.lookback_candles:idx].copy()
                    
                    # WAŻNE: lookback_df ma indeksy odnoszące się do idx w calculate_indicators
                    # Tworzymy nowy system indeksów 0-(lookback_candles-1) dla _find_support_line
                    lookback_df_indexed = lookback_df.copy()
                    lookback_df_indexed['index'] = range(len(lookback_df_indexed))
                    
                    # Oblicz support line (zwraca LISTĘ linii - może być 0, 1 lub 2)
                    detected_lines = self._find_support_line(lookback_df_indexed)
                    
                    # Jeśli wykryto linie, zapisz KAŻDĄ z nich do daily_support_data (dict)
                    if detected_lines:
                        lookback_start_dt = df.iloc[idx - self.lookback_candles]['DateTime']
                        lookback_end_dt = df.iloc[idx - 1]['DateTime']
                        
                        # Inicjalizuj listę dla tej daty jeśli nie istnieje
                        if current_date not in self.daily_support_data:
                            self.daily_support_data[current_date] = []
                        
                        for line_info in detected_lines:
                            self.daily_support_data[current_date].append({
                                'date': current_date,
                                'type': line_info['type'],  # 'ascending' lub 'descending'
                                'slope': line_info['slope'],
                                'intercept': line_info['intercept'],
                                'support_points': line_info['used_minima'],
                                'local_maxima': line_info['local_maxima'],
                                'all_minima': line_info['all_minima'],
                                'impulses': line_info['impulses'],
                                'hierarchical_supports': line_info['hierarchical_supports'],
                                'hierarchical_resistances': line_info['hierarchical_resistances'],
                                'lookback_start_dt': lookback_start_dt,
                                'lookback_end_dt': lookback_end_dt,
                                'day_start_idx': idx
                            })
                        
                        # Dla backwardowej kompatybilności: użyj pierwszej linii do Support_Slope/Intercept
                        cached_slope = detected_lines[0]['slope']
                        cached_intercept = detected_lines[0]['intercept']
                    else:
                        # Brak wykrytych linii
                        cached_slope = 0
                        cached_intercept = 0
                    
                    if days_calculated % 10 == 0:
                        self._logger.debug(f"Przetworzono {days_calculated} dni... ({current_date})")
                
                # Użyj cache'owanej wartości dla tego dnia
                support_slopes.append(cached_slope)
                support_intercepts.append(cached_intercept)
        
        df['Support_Slope'] = support_slopes
        df['Support_Intercept'] = support_intercepts
        
        # Oblicz wartość support line dla każdej świeczki
        # Używamy daily_support_data żeby znaleźć właściwy lookback_start_dt dla każdego dnia
        support_prices = []
        
        for idx in range(len(df)):
            if pd.isna(df.iloc[idx]['Support_Slope']):
                support_prices.append(np.nan)
            else:
                row_date = df.iloc[idx]['Date']
                row_datetime = df.iloc[idx]['DateTime']
                
                # O(1) lookup w dict zamiast O(n) iteracji po liście
                lines_for_date = self.daily_support_data.get(row_date, [])
                if not lines_for_date:
                    support_prices.append(np.nan)
                    continue
                
                # Użyj pierwszej linii (backward compatibility)
                lookback_start_dt = lines_for_date[0]['lookback_start_dt']
                
                # Offset = ile świeczek od lookback_start_dt do tej świeczki
                offset = len(df[(df['DateTime'] >= lookback_start_dt) & (df['DateTime'] < row_datetime)])
                
                support_price = df.iloc[idx]['Support_Intercept'] + df.iloc[idx]['Support_Slope'] * offset
                support_prices.append(support_price)
        
        df['Support_Price'] = support_prices
        
        return df
    
    def _find_support_line(self, lookback_df):
        """
        Znajduje główną linię support oraz hierarchiczne linie równoległe.
        
        Używa PEŁNEJ logiki z impulse_detector:
        - Wykrywa impulsy z wszystkimi kryteriami (7 warunków)
        - Znajduje lokalne minima/maxima
        - Wyznacza support przez te punkty (bounce/breakout scoring)
        - Wykrywa hierarchiczne linie równoległe (S2, S3, R2, R3)
        
        Zwraca dict z kluczami:
        - 'slope': nachylenie głównej linii
        - 'intercept': punkt przecięcia Y głównej linii
        - 'score': liczba punktów dopasowanych do głównej linii
        - 'used_minima': lista punktów użytych do dopasowania głównej linii
        - 'local_maxima': wszystkie lokalne maksima
        - 'all_minima': wszystkie lokalne minima
        - 'impulses': punkty impulsów
        - 'hierarchical_supports': lista linii wsparcia PONIŻEJ głównej (S2, S3, ...)
        - 'hierarchical_resistances': lista linii oporu POWYŻEJ głównej (R2, R3, ...)
        
        Każda hierarchiczna linia to dict z:
        - 'slope', 'intercept', 'touches', 'offset', 'score', 'level'
        - Wyznacza support przez te punkty (bounce/breakout scoring)
        """
        from scipy.signal import argrelextrema
        
        # 1. Wykryj impulsy (PEŁNA wersja z impulse_detector)
        impulses = self._detect_impulses_full(lookback_df)
        #print(f"  DEBUG: Wykryto {len(impulses)} impulsów w oknie lookback")
        
        # 2. Znajdź lokalne minima/maxima
        minima_idx = argrelextrema(lookback_df['Low'].values, np.less, order=5)[0]
        maxima_idx = argrelextrema(lookback_df['High'].values, np.greater, order=5)[0]
        #print(f"  DEBUG: Wykryto {len(minima_idx)} lokalnych minimów, {len(maxima_idx)} lokalnych maksimów")
        
        # 3. Zbuduj listę punktów (impulses + minima)
        points = []
        
        # Dodaj impulsy
        for imp_idx in impulses:
            points.append({
                'index': lookback_df.iloc[imp_idx]['index'],
                'price': lookback_df.iloc[imp_idx]['Low'],
                'type': 'impulse'
            })
        
        # Dodaj minima
        for min_idx in minima_idx:
            points.append({
                'index': lookback_df.iloc[min_idx]['index'],
                'price': lookback_df.iloc[min_idx]['Low'],
                'type': 'minimum'
            })

        # Zbierz wszystkie lokalne minima (do celów wizualnych)
        all_minima = []
        for min_idx in minima_idx:
            all_minima.append({'index': int(lookback_df.iloc[min_idx]['index']), 'price': float(lookback_df.iloc[min_idx]['Low'])})

        # Zbierz lokalne maksima (do celów wizualnych)
        local_maxima = []
        for max_idx in maxima_idx:
            local_maxima.append({'index': int(lookback_df.iloc[max_idx]['index']), 'price': float(lookback_df.iloc[max_idx]['High'])})

        # Zbierz impulsy jako punkty (do celów wizualnych)
        impulse_points = []
        for imp_idx in impulses:
            impulse_points.append({'index': int(lookback_df.iloc[imp_idx]['index']), 'price': float(lookback_df.iloc[imp_idx]['Low'])})
        
        if len(points) < 2:
            # Fallback: użyj dwóch najniższych punktów
            sorted_idx = lookback_df.nsmallest(2, 'Low').index.tolist()
            points = [{'index': lookback_df.index.get_loc(i), 
                      'price': lookback_df.loc[i, 'Low'],
                      'type': 'fallback'} for i in sorted_idx]

        # 4. Znajdź najlepsze PARY linii (wznosząca + opadająca z tym samym |slope|)
        # Wykrywanie jednoczesne: para linii (slope, -slope) ma łączny największy score
        
        # Krok 1: Oblicz score dla wszystkich możliwych linii
        def calculate_line_score(slope, points, tolerance=30):
            """Oblicza score dla linii o danym slope przez punkty."""
            best_intercept = None
            best_score = 0
            best_used = []
            
            # Próbuj różnych intercept (przez każdy punkt)
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
                        used.append({'index': p['index'], 'price': float(p['price'])})
                
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
        
        # Krok 2: Zbierz wszystkie unikalne wartości |slope| z par punktów
        unique_slopes = set()
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                p1, p2 = points[i], points[j]
                if p2['index'] == p1['index']:
                    continue
                
                slope = (p2['price'] - p1['price']) / (p2['index'] - p1['index'])
                abs_slope = abs(slope)
                
                # Tylko slope >= min_slope
                if abs_slope >= self.min_slope:
                    unique_slopes.add(abs_slope)
        
        # Krok 3: Dla każdego |slope| oblicz combined_score dla pary (+slope, -slope)
        best_pair = None
        best_combined_score = 0
        
        for abs_slope in unique_slopes:
            # Oblicz score dla linii wznoszącej (+slope)
            asc_result = calculate_line_score(abs_slope, points)
            
            # Oblicz score dla linii opadającej (-slope)
            desc_result = calculate_line_score(-abs_slope, points)
            
            # Łączny score pary
            combined_score = asc_result['score'] + desc_result['score']
            
            # Czy to najlepsza para?
            if combined_score > best_combined_score:
                best_combined_score = combined_score
                best_pair = {
                    'ascending': asc_result,
                    'descending': desc_result,
                    'combined_score': combined_score
                }
        
        # Krok 4: Przygotuj wyniki
        best_ascending = best_pair['ascending'] if best_pair and best_pair['ascending']['score'] > 0 else {'score': 0}
        best_descending = best_pair['descending'] if best_pair and best_pair['descending']['score'] > 0 and self.allow_descending else {'score': 0}

        # Zbierz wykryte linie (może być 0, 1 lub 2)
        detected_lines = []
        
        if best_ascending['score'] > 0:
            detected_lines.append({
                'type': 'ascending',
                'slope': best_ascending['slope'],
                'intercept': best_ascending['intercept'],
                'score': best_ascending['score'],
                'used_minima': best_ascending['used']
            })
        
        if best_descending['score'] > 0:
            detected_lines.append({
                'type': 'descending',
                'slope': best_descending['slope'],
                'intercept': best_descending['intercept'],
                'score': best_descending['score'],
                'used_minima': best_descending['used']
            })
        
        # Jeśli nie wykryto żadnej linii, zwróć pustą listę
        if not detected_lines:
            return []
        
        # Przygotuj dane w formacie wymaganym przez find_hierarchical_parallel_lines
        # (wykonaj raz, użyj dla wszystkich linii)
        from scipy.signal import argrelextrema
        
        results = []  # Lista wyników dla wszystkich wykrytych linii
        
        # Konwertuj ekstrema na DataFrame
        extrema_data = []
        for idx in argrelextrema(lookback_df['High'].values, np.greater, order=5)[0]:
            extrema_data.append({
                'datetime': lookback_df.iloc[idx].name if hasattr(lookback_df.iloc[idx], 'name') else idx,
                'price': lookback_df.iloc[idx]['High'],
                'type': 'high'
            })
        for idx in argrelextrema(lookback_df['Low'].values, np.less, order=5)[0]:
            extrema_data.append({
                'datetime': lookback_df.iloc[idx].name if hasattr(lookback_df.iloc[idx], 'name') else idx,
                'price': lookback_df.iloc[idx]['Low'],
                'type': 'low'
            })
        extrema_df = pd.DataFrame(extrema_data)
        
        # Konwertuj impulsy na DataFrame
        impulse_data = []
        for idx in impulses:
            impulse_data.append({
                'datetime': lookback_df.iloc[idx].name if hasattr(lookback_df.iloc[idx], 'name') else idx,
                'price': lookback_df.iloc[idx]['Low'],
                'type': 'impulse'
            })
        impulses_df = pd.DataFrame(impulse_data)
        
        # Dla każdej wykrytej linii oblicz hierarchiczne linie równoległe
        for line in detected_lines:
            base_line = {
                'slope': line['slope'],
                'intercept': line['intercept'],
                'touches': line['used_minima'],
                'score': line['score']
            }
            
            # Wywołaj funkcję hierarchiczną - użyj parametrów z konfiguracji
            hierarchical_supports, hierarchical_resistances = find_hierarchical_parallel_lines(
                lookback_df, 
                base_line, 
                extrema_df, 
                impulses_df,
                num_levels_below=self.hierarchical_levels_below,
                num_levels_above=self.hierarchical_levels_above,
                tolerance=self.hierarchical_tolerance,
                debug=False  # wyłącz debug logi dla każdego dnia (za dużo outputu)
            )
            
            results.append({
                'type': line['type'],
                'slope': line['slope'],
                'intercept': line['intercept'],
                'score': line['score'],
                'used_minima': line['used_minima'],
                'local_maxima': local_maxima,
                'all_minima': all_minima,
                'impulses': impulse_points,
                'hierarchical_supports': hierarchical_supports,
                'hierarchical_resistances': hierarchical_resistances
            })
        
        return results
    
    def _detect_impulses_full(self, df):
        """
        PEŁNA detekcja impulsów z impulse_detector.py (wszystkie 7 kryteriów)
        Zwraca indeksy świeczek będących impulsami
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
            
            # 3. Volume spike
            avg_vol = df.iloc[i-20:i]['Volume'].mean()
            if current['Volume'] > avg_vol * 1.5:
                strength += 1
            
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
            
            # 7. Support retest (price near previous low but holds)
            recent_low = df.iloc[i-20:i]['Low'].min()
            if abs(current['Low'] - recent_low) < 50 and current['Close'] > current['Low'] + body_size * 0.5:
                strength += 1
            
            # Impulse jeśli spełnia min 4 kryteria
            if strength >= 4:
                impulses.append(i)
        
        return impulses

    def _map_support_point_to_datetime(self, point, support_info, df):
        """
        Zamienia punkt support (z kluczem 'index' będącym offsetem od lookback_start_dt)
        na DateTime, ale TYLKO w obrębie okna lookback (lookback_start_dt .. lookback_end_dt).
        Zwraca DateTime lub None jeśli mapping nie jest możliwy.
        """
        try:
            lookback_start = support_info['lookback_start_dt']
            lookback_end = support_info.get('lookback_end_dt', None)
        except Exception:
            return None

        # Ogranicz kandydatów tylko do okna lookback
        candidates = df[(df['DateTime'] >= lookback_start)]
        if lookback_end is not None:
            candidates = candidates[(candidates['DateTime'] <= lookback_end)]

        # Upewnij się, że offset mieści się w oknie
        try:
            offset = int(point['index'])
        except Exception:
            return None

        if offset < 0 or offset >= len(candidates):
            return None

        # Zwróć DateTime tej świeczki
        return candidates.iloc[offset]['DateTime']
    
    def should_enter(self, df, idx):
        """
        Sprawdza breakout dla WSZYSTKICH linii wykrytych dla danego dnia.
        
        Dla każdej linii:
        - LONG (slope > 0): breakout w górę (Close > Support)
        - SHORT (slope < 0): breakout w dół (Close < Resistance)
        
        Zwraca PIERWSZĄ wykrytą okazję (priorytet: LONG przed SHORT).
        """
        # Wymagamy poprzedniej candle (idx >= 1)
        if idx < 1:
            return None
        
        current = df.iloc[idx]
        previous = df.iloc[idx - 1]
        current_dt = current['DateTime']
        current_date = current_dt.date()
        
        # O(1) lookup w dict
        lines_for_today = self.daily_support_data.get(current_date, [])
        
        if not lines_for_today:
            return None
        
        # Sprawdź każdą linię
        for line_info in lines_for_today:
            slope = line_info['slope']
            intercept = line_info['intercept']
            line_type = line_info.get('type', 'ascending')
            
            # Oblicz wartość linii dla tej świeczki
            # Offset: ile świeczek od lookback_start_dt do current_dt
            lookback_start_dt = line_info['lookback_start_dt']
            offset = len(df[(df['DateTime'] >= lookback_start_dt) & (df['DateTime'] < current_dt)])
            line_price = intercept + slope * offset
            
            if not self.retest_mode:
                # IMMEDIATE: breakout
                
                if slope > 0:
                    # LONG: Close przekracza support W GÓRĘ
                    if previous['Close'] <= line_price and current['Close'] > line_price:
                        entry_price = current['Close']
                        sl_price = entry_price - self.risk_pips
                        tp_price = entry_price + self.reward_pips
                        
                        self._logger.info(f"LONG BREAKOUT: {current_dt} | Prev: {previous['Close']:.2f} <= Support: {line_price:.2f} < Close: {current['Close']:.2f}")
                        
                        return {
                            'direction': 'long',
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'tp_price': tp_price,
                            'time': current_dt,
                            'support_price': line_price,
                            'reason': f'Breakout above support {line_price:.2f}'
                        }
                
                elif slope < 0:
                    # SHORT: Close przekracza resistance W DÓŁ
                    if previous['Close'] >= line_price and current['Close'] < line_price:
                        entry_price = current['Close']
                        sl_price = entry_price + self.risk_pips  # SL powyżej dla SHORT
                        tp_price = entry_price - self.reward_pips  # TP poniżej dla SHORT
                        
                        self._logger.info(f"SHORT BREAKOUT: {current_dt} | Prev: {previous['Close']:.2f} >= Resistance: {line_price:.2f} > Close: {current['Close']:.2f}")
                        
                        return {
                            'direction': 'short',
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'tp_price': tp_price,
                            'time': current_dt,
                            'support_price': line_price,  # Używamy tej samej nazwy klucza (ale to resistance dla SHORT)
                            'reason': f'Breakout below resistance {line_price:.2f}'
                        }
            else:
                # RETEST: czeka na powrót do linii i odbicie
                # TODO: implementacja retest logic dla LONG i SHORT
                pass
        
        return None
    
    def check_exit(self, df, idx, trade):
        """
        Sprawdza SL/TP dla LONG i SHORT positions.
        
        LONG: TP gdy High >= tp_price, SL gdy Low <= sl_price
        SHORT: TP gdy Low <= tp_price, SL gdy High >= sl_price
        
        Dodatkowo: jeśli close_at_eod=True, zamyka pozycję na ostatniej świeczce dnia.
        """
        current = df.iloc[idx]
        direction = trade['direction']
        
        # SL/TP sprawdzamy NAJPIERW - mają priorytet nad EOD
        
        if direction == 'long':
            # LONG position
            # Check TP (w górę)
            if current['High'] >= trade['tp_price']:
                pips = trade['tp_price'] - trade['entry_price']
                return {
                    'exit_price': trade['tp_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'TP',
                    'reason': 'Take Profit'
                }
            
            # Check SL (w dół)
            if current['Low'] <= trade['sl_price']:
                pips = trade['sl_price'] - trade['entry_price']
                return {
                    'exit_price': trade['sl_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'SL',
                    'reason': 'Stop Loss'
                }
        
        elif direction == 'short':
            # SHORT position
            # Check TP (w dół)
            if current['Low'] <= trade['tp_price']:
                pips = trade['entry_price'] - trade['tp_price']  # Dodatnie dla SHORT gdy TP w dół
                return {
                    'exit_price': trade['tp_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'TP',
                    'reason': 'Take Profit'
                }
            
            # Check SL (w górę)
            if current['High'] >= trade['sl_price']:
                pips = trade['entry_price'] - trade['sl_price']  # Ujemne dla SHORT przy SL
                return {
                    'exit_price': trade['sl_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'SL',
                    'reason': 'Stop Loss'
                }
        
        # Sprawdź czy to koniec dnia (EOD - End of Day) - tylko gdy SL/TP NIE osiągnięte
        if self.close_at_eod:
            current_date = current['DateTime'].date()
            # Sprawdź czy następna świeczka jest z innego dnia (lub to ostatnia świeczka)
            is_last_candle_of_day = False
            
            if idx < len(df) - 1:
                next_candle = df.iloc[idx + 1]
                next_date = next_candle['DateTime'].date()
                if next_date != current_date:
                    is_last_candle_of_day = True
            else:
                # Ostatnia świeczka w całym DataFrame
                is_last_candle_of_day = True
            
            if is_last_candle_of_day:
                # Zamknij po cenie Close
                exit_price = current['Close']
                if direction == 'long':
                    pips = exit_price - trade['entry_price']
                else:  # short
                    pips = trade['entry_price'] - exit_price
                
                return {
                    'exit_price': exit_price,
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'EOD',
                    'reason': 'End of Day close'
                }
        
        return None
    
    def plot_daily_chart(self, df, date, output_dir='support_charts', show_volume=True, mark_high_low=False, trades=None):
        """Plot daily chart with hierarchical parallel lines (może być wiele linii dla jednego dnia).
        
        Args:
            trades: Lista transakcji do narysowania (opcjonalne)
        """
        import matplotlib.pyplot as plt
        import mplfinance as mpf
        import matplotlib.dates as mdates
        from matplotlib.ticker import NullLocator
        
        # O(1) lookup w dict - WSZYSTKIE support data dla tego dnia (może być wiele - wznosząca i opadająca)
        support_infos = self.daily_support_data.get(date, [])
        
        if not support_infos:
            return
        
        # Znajdź 5 pełnych dni handlowych przed datą analizowaną
        df['Date'] = df['DateTime'].dt.date
        
        # Wszystkie unikalne dni handlowe przed/włącznie z date
        trading_days = sorted(df[df['Date'] <= date]['Date'].unique())
        
        # Weź wymaganą liczbę dni (lookback + 1 analizowany)
        days_needed = self.lookback_days + 1
        if len(trading_days) >= days_needed:
            days_to_show = trading_days[-days_needed:]
        else:
            days_to_show = trading_days
        
        # debug
        #print(f"    Trading days dla {date}: {trading_days[-10:] if len(trading_days) > 10 else trading_days}", flush=True)
        #print(f"    Days to show: {days_to_show}", flush=True)
        
        start_date_plot = days_to_show[0]
        end_date_plot = date
        
        # Filtruj dane
        df_plot = df[(df['Date'] >= start_date_plot) & (df['Date'] <= end_date_plot)].copy()
        df_plot = df_plot.set_index('DateTime')
        
        if len(df_plot) == 0:
            return

        # Debug: ile dni na wykresie
        unique_dates = df_plot.index.date
        num_days = len(set(unique_dates))
        self._logger.debug(f"Wykres {date}: {num_days} dni (od {start_date_plot} do {end_date_plot}), {len(df_plot)} świeczek")
        
        # Przygotuj dane dla mplfinance
        df_plot = df_plot.rename(columns={
            'Open': 'Open',
            'High': 'High', 
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        })
        
        # Dodatkowe linie
        apds = []
        
        # Przetwórz każdą wykrytą linię (może być 0, 1 lub 2)
        for line_idx, support_info in enumerate(support_infos):
            # Oblicz support line values dla wykresu
            slope = support_info['slope']
            intercept = support_info['intercept']
            line_type = support_info.get('type', 'ascending')
            
            self._logger.debug(f"  DEBUG: Line {line_idx+1}/{len(support_infos)} ({line_type}) - slope={slope:.6f}, intercept={intercept:.2f}")
            self._logger.debug(f"  DEBUG: Lookback range DateTime: {support_info['lookback_start_dt']} - {support_info['lookback_end_dt']}")
            
            # Support line została wyznaczona na lookback_df z indeksami 0 do (lookback_candles-1)
            # lookback_start_dt to DateTime pierwszej świeczki w oknie lookback (indeks 0 w lookback_df)
            
            # Dla każdej świeczki w df_plot oblicz wartość support
            support_values = []
            for i, idx_val in enumerate(df_plot.index):
                # Znajdź offset względem lookback_start_dt
                # Ile świeczek minęło od początku lookback do tej świeczki?
                offset_in_lookback = len(df[(df['DateTime'] >= support_info['lookback_start_dt']) & 
                                            (df['DateTime'] < idx_val)])
                
                support_price = intercept + slope * offset_in_lookback
                support_values.append(support_price)
            
            # Użyj unikalnej nazwy kolumny aby uniknąć konfliktów gdy jest wiele linii
            col_prefix = f'Line{line_idx}'
            df_plot[f'{col_prefix}_Support'] = support_values
            
            # Określ kolor głównej linii na podstawie slope
            # WZNOSZĄC (slope > 0) → ZIELONA, OPADAJĄCE (slope < 0) → CZERWONA
            main_line_color = 'red' if slope < 0 else 'green'
            main_line_label = f'R1 Main ({self.lookback_days} days)' if slope < 0 else f'S1 Main ({self.lookback_days} days)'
            
            # Dodaj główną linię (solidna) - label tylko gdy show_legend=True
            main_line_kwargs = {
                'color': main_line_color,
                'width': 1,
                'linestyle': '-',
                'alpha': 0.6
            }
            if self.show_legend:
                main_line_kwargs['label'] = main_line_label
            
            apds.append(mpf.make_addplot(df_plot[f'{col_prefix}_Support'], **main_line_kwargs))
            
            # Dodaj hierarchiczne linie wsparcia PONIŻEJ głównej (S2, S3, S4, S5...)
            # Wszystkie linie hierarchiczne są ZIELONE (wznosząc) i PRZERYWANE
            hierarchical_supports = support_info.get('hierarchical_supports', [])
            for i, supp_line in enumerate(hierarchical_supports):
                supp_slope = supp_line['slope']
                supp_intercept = supp_line['intercept']
                supp_level = supp_line['level']
                supp_offset = supp_line['offset']
                supp_score = supp_line['score']
                
                # Oblicz wartości dla tej linii
                supp_values = []
                for idx_val in df_plot.index:
                    offset_in_lookback = len(df[(df['DateTime'] >= support_info['lookback_start_dt']) & 
                                                (df['DateTime'] < idx_val)])
                    supp_price = supp_intercept + supp_slope * offset_in_lookback
                    supp_values.append(supp_price)
                
                df_plot[f'{col_prefix}_Support_L{supp_level}'] = supp_values
                
                # Wszystkie hierarchiczne linie są zielone i przerywane
                supp_kwargs = {
                    'color': main_line_color,
                    'width': 1,
                    'linestyle': '--',
                    'alpha': 0.6
                }
                if self.show_legend:
                    supp_kwargs['label'] = f'S{supp_level} ({supp_offset:+.0f} pts, {supp_score} p)'
                
                apds.append(
                    mpf.make_addplot(df_plot[f'{col_prefix}_Support_L{supp_level}'], **supp_kwargs)
                )
            
            # Dodaj hierarchiczne linie oporu POWYŻEJ głównej (R2, R3, R4, R5...)
            # Wszystkie linie hierarchiczne są CZERWONE (opadające) i PRZERYWANE
            hierarchical_resistances = support_info.get('hierarchical_resistances', [])
            for i, res_line in enumerate(hierarchical_resistances):
                res_slope = res_line['slope']
                res_intercept = res_line['intercept']
                res_level = res_line['level']
                res_offset = res_line['offset']
                res_score = res_line['score']
                
                # Oblicz wartości dla tej linii
                res_values = []
                for idx_val in df_plot.index:
                    offset_in_lookback = len(df[(df['DateTime'] >= support_info['lookback_start_dt']) & 
                                                (df['DateTime'] < idx_val)])
                    res_price = res_intercept + res_slope * offset_in_lookback
                    res_values.append(res_price)
                
                df_plot[f'{col_prefix}_Resistance_L{res_level}'] = res_values
                
                # Wszystkie hierarchiczne linie są czerwone i przerywane
                res_kwargs = {
                    'color': main_line_color,
                    'width': 1,
                    'linestyle': '--',
                    'alpha': 0.6
                }
                if self.show_legend:
                    res_kwargs['label'] = f'R{res_level} ({res_offset:+.0f} pts, {res_score} p)'
                
                apds.append(
                    mpf.make_addplot(df_plot[f'{col_prefix}_Resistance_L{res_level}'], **res_kwargs)
                )

            # Optionally mark the exact minima used to fit the support line (and highs if desired)
            if mark_high_low:
                try:
                    # support_points stored earlier are in terms of lookback_df index and price
                    # Use helper _map_support_point_to_datetime to convert offsets to DateTime strictly inside lookback window
                    support_points = support_info.get('support_points', [])

                    # Build marker arrays aligned with df_plot index
                    used_min_markers = np.array([np.nan] * len(df_plot), dtype=float)   # minima użyte do dopasowania (yellow)
                    all_min_markers = np.array([np.nan] * len(df_plot), dtype=float)    # wszystkie lokalne minima (red)
                    exact_high_markers = np.array([np.nan] * len(df_plot), dtype=float) # lokalne maksima (green)
                    impulse_markers = np.array([np.nan] * len(df_plot), dtype=float)    # impulses (magenta)

                    # For each support point: map strictly within lookback window
                    lookback_start = support_info['lookback_start_dt']
                    for p in support_points:
                        point_dt = self._map_support_point_to_datetime(p, support_info, df)
                        if point_dt is None:
                            # point lies outside lookback window — skip
                            continue
                        if point_dt in df_plot.index:
                            plot_idx = df_plot.index.get_loc(point_dt)
                            used_min_markers[plot_idx] = float(p['price'])

                    # exact highs
                    local_maxima = support_info.get('local_maxima', [])
                    if local_maxima:
                        for hm in local_maxima:
                            dt = self._map_support_point_to_datetime(hm, support_info, df)
                            if dt is None:
                                continue
                            if dt in df_plot.index:
                                idx_pos = df_plot.index.get_loc(dt)
                                exact_high_markers[idx_pos] = float(hm['price'])

                    # all minima
                    all_minima = support_info.get('all_minima', [])
                    if all_minima:
                        for mm in all_minima:
                            dtm = self._map_support_point_to_datetime(mm, support_info, df)
                            if dtm is None:
                                continue
                            if dtm in df_plot.index:
                                idx_pos = df_plot.index.get_loc(dtm)
                                all_min_markers[idx_pos] = float(mm['price'])

                    # impulses
                    impulse_pts = support_info.get('impulses', [])
                    if impulse_pts:
                        for im in impulse_pts:
                            dt_imp = self._map_support_point_to_datetime(im, support_info, df)
                            if dt_imp is None:
                                continue
                            if dt_imp in df_plot.index:
                                idx_pos = df_plot.index.get_loc(dt_imp)
                                impulse_markers[idx_pos] = float(im['price'])
                    
                    # Dodaj markery do apds - label tylko gdy show_legend=True
                    if not np.all(np.isnan(used_min_markers)):
                        kwargs = {'type': 'scatter', 'markersize': 50, 'marker': 'o', 'color': 'yellow'}
                        if self.show_legend:
                            kwargs['label'] = f'Line{line_idx} Used Minima'
                        apds.append(mpf.make_addplot(used_min_markers, **kwargs))
                    if not np.all(np.isnan(all_min_markers)):
                        kwargs = {'type': 'scatter', 'markersize': 30, 'marker': 'x', 'color': 'red'}
                        if self.show_legend:
                            kwargs['label'] = f'Line{line_idx} All Minima'
                        apds.append(mpf.make_addplot(all_min_markers, **kwargs))
                    if not np.all(np.isnan(exact_high_markers)):
                        kwargs = {'type': 'scatter', 'markersize': 30, 'marker': 'x', 'color': 'green'}
                        if self.show_legend:
                            kwargs['label'] = f'Line{line_idx} Highs'
                        apds.append(mpf.make_addplot(exact_high_markers, **kwargs))
                    if not np.all(np.isnan(impulse_markers)):
                        kwargs = {'type': 'scatter', 'markersize': 40, 'marker': '^', 'color': 'magenta'}
                        if self.show_legend:
                            kwargs['label'] = f'Line{line_idx} Impulses'
                        apds.append(mpf.make_addplot(impulse_markers, **kwargs))
                except Exception as e:
                    self._logger.debug(f'mark_high_low enabled but failed to place exact support points for line {line_idx}: {e}')

        
        # Oznacz breakouty (jeśli istnieją w danych)
        # NOTE: Breakouty są już wykrywane w should_enter(), więc ta sekcja jest opcjonalna
        # Możemy dodać wizualizację breakoutów jeśli potrzebne
        breakouts = df_plot[df_plot.index.date == date]
        if len(breakouts) > 0 and 'Support_Price' in df.columns:
            # Znajdź breakouty
            for idx in breakouts.index:
                if idx in df.index:
                    row_idx = df.index.get_loc(idx)
                    if row_idx > 0:
                        current = df.iloc[row_idx]
                        previous = df.iloc[row_idx - 1]
                        support_price = current.get('Support_Price')
                        if not pd.isna(support_price):
                            # Breakout w górę (LONG)
                            if previous['Close'] <= support_price and current['Close'] > support_price:
                                breakout_marker = [np.nan] * len(df_plot)
                                if idx in df_plot.index:
                                    plot_idx = df_plot.index.get_loc(idx)
                                    breakout_marker[plot_idx] = current['Close']
                                    kwargs = {'marker': 'o', 'markersize': 100, 'mfc': 'none', 'mec': 'green', 'linestyle': 'None'}
                                    if self.show_legend:
                                        kwargs['label'] = 'Breakout UP'
                                    apds.append(mpf.make_addplot(breakout_marker, **kwargs))
                            # Breakout w dół (SHORT)
                            elif previous['Close'] >= support_price and current['Close'] < support_price:
                                breakout_marker = [np.nan] * len(df_plot)
                                if idx in df_plot.index:
                                    plot_idx = df_plot.index.get_loc(idx)
                                    breakout_marker[plot_idx] = current['Close']
                                    kwargs = {'marker': 'o', 'markersize': 100, 'mfc': 'none', 'mec': 'red', 'linestyle': 'None'}
                                    if self.show_legend:
                                        kwargs['label'] = 'Breakout DOWN'
                                    apds.append(mpf.make_addplot(breakout_marker, **kwargs))
        
        # Wykres
        vlines_dates = df_plot.resample('D').first().index.tolist()
        # Filtruj vlines - usuwaj daty sprzed pierwszej świeczki
        vlines_dates = [d for d in vlines_dates if d >= df_plot.index[0]]
        
        # DEBUG: ile świeczek w każdej sekcji dziennej (log)
        self._logger.debug(f"Podział na dni dla wykresu {date}:")
        for i, vline_date in enumerate(vlines_dates):
            if i < len(vlines_dates) - 1:
                # Świeczki między tym a następnym vline
                day_candles = df_plot[(df_plot.index >= vline_date) & (df_plot.index < vlines_dates[i+1])]
                self._logger.debug(f"{vline_date.strftime('%Y-%m-%d')}: {len(day_candles)} świeczek")
            else:
                # Ostatni dzień - do końca wykresu
                day_candles = df_plot[df_plot.index >= vline_date]
                self._logger.debug(f"{vline_date.strftime('%Y-%m-%d')}: {len(day_candles)} świeczek (ostatni dzień)")
        
        fig, axes = mpf.plot(
            df_plot[['Open', 'High', 'Low', 'Close', 'Volume']],
            type='candle',
            style='charles',
            addplot=apds,
            volume=show_volume,
            title=f'Support Breakout - {date}',
            figsize=(14, 8),
            returnfig=True,
            vlines=dict(vlines=vlines_dates, linewidths=0.5, colors='gray', alpha=0.5) if vlines_dates else None,
            show_nontrading=False
        )
        
        # Wyłącz siatkę
        axes[0].grid(False)
        if show_volume and len(axes) > 1:
            axes[1].grid(False)
        
        # Podpisy osi X raz dziennie
        # mplfinance używa numeracji świeczek, nie DateTime - musimy ręcznie ustawić podpisy
        unique_days = df_plot.resample('D').first()
        if len(unique_days) > 0:
            tick_positions = []
            tick_labels = []
            for day_start in unique_days.index:
                if day_start in df_plot.index:
                    tick_positions.append(df_plot.index.get_loc(day_start))
                    tick_labels.append(day_start.strftime('%Y-%m-%d'))
            
            if len(tick_positions) > 0:
                axes[0].set_xticks(tick_positions)
                axes[0].set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
        
        # Zapisz
        os.makedirs(output_dir, exist_ok=True)
        filename = f'{output_dir}/support_{date}.png'
        # Before saving, draw hollow markers on top of mplfinance figure using axes[0].scatter
        ax = axes[0]

        def _scatter_from_array(arr, color, markersize, marker='o', hollow=True, label=None):
            try:
                arr_np = np.array(arr, dtype=float)
            except Exception:
                return
            mask = ~np.isnan(arr_np)
            if not mask.any():
                return
            x = np.where(mask)[0]
            y = arr_np[mask]
            s = max(8, markersize)  # basic size
            
            # Label tylko gdy show_legend=True
            actual_label = label if self.show_legend else None
            
            if marker == 'x':
                ax.scatter(x, y, s=s, c=color, marker='x', zorder=6, label=actual_label)
            else:
                if hollow:
                    ax.scatter(x, y, s=s, facecolors='none', edgecolors=color, linewidths=1.2, marker=marker, zorder=6, label=actual_label)
                else:
                    ax.scatter(x, y, s=s, c=color, marker=marker, zorder=6, label=actual_label)
        if mark_high_low:
            # Draw support points (yellow hollow)
            _scatter_from_array(used_min_markers, 'yellow', 120, marker='o', hollow=True, label='Support Points')
            # Draw all minima (red hollow)
            _scatter_from_array(all_min_markers, 'red', 80, marker='o', hollow=True, label='All Minima')
            # Draw local highs (green hollow)
            _scatter_from_array(exact_high_markers, 'green', 120, marker='o', hollow=True, label='Local Highs')
            # Draw impulses (magenta x)
            _scatter_from_array(impulse_markers, 'magenta', 80, marker='x', hollow=False, label='Impulses')
        
        # Rysuj transakcje na wykresie
        if trades:
            for trade in trades:
                # Sprawdź czy transakcja jest w zakresie tego wykresu
                entry_time = pd.to_datetime(trade['time'])
                exit_time = pd.to_datetime(trade['exit_time'])
                
                # Pomiń jeśli transakcja nie jest w zakresie wykresu
                if entry_time not in df_plot.index and exit_time not in df_plot.index:
                    continue
                
                direction = trade['direction']
                entry_price = trade['entry_price']
                exit_price = trade['exit_price']
                sl_price = trade['sl_price']
                tp_price = trade['tp_price']
                
                # Kolory: zielony=LONG, czerwony=SHORT
                entry_color = 'green' if direction == 'long' else 'red'
                exit_color = entry_color
                
                # Pozycje w wykresie
                entry_idx = df_plot.index.get_loc(entry_time) if entry_time in df_plot.index else None
                exit_idx = df_plot.index.get_loc(exit_time) if exit_time in df_plot.index else None
                
                # Offset dla strzałek (w jednostkach świeczek) aby nie zasłaniały punktów
                arrow_offset = 3
                
                # Strzałka wejścia (w prawo, przesunięta w prawo)
                if entry_idx is not None:
                    ax.scatter(entry_idx - arrow_offset, entry_price, s=30, marker='>', color=entry_color, 
                              edgecolors='black', linewidths=1, zorder=10, alpha=0.7)
                
                # Strzałka wyjścia (w lewo, przesunięta w lewo)
                if exit_idx is not None:
                    ax.scatter(exit_idx + arrow_offset, exit_price, s=30, marker='<', color=exit_color, 
                              edgecolors='black', linewidths=1, zorder=10, alpha=0.7)
                
                # Linie SL (czerwona przerywana) i TP (zielona przerywana)
                if entry_idx is not None and exit_idx is not None:
                    x_range = [entry_idx, exit_idx]
                    
                    # SL
                    ax.plot(x_range, [sl_price, sl_price], color='red', linestyle='--', 
                           linewidth=1, zorder=8, alpha=0.7)
                    
                    # TP
                    ax.plot(x_range, [tp_price, tp_price], color='green', linestyle='--', 
                           linewidth=1, zorder=8, alpha=0.7)
                    
                    # Niebieska przerywana między wejściem a wyjściem (ukośna od entry do exit)
                    ax.plot(x_range, [entry_price, exit_price], color='blue', linestyle='--', 
                           linewidth=1, zorder=9, alpha=0.7)
        
        # Ensure legend is present and remembered for tests (działa dla wszystkich elementów)
        handles, labels = ax.get_legend_handles_labels()
        
        if labels and self.show_legend:
            try:
                ax.legend(handles, labels, loc='lower right', fontsize=9)
            except Exception:
                # ignore legend failures on some mpl backends
                pass
        self._last_legend_labels = labels if mark_high_low else []

        fig.savefig(filename, dpi=self.chart_dpi, bbox_inches='tight')
        
        # Loguj informacje o wygenerowanym obrazku
        file_size = os.path.getsize(filename) / 1024  # rozmiar w KB
        self._logger.info(f"Wygenerowano wykres: {filename} | DPI: {self.chart_dpi} "
                          "| Rozmiar: {file_size:.1f} KB | Linie: {len(support_infos)} | Legend: {self.show_legend}")
        
        plt.close(fig)
        
        return filename