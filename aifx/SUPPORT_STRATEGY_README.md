# Support Breakout Strategy - Hierarchiczne Linie Równoległe

## Przegląd

Support Breakout Strategy to zaawansowany system tradingowy wykrywający breakouty powyżej głównej linii wsparcia wraz z **hierarchicznymi liniami równoległymi** (S2, S3, R2, R3).

Główne cechy:
- ✅ Wykrywanie głównej linii wsparcia (S1) z poprzednich N dni
- ✅ **Hierarchiczne linie równoległe** poniżej (S2, S3) i powyżej (R1, R2, R3) głównej
- ✅ Tylko pozycje LONG (breakout powyżej wsparcia)
- ✅ Integracja z `impulse_detector` dla wykrywania impulsów
- ✅ Wizualizacja wszystkich linii z gradientowymi kolorami i opisami

## Hierarchiczne Linie Równoległe

System wykrywa **strukturę równoodległych poziomów** składającą się z:

- **S1**: główna linia wsparcia (czerwona, ciągła, grubość 4)
- **S2, S3**: linie wsparcia PONIŻEJ głównej (darkred, maroon - przerywane/kropkowane)
- **R2, R3**: linie oporu POWYŻEJ głównej (blue, dodgerblue - przerywane/kropkowane)

### Właściwości Hierarchicznych Linii

1. **Równoległość**: wszystkie linie mają identyczny slope (nachylenie)
2. **Przesunięcie pionowe**: każda linia przesunięta o offset (w punktach)
3. **Poziomy**: S2 = poziom 2 poniżej, S3 = poziom 3 poniżej, R2 = poziom 2 powyżej, itd.
4. **Score**: liczba punktów (H/L/impulsy) dotykających linii (minimum 3)

Struktura **NIE jest fraktalną** - to równomierne stepping z odległością d₁, 2×d₁, 3×d₁ (brak samopodobieństwa).

## Użycie

### Podstawowe użycie

```python
from support_breakout_strategy import SupportBreakoutStrategy
import pandas as pd

# Wczytaj dane OHLCV
df = pd.read_csv('data.csv', sep='\t')
df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
df = df.rename(columns={
    '<OPEN>': 'Open',
    '<HIGH>': 'High',
    '<LOW>': 'Low',
    '<CLOSE>': 'Close',
    '<TICKVOL>': 'Volume'
})
df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()

# Utwórz strategię
strategy = SupportBreakoutStrategy(
    lookback_days=3,        # Okno lookback (3 dni)
    risk_pips=50,           # Ryzyko w pipsach
    reward_ratio=3,         # Współczynnik R:R
    min_slope=0.3           # Minimalny slope (tylko wznoszące linie)
)

# Oblicz wskaźniki (wykrywa hierarchiczne linie)
df_calc = strategy.calculate_indicators(df)

# Wyświetl hierarchiczne linie
for entry in strategy.daily_support_data:
    h_supp = entry.get('hierarchical_supports', [])
    h_res = entry.get('hierarchical_resistances', [])
    
    print(f"{entry['date']}: {len(h_supp)} wsparć, {len(h_res)} oporów")
    
    for supp in h_supp:
        print(f"  S{supp['level']}: offset={supp['offset']:+.0f}, score={supp['score']}")
    
    for res in h_res:
        print(f"  R{res['level']}: offset={res['offset']:+.0f}, score={res['score']}")
```

### Generowanie Wykresów

```python
# Generuj wykresy z hierarchicznymi liniami
for entry in strategy.daily_support_data:
    date = entry['date']
    filename = strategy.plot_daily_chart(
        df,
        date,
        output_dir='charts',
        show_volume=True,
        mark_high_low=False  # Znaczniki ekstremów (opcjonalnie)
    )
    print(f"✓ {filename}")
```

### Backtest

```python
from backtest_engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=10000,
    risk_per_trade_pct=2.0
)

results = engine.run(df, strategy, '2025-10-01', '2025-10-20')

print(f"Total Trades: {results['stats']['total_trades']}")
print(f"Win Rate: {results['stats']['win_rate']:.1f}%")
print(f"Total P&L: ${results['stats']['total_pnl']:.2f}")
```

## Struktura Danych

### daily_support_data

Każdy wpis zawiera:

```python
{
    'date': datetime.date,                      # Data analizy
    'slope': float,                             # Nachylenie głównej linii
    'intercept': float,                         # Punkt Y głównej linii
    'support_points': [{'index': int, 'price': float}],  # Punkty głównej linii
    'local_maxima': [{'index': int, 'price': float}],    # Lokalne maksima
    'all_minima': [{'index': int, 'price': float}],      # Lokalne minima
    'impulses': [{'index': int, 'price': float}],        # Impulsy
    'hierarchical_supports': [                  # Linie wsparcia poniżej S1
        {
            'slope': float,                     # Nachylenie (równoległe!)
            'intercept': float,                 # Punkt Y
            'touches': [...],                   # Punkty dotykające
            'offset': float,                    # Odległość pionowa (< 0)
            'score': int,                       # Liczba punktów (>= 3)
            'level': int                        # Numer poziomu (2, 3, 4...)
        }
    ],
    'hierarchical_resistances': [               # Linie oporu powyżej S1
        {
            'slope': float,                     # Nachylenie (równoległe!)
            'intercept': float,                 # Punkt Y
            'touches': [...],                   # Punkty dotykające
            'offset': float,                    # Odległość pionowa (> 0)
            'score': int,                       # Liczba punktów (>= 3)
            'level': int                        # Numer poziomu (2, 3, 4...)
        }
    ],
    'lookback_start_dt': datetime,              # Początek okna lookback
    'lookback_end_dt': datetime,                # Koniec okna lookback
    'day_start_idx': int                        # Index w DataFrame
}
```

