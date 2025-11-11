import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mplfinance as mpf
import os

class SupportBreakoutStrategy:
    """
    Strategia breakout powyżej głównej linii support
    Support wyznaczany z poprzednich 5 dni
    Only LONG positions
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
                    
                    # Oblicz support line (zwraca slope/intercept dla indeksów 0-479)
                    cached_slope, cached_intercept = self._find_support_line(lookback_df_indexed)
                    
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
                        'lookback_start_dt': lookback_start_dt,  # DateTime początku lookback
                        'lookback_end_dt': lookback_end_dt,       # DateTime końca lookback
                        'day_start_idx': idx  # Index początku tego dnia w df (dla backtestu)
                    })
                    
                    if days_calculated % 10 == 0:
                        print(f"  Przetworzono {days_calculated} dni... ({current_date})", flush=True)
                
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
        Znajduje główną linię support używając PEŁNEJ logiki z impulse_detector:
        - Wykrywa impulsy z wszystkimi kryteriami
        - Znajduje lokalne minima/maxima
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
        
        #print(f"  DEBUG: Najlepsza linia: {best_impulse_hits} impulsów, {best_minima_hits} minimów (score={best_score})")
        return best_slope, best_intercept
    
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
    
    def should_enter(self, df, idx):
        """
        Sprawdza breakout powyżej support line
        
        IMMEDIATE mode: Close > Support_Price
        RETEST mode: Close wrócił do Support ±tolerance i odbił
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
                
                print(f"  🔔 BREAKOUT: {current['DateTime']} | Prev Close: {previous['Close']:.2f} <= Support: {support_price:.2f} < Close: {current['Close']:.2f}", flush=True)
                
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
    
    def plot_daily_chart(self, df, date, output_dir='support_charts', show_volume=True):
        """
        Generuje wykres dla danego dnia z support line + zakres lookback
        Pokazuje zawsze 5 PEŁNYCH dni handlowych + analizowany dzień
        """
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
        print(f"    Wykres {date}: {num_days} dni (od {start_date_plot} do {end_date_plot}), {len(df_plot)} świeczek", flush=True)
        
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
        
        #print(f"  DEBUG: Support line params - slope={slope:.6f}, intercept={intercept:.2f}", flush=True)
        #print(f"  DEBUG: Lookback range DateTime: {support_info['lookback_start_dt']} - {support_info['lookback_end_dt']}", flush=True)
        
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
            mpf.make_addplot(df_plot['Support'], color='red', width=1.5, linestyle='--', label=f'Support ({self.lookback_days}d)')
        ]
        
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
                                apds.append(mpf.make_addplot(breakout_marker, type='scatter', markersize=100, marker='o', color='green', label='Breakout'))
        
        # Wykres
        vlines_dates = df_plot.resample('D').first().index.tolist()
        # Filtruj vlines - usuwaj daty sprzed pierwszej świeczki
        vlines_dates = [d for d in vlines_dates if d >= df_plot.index[0]]
        
        # DEBUG: ile świeczek w każdej sekcji dziennej
        print(f"    DEBUG: Podział na dni dla wykresu {date}:")
        for i, vline_date in enumerate(vlines_dates):
            if i < len(vlines_dates) - 1:
                # Świeczki między tym a następnym vline
                day_candles = df_plot[(df_plot.index >= vline_date) & (df_plot.index < vlines_dates[i+1])]
                print(f"      {vline_date.strftime('%Y-%m-%d')}: {len(day_candles)} świeczek")
            else:
                # Ostatni dzień - do końca wykresu
                day_candles = df_plot[df_plot.index >= vline_date]
                print(f"      {vline_date.strftime('%Y-%m-%d')}: {len(day_candles)} świeczek (ostatni dzień)")
        
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
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return filename