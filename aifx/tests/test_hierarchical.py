import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from support_breakout_strategy import SupportBreakoutStrategy

# Wczytaj dane
df = pd.read_csv('FUS100.15.csv', sep='\t')
df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
df = df.rename(columns={
    '<OPEN>': 'Open',
    '<HIGH>': 'High',
    '<LOW>': 'Low',
    '<CLOSE>': 'Close',
    '<TICKVOL>': 'Volume'
})
df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()

# Utwórz strategię i oblicz wskaźniki dla małego podzbioru
df_subset = df[df['DateTime'] >= '2025-10-01'].copy()
strategy = SupportBreakoutStrategy(lookback_days=3, risk_pips=50, reward_ratio=3, min_slope=0.3)
df_calc = strategy.calculate_indicators(df_subset)

print(f'Support data entries: {len(strategy.daily_support_data)}')
print('\nPrzykłady z hierarchicznymi liniami:')
for entry in strategy.daily_support_data[:10]:
    h_supp = entry.get('hierarchical_supports', [])
    h_res = entry.get('hierarchical_resistances', [])
    print(f"  {entry['date']}: {len(h_supp)} wsparć poniżej, {len(h_res)} oporów powyżej")
    if h_supp:
        for supp in h_supp:
            print(f"    - S{supp['level']}: offset={supp['offset']:+.0f}, score={supp['score']}")
    if h_res:
        for res in h_res:
            print(f"    - R{res['level']}: offset={res['offset']:+.0f}, score={res['score']}")
