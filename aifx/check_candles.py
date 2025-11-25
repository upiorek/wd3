import pandas as pd
from run_support_backtest import load_data
from datetime import date

df = load_data('FUS100.15_single.csv', 'mbank')
print(f'Lookback candles z config: 60')

df_before = df[df['DateTime'].dt.date <= date(2025, 10, 24)]
print(f'Świeczki przed/włącznie z 2025-10-24: {len(df_before)}')

if len(df_before) >= 60:
    df_plot = df_before.iloc[-60:]
    print(f'Świeczki na wykresie (ostatnie 60): {len(df_plot)}')
    print(f'Zakres: {df_plot.iloc[0]["DateTime"]} - {df_plot.iloc[-1]["DateTime"]}')
    
    # Policz unikalne dni
    unique_days = df_plot['DateTime'].dt.date.nunique()
    print(f'Unikalne dni: {unique_days}')