## Wizualizacja

Wykresy zawierają:

- **S1**: czerwona linia ciągła (grubość 4) - główna linia wsparcia
- **S2, S3**: ciemno-czerwone linie przerywane/kropkowane (grubość 3/2)
- **R2, R3**: niebieskie linie przerywane/kropkowane (grubość 3/2)
- **Legenda**: etykiety z poziomem, offsetem i score (np. "S2 (-170 pts, 7 p)")
- **Opcjonalnie**: znaczniki lokalnych ekstremów i impulsów (mark_high_low=True)

### Kolory

- Wsparcia: `red` → `darkred` → `maroon` → `brown` → `firebrick`
- Opory: `blue` → `dodgerblue` → `deepskyblue` → `lightskyblue`

## Testy Jednostkowe

Uruchom kompleksowy zestaw testów:

```bash
python test_support_strategy.py
```

Testy weryfikują:
1. ✅ Podstawowe wykrywanie linii wsparcia
2. ✅ Wykrywanie hierarchicznych linii równoległych
3. ✅ Równoległość wszystkich linii (identyczny slope)
4. ✅ Znaki offsetów (wsparcia < 0, opory > 0)
5. ✅ Strukturę danych (wymagane klucze, typy, zakresy)
6. ✅ Generowanie wykresów z hierarchicznymi liniami

## Parametry Strategii

```python
SupportBreakoutStrategy(
    lookback_days=5,        # Liczba dni lookback (domyślnie 5)
    risk_pips=50,           # Ryzyko SL w pipsach (domyślnie 50)
    reward_ratio=3,         # R:R ratio dla TP (domyślnie 3)
    retest_mode=False,      # False=immediate, True=czeka na retest
    retest_tolerance=30,    # Odległość od linii dla retest (pips)
    min_slope=0.1           # Minimalny slope (tylko LONG, slope > 0)
)
```

### Dostrajanie

- **lookback_days**: 3-7 dni (krótszy = więcej linii, dłuższy = stabilniejsze)
- **min_slope**: 0.1-0.5 (wyższy = tylko silne trendy wzrostowe)
- **risk_pips**: 20-100 (zależne od instrumentu i volatility)
- **reward_ratio**: 2-5 (wyższy = większy potencjał, mniej TP)

## Integracja z impulse_detector

Strategia używa `impulse_detector.py` do:
- Wykrywania impulsów (7 kryteriów)
- Znajdowania lokalnych ekstremów
- **Wykrywania hierarchicznych linii równoległych** (`find_hierarchical_parallel_lines()`)

Hierarchiczne linie wykrywane są automatycznie z parametrami:
- `num_levels_below=2` - 2 linie wsparcia poniżej S1
- `num_levels_above=2` - 2 linie oporu powyżej S1
- `tolerance=30` - max odległość punktu od linii (punkty)
- `debug=False` - wyłączone logi debugowe (zbyt dużo outputu)

## Przykładowe Wyniki

Na danych FUS100.15 (październik 2025):

```
2025-10-06: 2 wsparć poniżej, 1 oporów powyżej
  - S2: offset=-170, score=7
  - S3: offset=-70, score=6
  - R2: offset=+60, score=5

2025-10-15: 2 wsparć poniżej, 2 oporów powyżej
  - S2: offset=-100, score=6
  - S3: offset=-260, score=4
  - R2: offset=+60, score=6
  - R3: offset=+60, score=3
```

## Znane Ograniczenia

1. **Forward-looking bias**: weryfikacja patrzy w przyszłość (nie real-time)
2. **Tylko LONG**: nie traduje short positions
3. **Wymaga trendu wzrostowego**: `min_slope > 0`
4. **Performance**: dla dużych zakresów (>10k świec) może być wolne
5. **Tolerance**: wymaga dostrojenia do instrumentu (20-50 pkt dla indeksów)

## TODO

- [ ] Detekcja typu trójkąta (zbieżny vs rozszerzający - szerokość kanału)
- [ ] Filtr: pomiń zbieżne, traduj tylko rozszerzające
- [ ] Walidacja 5 warunków wejścia dla rozszerzającego
- [ ] Real-time mode bez forward-looking bias
- [ ] Optymalizacja performance (vectorization)
- [ ] Export wyników do JSON/CSV

## Licencja

MIT License

## Autor

AI FX Trading System  
Version: 2.0  
Date: 2025-11-12

---

**Podsumowanie**: Support Breakout Strategy z hierarchicznymi liniami równoległymi to zaawansowany system wykrywający strukturę równoodległych poziomów (S1, S2, S3, R2, R3) z wizualizacją, testami i integracją z impulse_detector. Wszystkie linie są równoległe (ten sam slope) i opisane offsetem i score. System gotowy do użycia w backtestingu i analizie technicznej.
