import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging

# Setup logger to write to same debug file used by strategy (support_charts/debug.txt)
import sys
main_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if len(sys.argv) > 0 else os.getcwd()
logs_dir = os.path.join(main_dir, 'support_charts')
os.makedirs(logs_dir, exist_ok=True)
_log_path = os.path.join(logs_dir, 'debug.txt')
_logger = logging.getLogger('aifx_debug')
if not _logger.handlers:
    _fh = logging.FileHandler(_log_path, mode='a', encoding='utf-8')
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    _logger.addHandler(_fh)
_logger.setLevel(logging.DEBUG)

class BacktestEngine:
    """
    Silnik backtestingu - testuje strategię na danych historycznych
    
    Psychologia: Backtest pokazuje jak strategia radziła sobie z przeszłymi
    zmianami sentymentu - ale przeszłe wyniki nie gwarantują przyszłych!
    """
    
    def __init__(self, initial_capital=10000, risk_per_trade_pct=2.0):
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct  # % kapitału na trade
        
    def run(self, df, strategy, start_date=None, end_date=None):
        """Uruchamia backtest strategii"""
        
        # Rozszerz zakres dla lookback (potrzebujemy danych sprzed start_date)
        lookback_days = getattr(strategy, 'lookback_days', 5)
        
        if start_date:
            from datetime import timedelta
            start_dt = pd.to_datetime(start_date)
            # Weź dane od (start_date - lookback_days * 2) dla pewności że mamy wystarczająco danych
            # *2 bo dni kalendarzowe vs dni handlowe
            extended_start = start_dt - timedelta(days=lookback_days * 2)
            df_for_calc = df[df['DateTime'] >= extended_start].copy()
        else:
            df_for_calc = df.copy()
        
        if end_date:
            # end_date oznacza "cały dzień end_date", więc filtruj < następny dzień 00:00
            from datetime import timedelta
            end_dt_exclusive = pd.to_datetime(end_date) + timedelta(days=1)
            df_for_calc = df_for_calc[df_for_calc['DateTime'] < end_dt_exclusive]
        
        # Oblicz wskaźniki na rozszerzonym zakresie (support dla WSZYSTKICH dni w extended range)
        df_for_calc = strategy.calculate_indicators(df_for_calc)
        
        # Filtruj do właściwego zakresu testowego (ale wskaźniki już obliczone)
        # Zachowaj 1 candlestick przed start_date dla porównania previous candle
        if start_date:
            start_dt_exact = pd.to_datetime(start_date)
            # Znajdź świeczki >= start_date
            mask_from_start = df_for_calc['DateTime'] >= start_dt_exact
            
            if mask_from_start.sum() > 0:
                # Index pierwszej świeczki >= start_date w df_for_calc
                first_idx_in_df = mask_from_start.idxmax()  # Zwraca index pierwszego True
                
                # Zachowaj od poprzedniej świeczki (jeśli istnieje)
                if first_idx_in_df > df_for_calc.index[0]:
                    start_idx = first_idx_in_df - 1
                else:
                    start_idx = first_idx_in_df
                
                df_for_calc = df_for_calc.loc[start_idx:].copy()
        
        df_for_calc = df_for_calc.reset_index(drop=True)
        
        #print(f"Po filtrowaniu: {len(df_for_calc)} świeczek, zakres: {df_for_calc.iloc[0]['DateTime']} - {df_for_calc.iloc[-1]['DateTime']}", flush=True)
        
        # Zmienne stanu
        capital = self.initial_capital
        trades = []
        active_trade = None
        equity_curve = []
        
        # Progress tracking
        last_date = None
        days_processed = 0
        
        # Iteruj przez świeczki
        for idx in range(len(df_for_calc)):
            current_row = df_for_calc.iloc[idx]
            
            # Progress update (co nowy dzień)
            current_date = current_row['DateTime'].date()
            if last_date is None or current_date != last_date:
                days_processed += 1
                if days_processed % 10 == 0:  # Co 10 dni
                    _logger.debug(f"Przetworzono {days_processed} dni... ({current_date})")
                last_date = current_date
            
            # Sprawdź czy jest aktywny trade
            if active_trade is not None:
                # Sprawdź exit
                exit_info = strategy.check_exit(df_for_calc, idx, active_trade)
                
                if exit_info:
                    # Zamknij trade
                    trade_result = {
                        **active_trade,
                        **exit_info,
                        'capital_before': capital
                    }
                    
                    # Oblicz position size (fixed risk)
                    risk_amount = capital * (self.risk_per_trade_pct / 100.0)
                    position_size = risk_amount / abs(active_trade['entry_price'] - active_trade['sl_price'])
                    
                    # P&L
                    pnl = exit_info['pips'] * position_size
                    capital += pnl
                    
                    trade_result['position_size'] = position_size
                    trade_result['pnl'] = pnl
                    trade_result['capital_after'] = capital
                    
                    trades.append(trade_result)
                    active_trade = None
            
            else:
                # Szukaj nowego entry
                entry_signal = strategy.should_enter(df_for_calc, idx)
                
                if entry_signal:
                    active_trade = entry_signal.copy()
            
            # Zapisz equity
            equity_curve.append({
                'DateTime': current_row['DateTime'],
                'Capital': capital
            })
        
        # Oblicz statystyki
        stats = self._calculate_stats(trades, equity_curve)
        
        return {
            'trades': trades,
            'equity_curve': pd.DataFrame(equity_curve),
            'stats': stats,
            'df_full': df_for_calc  # Zwróć df z obliczonymi wskaźnikami
        }
    
    def _calculate_stats(self, trades, equity_curve):
        """
        Oblicza statystyki backtestingu
        
        Psychologia każdej metryki:
        - Win Rate: % czasu gdy tłum podążał w naszym kierunku
        - Avg Win/Loss: asymetria greed vs fear
        - Max Drawdown: najgorszy moment stresu/paniki
        - Sharpe: stosunek zysku do stresu
        """
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pips': 0,
                'total_pnl': 0,
                'avg_win_pips': 0,
                'avg_loss_pips': 0,
                'max_drawdown_pct': 0,
                'final_capital': self.initial_capital,
                'return_pct': 0
            }
        
        df_trades = pd.DataFrame(trades)
        
        wins = df_trades[df_trades['result'] == 'TP']
        losses = df_trades[df_trades['result'] == 'SL']
        
        # Equity curve dla drawdown
        df_equity = pd.DataFrame(equity_curve)
        running_max = df_equity['Capital'].expanding().max()
        drawdown = (df_equity['Capital'] - running_max) / running_max * 100
        
        stats = {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / len(trades) * 100) if trades else 0,
            'total_pips': df_trades['pips'].sum(),
            'total_pnl': df_trades['pnl'].sum(),
            'avg_win_pips': wins['pips'].mean() if len(wins) > 0 else 0,
            'avg_loss_pips': losses['pips'].mean() if len(losses) > 0 else 0,
            'avg_win_pnl': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss_pnl': losses['pnl'].mean() if len(losses) > 0 else 0,
            'max_drawdown_pct': drawdown.min(),
            'final_capital': df_equity['Capital'].iloc[-1],
            'return_pct': ((df_equity['Capital'].iloc[-1] - self.initial_capital) / self.initial_capital * 100)
        }
        
        return stats
