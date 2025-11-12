import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
# Use non-interactive backend for headless environments/tests
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
import os
import logging
from impulse_detector import find_hierarchical_parallel_lines

class SupportBreakoutStrategy:
    """
    Strategia breakout powyżej głównej linii support z hierarchicznymi liniami równoległymi.
    
    Główne cechy:
    - Support wyznaczany z poprzednich N dni (domyślnie 5)
    - Wykrywanie hierarchicznych linii równoległych (S2, S3, R2, R3)
    - Tylko pozycje LONG
    - Integracja z impulse_detector dla wykrywania impulsów
    
    Hierarchiczne linie:
    - S1: główna linia wsparcia (czerwona, ciągła)
    - S2, S3: linie wsparcia PONIŻEJ głównej (równoległe, offset ujemny)
    - R2, R3: linie oporu POWYŻEJ głównej (równoległe, offset dodatni)
    
    Wszystkie linie są RÓWNOLEGŁE (ten sam slope) i przesunięte pionowo
    o odległości d₁, 2×d₁, 3×d₁ (struktura równoodległych poziomów).
    
    Only LONG positions.
    """
    
    def __init__(self, lookback_days=5, risk_pips=50, reward_ratio=3, 
                 retest_mode=False, retest_tolerance=30, min_slope=0.1):
        self.lookback_days = lookback_days
        self.lookback_candles = lookback_days * 96  # 5 dni * 96 świeczek M15/dzień
        self.risk_pips = risk_pips
        self.reward_pips = risk_pips * reward_ratio
        self.reward_ratio = reward_ratio
        self.retest_mode = retest_mode  # False = immediate, True = czeka na retest
        self.retest_tolerance = retest_tolerance  # odległość od linii dla retesту
        self.min_slope = min_slope  # Minimalny slope dla akceptacji linii wsparcia
        
        self.support_lines = {}  # Cache dla support lines
        self.daily_support_data = []  # Lista: {date, slope, intercept, lookback_start, lookback_end}
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
                    
                    # Oblicz support line (zwraca dict z slope/intercept i punktami użytymi do dopasowania)
                    cached = self._find_support_line(lookback_df_indexed)
                    cached_slope = cached.get('slope', 0)
                    cached_intercept = cached.get('intercept', 0)
                    cached_used_minima = cached.get('used_minima', [])
                    cached_local_maxima = cached.get('local_maxima', [])
                    cached_all_minima = cached.get('all_minima', [])
                    cached_impulses = cached.get('impulses', [])
                    
                    # DEBUG: sprawdź kierunek linii
                    #if cached_slope > 0:
                    #    print(f"  ✓ {current_date}: Support WZNOSZĄCA (slope={cached_slope:.6f}, intercept={cached_intercept:.2f})", flush=True)
                    #elif cached_slope < 0:
                    #    print(f"  ✗ {current_date}: Support OPADAJĄCA (slope={cached_slope:.6f}, intercept={cached_intercept:.2f})", flush=True)
                    #else:
                    #    print(f"  - {current_date}: Support PŁASKA (slope={cached_slope:.6f}, intercept={cached_intercept:.2f})", flush=True)
                    
                    # Zapisz info o support dla tego dnia (do wizualizacji)
                    # Używamy DateTime zamiast indeksów (bo indeksy mogą być zresetowane przez backtest_engine)
                    lookback_start_dt = df.iloc[idx - self.lookback_candles]['DateTime']
                    lookback_end_dt = df.iloc[idx - 1]['DateTime']
                    
                    self.daily_support_data.append({
                        'date': current_date,
                        'slope': cached_slope,
                        'intercept': cached_intercept,
                        'support_points': cached_used_minima,  # lista minimów (DateTime, price)
                        'local_maxima': cached_local_maxima,
                        'all_minima': cached_all_minima,
                        'impulses': cached_impulses,
                        'hierarchical_supports': cached.get('hierarchical_supports', []),  # linie wsparcia poniżej głównej
                        'hierarchical_resistances': cached.get('hierarchical_resistances', []),  # linie oporu powyżej głównej
                        'lookback_start_dt': lookback_start_dt,  # DateTime początku lookback
                        'lookback_end_dt': lookback_end_dt,       # DateTime końca lookback
                        'day_start_idx': idx  # Index początku tego dnia w df (dla backtestu)
                    })
                    
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
                
                # Znajdź lookback_start_dt dla tego dnia z daily_support_data
                lookback_start_dt = None
                for info in self.daily_support_data:
                    if info['date'] == row_date:
                        lookback_start_dt = info['lookback_start_dt']
                        break
                
                if lookback_start_dt is None:
                    support_prices.append(np.nan)
                    continue
                
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

        # 4. Znajdź najlepszą WZNOSZĄCĄ linię (bounce/breakout scoring jak w impulse_detector)
        best_slope = 0
        best_intercept = 0
        best_score = -1
        best_used_minima = []

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                p1, p2 = points[i], points[j]

                if p2['index'] == p1['index']:
                    continue

                slope = (p2['price'] - p1['price']) / (p2['index'] - p1['index'])

                # WYMÓG: tylko wznoszące linie (slope >= min_slope) dla strategii long
                if slope < self.min_slope:
                    continue

                intercept = p1['price'] - slope * p1['index']

                # Scoring: impulses mają wyższą wagę
                score = 0
                impulse_hits = 0
                minima_hits = 0
                for p in points:
                    expected_price = slope * p['index'] + intercept
                    dist = abs(p['price'] - expected_price)

                    if dist <= 30:  # tolerance
                        weight = 2 if p['type'] == 'impulse' else 1
                        score += weight
                        if p['type'] == 'impulse':
                            impulse_hits += 1
                        elif p['type'] == 'minimum':
                            minima_hits += 1

                if score > best_score:
                    best_score = score
                    best_slope = slope
                    best_intercept = intercept
                    best_impulse_hits = impulse_hits
                    best_minima_hits = minima_hits
                    # Zapisz punkty, które trafiły w tolerancję (użyte do dopasowania)
                    used = []
                    for p in points:
                        expected_price = slope * p['index'] + intercept
                        dist = abs(p['price'] - expected_price)
                        if dist <= 30:
                            used.append({'index': p['index'], 'price': float(p['price'])})
                    best_used_minima = used

        #print(f"  DEBUG: Najlepsza linia: {best_impulse_hits} impulsów, {best_minima_hits} minimów (score={best_score})")
        
        # Teraz wykryj hierarchiczne linie równoległe używając find_hierarchical_parallel_lines()
        base_line = {
            'slope': best_slope,
            'intercept': best_intercept,
            'touches': best_used_minima,
            'score': best_score
        }
        
        # Przygotuj dane w formacie wymaganym przez find_hierarchical_parallel_lines
        # Funkcja oczekuje DataFrame z kolumnami: datetime, price, type
        
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
        
        # Wywołaj funkcję hierarchiczną (2 poziomy poniżej, 2 powyżej)
        hierarchical_supports, hierarchical_resistances = find_hierarchical_parallel_lines(
            lookback_df, 
            base_line, 
            extrema_df, 
            impulses_df,
            num_levels_below=2,
            num_levels_above=2,
            tolerance=30,
            debug=False  # wyłącz debug logi dla każdego dnia (za dużo outputu)
        )
        
        return {
            'slope': best_slope,
            'intercept': best_intercept,
            'score': best_score,
            'used_minima': best_used_minima,
            'local_maxima': local_maxima,
            'all_minima': all_minima,
            'impulses': impulse_points,
            'hierarchical_supports': hierarchical_supports,
            'hierarchical_resistances': hierarchical_resistances
        }
    
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
        Sprawdza breakout powyżej support line
        
        IMMEDIATE mode: Close > Support_Price
        RETEST mode: Close wrócił do Support +/- tolerance i odbił
        """
        # Wymagamy poprzedniej candle (idx >= 1)
        if idx < 1:
            return None
        
        current = df.iloc[idx]
        previous = df.iloc[idx - 1]
        
        # Brak support line
        if pd.isna(current['Support_Price']):
            return None
        
        support_price = current['Support_Price']
        
        if not self.retest_mode:
            # IMMEDIATE: breakout - Close przekracza support
            if previous['Close'] <= support_price and current['Close'] > support_price:
                entry_price = current['Close']
                sl_price = entry_price - self.risk_pips
                tp_price = entry_price + self.reward_pips
                
                self._logger.info(f"BREAKOUT: {current['DateTime']} | Prev Close: {previous['Close']:.2f} <= Support: {support_price:.2f} < Close: {current['Close']:.2f}")
                
                return {
                    'direction': 'long',
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'time': current['DateTime'],
                    'support_price': support_price,
                    'reason': f'Breakout above support {support_price:.2f}'
                }
        else:
            # RETEST: czeka na powrót do linii i odbicie
            # TODO: implementacja retest logic
            pass
        
        return None
    
    def check_exit(self, df, idx, trade):
        """Sprawdza SL/TP"""
        current = df.iloc[idx]
        
        # Check TP
        if current['High'] >= trade['tp_price']:
            pips = trade['tp_price'] - trade['entry_price']
            return {
                'exit_price': trade['tp_price'],
                'exit_time': current['DateTime'],
                'pips': pips,
                'result': 'TP',
                'reason': 'Take Profit'
            }
        
        # Check SL
        if current['Low'] <= trade['sl_price']:
            pips = trade['sl_price'] - trade['entry_price']
            return {
                'exit_price': trade['sl_price'],
                'exit_time': current['DateTime'],
                'pips': pips,
                'result': 'SL',
                'reason': 'Stop Loss'
            }
        
        return None
    
    def plot_daily_chart(self, df, date, output_dir='support_charts', show_volume=True, mark_high_low=False):
        """Plot daily chart with hierarchical parallel lines."""
        import matplotlib.pyplot as plt
        import mplfinance as mpf
        import matplotlib.dates as mdates
        from matplotlib.ticker import NullLocator
        
        # Znajdź support data dla tego dnia
        support_info = None
        for info in self.daily_support_data:
            if info['date'] == date:
                support_info = info
                break
        
        if not support_info:
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
        
        # Oblicz support line values dla wykresu
        slope = support_info['slope']
        intercept = support_info['intercept']
        
        self._logger.debug(f"  DEBUG: Support line params - slope={slope:.6f}, intercept={intercept:.2f}")
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
            
            # Debug pierwszych i ostatnich 3 świeczek
            #if i < 3 or i >= len(df_plot) - 3:
            #    candle_low = df_plot.iloc[i]['Low']
            #    candle_high = df_plot.iloc[i]['High']
            #    print(f"    Candle {i} ({idx_val}): offset={offset_in_lookback}, support={support_price:.2f}, Low={candle_low:.2f}, High={candle_high:.2f}", flush=True)
        
        df_plot['Support'] = support_values
        
        # Dodatkowe linie
        apds = [
            mpf.make_addplot(df_plot['Support'], color='red', width=4, linestyle='-', label=f'S1 Main ({self.lookback_days} days)', alpha=1.0)
        ]
        
        # Dodaj hierarchiczne linie wsparcia PONIŻEJ głównej (S2, S3, ...)
        hierarchical_supports = support_info.get('hierarchical_supports', [])
        support_colors = ['darkred', 'maroon', 'brown', 'firebrick']
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
            
            df_plot[f'Support_L{supp_level}'] = supp_values
            
            color = support_colors[i % len(support_colors)]
            linestyle = '--' if i == 0 else ':'
            linewidth = 3 if i == 0 else 2
            
            apds.append(
                mpf.make_addplot(df_plot[f'Support_L{supp_level}'], 
                                color=color, 
                                width=linewidth, 
                                linestyle=linestyle, 
                                label=f'S{supp_level} ({supp_offset:+.0f} pts, {supp_score} p)',
                                alpha=0.8)
            )
        
        # Dodaj hierarchiczne linie oporu POWYŻEJ głównej (R2, R3, ...)
        hierarchical_resistances = support_info.get('hierarchical_resistances', [])
        resistance_colors = ['blue', 'dodgerblue', 'deepskyblue', 'lightskyblue']
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
            
            df_plot[f'Resistance_L{res_level}'] = res_values
            
            color = resistance_colors[i % len(resistance_colors)]
            linestyle = '--' if i == 0 else ':'
            linewidth = 3 if i == 0 else 2
            
            apds.append(
                mpf.make_addplot(df_plot[f'Resistance_L{res_level}'], 
                                color=color, 
                                width=linewidth, 
                                linestyle=linestyle, 
                                label=f'R{res_level} ({res_offset:+.0f} pts, {res_score} p)',
                                alpha=0.8)
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
            except Exception as e:
                self._logger.debug(f'mark_high_low enabled but failed to place exact support points: {e}')
        
        # Oznacz breakouty
        breakouts = df_plot[df_plot.index.date == date]
        if len(breakouts) > 0 and 'Support_Price' in df.columns:
            # Znajdź breakouty
            for idx in breakouts.index:
                if idx in df.index:
                    row_idx = df.index.get_loc(idx)
                    if row_idx > 0:
                        current = df.iloc[row_idx]
                        previous = df.iloc[row_idx - 1]
                        if not pd.isna(current.get('Support_Price')) and previous['Close'] <= current['Support_Price'] and current['Close'] > current['Support_Price']:
                            # To jest breakout
                            breakout_marker = [np.nan] * len(df_plot)
                            if idx in df_plot.index:
                                plot_idx = df_plot.index.get_loc(idx)
                                breakout_marker[plot_idx] = current['Close']
                                apds.append(mpf.make_addplot(breakout_marker, marker='o', markersize=100, mfc='none', mec='green', linestyle='None', label='Breakout'))
        
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
            if marker == 'x':
                ax.scatter(x, y, s=s, c=color, marker='x', zorder=6, label=label)
            else:
                if hollow:
                    ax.scatter(x, y, s=s, facecolors='none', edgecolors=color, linewidths=1.2, marker=marker, zorder=6, label=label)
                else:
                    ax.scatter(x, y, s=s, c=color, marker=marker, zorder=6, label=label)
        if mark_high_low:
            # Draw support points (yellow hollow)
            _scatter_from_array(used_min_markers, 'yellow', 120, marker='o', hollow=True, label='Support Points')
            # Draw all minima (red hollow)
            _scatter_from_array(all_min_markers, 'red', 80, marker='o', hollow=True, label='All Minima')
            # Draw local highs (green hollow)
            _scatter_from_array(exact_high_markers, 'green', 120, marker='o', hollow=True, label='Local Highs')
            # Draw impulses (magenta x)
            _scatter_from_array(impulse_markers, 'magenta', 80, marker='x', hollow=False, label='Impulses')

            # Ensure legend is present and remembered for tests
            handles, labels = ax.get_legend_handles_labels()
            if labels:
                try:
                    ax.legend(handles, labels, loc='lower right', fontsize=9)
                except Exception:
                    # ignore legend failures on some mpl backends
                    pass
            self._last_legend_labels = labels
        else:
            # No markers drawn
            self._last_legend_labels = []

        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return filename