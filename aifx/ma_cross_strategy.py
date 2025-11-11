import pandas as pd
import numpy as np
from datetime import datetime

class MACrossStrategy:
    """Strategia przecięcia średnich kroczących z R:R 2:5"""
    
    def __init__(self, fast_period=20, slow_period=50, risk_pips=20, reward_ratio=2.5):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.risk_pips = risk_pips  # SL w pipsach
        self.reward_pips = risk_pips * reward_ratio  # TP w pipsach (2:5 = 2.5)
        
    def calculate_indicators(self, df):
        """Oblicza MA dla strategii"""
        df['MA_Fast'] = df['Close'].ewm(span=self.fast_period, adjust=False).mean()
        df['MA_Slow'] = df['Close'].ewm(span=self.slow_period, adjust=False).mean()
        return df
    
    def should_enter(self, df, idx):
        """
        Sprawdza crossing MA:
        - Long: Fast crosses above Slow
        - Short: Fast crosses below Slow
        
        Psychologia: Crossing MA = zmiana sentymentu tłumu, momentum shift
        """
        if idx < self.slow_period + 1:
            return None
            
        current = df.iloc[idx]
        previous = df.iloc[idx - 1]
        
        # Bullish cross - tłum przechodzi w tryb greed
        if previous['MA_Fast'] <= previous['MA_Slow'] and current['MA_Fast'] > current['MA_Slow']:
            entry_price = current['Close']
            sl_price = entry_price - self.risk_pips
            tp_price = entry_price + self.reward_pips
            
            return {
                'direction': 'long',
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'time': current['DateTime'],
                'reason': f'MA Cross UP (Fast: {current["MA_Fast"]:.2f}, Slow: {current["MA_Slow"]:.2f})'
            }
        
        # Bearish cross - tłum przechodzi w tryb fear
        elif previous['MA_Fast'] >= previous['MA_Slow'] and current['MA_Fast'] < current['MA_Slow']:
            entry_price = current['Close']
            sl_price = entry_price + self.risk_pips
            tp_price = entry_price - self.reward_pips
            
            return {
                'direction': 'short',
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'time': current['DateTime'],
                'reason': f'MA Cross DOWN (Fast: {current["MA_Fast"]:.2f}, Slow: {current["MA_Slow"]:.2f})'
            }
        
        return None
    
    def check_exit(self, df, idx, trade):
        """
        Sprawdza czy SL lub TP zostały osiągnięte
        
        Psychologia: Fixed SL/TP eliminuje emocje - decyzja podjęta z góry
        """
        current = df.iloc[idx]
        
        if trade['direction'] == 'long':
            # Check TP (na High świeczki)
            if current['High'] >= trade['tp_price']:
                pips = trade['tp_price'] - trade['entry_price']
                return {
                    'exit_price': trade['tp_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'TP',
                    'reason': 'Take Profit hit'
                }
            # Check SL (na Low świeczki)
            if current['Low'] <= trade['sl_price']:
                pips = trade['sl_price'] - trade['entry_price']
                return {
                    'exit_price': trade['sl_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'SL',
                    'reason': 'Stop Loss hit'
                }
        
        elif trade['direction'] == 'short':
            # Check TP (na Low świeczki)
            if current['Low'] <= trade['tp_price']:
                pips = trade['entry_price'] - trade['tp_price']
                return {
                    'exit_price': trade['tp_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'TP',
                    'reason': 'Take Profit hit'
                }
            # Check SL (na High świeczki)
            if current['High'] >= trade['sl_price']:
                pips = trade['entry_price'] - trade['sl_price']
                return {
                    'exit_price': trade['sl_price'],
                    'exit_time': current['DateTime'],
                    'pips': pips,
                    'result': 'SL',
                    'reason': 'Stop Loss hit'
                }
        
        return None
